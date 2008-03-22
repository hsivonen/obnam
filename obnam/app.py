# Copyright (C) 2008  Lars Wirzenius <liw@iki.fi>
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


"""Main program for Obnam."""


import logging
import os
import re

import obnam



# Maximum number of files per file group we create.
MAX_PER_FILEGROUP = 16


class Application:

    """Main program logic for Obnam, a backup application."""

    def __init__(self, context):
        self._roots = []
        self._context = context
        self._exclusion_strings = []
        self._exclusion_regexps = []
        self._filelist = None

    def get_context(self):
        """Get the context for the backup application."""
        return self._context

    def add_root(self, root):
        """Add a file or directory to list of backup roots."""
        self._roots.append(root)

    def get_roots(self):
        """Return current set of roots to be backed up."""
        return self._roots

    def get_exclusion_regexps(self):
        """Return list of regexp to exclude things from backup."""
        
        config = self.get_context().config
        strings = config.get("backup", "exclude")
        if self._exclusion_strings != strings:
            for string in strings:
                logging.debug("Compiling exclusion pattern '%s'" % string)
                self._exclusion_regexps.append(re.compile(string))
        
        return self._exclusion_regexps

    def prune(self, dirname, dirnames, filenames):
        """Remove excluded items from dirnames and filenames.
        
        Because this is called by obnam.walk.depth_first, the lists
        are modified in place.
        
        """
        
        self._prune_one_list(dirname, dirnames)
        self._prune_one_list(dirname, filenames)

    def _prune_one_list(self, dirname, basenames):
        """Prune one list of basenames based on exlusion list.
        
        Because this is called from self.prune, the list is modified
        in place.
        
        """

        i = 0
        while i < len(basenames):
            path = os.path.join(dirname, basenames[i])
            for regexp in self.get_exclusion_regexps():
                if regexp.search(path):
                    del basenames[i]
                    break
            else:
                i += 1

    def set_prevgen_filelist(self, filelist):
        """Set the Filelist object from the previous generation.
        
        This is used when looking up files in previous generations. We
        only look at one generation's Filelist, since they're big. Note
        that Filelist objects are the _old_ way of storing file meta
        data, and we will no use better ways that let us look further
        back in history.
        
        """
        
        self._filelist = filelist

    def find_file_by_name(self, filename):
        """Find a backed up file given its filename.
        
        Return tuple (STAT, CONTREF, SIGREF, DELTAREF), where the
        references may be None, or None instead of the entire tuple
        if no file with the given name could be found.
        
        """
        
        if self._filelist:
            fc = self._filelist.find(filename)
            if fc != None:
                subs = fc.get_subcomponents()
                stat = obnam.cmp.first_by_kind(subs, obnam.cmp.STAT)
                cont = obnam.cmp.first_string_by_kind(subs, obnam.cmp.CONTREF)
                sig = obnam.cmp.first_string_by_kind(subs, obnam.cmp.SIGREF)
                d = obnam.cmp.first_string_by_kind(subs, obnam.cmp.DELTAREF)
                return obnam.cmp.parse_stat_component(stat), cont, sig, d
        
        return None

    def make_filegroups(self, filenames):
        """Make list of new FILEGROUP objects.
        
        Return list of object identifiers to the FILEGROUP objects.
        
        """

        list = []
        for filename in filenames:
            if (not list or
                len(list[-1].get_files()) >= MAX_PER_FILEGROUP):
                id = obnam.obj.object_id_new()
                list.append(obnam.obj.FileGroupObject(id=id))
            stat = os.stat(filename)
            contref = None
            sigref = None
            deltaref = None
            list[-1].add_file(filename, stat, contref, sigref, deltaref)
                
        return list
