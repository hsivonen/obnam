# Copyright 2013  Lars Wirzenius
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
#
# =*= License: GPL-3+ =*=


import obnamlib


class RepositoryDoesNotExist(obnamlib.Error):

    def __init__(self, url):
        self.msg = 'Repository %s does not exist' % url


class RepositoryFactory(object):

    def __init__(self, repo_url):
        self._repo_url = repo_url

    def open_repository(self, create=False):
        raise RepositoryDoesNotExist(self._repo_url)

