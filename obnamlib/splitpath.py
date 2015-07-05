# Copyright 2015  Lars Wirzenius
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# =*= License: GPL-3+ =*=


import os


def split_pathname(pathname):
    if not pathname:
        raise Exception('internal error in split_pathname (empty path)')
    return list(reversed(list(_split(pathname))))


def _split(pathname):
    while pathname:
        head, tail = os.path.split(pathname)
        assert head or tail
        if tail:
            yield tail
            pathname = head
        elif head == os.sep:
            yield head
            break
        else:
            pathname = head
