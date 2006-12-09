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


import os
import subprocess
import tempfile


def pipeline(*args):
    """Set up a Unix pipeline of processes, given the argv lists
    
    Returns a subprocess.Popen object corresponding to the last process
    in the pipeline.

    """
    
    p = subprocess.Popen(args[0], stdin=None, stdout=subprocess.PIPE)
    for argv in args[1:]:
        p = subprocess.Popen(argv, stdin=p.stdout, stdout=subprocess.PIPE)
    return p


def compute_signature(context, filename):
    """Compute an rsync signature for 'filename'"""
    p = pipeline([context.config.get("backup", "odirect-read"), filename],
                  ["rdiff", "--", "signature", "-", "-"])
    (stdout, stderr) = p.communicate(None)
    if p.returncode == 0:
        return stdout
    else:
        return False


def compute_delta(context, signature, filename):
    """Compute an rsync delta for a file, given signature of old version"""
    (fd, tempname) = tempfile.mkstemp()
    os.write(fd, signature)
    os.close(fd)

    p = pipeline([context.config.get("backup", "odirect-read"), filename],
                  ["rdiff", "--", "delta", tempname, "-", "-"])

    (stdout, stderr) = p.communicate(None)
    os.remove(tempname)
    if p.returncode == 0:
        return stdout
    else:
        return False


def apply_delta(basis_filename, deltadata, new_filename):
    """Apply an rsync delta for a file, to get a new version of it"""
    p = subprocess.Popen(["rdiff", "--", "patch", basis_filename, "-",
                          new_filename],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    (stdout, stderr) = p.communicate(input=deltadata)
    if p.returncode == 0:
        return True
    else:
        return False
