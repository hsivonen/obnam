#!/bin/sh

set -e

n=$(find "$1/store" -type f | 
    xargs ./showblock | 
    grep -c '^ *data: FILECONTENTS$'; 
    true)

if [ "$n" != 1 ]
then
    echo "ERROR: $1/store contains $n file contents objects, not 1" 1>&2
    exit 1
fi
