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

import obnamlib


class Lookupper(object):

    """Look up things in a specific generation."""
    
    def __init__(self, store, host, gen):
        self.store = store
        self.host = host
        self.gen = gen
        
    def split(self, pathname):
        """Split a pathname into its parts.
        
        Parts are separated by os.sep. The root directory (os.sep)
        is also a part.
        
        This assumes Unix filename semantics: os.sep is used also
        for root directory.
        
        """
        
        parts = pathname.split(os.sep)
        if pathname.startswith(os.sep):
            parts = [os.sep] + parts
        parts = [part for part in parts if part]

        return parts
        
    def get_file_in_filegroups(self, basename, fgrefs):
        """Look up the meta data for a file in a set of file groups.
        
        This is similar to get_file, but a) takes only the basename
        and b) looks it up in a set of FILEGROUP objects. Return
        value is the same as for get_file, as is the way failure
        to find is handled.
        
        """

        for fgref in fgrefs:
            logging.debug("get_file_in_filegroups: fgref=%s" % fgref)
            fg = self.store.get_object(self.host, fgref)
            if basename in fg.names:
                return fg.get_file(basename)
        
        raise obnamlib.NotFound("Cannot find %s in filegroups %s" %
                                (basename, ", ".join(fgrefs)))
        
    def get_file(self, pathname):
        """Look up the meta data for a file.
        
        Return tuple (stat_result, content reference, signature
        reference, delta reference), where the three references are
        either None or the string value of the corresponding component.
        
        If not found, the NotFound exception is raised.
        
        """
        
        parts = self.split(pathname)
        
        if len(parts) == 1:
            return self.get_file_in_filegroups(parts[0], self.gen.fgrefs)
        else:
            dir = self.get_dir_in_dirrefs(pathname, parts[:-1], 
                                          self.gen.dirrefs)
            return self.get_file_in_filegroups(parts[-1], dir.fgrefs)

    def get_dir_in_dirrefs(self, pathname, parts, dirrefs):
        """Find a directory in a list of directory references.
        
        pathname is the original pathname, parts is what we actually use
        to look things up. pathname is only used for error reporting.
        
        """
        
        assert parts, "parts is '%s', should be non-empty" % repr(parts)

        for dirref in dirrefs:
            dir = self.store.get_object(self.host, dirref)
            if dir.name == parts[0]:
                if len(parts) == 1:
                    return dir
                else:
                    return self.get_dir_in_dirrefs(pathname, parts[1:],
                                                   dir.dirrefs)
        
        raise obnamlib.NotFound("Cannot find %s in store" % pathname)
        
    def get_dir(self, pathname):
        """Look up the meta data for a directory.
        
        Return an obnamlib.Dir object.
        
        """

        parts = self.split(pathname)

        return self.get_dir_in_dirrefs(pathname, parts, self.gen.dirrefs)

    def is_file(self, pathname):
        """Is a filesystem entity a non-directory file?
        
        Return True for non-directories (regular files, device nodes,
        etc), and False for directories. Raise NotFound if it doesn't
        exist at all.
        
        """
        
        try:
            meta = self.get_file(pathname)
            return True
        except obnamlib.NotFound:
            meta = self.get_dir(pathname)
            return False
