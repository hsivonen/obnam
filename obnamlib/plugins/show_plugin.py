# Copyright (C) 2009  Lars Wirzenius
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

    def open_root(self):
        return self.store.get_object(0)

    def open_host(self):
        hostname = self.app.config['hostname']
        rootobj = self.open_root()
        for hostid in rootobj.hostids:
            hostobj = self.store.get_object(hostid)
            if hostobj.hostname == hostname:
                return hostobj
        raise obnamlib.AppException('Host %s not found in store' % hostname)

    def hosts(self, args):
        self.open_store()
        rootobj = self.open_root()
        for hostid in rootobj.hostids:
            hostobj = self.store.get_object(hostid)
            print hostobj.hostname
    
    def generations(self, args):
        self.open_store()
        hostobj = self.open_host()
        for genid in hostobj.genids:
            print genid

    def ls(self, args):
        self.open_store()
        for genid_str in args:
            gen = self.store.get_object(int(genid_str))
            self.show_objects(None, gen.fileids, gen.dirids)
    
    def show_objects(self, dirname, fileids, dirids):
        if dirname:
            print '%s:' % dirname
        fileobjs = [self.store.get_object(x) for x in fileids]
        dirobjs = [self.store.get_object(x) for x in dirids]
        items = [(x.basename, x) for x in fileobjs + dirobjs]
        for basename, obj in sorted(items):
            print self.format(obj)
        for dirobj in dirobjs:
            print
            self.show_objects(dirobj.basename, dirobj.fileids, dirobj.dirids)

    def format(self, obj):
        perms = ['?'] + ['-'] * 9
        tab = [
            (stat.S_IFREG, 0, '-'),
            (stat.S_IFDIR, 0, 'd'),
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
        mode = obj.st_mode or 0
        for bitmap, offset, char in tab:
            if (mode & bitmap) == bitmap:
                perms[offset] = char
        perms = ''.join(perms)
        
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S', 
                                  time.gmtime(obj.st_mtime))
        return ('%s %2d %-8s %-8s %5d %s %s' % 
                (perms, 
                 obj.st_nlink or 0, 
                 obj.username or '', 
                 obj.groupname or '',
                 obj.st_size or 0, 
                 timestamp, 
                 obj.basename or ''))

