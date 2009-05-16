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


import logging
import sys

import obnamlib

class BackupApplication(object):

    def run(self, args=None):
        self.setup_logging()
        self.load_configs()
        self.parse_command_line()
        ui_class = self.find_ui()
        ui = ui_class(self.cfg)
        ui.run(args or sys.argv[1:])

    def setup_logging(self):
        logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

    def load_configs(self):
        self.cfg = obnamlib.Config()

    def parse_command_line(self):
        pass

    def find_ui(self):
        return obnamlib.CommandLineUI
