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


class UserInterface(object):

    """User interface base class.

    The application supports both a command line and graphical user
    interfaces. This class defines the base class for both kinds of
    user interfaces. Because the two are so different, this is a very
    simple interface.

    Sub-classes should implement the run() method to actually do
    useful things.

    """

    def __init__(self, config):
        self.config = config

    def run(self, args): # pragma: no cover
        """Actually run the user interface."""
