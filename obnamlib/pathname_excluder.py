# Copyright (C) 2015  Lars Wirzenius
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


import re


class PathnameExcluder(object):

    '''Decide which pathnames to exclude from a backup. '''

    def __init__(self):
        self._patterns = []

    def add_regexp(self, regexp):
        self._patterns.append(re.compile(regexp))

    def is_allowed(self, pathname):
        for pattern in self._patterns:
            if pattern.search(pathname):
                return False
        return True
