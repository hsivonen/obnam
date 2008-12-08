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


import obnamlib


class Object(object):

    """Data about files that are backed up.

    A backup object contains data about files that are backed up:
    its metadata, or content, or other such things. A backup object
    can also contain data necessary for the backup process: a
    backup generation, for example.

    Backup objects should be instantiated via a BackupObjectFactory,
    or a Store, not directly.

    This class is meant to be sub-classed for specific kinds of
    object, and not used directly.

    """

    def __init__(self, id):
        self.id = id
        self.components = []

    def prepare_for_encoding(self):
        """Prepare object for encoding.

        For performance or convenience reasons, a subclass may decide
        to keep some information in properties of its instance, rather
        than as components in self.components. However, when the object
        is encoded, everything should be in self.components. The
        encoder will call this method to ensure that happens.

        """

    def find(self, kind=None):
        """Find top-level components that match non-None arguments."""
        list = []
        for cmp in self.components:
            if kind is not None and cmp.kind == kind:
                list.append(cmp)
        return list

    def find_strings(self, **kwargs):
        """Like find, but return string values of components."""
        return [c.string for c in self.find(**kwargs)]

    def extract(self, **kwargs):
        """Find and remove the top-level components matching **kwargs."""
        list = self.find(**kwargs)
        self.components = [x for x in self.components if x not in list]
        return list
