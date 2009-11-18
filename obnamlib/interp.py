# Copyright (C) 2009  Lars Wirzenius
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


class Interpreter(object):

    '''A command interpreter for command line applications.'''
    
    def __init__(self):
        self.commands = {}
    
    def register(self, name, callback):
        if name not in self.commands:
            self.commands[name] = callback
        
    def execute(self, name, args):
        self.commands[name](args)
