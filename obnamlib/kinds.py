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


class Kinds(object):

    """Store info about component and object kinds.

    Components and Objects have "kinds" (types, labels), which
    identify what they are: a filename versus a file content, for
    example. For each kind we need to store some information: its
    numeric code and the corresponding textual name, for example. We
    also need ways of getting from one to the other. This class stores
    that information and provides that mapping.

    Additionally we need a Python identifier for each kind, so that we
    can easily refer to the kinds in the source code. This class provides
    that, too, via the add_identifiers method.

    Because Component and Object kinds have different requirements,
    this is a base class that gets subclassed elsewhere.

    """

    def __init__(self):
        # We store the mappings in a dictionary, indexed by code.
        self.dict = {}

    def add(self, code, name):
        """Add a mapping between a numeric code and textual name."""
        for c, n in self.pairs():
            if c == code:
                raise KeyError("Code %s already added" % code)
            if n == name:
                raise KeyError("Name %s already added" % name)
        self.dict[code] = name

    def nameof(self, code):
        """Return name corresponding to a code."""
        return self.dict[code]

    def codeof(self, name):
        """Return code corresponding to a name."""
        for code, name2 in self.pairs():
            if name == name2:
                return code
        raise KeyError(name)

    def pairs(self):
        """Return list of all mappings as tuples of code and name."""
        return [(code, name) for code, name in self.dict.iteritems()]

    def add_identifiers(self, module):
        """Add identifiers from list of kinds to a module's namespace.

        Suggested use:

        import obnamlib
        kinds = obnamlib.Kinds()
        kinds.add(123, "FOO")
        kinds.add_identifiers(obnamlib)
        ...
        c = Component(kind=obnamlib.FOO)

        """

        for code, value in self.pairs():
            setattr(module, value, code)

    def add_to_obnamlib(self): # pragma: no cover
        """Add all our names to obnamlib.

        This method must be called from obnamlib/__init__.py only!

        """

        self.add_identifiers(obnamlib)
