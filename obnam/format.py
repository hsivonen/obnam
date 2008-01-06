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
    subs = file_component.get_subcomponents()
    stat_component = obnam.cmp.first_by_kind(subs, obnam.cmp.STAT)
    st = obnam.cmp.parse_stat_component(stat_component)
    for kind, func in fields:
        list.append(func(st.__getattribute__(kind)))
    return list


def timestamp(seconds):
    """Format a time stamp given in seconds since epoch"""
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(seconds))
