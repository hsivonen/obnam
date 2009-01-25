# obnamlib/__init__.py
#
# Copyright (C) 2008  Lars Wirzenius <liw@liw.fi>
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

import obnamlib


def make_stat(st_mode=0, st_ino=0, st_dev=0, st_nlink=0, st_uid=0,
              st_gid=0, st_size=0, st_atime=0, st_mtime=0, st_ctime=0,
              st_blocks=0, st_blksize=0, st_rdev=0):

    """Construct a new stat_result object with the given field values."""

    dict = {
        "st_mode": st_mode,
        "st_ino": st_ino,
        "st_dev": st_dev,
        "st_nlink": st_nlink,
        "st_uid": st_uid,
        "st_gid": st_gid,
        "st_size": st_size,
        "st_atime": st_atime,
        "st_mtime": st_mtime,
        "st_ctime": st_ctime,
        "st_blocks": st_blocks,
        "st_blksize": st_blksize,
        "st_rdev": st_rdev,
    }
    
    tup = (st_mode, st_ino, st_dev, st_nlink, st_uid, st_gid, st_size,
           st_atime, st_mtime, st_ctime)

    return os.stat_result(tup, dict)

def encode_stat(stat):
    """Encode a stat_result as a Component."""
    encoded_value = obnamlib.varint.encode_many([stat.st_mode, 
                                                 stat.st_ino,
                                                 stat.st_dev, 
                                                 stat.st_nlink, 
                                                 stat.st_uid, 
                                                 stat.st_gid, 
                                                 stat.st_size,
                                                 stat.st_atime, 
                                                 stat.st_mtime, 
                                                 stat.st_ctime, 
                                                 stat.st_blocks,
                                                 stat.st_blksize, 
                                                 stat.st_rdev])
    return obnamlib.Component(kind=obnamlib.STAT, string=encoded_value)

def decode_stat(encoded_stat):
    """Decode a Component of kind STAT to a stat_result."""
    
    (st_mode, st_ino, st_dev, st_nlink, st_uid, st_gid,
     st_size, st_atime, st_mtime, st_ctime, st_blocks, st_blksize, 
     st_rdev) = obnamlib.varint.decode_many(encoded_stat.string)
    return obnamlib.make_stat(st_mode=st_mode,
                              st_ino=st_ino,
                              st_dev=st_dev,
                              st_nlink=st_nlink,
                              st_uid=st_uid,
                              st_gid=st_gid,
                              st_size=st_size,
                              st_atime=st_atime,
                              st_mtime=st_mtime,
                              st_ctime=st_ctime,
                              st_blocks=st_blocks,
                              st_blksize=st_blksize,
                              st_rdev=st_rdev)
