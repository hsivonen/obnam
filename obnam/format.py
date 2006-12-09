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
    tests = (
        (stat.S_ISDIR, "d"),
        (stat.S_ISCHR, "c"),
        (stat.S_ISBLK, "b"),
        (stat.S_ISREG, "-"),
        (stat.S_ISFIFO, "p"),
        (stat.S_ISLNK, "l"),
        (stat.S_ISSOCK, "s"),
    )
    for func, result in tests:
        if func(mode):
            return result
    return "?"


def filemode(mode):
    """Format the entire file mode like 'ls -l'"""
    return filetype(mode) + permissions(mode)


def inode_fields(inode):
    format_integer = lambda x: "%d" % x
    format_time = lambda x: time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(x))

    fields = (
        (obnam.cmp.ST_MODE, filemode),
        (obnam.cmp.ST_NLINK, format_integer),
        (obnam.cmp.ST_UID, format_integer),
        (obnam.cmp.ST_GID, format_integer),
        (obnam.cmp.ST_SIZE, format_integer),
        (obnam.cmp.ST_MTIME, format_time),
    )

    list = []
    subs = obnam.cmp.get_subcomponents(inode)
    for kind, func in fields:
        for value in obnam.cmp.find_strings_by_kind(subs, kind):
            (value, _) = obnam.varint.decode(value, 0)
            list.append(func(value))
    return list
