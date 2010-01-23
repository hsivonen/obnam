# Copyright (C) 2009  Lars Wirzenius
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import logging
import os
import stat

import obnamlib


class RestorePlugin(obnamlib.ObnamPlugin):

    # A note about the implementation: we need to make sure all the
    # files we restore go into the target directory. We do this by
    # prefixing all filenames we write to with './', and then using
    # os.path.join to put the target directory name at the beginning.
    # The './' business is necessary because os.path.join(a,b) returns
    # just b if b is an absolute path.

    def enable(self):
        self.app.register_command('restore', self.restore)
        
    def restore(self, args):
        fsf = obnamlib.VfsFactory()
        self.store = obnamlib.Store(fsf.new(self.app.config['store']))
        self.store.open_host(self.app.config['hostname'])
        self.fs = fsf.new(args[0])
        
        for genspec in args[1:]:
            gen = self.genid(genspec)
            self.restore_recursively(gen, '.', '/')

    def genid(self, genspec):
        if genspec == 'latest':
            return self.store.list_generations()[-1]
        return genspec
    
    def restore_recursively(self, gen, to_dir, root):
        if not self.fs.exists('./' + root):
            self.fs.makedirs('./' + root)
        for basename in self.store.listdir(gen, root):
            full = os.path.join(root, basename)
            metadata = self.store.get_metadata(gen, full)
            if stat.S_ISDIR(metadata.st_mode):
                self.restore_recursively(gen, to_dir, full)
            else:
                self.restore_file(gen, to_dir, full)
        metadata = self.store.get_metadata(gen, root)
        obnamlib.set_metadata(self.fs, './' + root, metadata)

    def restore_file(self, gen, to_dir, filename):
        metadata = self.store.get_metadata(gen, filename)
        if stat.S_ISLNK(metadata.st_mode):
            self.restore_symlink(gen, to_dir, filename, metadata)
        else:
            self.restore_regular_file(gen, to_dir, filename, metadata)
        
    def restore_symlink(self, gen, to_dir, filename, metadata):
        to_filename = os.path.join(to_dir, './' + filename)
        obnamlib.set_metadata(self.fs, to_filename, metadata)
        
    def restore_regular_file(self, gen, to_dir, filename, metadata):
        to_filename = os.path.join(to_dir, './' + filename)
        f = self.fs.open(to_filename, 'w')

        chunkids = self.store.get_file_chunks(gen, filename)
        if chunkids:
            self.restore_chunks(f, chunkids)
        else:
            cgids = self.store.get_file_chunk_groups(gen, filename)
            for cgid in cgids:
                chunkids = self.store.get_chunk_group(cgid)
                self.restore_chunks(f, chunkids)

        f.close()
        obnamlib.set_metadata(self.fs, to_filename, metadata)

    def restore_chunks(self, f, chunkids):
        for chunkid in chunkids:
            data = self.store.get_chunk(chunkid)
            f.write(data)

