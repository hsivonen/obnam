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

    def enable(self):
        self.app.register_command('clients', self.clients)
        self.app.register_command('generations', self.generations)
        self.app.register_command('genids', self.genids)
        self.app.register_command('ls', self.ls)

    def open_repository(self):
        self.app.config.require('repository')
        self.app.config.require('client-name')
        fs = self.app.fsf.new(self.app.config['repository'])
        fs.connect()
        self.repo = obnamlib.Repository(fs, self.app.config['node-size'], 
                                        self.app.config['upload-queue-size'],
                                        self.app.config['lru-size'])
        self.repo.open_client(self.app.config['client-name'])

    def clients(self, args):
        self.open_repository()
        for client_name in self.repo.list_clients():
            print client_name
    
    def generations(self, args):
        self.open_repository()
        for gen in self.repo.list_generations():
            start, end = self.repo.get_generation_times(gen)
            is_checkpoint = self.repo.get_is_checkpoint(gen)
            if is_checkpoint:
                checkpoint = ' (checkpoint)'
            else:
                checkpoint = ''
            sys.stdout.write('%s\t%s .. %s%s\n' %
                             (gen, 
                              self.format_time(start), 
                              self.format_time(end),
                              checkpoint))
    
    def genids(self, args):
        self.open_repository()
        for gen in self.repo.list_generations():
            sys.stdout.write('%s\n' % gen)

    def ls(self, args):
        self.open_repository()
        for gen in args or ["latest"]:
            gen = self.repo.genspec(gen)
            started = self.format_time(0)
            ended = self.format_time(0)
            print 'Generation %s (%s - %s)' % (gen, started, ended)
            self.show_objects(gen, '/')
    
    def format_time(self, timestamp):
        return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))
    
    def isdir(self, gen, filename):
        metadata = self.repo.get_metadata(gen, filename)
        return metadata.isdir()
    
    def show_objects(self, gen, dirname):
        print
        print '%s:' % dirname
        subdirs = []
        for basename in self.repo.listdir(gen, dirname):
            full = os.path.join(dirname, basename)
            print self.format(gen, dirname, basename)
            if self.isdir(gen, full):
                subdirs.append(full)
        for subdir in subdirs:
            self.show_objects(gen, subdir)

    def format(self, gen, dirname, basename):
        full = os.path.join(dirname, basename)
        metadata = self.repo.get_metadata(gen, full)

        perms = ['?'] + ['-'] * 9
        tab = [
            (stat.S_IFREG, 0, '-'),
            (stat.S_IFDIR, 0, 'd'),
            (stat.S_IFLNK, 0, 'l'),
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
                                  time.gmtime(metadata.st_mtime))

        if metadata.islink():
            name = '%s -> %s' % (basename, metadata.target)
        else:
            name = basename

        return ('%s %2d %-8s %-8s %5d %s %s' % 
                (perms, 
                 metadata.st_nlink or 0, 
                 metadata.username or '', 
                 metadata.groupname or '',
                 metadata.st_size or 0, 
                 timestamp, 
                 name))

