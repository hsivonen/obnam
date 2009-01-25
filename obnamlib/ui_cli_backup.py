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


class BackupCommand(object):

    """A sub-command for the command line interface to back up some data."""

    PART_SIZE = 256 * 1024

    def backup_new_file(self, relative_path):
        """Back up a completely new file."""
        f = self.fs.open(relative_path, "r")
        content = self.store.put_contents(f, self.PART_SIZE)
        f.close()
        return content

    def backup_new_files_as_groups(self, relative_paths):
        """Back a set of new files as a new FILEGROUP."""
        fg = self.store.new_object(kind=obnamlib.FILEGROUP)
        for path in relative_paths:
            fc = self.backup_new_file(path)
            file_component = obnamlib.Component(kind=obnamlib.FILE)
            file_component.children += [
                obnamlib.Component(kind=obnamlib.FILENAME, 
                                   string=os.path.basename(path)),
                obnamlib.Component(kind=obnamlib.CONTREF, string=fc.id),
                ]
            fg.components.append(file_component)
        self.store.put_object(fg)
        return [fg]

    def backup_dir(self, relative_path, subdirs, filenames):
        """Back up a single directory, non-recursively.

        subdirs is a list of obnamlib.Dir objects for the direct
        subdirectories of the target directory. They must have been
        backed up already.

        """

        dir = self.store.new_object(obnamlib.DIR)
        dir.name = os.path.basename(relative_path)
        dir.dirrefs = [x.id for x in subdirs]
        fullnames = [os.path.join(relative_path, x) for x in filenames]
        if filenames:
            dir.fgrefs = [x.id 
                          for x in self.backup_new_files_as_groups(fullnames)]
        else:
            dir.fgrefs = []
        self.store.put_object(dir)
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
