# Copyright (C) 2006  Lars Wirzenius <liw@iki.fi>
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


"""Setting up the logging module"""


import logging
import sys
import time


levels = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}


class TimeOffsetFormatter(logging.Formatter):

    """Format timestamps as offsets since the beginning of logging"""

    def __init__(self, fmt=None, datefmt=None):
        logging.Formatter.__init__(self, fmt, datefmt)
        self.startup_time = time.time()

    def formatTime(self, record, datefmt=None):
        offset = record.created - self.startup_time
        minutes = int(offset / 60)
        seconds = offset % 60
        return "%dm%.1fs" % (minutes, seconds)

def setup(config):
    level = config.get("backup", "log-level")

    formatter = TimeOffsetFormatter("%(asctime)s %(levelname)s: %(message)s")
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    
    logger = logging.getLogger()
    logger.setLevel(levels[level.lower()])
    logger.addHandler(handler)
