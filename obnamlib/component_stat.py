# Copyright (C) 2009  Lars Wirzenius <liw@liw.fi>
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


import obnamlib


class Stat(obnamlib.StringComponent):

    string_kind = obnamlib.STAT

    def __init__(self, stat):
        encoded = obnamlib.varint.encode_many([stat.st_mode,
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
        obnamlib.StringComponent.__init__(self, encoded)

    @property
    def stat(self):
        (st_mode, st_ino, st_dev, st_nlink, st_uid, st_gid,
         st_size, st_atime, st_mtime, st_ctime, st_blocks, st_blksize, 
         st_rdev) = obnamlib.varint.decode_many(str(self))
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
