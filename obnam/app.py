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


class Application:

    """Main program logic for Obnam, a backup application."""

    def __init__(self, context):
        self._roots = []
        self._context = context
        self._exclusion_strings = []
        self._exclusion_regexps = []

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
