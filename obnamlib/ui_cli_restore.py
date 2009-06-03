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


class RestoreCommand(obnamlib.CommandLineCommand):

    """Restore files from a generation."""
    
    def hardlink_key(self, st): # pragma: no cover
        """Return hash key into hardlink lookup table from stat result."""
        return "%d/%d" % (st.st_dev, st.st_ino)

    def restore_helper(self, filename, st, contref, deltaref, target):
        # This is where we handle hard links. The first link is restored
        # normally, but we remember the name of the file we created.
        # For the remaining links, we create a link to the remembered
        # file instead.
        if st.st_nlink > 1 and not stat.S_ISDIR(st.st_mode): # pragma: no cover
            key = self.hardlink_key(st)
            if key in self.hardlinks:
                existing_link = self.hardlinks[key]
                self.vfs.link(existing_link, filename)
                return
            else:
                self.hardlinks[key] = filename

        if stat.S_ISREG(st.st_mode):
            f = self.vfs.open(filename, "w")
            self.store.cat(self.host, f, contref, deltaref)
            f.close()
        elif stat.S_ISLNK(st.st_mode):
            self.vfs.symlink(target, filename)
        if not stat.S_ISLNK(st.st_mode):
            self.vfs.chmod(filename, st.st_mode)
        self.vfs.lutimes(filename, st.st_atime, st.st_mtime)

    def restore_file(self, dirname, file):
        basename = file.first_string(kind=obnamlib.FILENAME)
        filename = os.path.join(dirname, basename)

        st = obnamlib.decode_stat(file.first(kind=obnamlib.STAT))
        contref = file.first_string(kind=obnamlib.CONTREF)
        deltaref = file.first_string(kind=obnamlib.DELTAREF)
        target = file.first_string(kind=obnamlib.SYMLINKTARGET)
        
        self.restore_helper(filename, st, contref, deltaref, target)

    def restore_filename(self, lookupper, filename):
        st, contref, sigref, deltaref, target = lookupper.get_file(filename)
        self.vfs.makedirs(os.path.dirname(filename))
        self.restore_helper(filename, st, contref, deltaref, target)

    def set_dir_stat(self, dirs): # pragma: no cover
        """Set the stat info for some directories."""
        for pathname in dirs:
            stat = self.lookupper.get_dir(pathname).stat
            self.vfs.chmod(pathname, stat.st_mode)
            self.vfs.lutimes(pathname, stat.st_atime, stat.st_mtime)

    def restore_dir(self, walker, root):
        dirs = []
        for dirname, dirnames, files in walker.walk(root):
            logging.info("Restore %s" % dirname)
            self.vfs.mkdir(dirname)
            dirs.insert(0, dirname)
            for file in files:
                self.restore_file(dirname, file)
        self.set_dir_stat(dirs)

    def restore_generation(self, walker):
        logging.info("Restoring generation")
        dirs = []
        for dirname, dirnames, files in walker.walk_generation():
            logging.info("Restore %s" % dirname)
            if not self.vfs.exists(dirname):
                self.vfs.mkdir(dirname)
            dirs.insert(0, dirname)
            for file in files:
                self.restore_file(dirname, file)
        self.set_dir_stat(dirs)

    def restore(self, host_id, genref, roots): # pragma: no cover
        """Restore files and directories (with contents)."""
        
        self.host = self.store.get_host(host_id)
        
        genref = self.host.get_generation_id(genref)
        
        gen = self.store.get_object(self.host, genref)
        walker = obnamlib.StoreWalker(self.store, self.host, gen)
        
        self.hardlinks = {}

        self.lookupper = obnamlib.Lookupper(self.store, self.host, gen)
        if roots:
            for root in roots:
                if self.lookupper.is_file(root):
                    self.restore_filename(lookupper, root)
                else:
                    self.restore_dir(walker, root)
        else:
            self.restore_generation(walker)
    
    def run(self, options, args, progress): # pragma: no cover
        target = args[0]
        roots = args[1:]

        self.store = obnamlib.Store(options.store, "r")
        self.store.transformations = obnamlib.choose_transformations(options)
        self.vfs = obnamlib.VfsFactory().new(target, progress)

        self.restore(options.host, options.generation, roots)
        self.store.close()
        self.vfs.close()
