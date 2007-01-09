#!/bin/sh

if find "$1/store" -type f | xargs ./showblock |
    grep stuff/excluded > /dev/null
then
    echo "ERROR: stuff/excluded got included in backup" 1>&2
    exit 1
fi
