#!/usr/bin/python
#
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


import os
import shutil
import sys
import tempfile


def tar_method(tempdir, rootdir):
    result = os.path.join(tempdir, "tar.tar")
    return result, ["tar", "-C", rootdir, "-cf", result, "."]


def targz_method(tempdir, rootdir):
    result = os.path.join(tempdir, "tar.tar.gz")
    return result, ["tar", "-C", rootdir, "-czf", result, "."]


def rsync_method(tempdir, rootdir):
    result = os.path.join(tempdir, "rsync")
    os.mkdir(result)
    return result, ["rsync", "-aH", "--delete", rootdir, result]


def obnam_method(tempdir, rootdir):
    result = os.path.join(tempdir, "obnam-store")
    return result, ["./cli.py", "--store", result, "-C", rootdir, "backup", "."]


def profiled_obnam_method(tempdir, rootdir):
    result, args = obnam_method(tempdir, rootdir)
    return result, ["/usr/lib/python2.4/profile.py", "-o", "obnam.prof"] \
                    + args


backup_methods = (
    ("tar", tar_method),
    ("targz", targz_method),
    ("rsync", rsync_method),
    ("obnam", obnam_method),
#    ("obnam", profiled_obnam_method),
)


def create_tempdir():
    return tempfile.mkdtemp()


def run_command(argv):
    start = os.times()
    status = os.spawnvp(os.P_WAIT, argv[0], argv)
    finish = os.times()
    if status != 0:
        sys.stderr.write("Command failed (%d): %s\n" % 
                            (status, " ".join(argv)))
        sys.exit(1)
    user = finish[2] - start[2]
    system = finish[3] - start[3]
    real = finish[4] - start[4]
    return user, system, real


def sizeof(file_or_dir):
    if os.path.isdir(file_or_dir):
        size = 0
        for dirpath, dirnames, filenames in os.walk(file_or_dir):
            for filename in filenames:
                filename = os.path.join(dirpath, filename)
                size += os.lstat(filename).st_size
        return size
    else:
        return os.stat(file_or_dir).st_size


def heading():
    return "%-12s %6s %6s %6s %6s" % \
                ("Method", "User", "System", "Real", "MB")


def format(desc, user, system, real, size):
    return "%-12s %6.1f %6.1f %6.1f %6d" % \
                (desc, user, system, real, size/(1024*1024))


def run_testcase(testcase):
    tempdir = create_tempdir()
    rootdir = os.path.join(tempdir, "root")
    os.mkdir(rootdir)

    print "Testcase: " + testcase
    print "==========" + "=" * len(testcase)
    print 
    x = heading()
    print x
    print "-" * len(x)
    
    if testcase.endswith(".tar.bz2"):
        flag = "-j"
    else:
        flag = "-z"
    (user, system, real) = run_command(["tar", "-C", rootdir, 
                                        flag, "-xf", testcase])
    size = sizeof(rootdir)
    print format("Unpacking", user, system, real, size)

    for name, method in backup_methods:
        (result, argv) = method(tempdir, rootdir)
        (user, system, real) = run_command(argv)
        size = sizeof(result)
        print format(name, user, system, real, size)
        run_command(["rm", "-rf", result])
        
    run_command(["rm", "-rf", tempdir])

    print
    

def main():
    for filename in sys.argv[1:]:
        if filename.endswith(".tar.bz2") or filename.endswith(".tar.gz"):
            run_testcase(filename)


if __name__ == "__main__":
    main()
