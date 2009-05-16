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

import obnamlib


class StoreWalker(object):

    """Walk a directory structure in a store."""
    
    def __init__(self, store, host, gen):
        self.store = store
        self.host = host
        self.gen = gen
        self.lookupper = obnamlib.Lookupper(store, host, gen)
        self._root_dirs = None
        self._root_files = None

    @property
    def root_dirs(self):
        if self._root_dirs is None:
            self._root_dirs = self.get_root_dirs()
        return self._root_dirs

    def get_root_dirs(self):
        """Return names of all root directories in a generation."""
        
        list = []
        for dirref in self.gen.dirrefs:
            dir = self.store.get_object(self.host, dirref)
            list.append(dir.name)
        return list

    @property
    def root_files(self):
        if self._root_files is None:
            self._root_files = self.get_root_files()
        return self._root_files

    def get_root_files(self):
        """Return FILE components of all root files in a generation."""
        
        list = []
        for fgref in self.gen.fgrefs:
            fg = self.store.get_object(self.host, fgref)
            list += fg.files
        return list

    def find_dirnames(self, dir):
        """Find names of subdirectories of dir."""
        
        names = []
        
        for dirref in dir.dirrefs:
            subdir = self.store.get_object(self.host, dirref)
            names.append(subdir.name)
        
        return names

    def find_files(self, dir):
        """Find FILE components of non-directories in dir."""
        
        list = []
        
        for fgref in dir.fgrefs:
            fg = self.store.get_object(self.host, fgref)
            list += fg.files
        
        return list
        
    def walk(self, root):
        """Similar to os.walk, but walk a backed up directory tree.
        
        'root' is a pathname. It must refer to a directory, and will
        be looked up.
        
        Returns a generator that yields, for each directory, a tuple:
            
            dirpath, dirnames, filenames
        
        """
        
        logging.debug("walker.walk: root=%s" % repr(root))
        if self.lookupper.is_file(root):
            raise obnamlib.Exception("%s must be a directory" % root)

        dir = self.lookupper.get_dir(root)
        dirnames = self.find_dirnames(dir)
        files = self.find_files(dir)
        
        yield root, dirnames, files

        for dirname in dirnames:
            full_name = os.path.join(root, dirname)
            for x in self.walk(full_name):
                yield x

    def walk_generation(self):
        """Walk through the entire generation.
        
        This is a helper method to call the walk method for every root.
        In addition, the files at the root of the generation are returned
        with a fake "." directory.
        
        """
        
        if self.root_files:
            logging.debug("walk_generation: root_files=%s" % 
                          repr(self.root_files))
            yield ".", [], self.root_files
            
        for dirname in self.root_dirs:
            logging.debug("walk_generation: dirname=%s" % repr(dirname))
            for x in self.walk(dirname):
                yield x
