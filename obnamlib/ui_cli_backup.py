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


import logging
import os
import stat

import obnamlib


class DummyLookupper:

    def get_dir(self, name):
        raise obnamlib.NotFound(name)


class BackupCommand(object):

    """A sub-command for the command line interface to back up some data."""

    PART_SIZE = 256 * 1024

    def backup_new_symlink(self, relative_path, stat):
        """Backup a new symlink."""
        target = self.fs.readlink(relative_path)
        fc = obnamlib.File(os.path.basename(relative_path), stat, 
                           symlink_target=target)
        return fc

    def backup_new_other(self, path, st):
        """Backup a new thing that is not a symlink or regular file."""
        return obnamlib.File(os.path.basename(path), st)

    def backup_new_file(self, path, st):
        """Back up a completely new file."""
        
        f = self.fs.open(path, "r")
        content = self.store.put_contents(f, self.PART_SIZE)
        f.close()
        fc = obnamlib.File(os.path.basename(path), st, content.id, None, None)
        return fc

    def backup_new_files_as_groups(self, relative_paths, lstat=None):
        """Back a set of new files as a new FILEGROUP."""
        if lstat is None: # pragma: no cover
            lstat = self.fs.lstat
        fg = self.store.new_object(kind=obnamlib.FILEGROUP)
        for path in relative_paths:
            st = lstat(path)
            fc = None
            if stat.S_ISREG(st.st_mode):
                fc = self.backup_new_file(path, st)
            elif stat.S_ISLNK(st.st_mode):
                fc = self.backup_new_symlink(path, st)
            else:
                fc = self.backup_new_other(path, st)
            fg.components.append(fc)
        self.store.put_object(fg)
        return [fg]

    def new_dir(self, relative_path, st, subdirs, filegroups):
        """Create a new obnamlib.Dir."""
        dir = self.store.new_object(obnamlib.DIR)
        dir.name = os.path.basename(relative_path)
        dir.stat = st
        dir.dirrefs = [x.id for x in subdirs]
        dir.fgrefs = [x.id for x in filegroups]
        self.store.put_object(dir)
        return dir

    def backup_existing_dir(self, prevdir, relative_path, st, subdirs, 
                            filenames):
        """Back up a directory that exists in the previous generation."""

        return self.backup_new_dir(relative_path, st, subdirs, filenames)

    def backup_new_dir(self, relative_path, st, subdirs, filenames):
        """Back up a new directory."""
        fullnames = [os.path.join(relative_path, x) for x in filenames]
        filegroups = self.backup_new_files_as_groups(fullnames)
        return self.new_dir(relative_path, st, subdirs, filegroups)

    def get_dir_in_prevgen(self, relative_path):
        """Return obnamlib.Dir in previous generation, or None."""
        try:
            return self.prevgen_lookupper.get_dir(relative_path)
        except obnamlib.NotFound:
            return None

    def backup_dir(self, relative_path, subdirs, filenames, lstat=None):
        """Back up a single directory, non-recursively.

        subdirs is a list of obnamlib.Dir objects for the direct
        subdirectories of the target directory. They must have been
        backed up already.

        """

        if lstat is None: # pragma: no cover
            lstat = self.fs.lstat
        st = lstat(relative_path)

        prevdir = self.get_dir_in_prevgen(relative_path)
        if prevdir:
            dir = self.backup_existing_dir(prevdir, relative_path, st,
                                           subdirs, filenames)
        else:
            dir = self.backup_new_dir(relative_path, st, subdirs, filenames)

        return dir

    def backup_recursively(self, root):
        """Back up a directory, recursively."""

        # We traverse the directory tree depth-first. When we get to a
        # directory, we need to know its subdirectories. We keep them
        # in this dict, which is indexed by the directory pathname.
        # The value is a list of obnamlib.Dir objects.
        subdirs = {}

        for dirname, dirnames, filenames in self.fs.depth_first(root):
            list = subdirs.pop(dirname, [])
            dir = self.backup_dir(dirname, list, filenames)
            if dirname == root:
                root_object = dir
            else:
                parent = os.path.dirname(dirname)
                subdirs[parent] = subdirs.get(parent, []) + [dir]

        return root_object

    def backup_generation(self, roots):
        """Back up a generation."""

        gen = self.store.new_object(obnamlib.GEN)

        dirs = [x for x in roots if self.fs.isdir(x)]
        nondirs = [x for x in roots if x not in dirs]

        for root in dirs:
            gen.dirrefs.append(self.backup_recursively(root).id)

        gen.fgrefs += [x.id for x in self.backup_new_files_as_groups(nondirs)]

        self.store.put_object(gen)

        return gen

    def backup(self, host_id, roots):
        host = self.store.get_host(host_id)
        if host.genrefs: # pragma: no cover
            prevgen = host.genrefs[-1]
            self.prevgen_lookupper = obnamlib.Lookupper(self.store, host, 
                                                        prevgen)
        else:
            self.prevgen_lookupper = DummyLookupper()
        gen = self.backup_generation(roots)
        host.genrefs.append(gen.id)
        self.store.commit(host)

    def __call__(self, config, args): # pragma: no cover
        host_id = args[0]
        store_url = args[1]
        roots = args[2:]

        self.store = obnamlib.Store(store_url, "w")
        self.fs = obnamlib.LocalFS("/")

        roots = [os.path.abspath(root) for root in roots]
        self.backup(host_id, roots)
