#!/bin/sh

set -e

du -sk "$1/store" > "$1/twogen.size"
