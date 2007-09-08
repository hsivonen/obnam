# Copyright (C) 2006, 2007  Lars Wirzenius <liw@iki.fi>
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
import os
import sys
import time


levels = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}


def setup(config):
    filename = config.get("backup", "log-file")
    f = sys.stdout
    if filename:
        fd = os.open(filename, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0600)
        f = os.fdopen(fd, "a")
    level = config.get("backup", "log-level")

    formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s",
                                  "%Y-%m-%d %H:%M:%S")
    
    handler = logging.StreamHandler(f)
    handler.setFormatter(formatter)
    
    logger = logging.getLogger()
    logger.setLevel(levels[level.lower()])
    logger.addHandler(handler)
