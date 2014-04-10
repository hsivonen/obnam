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


import errno
import logging

import obnamlib


class UnknownRepositoryFormat(obnamlib.ObnamError):

    msg = 'Unknown format {format} at {url}'


class UnknownRepositoryFormatWanted(obnamlib.ObnamError):

    msg = 'Unknown format {format} requested'


class NotARepository(obnamlib.ObnamError):

    msg = '{url} does not seem to be an Obnam repository'


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

    def setup_hooks(self, hooks): # pragma: no cover
        '''Create all repository related hooks.

        The factory instantiates all supported repository format classes.
        This causes the hooks to be created.

        '''

        for impl in self._implementations:
            impl.setup_hooks(hooks)

    def open_existing_repo(self, fs, **kwargs):
        '''Open an existing repository.

        Any keyword arguments are passed into the RepositoryInterface
        object at creation time, and the fs is set with the set_fs
        method.

        '''

        try:
            existing_format = self._read_existing_format(fs)
        except EnvironmentError as e: # pragma: no cover
            if e.errno == errno.ENOENT:
                raise NotARepository(url=fs.baseurl)
            raise

        for impl in self._implementations:
            if impl.format == existing_format:
                return self._open_repo(impl, fs, kwargs)
        raise UnknownRepositoryFormat(url=fs.baseurl, format=existing_format)

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

        if wanted_format not in self._implementations:
            raise UnknownRepositoryFormatWanted(format=wanted_format)

        try:
            fs.write_file('metadata/format', '%s\n' % wanted_format.format)
        except OSError as e:
            logging.debug('create_repo: e=%s' % e, exc_info=1)
            logging.debug('create_repo: e.errno=%s' % e.errno)
            # SFTP (paramiko) sets errno to None when file creation
            # fails when the file already exists. Local filesystems
            # set it to EEXIST. Life is wonderful.
            if e.errno in (errno.EEXIST, None):
                return self.open_existing_repo(fs, **kwargs)
            raise # pragma: no cover
        else:
            logging.debug('create_repo: metadata/format created ok')
            repo = self._open_repo(wanted_format, fs, kwargs)
            repo.init_repo()
            return repo
