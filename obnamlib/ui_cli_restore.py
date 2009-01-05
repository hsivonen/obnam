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


class RestoreCommand(object):

    """A restore command for the command line."""

    def setup(self, store_url, host_id, gen_id, target):
        """Set things up for running other parts of this class."""
        
        self.store = obnamlib.Store(store_url, "w")
        self.host = self.store.get_host(host_id)
        self.gen = self.store.get_object(self.host, gen_id)
        self.lookupper = obnamlib.Lookupper(self.store, self.host, self.gen)
        self.target = target
        self.fs = obnamlib.LocalFS(target)

    def target_name(self, pathname):
        """Construct the name of an output file in the target directory."""
        if os.path.isabs(pathname):
            drive, pathname = os.path.splitdrive(pathname)
            pathname = "." + pathname
        return os.path.normpath(os.path.join(self.target, pathname))

    def restore(self, paths, target):
        """Restore files from backup to a target directory."""
        
    def __call__(self, config, args):
        host_id = args[0]
        store_url = args[1]
        gen_id = args[2]
        target = args[3]
        paths = args[4:]

        self.setup(store_url, host_id, gen_id, target)

#        self.restore(target, paths)
