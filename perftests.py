#!/usr/bin/python


import os
import shutil
import sys
import tempfile


def tar_method(tempdir, rootdir, testcase):
    result = os.path.join(tempdir, "tar.tar")
    return result, ["tar", "-C", rootdir, "-cf", result, "."]


def targz_method(tempdir, rootdir, testcase):
    result = os.path.join(tempdir, "tar.tar.gz")
    return result, ["tar", "-C", rootdir, "-czf", result, "."]


def obnam(tempdir, rootdir, testcase):
    result = os.path.join(tempdir, "obnam-store")
    return result, ["./obnam", "--block-store", result, rootdir]


backup_methods = (
    ("tar", tar_method),
    ("targz", targz_method),
    ("obnam", obnam_method),
)


def create_tempdir():
    return tempfile.mkdtemp()


import time
_start_of_program = time.time()
def time_offset():
    return "%.2f" % (time.time() - _start_of_program)


def run_command(argv):
    print "Starting command:", argv
    print "Time offset since start of program:", time_offset()
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
    print "Command finished, time offset is now:", time_offset()
    print
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


def format(desc, user, system, real, size):
    return """\
Operation: %s
User mode CPU: %.2f
System mode CPU: %.2f
Real time: %.2f
Size: %d bytes
""" % (desc, user, system, real, size)


def get_diskstats():
    diskstats = {}
    f = file("/proc/diskstats", "r")
    for line in f:
        fields = line.split()
        diskstats[fields[0] + ":" + fields[1]] = fields
    f.close()
    return diskstats


# Descriptions of fields in /proc/diskstats
field_desc = (
    "# of reads issued",
    "# of reads merged",
    "# of sectors read",
    "# of milliseconds spent reading",
    "# of writes completed",
    "# of writes merged",
    "# of sectors written",
    "# of milliseconds spent writing",
    "# of I/Os currently in progress",
    "# of milliseconds spent doing I/Os",
    "weighed # of milliseconds spent doing I/Os",
)


# Read Documentation/iostats.txt in the Linux kernel source tree.
def report_diskstats_change(ds1, ds2):
    list = []
    for key in ds2:
        if key in ds1:
            fields1 = ds1[key][3:]
            fields2 = ds2[key][3:]
            if len(fields1) == 11 and len(fields2) == 11:
                deltas = []
                for i in range(11):
                    delta = int(fields2[i]) - int(fields1[i])
                    if delta:
                        deltas.append((i, delta))
                if deltas:
                    list.append((key, deltas))
    if list:
        print "Disk stats changes:"
        for disk, deltas in list:
            print "Disk:", disk
            for i, delta in deltas:
                print "  ", field_desc[i] + ":", delta
    else:
        print "No changes to disk stats"    
    print


def run_testcase(testcase):
    tempdir = create_tempdir()
    rootdir = os.path.join(tempdir, "root")
    os.mkdir(rootdir)

    print "Testcase:", testcase
    print "-------------------------------------------------------"
    print 
    sys.stdout.flush()

    if testcase.endswith(".tar.bz2"):
        flag = "-j"
    else:
        flag = "-z"
    (user, system, real) = run_command(["tar", "-C", rootdir, 
                                        flag, "-xf", testcase])
    size = sizeof(rootdir)
    print format("Unpacking", user, system, real, size)
    sys.stdout.flush()

    for name, method in backup_methods:
        (result, argv) = method(tempdir, rootdir, testcase)
        diskstats1 = get_diskstats()
        (user, system, real) = run_command(argv)
        diskstats2 = get_diskstats()
        size = sizeof(result)
        print format(name, user, system, real, size)
        report_diskstats_change(diskstats1, diskstats2)
        run_command(["rm", "-rf", result])
        sys.stdout.flush()

    run_command(["rm", "-rf", tempdir])

    print
    

def main():
    print "Wibbr perftests starting."
    print "========================="
    print
    print "Time at start:", time.strftime("%Y-%m-%d %H:%M:%S")
    print
    
    for dirname in sys.argv[1:]:
        for filename in os.listdir(dirname):
            if filename.endswith(".tar.bz2") or filename.endswith(".tar.gz"):
                testcase = os.path.join(dirname, filename)
                run_testcase(testcase)

    print "Time at end:", time.strftime("%Y-%m-%d %H:%M:%S")


if __name__ == "__main__":
    main()
