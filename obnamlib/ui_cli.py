# Copyright (C) 2008, 2009  Lars Wirzenius <liw@liw.fi>
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


import optparse
import socket
import sys

import obnamlib


DESCRIPTION = """\
A backup command.
"""


class CommandLineCommand(object):

    def add_options(self, parser): # pragma: no cover
        """Add options to parser."""
        
    def run(self, config, args, progress): # pragma: no cover
        """Run the command."""


class CommandLineUI(obnamlib.UserInterface):

    def __init__(self, config):
        obnamlib.UserInterface.__init__(self, config)
        self.commands = {
            "help": obnamlib.HelpCommand(),

            "backup": obnamlib.BackupCommand(),
            
            "restore": obnamlib.RestoreCommand(),
            
            "cat": obnamlib.CatCommand(),
            
            "list": obnamlib.GenerationsCommand(),
            "generations": obnamlib.GenerationsCommand(),

            "show": obnamlib.ShowGenerationsCommand(),
            "show-generations": obnamlib.ShowGenerationsCommand(),
            
            "fsck": obnamlib.FsckCommand(),

            "objtree": obnamlib.ObjtreeCommand(),

            "showobjs": obnamlib.ShowobjsCommand(),
            }

    def short_help(self, stdout=sys.stdout):
        stdout.write("Use the help command to get help for this program.\n")

    def hostid(self): # pragma: no cover
        """Return the default hostid (hostname)."""
        return socket.gethostname()

    def create_option_parser(self): # pragma: no cover
        parser = optparse.OptionParser(version="%prog " + obnamlib.VERSION,
                                       description=DESCRIPTION)
        
        parser.usage = "Usage: %prog [options] command [args]"
        parser.epilog = ""

        parser.add_option("--host", metavar="HOST", default=self.hostid(),
                          help="use HOST as the host identifier (default: "
                               "%default)")
        
        parser.add_option("--store", metavar="DIR",
                          help="store backup data in DIR")
        
        parser.add_option("--generation", metavar="GEN",
                          help="use generation GEN")

        parser.add_option("--use-gzip", action="store_true",
                          help="compress blocks with gzip?")

        parser.add_option("--encrypt-to", metavar="KEYID",
                          help="encrypt with gpg to KEYID")

        parser.add_option("--sign-with", metavar="KEYID",
                          help="sign with gpg using KEYID")
        
        parser.add_option("--gpg-home", metavar="DIR",
                          help="use DIR as gpg home directory")
        
        for cmd in self.commands.values():
            cmd.add_options(parser)
        
        return parser

    def run(self, args):
        parser = self.create_option_parser()
        options, args = parser.parse_args(args)
        progress = obnamlib.ProgressReporter()
	
        if not args:
            self.short_help()
        elif args[0] in self.commands:
            progress = obnamlib.ProgressReporter()
            try:
                cmd = self.commands[args[0]]
                cmd.run(options, args[1:], progress)
            except Exception, e: # pragma: no cover
                progress.done()
                raise
        else:
            raise obnamlib.Exception("Unknown command '%s'" % args[0])
