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


import os

import obnamlib


class RestoreCommand(object):

    """Restore files from a generation."""

    def restore_helper(self, filename, st, contref, deltaref):
        f = self.vfs.open(filename, "w")
        self.store.cat(self.host, f, contref, deltaref)
        f.close()

    def restore_file(self, dirname, file):
        basename = file.first_string(kind=obnamlib.FILENAME)
        filename = os.path.join(dirname, basename)

        st = obnamlib.decode_stat(file.first(kind=obnamlib.STAT))
        contref = file.first_string(kind=obnamlib.CONTREF)
        deltaref = file.first_string(kind=obnamlib.DELTAREF)
        
        self.restore_helper(filename, st, contref, deltaref)

    def restore_filename(self, lookupper, filename):
        st, contref, sigref, deltaref = lookupper.get_file(filename)
        self.vfs.makedirs(os.path.dirname(filename))
        self.restore_helper(filename, st, contref, deltaref)

    def restore_dir(self, walker, root):
        for dirname, dirnames, files in walker.walk(root):
            self.vfs.mkdir(dirname)
            for file in files:
                self.restore_file(dirname, file)

    def restore_generation(self, walker):
        for dirname, dirnames, files in walker.walk_generation():
            self.vfs.mkdir(dirname)
            for file in files:
                self.restore_file(dirname, file)

    def restore(self, host_id, genref, roots): # pragma: no cover
        """Restore files and directories (with contents)."""
        
        self.host = self.store.get_host(host_id)
        gen = self.store.get_object(self.host, genref)
        walker = obnamlib.StoreWalker(self.store, self.host, gen)

        if roots:
            lookupper = obnamlib.Lookupper(self.store, self.host, gen)
            for root in roots:
                if lookupper.is_file(root):
                    self.restore_filename(lookupper, root)
                else:
                    self.restore_dir(walker, root)
        else:
            self.restore_generation(walker)
    
    def __call__(self, config, args): # pragma: no cover
        target = args[0]
        host_id = args[1]
        store_url = args[2]
        genref = args[3]
        roots = args[4:]

        self.store = obnamlib.Store(store_url, "r")
        self.vfs = obnamlib.LocalFS(target)

        self.restore(host_id, genref, roots)
