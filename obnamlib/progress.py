# Copyright (C) 2009  Lars Wirzenius <liw@liw.fi>
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
import time

import obnamlib


class ProgressReporter(object):

    template = ("%(files-found)s files, up %(sent)s, down %(received)s "
                "in %(time-passed)s")

    def __init__(self, silent=False):
        self.silent = silent
        self.items = {
            "files-found": 0,
            "bytes-sent": 0,
            "bytes-received": 0,
            "sent": "",
            "received": "",
            "time-started": time.time(),
            "time-passed": "",
        }
        self.prevmsg = ""
        self.prevmsg_time = 0
        
    def __setitem__(self, key, value):
        assert key in self.items
        assert type(self.items[key]) == type(value)
        self.items[key] = value
        self.show()
        
    def __getitem__(self, key):
        return self.items[key]

    def show(self, force=False):
        if self.silent:
            return
        if force or time.time() - self.prevmsg_time >= 1:
            self.update_automatic_fields()
            msg = self.template % self.items
            self.update_screen(msg)
            self.prevmsg_time = time.time()

    def update_automatic_fields(self):
        duration = int(time.time() - self["time-started"])
        self.items["time-passed"] = obnamlib.format_time(duration)
        self.items["sent"] = obnamlib.format_size(self["bytes-sent"])
        self.items["received"] = obnamlib.format_size(self["bytes-received"])

    def update_screen(self, msg):
        w = 79 # FIXME: should determine screen width dynamically
        n = len(self.prevmsg)
        sys.stdout.write(("\r" * n) + (" " * n) + ("\r" * n) + msg)
        sys.stdout.flush()
        self.prevmsg = msg

    def done(self):
        if self.prevmsg:
            self.show(force=True)
            sys.stdout.write("\n")

