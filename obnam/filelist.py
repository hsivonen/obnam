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


def create():
    """Create a new, empty file list"""
    return {}


def num_files(fl):
    """Return the number of files in a file list"""
    return len(fl)


def list_files(fl):
    """Return list of all file in the file list currently"""
    return fl.keys()


def add(fl, pathname, contref, sigref, deltaref):
    """Add a file (and its metadata) to a file list"""
    fl[pathname] = create_file_component(pathname, contref, sigref, deltaref)


def add_file_component(fl, pathname, file_cmp):
    """Add a file component to a file list"""
    fl[pathname] = file_cmp


def find(fl, pathname):
    """Get the FILE component that corresponds to a pathname"""
    return fl.get(pathname, None)


def find_matching_inode(fl, pathname, stat_result):
    """Find the FILE component that matches stat_result"""
    prev = find(fl, pathname)
    if prev:
        prev_subs = prev.get_subcomponents()
        prev_stat = obnam.cmp.first_by_kind(prev_subs, obnam.cmp.STAT)
        prev_st = obnam.cmp.parse_stat_component(prev_stat)
        fields = (
            "st_dev",
            "st_ino",
            "st_mode",
            "st_nlink",
            "st_uid",
            "st_gid",
            "st_rdev",
            "st_size",
            "st_blksize",
            "st_blocks",
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


def to_object(fl, object_id):
    """Create an unencoded FILELIST object from a file list"""
    o = obnam.obj.create(object_id, obnam.obj.FILELIST)
    for pathname in fl:
        obnam.obj.add(o, fl[pathname])
    return o


def from_object(o):
    """Create a file list data structure from a backup object"""
    fl = create()
    for file in obnam.obj.find_by_kind(o, obnam.cmp.FILE):
        subs = file.get_subcomponents()
        pathname = obnam.cmp.first_string_by_kind(subs, obnam.cmp.FILENAME)
        fl[pathname] = file
    return fl
