# Small test program to see how fast Python creates files.

import os
import sys
import uuid

FILES_PER_DIR = 200

nfiles = int(sys.argv[1])
nbytes = int(sys.argv[2])

data = "x" * nbytes

dirno = 0
for i in range(nfiles):
    name = str(uuid.uuid4())
    if (i % FILES_PER_DIR) == 0:
        dirno += 1
    dir = "tmp/%d" % dirno
    if not os.path.isdir(dir):
        os.makedirs(dir)
    f = file(dir + "/" + name, "w")
    f.write(data)
    f.close()
