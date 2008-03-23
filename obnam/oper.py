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


"""Obnam operations."""


import obnam


class Operation:

    """A user-visible operation for the Obnam backup program.
    
    User-visible operations are things like "make a backup", "restore
    files from a backup", "list backup generations", and so on. This
    base class abstracts the operations so that they can be easily
    implemented. Associated with this is the OperationFactory class,
    which will automatically instantiate the right Operation subclass
    based on command line arguments. For this to work, subclasses
    MUST set the 'name' attribute to the command word the user will
    use on the command line.
    
    """

    name = None

    def __init__(self, app, args):
        self._app = app
        self._args = args

    def get_application(self):
        """Return application this operation instance will use."""
        return self._app

    def get_args(self):
        """Return arguments this operation instance will use."""
        return self._args

    def do_it(self, args):
        """Do the operation.
        
        'args' will contain all command line arguments /except/ the
        command word. There's no point in passing that to this class,
        since we already know it must be our name.
        
        Subclasses should override this method with something that
        is actually useful. The default implementation does nothing.
        
        """
