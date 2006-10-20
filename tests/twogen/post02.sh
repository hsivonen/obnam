#!/bin/sh

set -e

oldsize=$(awk '{ print $1 }' "$1/twogen.size")
newsize=$(du -sk "$1/store" | awk '{ print $1 }')
increase=$(expr "$newsize" - "$oldsize")

# The difference is only a few bytes, so at most two new blocks should
# be written: one with the new file data, and one with the new generation
# object. In disk usage, this should be two files, each occupying one
# disk block, or 4 kB. So the difference in disk usage should be at most
# 8 kB. If it is more, we fail.

case "$increase" in
 [0-8]) exit 0 ;;
 *) echo "Disk usage increase for store is $increase kB, which is bad."
    exit 1 ;;
esac
