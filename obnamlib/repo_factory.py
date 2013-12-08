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


class UnknownRepositoryFormat(obnamlib.Error):

    def __init__(self, fs, format):
        self.msg = 'Unknown format %s at %s' % (format, fs.baseurl)


class UnknownRepositoryFormatWanted(obnamlib.Error):

    def __init__(self, wanted):
        self.msg = 'Unknown format %s requested' % repr(wanted)


class RepositoryFactory(object):

    '''Create new objects implementing obnamlib.RepositoryInterface.'''

    def __init__(self):
        # The following can't be a static attribute, since the values
        # do not necessarily exist yet when the list would be initialised:
        # if this module is imported by obnamlib/__init__.py before the
        # interface implementations, then they wouldn't exist yet.
        # So we create it when the factory object is initialised instead.
        self._implementations = [
            obnamlib.RepositoryFormat6,
            ]

    def open_existing_repo(self, fs, **kwargs):
        '''Open an existing repository.

        Any keyword arguments are passed into the RepositoryInterface
        object at creation time, and the fs is set with the set_fs
        method.

        '''

        existing_format = self._read_existing_format(fs)
        for impl in self._implementations:
            if impl.format == existing_format:
                return self._open_repo(impl, fs, kwargs)
        raise UnknownRepositoryFormat(fs, existing_format)

    def _read_existing_format(self, fs):
        f = fs.open('metadata/format', 'r')
        line = f.readline()
        f.close()

        return line.strip()

    def _open_repo(self, klass, fs, kwargs):
        repo = klass(**kwargs)
        repo.set_fs(fs)
        return repo

    def create_repo(self, fs, wanted_format, **kwargs):
        '''Create a new repository.

        The directory for the repository must already exist.
        Any keyword arguments are given to the RepositoryInterface
        object at creation time.

        If the repository was already initialised, that's OK, even if
        the format was different from the one requested.

        '''

        if fs.exists('metadata/format'):
            return self.open_existing_repo(fs, **kwargs)

        for impl in self._implementations:
            if impl == wanted_format:
                break
        else:
            raise UnknownRepositoryFormatWanted(wanted_format)
        
        fs.write_file('metadata/format', '%s\n' % wanted_format.format)
        repo = self._open_repo(impl, fs, kwargs)
        repo.init_repo()
        return repo
