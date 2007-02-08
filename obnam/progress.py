# Copyright (C) 2007  Lars Wirzenius <liw@iki.fi>
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


"""Progress reporting for Obnam"""


import sys
import time


class ProgressReporter:

    initial_values = (("total_files", 0), ("uploaded", 0), ("downloaded", 0),
                      ("current_file", None))

    def __init__(self, config):
        self.config = config
        self.dict = dict(self.initial_values)
        self.prev_output = ""
        self.timestamp = 0
        self.min_time = 1.0 # seconds

    def clear(self):
        if self.config.getboolean("backup", "report-progress"):
            sys.stdout.write("\b \b" * len(self.prev_output))
            sys.stdout.flush()
        
    def update(self, key, value):
        self.dict[key] = value
        if self.config.getboolean("backup", "report-progress"):
            now = time.time()
            if now - self.timestamp >= self.min_time:
                self.clear()
                parts = []
                parts.append("Files: %(total_files)d" % self.dict)
                parts.append("up: %d MB" % 
                             (self.dict["uploaded"] / 1024 / 1024))
                parts.append("down: %d MB" % 
                             (self.dict["downloaded"] / 1024 / 1024))
                parts.append("now:")
                part_one = ", ".join(parts)
                current = self.dict["current_file"] or ""
                progress = "%s%s" % (part_one, current[-(79-len(part_one)):])
                sys.stdout.write(progress)
                sys.stdout.flush()
                self.prev_output = progress
                self.timestamp = now

    def update_total_files(self, total_files):
        self.update("total_files", total_files)

    def update_uploaded(self, uploaded):
        self.update("uploaded", uploaded)

    def update_downloaded(self, downloaded):
        self.update("downloaded", downloaded)

    def update_current_file(self, current_file):
        self.update("current_file", current_file)
