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


import os
import re
import stat
import sys
import time

import obnamlib


class ShowPlugin(obnamlib.ObnamPlugin):

    '''Show information about data in the backup repository.

    This implements commands for listing contents of root and client
    objects, or the contents of a backup generation.

    '''

    leftists = (2, 3, 6)
    min_widths = (1, 1, 1, 1, 6, 20, 1)

    def enable(self):
        self.app.add_subcommand('clients', self.clients)
        self.app.add_subcommand('generations', self.generations)
        self.app.add_subcommand('genids', self.genids)
        self.app.add_subcommand('ls', self.ls, arg_synopsis='[FILE]...')
        self.app.add_subcommand('diff', self.diff,
                                arg_synopsis='[GENERATION1] GENERATION2')
        self.app.add_subcommand('nagios-last-backup-age',
                                self.nagios_last_backup_age)

        self.app.settings.string(['warn-age'],
                                 'for nagios-last-backup-age: maximum age (by '
                                    'default in hours) for the most recent '
                                    'backup before status is warning. '
                                    'Accepts one char unit specifier '
                                    '(s,m,h,d for seconds, minutes, hours, '
                                    'and days.',
                                  metavar='AGE',
                                  default=obnamlib.DEFAULT_NAGIOS_WARN_AGE)
        self.app.settings.string(['critical-age'],
                                 'for nagios-last-backup-age: maximum age '
                                    '(by default in hours) for the most '
                                    'recent backup before statis is critical. '
                                    'Accepts one char unit specifier '
                                    '(s,m,h,d for seconds, minutes, hours, '
                                    'and days.',
                                  metavar='AGE',
                                  default=obnamlib.DEFAULT_NAGIOS_WARN_AGE)

    def open_repository(self, require_client=True):
        self.app.settings.require('repository')
        if require_client:
            self.app.settings.require('client-name')
        self.repo = self.app.get_repository_object()
        if require_client:
            client = self.app.settings['client-name']
            clients = self.repo.get_client_names()
            if client not in clients:
                raise obnamlib.Error(
                    'Client %s does not exist in repository %s' %
                    (client, self.app.settings['repository']))

    def clients(self, args):
        '''List clients using the repository.'''
        self.open_repository(require_client=False)
        for client_name in self.repo.get_client_names():
            self.app.output.write('%s\n' % client_name)
        self.repo.close()

    def generations(self, args):
        '''List backup generations for client.'''
        self.open_repository()
        client_name = self.app.settings['client-name']
        for gen_id in self.repo.get_client_generation_ids(client_name):
            start = self.repo.get_generation_key(
                gen_id, obnamlib.REPO_GENERATION_STARTED)
            end = self.repo.get_generation_key(
                gen_id, obnamlib.REPO_GENERATION_ENDED)
            is_checkpoint = False
            file_count = 0
            data_size = 0

            if is_checkpoint:
                checkpoint = ' (checkpoint)'
            else:
                checkpoint = ''
            sys.stdout.write('%s\t%s .. %s (%d files, %d bytes) %s\n' %
                             (self.repo.make_generation_spec(gen_id),
                              self.format_time(start),
                              self.format_time(end),
                              file_count,
                              data_size,
                              checkpoint))
        self.repo.close()

    def nagios_last_backup_age(self, args):
        '''Check if the most recent generation is recent enough.'''
        try:	
            self.open_repository()
        except obnamlib.Error, e:
            self.app.output.write('CRITICAL: %s\n' % e)
            sys.exit(2)

        most_recent = None

        warn_age = self._convert_time(self.app.settings['warn-age'])
        critical_age = self._convert_time(self.app.settings['critical-age'])

        client_name = self.app.settings['client-name']
        for gen_id in self.repo.get_client_generation_ids(client_name):
            # FIXME: get generation start, end times here.
            start, end = 0, 0
            if most_recent is None or start > most_recent:
                most_recent = start
        self.repo.close()

        now = self.app.time()
        if most_recent is None:
            # the repository is empty / the client does not exist
            self.app.output.write('CRITICAL: no backup found.\n')
            sys.exit(2)
        elif (now - most_recent > critical_age):
            self.app.output.write(
                'CRITICAL: backup is old.  last backup was %s.\n' %
                    (self.format_time(most_recent)))
            sys.exit(2)
        elif (now - most_recent > warn_age):
            self.app.output.write(
                'WARNING: backup is old.  last backup was %s.\n' %
                    self.format_time(most_recent))
            sys.exit(1)
        self.app.output.write(
            'OK: backup is recent.  last backup was %s.\n' %
                self.format_time(most_recent))

    def genids(self, args):
        '''List generation ids for client.'''
        self.open_repository()
        client_name = self.app.settings['client-name']
        for gen_id in self.repo.get_client_generation_ids(client_name):
            sys.stdout.write('%s\n' % self.repo.make_generation_spec(gen_id))
        self.repo.close()

    def ls(self, args):
        '''List contents of a generation.'''

        self.open_repository()

        if len(args) is 0:
            args = ['/']

        client_name = self.app.settings['client-name']
        for genspec in self.app.settings['generation']:
            gen_id = self.repo.interpret_generation_spec(client_name, genspec)
            # FIXME: Get generation start, end times here.
            started, ended = 0, 0
            started = self.format_time(started)
            ended = self.format_time(ended)
            self.app.output.write(
                'Generation %s (%s - %s)\n' % 
                (self.repo.make_generation_spec(gen_id), started, ended))
            for ls_file in args:
                ls_file = self.remove_trailing_slashes(ls_file)
                self.show_objects(gen_id, ls_file)

        self.repo.close()

    def remove_trailing_slashes(self, filename):
        while filename.endswith('/') and filename != '/':
            filename = filename[:-1]
        return filename

    def format_time(self, timestamp):
        return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))

    def isdir(self, gen_id, filename):
        mode = self.repo.get_file_key(
            gen_id, filename, obnamlib.REPO_FILE_MODE)
        return stat.S_ISDIR(mode)

    def show_objects(self, gen_id, dirname):
        self.show_item(gen_id, dirname)
        subdirs = []
        for filename in sorted(self.repo.get_file_children(gen_id, dirname)):
            if self.isdir(gen_id, filename):
                subdirs.append(filename)
            else:
                self.show_item(gen_id, filename)

        for subdir in subdirs:
            self.show_objects(gen_id, subdir)

    def show_item(self, gen_id, filename):
        fields = self.fields(gen_id, filename)
        widths = [
            1, # mode
            5, # nlink
            -8, # owner
            -8, # group
            10, # size
            1, # mtime
            -1, # name
        ]

        result = []
        for i in range(len(fields)):
            if widths[i] < 0:
                fmt = '%-*s'
            else:
                fmt = '%*s'
            result.append(fmt % (abs(widths[i]), fields[i]))
        self.app.output.write('%s\n' % ' '.join(result))

    def show_diff_for_file(self, gen_id, fullname, change_char):
        '''Show what has changed for a single file.

        change_char is a single char (+,- or *) indicating whether a file
        got added, removed or altered.

        If --verbose, just show all the details as ls shows, otherwise
        show just the file's full name.

        '''

        if self.app.settings['verbose']:
            sys.stdout.write('%s ' % change_char)
            self.show_item(gen_id, fullname)
        else:
            self.app.output.write('%s %s\n' % (change_char, fullname))

    def show_diff_for_common_file(self, gen_id1, gen_id2, fullname, subdirs):
        changed = False
        if self.isdir(gen_id1, fullname) != self.isdir(gen_id2, fullname):
            changed = True
        elif self.isdir(gen_id2, fullname):
            subdirs.append(fullname)
        else:
            # Files are both present and neither is a directory.
            # Compare md5
            # FIXME: not sure this logic is correct --liw
            def get_md5(gen_id):
                return self.repo.get_file_key(
                    gen_id, fullname, obnamlib.REPO_FILE_MD5)
            md5_1 = get_md5(gen_id1)
            md5_2 = get_md5(gen_id2)
            if md5_1 != md5_2:
                changed = True
        if changed:
            self.show_diff_for_file(gen_id2, fullname, '*')

    def show_diff(self, gen_id1, gen_id2, dirname):
        # This set contains the files from the old/src generation
        set1 = self.repo.get_file_children(gen_id1, dirname)
        subdirs = []
        # These are the new/dst generation files
        for filename in sorted(self.repo.get_file_children(gen_id2, dirname)):
            if filename in set1:
                # Its in both generations
                set1.remove(filename)
                self.show_diff_for_common_file(
                    gen_id1, gen_id2, filename, subdirs)
            else:
                # Its only in set2 - the file/dir got added
                self.show_diff_for_file(gen_id2, full, '+')
        for filename in sorted(set1):
            # This was only in gen1 - it got removed
            self.show_diff_for_file(gen_id1, filename, '-')

        for subdir in subdirs:
            self.show_diff(gen_id1, gen_id2, subdir)

    def diff(self, args):
        '''Show difference between two generations.'''

        if len(args) not in (1, 2):
            raise obnamlib.Error('Need one or two generations')

        self.open_repository()
        if len(args) == 1:
            gen_id2 = self.repo.interpret_generation_spec(args[0])
            # Now we have the dst/second generation for show_diff. Use
            # genids/list_generations to find the previous generation
            client_name = self.app.settings['client-name']
            genids = self.repo.get_client_generation_ids(client_name)
            index = genids.index(gen_id2)
            if index == 0:
                raise obnamlib.Error(
                    'Can\'t show first generation. Use \'ls\' instead')
            gen_id1 = genids[index - 1]
        else:
            gen_id1 = self.repo.interpret_generation_spec(args[0])
            gen_id2 = self.repo.interpret_generation_specb(args[1])

        self.show_diff(gen_id1, gen_id2, '/')
        self.repo.close()

    def fields(self, gen_id, filename):
        mode = self.repo.get_file_key(
            gen_id, filename, obnamlib.REPO_FILE_MODE)
        mtime_sec = self.repo.get_file_key(
            gen_id, filename, obnamlib.REPO_FILE_MTIME_SEC)
        target = self.repo.get_file_key(
            gen_id, filename, obnamlib.REPO_FILE_SYMLINK_TARGET)
        nlink = self.repo.get_file_key(
            gen_id, filename, obnamlib.REPO_FILE_NLINK)
        username = self.repo.get_file_key(
            gen_id, filename, obnamlib.REPO_FILE_USERNAME)
        groupname = self.repo.get_file_key(
            gen_id, filename, obnamlib.REPO_FILE_GROUPNAME)
        size = self.repo.get_file_key(
            gen_id, filename, obnamlib.REPO_FILE_SIZE)

        perms = ['?'] + ['-'] * 9
        tab = [
            (stat.S_IFREG, 0, '-'),
            (stat.S_IFDIR, 0, 'd'),
            (stat.S_IFLNK, 0, 'l'),
            (stat.S_IFIFO, 0, 'p'),
            (stat.S_IRUSR, 1, 'r'),
            (stat.S_IWUSR, 2, 'w'),
            (stat.S_IXUSR, 3, 'x'),
            (stat.S_IRGRP, 4, 'r'),
            (stat.S_IWGRP, 5, 'w'),
            (stat.S_IXGRP, 6, 'x'),
            (stat.S_IROTH, 7, 'r'),
            (stat.S_IWOTH, 8, 'w'),
            (stat.S_IXOTH, 9, 'x'),
        ]
        for bitmap, offset, char in tab:
            if (mode & bitmap) == bitmap:
                perms[offset] = char
        perms = ''.join(perms)

        timestamp = time.strftime(
            '%Y-%m-%d %H:%M:%S', time.gmtime(mtime_sec))

        if stat.S_ISLNK(mode):
            name = '%s -> %s' % (filename, target)
        else:
            name = filename

        return (perms,
                 str(nlink),
                 username,
                 groupname,
                 str(size),
                 timestamp,
                 name)

    def format(self, fields):
        return ' '. join(self.align(widths[i], fields[i], i)
                          for i in range(len(fields)))

    def align(self, width, field, field_no):
        if field_no in self.leftists:
            return '%-*s' % (width, field)
        else:
            return '%*s' % (width, field)

    def _convert_time(self, s, default_unit='h'):
        m = re.match('([0-9]+)([smhdw])?$', s)
        if m is None: raise ValueError
        ticks = int(m.group(1))
        unit = m.group(2)
        if unit is None: unit = default_unit

        if unit == 's':
            None
        elif unit == 'm':
            ticks *= 60
        elif unit == 'h':
            ticks *= 60*60
        elif unit == 'd':
            ticks *= 60*60*24
        elif unit == 'w':
            ticks *= 60*60*24*7
        else:
            raise ValueError
        return ticks

