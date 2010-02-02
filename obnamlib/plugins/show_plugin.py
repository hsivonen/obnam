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
import time

import obnamlib


class ShowPlugin(obnamlib.ObnamPlugin):

    '''Show information about data in the backup store.
    
    This implements commands for listing contents of root and host
    objects, or the contents of a backup generation.
    
    '''

    def enable(self):
        self.app.register_command('hosts', self.hosts)
        self.app.register_command('generations', self.generations)
        self.app.register_command('ls', self.ls)

    def open_store(self):
        fsf = obnamlib.VfsFactory()
        self.store = obnamlib.Store(fsf.new(self.app.config['store']))
        self.store.open_host(self.app.config['hostname'])

    def hosts(self, args):
        self.open_store()
        for hostname in self.store.list_hosts():
            print hostname
    
    def generations(self, args):
        self.open_store()
        for gen in self.store.list_generations():
            print gen

    def ls(self, args):
        self.open_store()
        for gen in args:
            started = self.format_time(0)
            ended = self.format_time(0)
            print 'Generation %s (%s - %s)' % (gen, started, ended)
            self.show_objects(gen, '/')
    
    def format_time(self, timestamp):
        return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))
    
    def isdir(self, gen, filename):
        metadata = self.store.get_metadata(gen, filename)
        return metadata.isdir()
    
    def show_objects(self, gen, dirname):
        print
        print '%s:' % dirname
        subdirs = []
        for basename in self.store.listdir(gen, dirname):
            full = os.path.join(dirname, basename)
            print self.format(gen, dirname, basename)
            if self.isdir(gen, full):
                subdirs.append(full)
        for subdir in subdirs:
            self.show_objects(gen, subdir)

    def format(self, gen, dirname, basename):
        full = os.path.join(dirname, basename)
        metadata = self.store.get_metadata(gen, full)

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

