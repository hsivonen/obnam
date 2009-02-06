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


import sys

import obnamlib


class CommandLineUI(obnamlib.UserInterface):

    commands = {
        "help": obnamlib.HelpCommand(),

        "backup": obnamlib.BackupCommand(),
        
        "restore": obnamlib.RestoreCommand(),
        
        "cat": obnamlib.CatCommand(),
        
        "list": obnamlib.GenerationsCommand(),
        "generations": obnamlib.GenerationsCommand(),

        "show": obnamlib.ShowGenerationsCommand(),
        "show-generations": obnamlib.ShowGenerationsCommand(),
        }

    def short_help(self, stdout=sys.stdout):
        stdout.write("Use the help command to get help for this program.\n")

    def run(self, args):
        if not args:
            self.short_help()
        elif args[0] in self.commands:
            self.commands[args[0]](self.config, args[1:])
        else:
            raise obnamlib.Exception("Unknown command '%s'" % args[0])
