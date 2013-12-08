# Copyright (C) 2009, 2010  Lars Wirzenius
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


import hashlib
import logging
import os
import stat
import time
import ttystatus

import obnamlib


class Hardlinks(object):

    '''Keep track of inodes with unrestored hardlinks.'''

    def __init__(self):
        self.inodes = dict()

    def key(self, metadata):
        return '%s:%s' % (metadata.st_dev, metadata.st_ino)

    def add(self, filename, metadata):
        self.inodes[self.key(metadata)] = (filename, metadata.st_nlink)

    def filename(self, metadata):
        key = self.key(metadata)
        if key in self.inodes:
            return self.inodes[key][0]
        else:
            return None

    def forget(self, metadata):
        key = self.key(metadata)
        filename, nlinks = self.inodes[key]
        if nlinks <= 2:
            del self.inodes[key]
        else:
            self.inodes[key] = (filename, nlinks - 1)


class RestorePlugin(obnamlib.ObnamPlugin):

    # A note about the implementation: we need to make sure all the
    # files we restore go into the target directory. We do this by
    # prefixing all filenames we write to with './', and then using
    # os.path.join to put the target directory name at the beginning.
    # The './' business is necessary because os.path.join(a,b) returns
    # just b if b is an absolute path.

    def enable(self):
        self.app.add_subcommand('restore', self.restore,
                                arg_synopsis='[DIRECTORY]...')
        self.app.settings.string(['to'], 'where to restore')
        self.app.settings.string_list(['generation'],
                                'which generation to restore',
                                 default=['latest'])

    @property
    def write_ok(self):
        return not self.app.settings['dry-run']

    def configure_ttystatus(self):
        self.app.ts['current'] = ''
        self.app.ts['total'] = 0
        self.app.ts['current-bytes'] = 0
        self.app.ts['total-bytes'] = 0

        self.app.ts.format('%RemainingTime(current-bytes,total-bytes) '
                           '%Counter(current) files '
                           '%ByteSize(current-bytes) '
                           '(%PercentDone(current-bytes,total-bytes)) '
                           '%ByteSpeed(current-bytes) '
                           '%Pathname(current)')

    def restore(self, args):
        '''Restore some or all files from a generation.'''
        self.app.settings.require('repository')
        self.app.settings.require('client-name')
        self.app.settings.require('generation')
        self.app.settings.require('to')

        logging.debug('restoring generation %s' %
                        self.app.settings['generation'])
        logging.debug('restoring to %s' % self.app.settings['to'])

        logging.debug('restoring what: %s' % repr(args))
        if not args:
            logging.debug('no args given, so restoring everything')
            args = ['/']

        self.downloaded_bytes = 0
        self.file_count = 0
        self.started = time.time()

        self.repo = self.app.get_repository_object()
        client_name = self.app.settings['client-name']

        if self.write_ok:
            self.fs = self.app.fsf.new(self.app.settings['to'], create=True)
            self.fs.connect()
        else:
            self.fs = None # this will trigger error if we try to really write

        self.hardlinks = Hardlinks()

        self.errors = False

        generations = self.app.settings['generation']
        if len(generations) != 1:
            raise obnamlib.Error(
                'The restore command wants exactly one generation option')
        gen = self.repo.interpret_generation_spec(client_name, generations[0])

        self.configure_ttystatus()
        # FIXME: should initialise  self.app.ts['total'] and
        # self.app.ts['total-bytes'] from the generation metadata,
        # but RepositoryInterface does not yet support that. To be
        # fixed later.

        self.app.dump_memory_profile('at beginning after setup')

        for arg in args:
            self.restore_something(gen, arg)
            self.app.dump_memory_profile('at restoring %s' % repr(arg))

        # FIXME: Close the repository here, so that its vfs gets
        # closed. This is not yet supported by RepositoryInterface.
        if self.write_ok:
            self.fs.close()

        self.app.ts.clear()
        self.report_stats()

        self.app.ts.finish()

        if self.errors:
            raise obnamlib.Error('There were errors when restoring')

    def repo_walk(self, gen_id, dirname, depth_first=False):
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

    def restore_something(self, gen, root):
        for pathname in self.repo_walk(gen, root, depth_first=True):
            self.file_count += 1
            self.app.ts['current'] = pathname
            self.restore_safely(gen, pathname, metadata)

    def restore_safely(self, gen, pathname, metadata):
        try:
            dirname = os.path.dirname(pathname)
            if self.write_ok and not self.fs.exists('./' + dirname):
                self.fs.makedirs('./' + dirname)

            set_metadata = True
            if metadata.isdir():
                self.restore_dir(gen, pathname, metadata)
            elif metadata.islink():
                self.restore_symlink(gen, pathname, metadata)
            elif metadata.st_nlink > 1:
                link = self.hardlinks.filename(metadata)
                if link:
                    self.restore_hardlink(pathname, link, metadata)
                    set_metadata = False
                else:
                    self.hardlinks.add(pathname, metadata)
                    self.restore_first_link(gen, pathname, metadata)
            else:
                self.restore_first_link(gen, pathname, metadata)
            if set_metadata and self.write_ok:
                try:
                    obnamlib.set_metadata(self.fs, './' + pathname, metadata)
                except (IOError, OSError), e:
                    msg = ('Could not set metadata: %s: %d: %s' %
                            (pathname, e.errno, e.strerror))
                    logging.error(msg)
                    self.app.ts.notify(msg)
                    self.errors = True
        except Exception, e:
            # Reaching this code path means we've hit a bug, so we log a full traceback.
            msg = "Failed to restore %s:" % (pathname,)
            logging.exception(msg)
            self.app.ts.notify(msg + " " + str(e))
            self.errors = True

    def restore_dir(self, gen, root, metadata):
        logging.debug('restoring dir %s' % root)
        if self.write_ok:
            if not self.fs.exists('./' + root):
                self.fs.mkdir('./' + root)
        self.app.dump_memory_profile('after recursing through %s' % repr(root))

    def restore_hardlink(self, filename, link, metadata):
        logging.debug('restoring hardlink %s to %s' % (filename, link))
        if self.write_ok:
            self.fs.link('./' + link, './' + filename)
            self.hardlinks.forget(metadata)

    def restore_symlink(self, gen, filename, metadata):
        logging.debug('restoring symlink %s' % filename)

    def restore_first_link(self, gen, filename, metadata):
        if stat.S_ISREG(metadata.st_mode):
            self.restore_regular_file(gen, filename, metadata)
        elif stat.S_ISFIFO(metadata.st_mode):
            self.restore_fifo(gen, filename, metadata)
        elif stat.S_ISSOCK(metadata.st_mode):
            self.restore_socket(gen, filename, metadata)
        elif stat.S_ISBLK(metadata.st_mode) or stat.S_ISCHR(metadata.st_mode):
            self.restore_device(gen, filename, metadata)
        else:
            msg = ('Unknown file type: %s (%o)' %
                   (filename, metadata.st_mode))
            logging.error(msg)
            self.app.ts.notify(msg)

    def restore_regular_file(self, gen, filename, metadata):
        logging.debug('restoring regular %s' % filename)
        if self.write_ok:
            f = self.fs.open('./' + filename, 'wb')
            summer = hashlib.md5()

            try:
                chunkids = self.repo.get_file_chunk_ids(gen, filename)
                self.restore_chunks(f, chunkids, summer)
            except obnamlib.MissingFilterError, e:
                msg = 'Missing filter error during restore: %s' % filename
                logging.error(msg)
                self.app.ts.notify(msg)
                self.errors = True
            f.close()

            correct_checksum = metadata.md5
            if summer.digest() != correct_checksum:
                msg = 'File checksum restore error: %s' % filename
                logging.error(msg)
                self.app.ts.notify(msg)
                self.errors = True

    def restore_chunks(self, f, chunkids, checksummer):
        zeroes = ''
        hole_at_end = False
        for chunkid in chunkids:
            data = self.repo.get_chunk_content(chunkid)
            self.verify_chunk_checksum(data, chunkid)
            checksummer.update(data)
            self.downloaded_bytes += len(data)
            if len(data) != len(zeroes):
                zeroes = '\0' * len(data)
            if data == zeroes:
                f.seek(len(data), 1)
                hole_at_end = True
            else:
                f.write(data)
                hole_at_end = False
            self.app.ts['current-bytes'] += len(data)
        if hole_at_end:
            pos = f.tell()
            if pos > 0:
                f.seek(-1, 1)
                f.write('\0')

    def verify_chunk_checksum(self, data, chunkid):
        # FIXME: The RepositoryInterface does not currently have
        # a way to do this, so at this time this is a no-op, to be
        # fixed later.
        pass

    def restore_fifo(self, gen, filename, metadata):
        logging.debug('restoring fifo %s' % filename)
        if self.write_ok:
            self.fs.mknod('./' + filename, metadata.st_mode)

    def restore_socket(self, gen, filename, metadata):
        logging.debug('restoring socket %s' % filename)
        if self.write_ok:
            self.fs.mknod('./' + filename, metadata.st_mode)

    def restore_device(self, gen, filename, metadata):
        logging.debug('restoring device %s' % filename)
        if self.write_ok:
            self.fs.mknod('./' + filename, metadata.st_mode)

    def report_stats(self):
        size_table = [
            (1024**4, 'TiB'),
            (1024**3, 'GiB'),
            (1024**2, 'MiB'),
            (1024**1, 'KiB'),
            (0, 'B')
        ]

        for size_base, size_unit in size_table:
            if self.downloaded_bytes >= size_base:
                if size_base > 0:
                    size_amount = (float(self.downloaded_bytes) /
                                    float(size_base))
                else:
                    size_amount = float(self.downloaded_bytes)
                break

        speed_table = [
            (1024**3, 'GiB/s'),
            (1024**2, 'MiB/s'),
            (1024**1, 'KiB/s'),
            (0, 'B/s')
        ]
        duration = time.time() - self.started
        speed = float(self.downloaded_bytes) / duration
        for speed_base, speed_unit in speed_table:
            if speed >= speed_base:
                if speed_base > 0:
                    speed_amount = speed / speed_base
                else:
                    speed_amount = speed
                break

        duration_string = ''
        seconds = duration
        if seconds >= 3600:
            duration_string += '%dh' % int(seconds/3600)
            seconds %= 3600
        if seconds >= 60:
            duration_string += '%dm' % int(seconds/60)
            seconds %= 60
        if seconds > 0:
            duration_string += '%ds' % round(seconds)

        logging.info('Restore performance statistics:')
        logging.info('* files restored: %s' % self.file_count)
        logging.info('* downloaded data: %s bytes (%s %s)' %
                        (self.downloaded_bytes, size_amount, size_unit))
        logging.info('* duration: %s s' % duration)
        logging.info('* average speed: %s %s' % (speed_amount, speed_unit))
        self.app.ts.notify(
            'Restored %d files, '
            'downloaded %.1f %s in %s at %.1f %s average speed' %
                (self.file_count,
                 size_amount, size_unit,
                 duration_string, speed_amount, speed_unit))
