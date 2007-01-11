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


def start_process(argv, stdin_fd, stdout_fd):
    """Start a new process, using stdin/out_fd for its standard in/out"""
    logging.debug("Starting process: %s" % argv)
    pid = os.fork()
    if pid == -1:
        raise Exception("fork failed")
    elif pid == 0:
        devnull_fd = os.open("/dev/null", os.O_RDWR)
        os.dup2(stdin_fd, 0)
        os.dup2(stdout_fd, 1)
#        os.dup2(devnull_fd, 2)
        os.close(stdin_fd)
        os.close(stdout_fd)
        os.close(devnull_fd)
        os.execvp(argv[0], argv)
        os._exit(os.EX_NOTFOUND)
    else:
        return pid

def start_pipeline(*argvlist):
    """Start a Unix pipeline, given list of argv arrays
    
    Return list of pids for the processes in the pipeline, a file descriptor
    from which the first process reads its standard input, and a file
    descriptor to which the last process writes it standard output.

    """

    assert len(argvlist) > 0

    pipe = os.pipe()
    stdin_fd = pipe[1]
    pids = []

    for argv in argvlist:
        new_pipe = os.pipe()
        pids.append(start_process(argv, pipe[0], new_pipe[1]))
        os.close(pipe[0])
        os.close(new_pipe[1])
        pipe = new_pipe

    return pids, stdin_fd, pipe[0]


def wait_pipeline(pids):
    """Wait for all processes in a list to die, return exit code of last"""
    exit = None
    for pid in pids:
        (_, exit) = os.waitpid(pid, 0)
    return exit


def read_until_eof(fd):
    """Read from a file descriptor until the end of the file"""
    data = ""
    while True:
        chunk = os.read(fd, 64 * 1024)
        if not chunk:
            break
        data += chunk
    return data


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
        o = obnam.obj.create(id, obnam.obj.DELTAPART)
        obnam.obj.add(o, obnam.cmp.create(obnam.cmp.DELTADATA, data))
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
            deltadata = obnam.obj.first_string_by_kind(deltapart,
                                                       obnam.cmp.DELTADATA)
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
