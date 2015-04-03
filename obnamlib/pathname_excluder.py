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
        self._exclude_patterns = []
        self._include_patterns = []

    def exclude_regexp(self, regexp):
        self._exclude_patterns.append(re.compile(regexp))

    def allow_regexp(self, regexp):
        self._include_patterns.append(re.compile(regexp))

    def is_allowed(self, pathname):
        return (self._matches(pathname, self._include_patterns) or
                not self._matches(pathname, self._exclude_patterns))

    def _matches(self, pathname, patterns):
        for pattern in patterns:
            if pattern.search(pathname):
                return True
        return False
