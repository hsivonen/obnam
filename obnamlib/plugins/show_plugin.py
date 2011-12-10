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
        self.app.add_subcommand('ls', self.ls, arg_synopsis='[GENERATION]...')

    def open_repository(self):
        self.app.settings.require('repository')
        self.app.settings.require('client-name')
        self.repo = self.app.open_repository()
        self.repo.open_client(self.app.settings['client-name'])

    def clients(self, args):
        '''List clients using the repository.'''
        self.open_repository()
        for client_name in self.repo.list_clients():
            print client_name
        self.repo.fs.close()
    
    def generations(self, args):
        '''List backup generations for client.'''
        self.open_repository()
        for gen in self.repo.list_generations():
            start, end = self.repo.get_generation_times(gen)
            is_checkpoint = self.repo.get_is_checkpoint(gen)
            if is_checkpoint:
                checkpoint = ' (checkpoint)'
            else:
                checkpoint = ''
            sys.stdout.write('%s\t%s .. %s (%d files, %d bytes) %s\n' %
                             (gen, 
                              self.format_time(start), 
                              self.format_time(end),
                              self.repo.client.get_generation_file_count(gen),
                              self.repo.client.get_generation_data(gen),
                              checkpoint))
        self.repo.fs.close()
    
    def genids(self, args):
        '''List generation ids for client.'''
        self.open_repository()
        for gen in self.repo.list_generations():
            sys.stdout.write('%s\n' % gen)
        self.repo.fs.close()

    def ls(self, args):
        '''List contents of a generation.'''
        self.open_repository()
        for gen in args or ["latest"]:
            gen = self.repo.genspec(gen)
            started = self.format_time(0)
            ended = self.format_time(0)
            print 'Generation %s (%s - %s)' % (gen, started, ended)
            self.show_objects(gen, '/')
        self.repo.fs.close()
    
    def format_time(self, timestamp):
        return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))
    
    def isdir(self, gen, filename):
        metadata = self.repo.get_metadata(gen, filename)
        return metadata.isdir()
    
    def show_objects(self, gen, dirname):
        print
        print '%s:' % dirname
        subdirs = []
        everything = []
        for basename in self.repo.listdir(gen, dirname):
            fields = self.fields(gen, dirname, basename)
            full = os.path.join(dirname, basename)
            everything.append(fields)
            if self.isdir(gen, full):
                subdirs.append(full)

        if everything:
            widths = self.widths(everything)
            for fields in everything:
                print self.format(widths, fields)

        for subdir in subdirs:
            self.show_objects(gen, subdir)

    def fields(self, gen, dirname, basename):
        full = os.path.join(dirname, basename)
        metadata = self.repo.get_metadata(gen, full)

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
        mode = metadata.st_mode or 0
        for bitmap, offset, char in tab:
            if (mode & bitmap) == bitmap:
                perms[offset] = char
        perms = ''.join(perms)
        
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S', 
                                  time.gmtime(metadata.st_mtime_sec))

        if metadata.islink():
            name = '%s -> %s' % (basename, metadata.target)
        else:
            name = basename

        return (perms, 
                 str(metadata.st_nlink or 0), 
                 metadata.username or '', 
                 metadata.groupname or '',
                 str(metadata.st_size or 0), 
                 timestamp, 
                 name)

    def widths(self, everything):
        w = list(self.min_widths)
        for fields in everything:
            for i, field in enumerate(fields):
                w[i] = max(w[i], len(field))
        return w

    def format(self, widths, fields):
        return ' '. join(self.align(widths[i], fields[i], i)
                          for i in range(len(fields)))

    def align(self, width, field, field_no):
        if field_no in self.leftists:
            return '%-*s' % (width, field)
        else:
            return '%*s' % (width, field)

