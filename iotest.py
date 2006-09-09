# Small test program to see how fast Python creates files.

import os
import sys
import uuid

nfiles = int(sys.argv[1])
nbytes = int(sys.argv[2])

data = "x" * nbytes

for i in range(nfiles):
    name = str(uuid.uuid4())
    dir = "tmp/" + "/".join(name[:3])
    if not os.path.isdir(dir):
        os.makedirs(dir)
    f = file(dir + "/" + name, "w")
    f.write(data)
    f.close()
