# Copyright (C) 2010  Lars Wirzenius
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


import logging
import os
import random
import stat
import sys
import urlparse

import obnamlib


class Fail(obnamlib.Error):

    def __init__(self, filename, reason):
        self.filename = filename
        self.reason = reason

    def __str__(self):
        return '%s: %s' % (self.filename, self.reason)


class VerifyPlugin(obnamlib.ObnamPlugin):

    def enable(self):
        self.app.add_subcommand('verify', self.verify,
                                arg_synopsis='[DIRECTORY]...')
        self.app.settings.integer(['verify-randomly'],
                                  'verify N files randomly from the backup '
                                    '(default is zero, meaning everything)',
                                  metavar='N')

    def verify(self, args):
        '''Verify that live data and backed up data match.'''
        self.app.settings.require('repository')
        self.app.settings.require('client-name')
        self.app.settings.require('generation')
        if len(self.app.settings['generation']) != 1:
            raise obnamlib.Error(
                'verify must be given exactly one generation')

        logging.debug('verifying generation %s' %
                        self.app.settings['generation'])
        if not args:
            self.app.settings.require('root')
            args = self.app.settings['root']
        if not args:
            logging.debug('no roots/args given, so verifying everything')
            args = ['/']
        logging.debug('verifying what: %s' % repr(args))

        self.repo = self.app.get_repository_object()
        client_name = self.app.settings['client-name']
        self.fs = self.app.fsf.new(args[0])
        self.fs.connect()
        t = urlparse.urlparse(args[0])
        root_url = urlparse.urlunparse((t[0], t[1], '/', t[3], t[4], t[5]))
        logging.debug('t: %s' % repr(t))
        logging.debug('root_url: %s' % repr(root_url))
        self.fs.reinit(root_url)

        self.failed = False
        gen_id = self.repo.interpret_generation_spec(
            client_name,
            self.app.settings['generation'][0])

        self.app.ts['done'] = 0
        self.app.ts['total'] = 0
        self.app.ts['filename'] = ''
        if not self.app.settings['quiet']:
            self.app.ts.format(
                '%ElapsedTime() '
                'verifying file %Counter(filename)/%Integer(total) '
                '%PercentDone(done,total): '
                '%Pathname(filename)')

        num_randomly = self.app.settings['verify-randomly']
        if num_randomly == 0:
            self.app.ts['total'] = \
                self.repo.get_generation_key(
                gen_id, obnamlib.REPO_GENERATION_FILE_COUNT)
            for filename, metadata in self.walk(gen_id, args):
                self.app.ts['filename'] = filename
                try:
                    self.verify_metadata(gen_id, filename, metadata)
                except Fail, e:
                    self.log_fail(e)
                else:
                    if metadata.isfile():
                        try:
                            self.verify_regular_file(gen_id, filename)
                        except Fail, e:
                            self.log_fail(e)
                self.app.ts['done'] += 1
        else:
            logging.debug('verifying %d files randomly' % num_randomly)
            self.app.ts['total'] = num_randomly
            self.app.ts.notify('finding all files to choose randomly')
            filenames = [filename
                         for filename, metadata in self.walk(gen_id, args)
                         if metadata.isfile()]
            chosen = []
            for i in range(min(num_randomly, len(filenames))):
                filename = random.choice(filenames)
                filenames.remove(filename)
                chosen.append(filename)
            for filename in chosen:
                self.app.ts['filename'] = filename
                metadata = self.construct_metadata_object(gen_id, filename)
                try:
                    self.verify_metadata(gen_id, filename, metadata)
                    self.verify_regular_file(gen_id, filename)
                except Fail, e:
                    self.log_fail(e)
                self.app.ts['done'] += 1

        self.fs.close()
        self.repo.close()
        self.app.ts.finish()

        if self.failed:
            sys.exit(1)
        print "Verify did not find problems."

    def log_fail(self, e):
        msg = 'verify failure: %s: %s' % (e.filename, e.reason)
        logging.error(msg)
        if self.app.settings['quiet']:
            sys.stderr.write('%s\n' % msg)
        else:
            self.app.ts.notify(msg)
        self.failed = True

    def verify_metadata(self, gen_id, filename, backed_up):
        try:
            live_data = obnamlib.read_metadata(self.fs, filename)
        except OSError, e:
            raise Fail(filename, 'missing or inaccessible: %s' % e.strerror)

        def X(key, field_name):
            v1 = self.repo.get_file_key(gen_id, filename, key)
            v2 = getattr(live_data, field_name)
            # obnamlib.Metadata stores some fields as None, but
            # RepositoryInterface returns 0 or '' instead. Convert
            # the value from obnamlib.Metadata accordingly, for comparison.
            if key in obnamlib.REPO_FILE_INTEGER_KEYS:
                v2 = v2 or 0
            else:
                v2 = v2 or ''
            if v1 != v2:
                raise Fail(
                    filename,
                    'metadata change: %s (%s vs %s)' % 
                    (field_name, repr(v1), repr(v2)))

        X(obnamlib.REPO_FILE_MODE, 'st_mode')
        X(obnamlib.REPO_FILE_MTIME_SEC, 'st_mtime_sec')
        X(obnamlib.REPO_FILE_MTIME_NSEC, 'st_mtime_nsec')
        X(obnamlib.REPO_FILE_NLINK, 'st_nlink')
        X(obnamlib.REPO_FILE_GROUPNAME, 'groupname')
        X(obnamlib.REPO_FILE_USERNAME, 'username')
        X(obnamlib.REPO_FILE_SYMLINK_TARGET, 'target')
        X(obnamlib.REPO_FILE_XATTR_BLOB, 'xattr')

    def verify_regular_file(self, gen_id, filename):
        logging.debug('verifying regular %s' % filename)
        f = self.fs.open(filename, 'r')

        chunkids = self.repo.get_file_chunk_ids(gen_id, filename)
        if not self.verify_chunks(f, chunkids):
            raise Fail(filename, 'data changed')

        f.close()

    def verify_chunks(self, f, chunkids):
        for chunkid in chunkids:
            backed_up = self.repo.get_chunk_content(chunkid)
            live_data = f.read(len(backed_up))
            if backed_up != live_data:
                return False
        return True

    def walk(self, gen_id, args):
        '''Iterate over each pathname specified by arguments.

        This is a generator.

        '''

        for arg in args:
            scheme, netloc, path, query, fragment = urlparse.urlsplit(arg)
            arg = os.path.normpath(path)
            for x in self.repo_walk(gen_id, arg):
                yield x, self.construct_metadata_object(gen_id, x)

    def repo_walk(self, gen_id, dirname, depth_first=False):
        # FIXME: this is duplicate code.
        '''Like os.walk, but for a generation.

        This is a generator. Each return value is a tuple consisting
        of a pathname and its corresponding metadata. Directories are
        recursed into.

        '''

        arg = os.path.normpath(dirname)
        mode = self.repo.get_file_key(
            gen_id, dirname, obnamlib.REPO_FILE_MODE)
        if stat.S_ISDIR(mode):
            if not depth_first:
                yield dirname
            kidpaths = self.repo.get_file_children(gen_id, dirname)
            for kp in kidpaths:
                for x in self.repo_walk(gen_id, kp, depth_first=depth_first):
                    yield x
            if depth_first:
                yield arg
        else:
            yield arg

    def construct_metadata_object(self, gen, filename):
        # FIXME: this is duplicate code.
        allowed = set(self.repo.get_allowed_file_keys())
        def K(key):
            if key in allowed:
                return self.repo.get_file_key(gen, filename, key)
            else:
                return None

        return obnamlib.Metadata(
            st_atime_sec=K(obnamlib.REPO_FILE_ATIME_SEC),
            st_atime_nsec=K(obnamlib.REPO_FILE_ATIME_NSEC),
            st_mtime_sec=K(obnamlib.REPO_FILE_MTIME_SEC),
            st_mtime_nsec=K(obnamlib.REPO_FILE_MTIME_NSEC),
            st_blocks=K(obnamlib.REPO_FILE_BLOCKS),
            st_dev=K(obnamlib.REPO_FILE_DEV),
            st_gid=K(obnamlib.REPO_FILE_GID),
            st_ino=K(obnamlib.REPO_FILE_INO),
            st_mode=K(obnamlib.REPO_FILE_MODE),
            st_nlink=K(obnamlib.REPO_FILE_NLINK),
            st_size=K(obnamlib.REPO_FILE_SIZE),
            st_uid=K(obnamlib.REPO_FILE_UID),
            username=K(obnamlib.REPO_FILE_USERNAME),
            groupname=K(obnamlib.REPO_FILE_GROUPNAME),
            target=K(obnamlib.REPO_FILE_SYMLINK_TARGET),
            xattr=K(obnamlib.REPO_FILE_XATTR_BLOB) or None,
            md5=K(obnamlib.REPO_FILE_MD5),
            )
