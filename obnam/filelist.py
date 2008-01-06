# Copyright (C) 2006  Lars Wirzenius <liw@iki.fi>
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


"""List of files in a backup generation"""


import os


import obnam


def create_file_component(pathname, contref, sigref, deltaref):
    """Create a FILE component for a given pathname (and metadata)"""
    return create_file_component_from_stat(pathname, os.lstat(pathname), 
                                           contref, sigref, deltaref)


def create_file_component_from_stat(pathname, st, contref, sigref, deltaref):
    """Create a FILE component given pathname, stat results, etc"""
    subs = []
    
    subs.append(obnam.cmp.Component(obnam.cmp.FILENAME, pathname))
    
    subs.append(obnam.cmp.create_stat_component(st))

    if contref:
        subs.append(obnam.cmp.Component(obnam.cmp.CONTREF, contref))
    if sigref:
        subs.append(obnam.cmp.Component(obnam.cmp.SIGREF, sigref))
    if deltaref:
        subs.append(obnam.cmp.Component(obnam.cmp.DELTAREF, deltaref))

    return obnam.cmp.Component(obnam.cmp.FILE, subs)


class Filelist:

    """Handle the metadata for one generation of backups"""

    def __init__(self):
        self.dict = {}

    def num_files(self):
        """Return the number of files in a file list"""
        return len(self.dict)
    
    def list_files(self):
        """Return list of all file in the file list currently"""
        return self.dict.keys()

    def add(self, pathname, contref, sigref, deltaref):
        """Add a file (and its metadata) to a file list"""
        self.dict[pathname] = create_file_component(pathname, 
                                                    contref, 
                                                    sigref, 
                                                    deltaref)

    def add_file_component(self, pathname, file_cmp):
        """Add a file component to a file list"""
        self.dict[pathname] = file_cmp

    def find(self, pathname):
        """Get the FILE component that corresponds to a pathname"""
        return self.dict.get(pathname, None)

    def find_matching_inode(self, pathname, stat_result):
        """Find the FILE component that matches stat_result"""
        prev = self.find(pathname)
        if prev:
            prev_subs = prev.get_subcomponents()
            prev_stat = obnam.cmp.first_by_kind(prev_subs, obnam.cmp.STAT)
            prev_st = obnam.cmp.parse_stat_component(prev_stat)
            fields = (
                "st_dev",
                "st_mode",
                "st_nlink",
                "st_uid",
                "st_gid",
                "st_size",
                "st_mtime",
                # No atime or ctime, on purpose. They can be changed without
                # requiring a new backup.
            )
            for field in fields:
                a_value = stat_result.__getattribute__(field)
                b_value = prev_st.__getattribute__(field)
                if a_value != b_value:
                    return None
            return prev
        else:
            return None

    def to_object(self, object_id):
        """Create an unencoded FILELIST object from a file list"""
        o = obnam.obj.FileListObject(id=object_id)
        for pathname in self.dict:
            o.add(self.dict[pathname])
        return o

    def from_object(self, o):
        """Add to file list data from a backup object"""
        for file in o.find_by_kind(obnam.cmp.FILE):
            subs = file.get_subcomponents()
            pathname = obnam.cmp.first_string_by_kind(subs, 
                                                      obnam.cmp.FILENAME)
            self.dict[pathname] = file
