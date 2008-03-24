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


"""Format data for presentation"""


import stat
import time


import obnam


def permissions(mode):
    """Return a string like "ls -l" to indicate the permissions"""

    ru = wu = xu = rg = wg = xg = ro = wo = xo = "-"

    if mode & stat.S_IRUSR:
        ru = "r"
    if mode & stat.S_IWUSR:
        wu = "w"
    if mode & stat.S_IXUSR:
        xu = "x"
    if mode & stat.S_ISUID:
        if mode & stat.S_IXUSR:
            xu = "s"
        else:
            xu = "S"

    if mode & stat.S_IRGRP:
        rg = "r"
    if mode & stat.S_IWGRP:
        wg = "w"
    if mode & stat.S_IXGRP:
        xg = "x"
    if mode & stat.S_ISGID:
        if mode & stat.S_IXGRP:
            xg = "s"
        else:
            xg = "S"

    if mode & stat.S_IROTH:
        ro = "r"
    if mode & stat.S_IWOTH:
        wo = "w"
    if mode & stat.S_IXOTH:
        xo = "x"
    if mode & stat.S_ISVTX:
        if mode & stat.S_IXOTH:
            xo = "t"
        else:
            xo = "T"
    
    return ru + wu + xu + rg + wg + xg + ro + wo + xo


def filetype(mode):
    """Return character to show the type of a file, like 'ls -l'"""
    tests = [(stat.S_ISDIR, "d"),
             (stat.S_ISCHR, "c"),
             (stat.S_ISBLK, "b"),
             (stat.S_ISREG, "-"),
             (stat.S_ISFIFO, "p"),
             (stat.S_ISLNK, "l"),
             (stat.S_ISSOCK, "s"),
            ]
    for func, result in tests:
        if func(mode):
            return result
    return "?"


def filemode(mode):
    """Format the entire file mode like 'ls -l'"""
    return filetype(mode) + permissions(mode)


def inode_fields(file_component):
    format_integer = lambda x: "%d" % x

    fields = [("st_mode", filemode),
              ("st_nlink", format_integer),
              ("st_uid", format_integer),
              ("st_gid", format_integer),
              ("st_size", format_integer),
              ("st_mtime", timestamp),
             ]

    list = []
    stat_component = file_component.first_by_kind(obnam.cmp.STAT)
    st = obnam.cmp.parse_stat_component(stat_component)
    for kind, func in fields:
        list.append(func(st.__getattribute__(kind)))
    return list


def timestamp(seconds):
    """Format a time stamp given in seconds since epoch"""
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(seconds))


class Listing:

    """Format listings of contents of backups.
    
    The listings are formatted similar to the Unix 'ls -l' command.
    
    """
    
    def __init__(self, context, output_file):
        self._context = context
        self._output = output_file
        self._get_object = obnam.io.get_object

    def get_objects(self, refs):
        list = []
        for ref in refs:
            o = self._get_object(self._context, ref)
            if o:
                list.append(o)
        return list

    def walk(self, dirs, filegroups):
        self.format(dirs, filegroups)
        for dir in dirs:
            dirrefs = dir.get_dirrefs()
            fgrefs = dir.get_filegrouprefs()
            if dirrefs or fgrefs:
                self._output.write("\n%s:\n" % dir.get_name())
                self.walk(self.get_objects(dirrefs), self.get_objects(fgrefs))
        
    def format(self, dirs, filegroups):
        list = []

        for dir in dirs:
            list.append((dir.get_name(), dir.get_stat()))
        for fg in filegroups:
            for name in fg.get_names():
                list.append((name, fg.get_stat(name)))

        list.sort()

        for name, stat in list:
            self._output.write("%s %d %d %d %d %s %s\n" % 
                               (filemode(stat.st_mode),
                                stat.st_nlink,
                                stat.st_uid,
                                stat.st_gid,
                                stat.st_size,
                                timestamp(stat.st_mtime),
                                name))
