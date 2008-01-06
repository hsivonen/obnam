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


class UnknownCommand(obnam.exception.ExceptionBase):

    def __init__(self, argv, errno):
        self._msg = "Unknown command (error %d): %s" % (errno, " ".join(argv))


class CommandFailure(obnam.exception.ExceptionBase):

    def __init__(self, argv, returncode, stderr):
        self._msg = "Command failed: %s\nError code: %d\n%s" % \
                    (" ".join(argv), 
                     returncode, 
                     obnam.gpg.indent_string(stderr))


def run_command(argv):
    try:
        p = subprocess.Popen(argv, stdout=subprocess.PIPE, 
                             stderr=subprocess.PIPE)
    except os.error, e:
        raise UnknownCommand(argv, e.errno)
    return p


def compute_signature(context, filename):
    """Compute an rsync signature for 'filename'"""

    argv = [context.config.get("backup", "odirect-pipe"),
            context.config.get("backup", "odirect-read"),
            filename,
            "rdiff", "--", "signature", "-", "-"]
    p = run_command(argv)
    stdout_data, stderr_data = p.communicate()
    
    if p.returncode == 0:
        return stdout_data
    else:
        raise CommandFailure(argv, p.returncode, stderr_data)


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
    p = run_command(argv)

    list = []
    block_size = context.config.getint("backup", "block-size")
    while True:
        data = p.stdout.read(block_size)
        if not data:
            break
        id = obnam.obj.object_id_new()
        o = obnam.obj.DeltaPartObject(id=id)
        o.add(obnam.cmp.Component(obnam.cmp.DELTADATA, data))
        o = o.encode()
        obnam.io.enqueue_object(context, context.content_oq, 
                                context.contmap, id, o, False)
        list.append(id)
    exit = p.wait()
    os.remove(tempname)
    if exit == 0:
        return list
    else:
        raise CommandFailure(argv, exit, "")


def apply_delta(context, basis_filename, deltapart_ids, new_filename):
    """Apply an rsync delta for a file, to get a new version of it"""
    
    devnull = os.open("/dev/null", os.O_WRONLY)
    if devnull == -1:
        return False

    argv = ["rdiff", "--", "patch", basis_filename, "-", new_filename]
    try:
        p = subprocess.Popen(argv,
                             stdin=subprocess.PIPE, stdout=devnull,
                             stderr=subprocess.PIPE)
    except os.error, e:
        raise UnknownCommand(argv, e.errno)

    ret = True
    for id in deltapart_ids:
        deltapart = obnam.io.get_object(context, id)
        if deltapart:
            deltadata = deltapart.first_string_by_kind(obnam.cmp.DELTADATA)
            p.stdin.write(deltadata)
        else:
            assert 0
            ret = False

    stdout_data, stderr_data = p.communicate(input="")
    os.close(devnull)
    if p.returncode != 0:
        raise CommandFailed(argv, p.returncode, stderr_data)
    else:
        return ret
