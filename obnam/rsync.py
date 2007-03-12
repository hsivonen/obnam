# Copyright (C) 2006  Lars Wirzenius <liw@iki.fi>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


"""Rsync stuff for making backups"""


import logging
import os
import subprocess
import tempfile


import obnam


def compute_signature(context, filename):
    """Compute an rsync signature for 'filename'"""

    argv = [context.config.get("backup", "odirect-pipe"),
            context.config.get("backup", "odirect-read"),
            filename,
            "rdiff", "--", "signature", "-", "-"]
    p = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout_data, stderr_data = p.communicate()
    
    if p.returncode == 0:
        return stdout_data
    else:
        return False


def compute_delta(context, signature, filename):
    """Compute an rsync delta for a file, given signature of old version
    
    Return list of ids of DELTAPART objects.
    
    """

    (fd, tempname) = tempfile.mkstemp()
    os.write(fd, signature)
    os.close(fd)

    argv = [context.config.get("backup", "odirect-pipe"),
            context.config.get("backup", "odirect-read"),
            filename,
            "rdiff", "--", "delta", tempname, "-", "-"]
    p = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    list = []
    block_size = context.config.getint("backup", "block-size")
    while True:
        data = p.stdout.read(block_size)
        if not data:
            break
        id = obnam.obj.object_id_new()
        o = obnam.obj.Object(id, obnam.obj.DELTAPART)
        o.add(obnam.cmp.Component(obnam.cmp.DELTADATA, data))
        o = obnam.obj.encode(o)
        obnam.io.enqueue_object(context, context.content_oq, 
                                context.contmap, id, o)
        list.append(id)
    exit = p.wait()
    os.remove(tempname)
    if exit == 0:
        return list
    else:
        return False


def apply_delta(context, basis_filename, deltapart_ids, new_filename):
    """Apply an rsync delta for a file, to get a new version of it"""
    
    devnull = os.open("/dev/null", os.O_WRONLY)
    if devnull == -1:
        return False

    p = subprocess.Popen(["rdiff", "--", "patch", basis_filename, "-",
                          new_filename],
                         stdin=subprocess.PIPE, stdout=devnull,
                         stderr=subprocess.PIPE)

    ret = True
    for id in deltapart_ids:
        deltapart = obnam.io.get_object(context, id)
        if deltapart:
            deltadata = deltapart.first_string_by_kind(obnam.cmp.DELTADATA)
            p.stdin.write(deltadata)
        else:
            assert 0
            ret = False

    p.communicate(input="")
    os.close(devnull)
    if ret and p.returncode == 0:
        return True
    else:
        return False
