#!/bin/sh

set -e

n=$(find "$1/store" -type f | 
    xargs ./showblock | 
    grep -c '^ *Component: 102 SIGREF$'; 
    true)

if [ "$n" != 1 ]
then
    echo "ERROR: $1/store contains $n SIGREF components, not 1" 1>&2
    exit 1
fi
