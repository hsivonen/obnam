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


import logging
import os
import stat

import obnamlib


BLOCK_SIZE = 4096 # A guess, for sftp: its .stat doesn't return st_blocks


class DiskUsageCommand(obnamlib.CommandLineCommand):

    """Command to show disk usage of a backup store."""

    def estimate(self, fs, pathname):
        st = fs.lstat(pathname)
        if hasattr(st, "st_blocks"):
            return st.st_blocks * 512 # posix says st_blocks uses 512 bytes
        else:
            # sftp does not implement st_blocks. We guess the block size
            # and estimate the disk usage from st_size. This is highly
            # error prone, but sufficient for my immediate needs.
            # FIXME: Should get filesystem block size, not hardcode it.
            # FIXME: Should extend sftp to fix this properly.
            nblocks = st.st_size / BLOCK_SIZE
            if st.st_size % BLOCK_SIZE:
                nblocks += 1
            return nblocks * BLOCK_SIZE

    def format_size(self, size):
        return size / 1024

    def disk_usage(self, fs):
        du = 0
        for dirname, dirnames, filenames in fs.depth_first('.'):
            for x in [dirname] + filenames:
                du += self.estimate(fs, x)
        fs.close()
        print self.format_size(du), fs.baseurl

    def run(self, options, args, progress): # pragma: no cover
        fsf = obnamlib.VfsFactory()
        for url in args:
            fs = fsf.new(url, progress)
            fs.connect()
            self.disk_usage(fs)
            fs.close()
        progress.done()
