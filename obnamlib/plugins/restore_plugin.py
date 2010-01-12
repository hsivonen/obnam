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


import logging
import os
import stat

import obnamlib


class RestorePlugin(obnamlib.ObnamPlugin):

    def enable(self):
        self.app.register_command('restore', self.restore)

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

    def genid(self, genid_str):
        if genid_str == 'latest':
            return self.hostobj.genids[-1]
        return int(genid_str)
        
    def restore(self, args):
        fsf = obnamlib.VfsFactory()
        self.store = obnamlib.Store(fsf.new(self.app.config['store']))
        self.fs = fsf.new(args[0])
        self.hostobj = self.open_host()
        
        for genid_str in args[1:]:
            gen = self.store.get_object(self.genid(genid_str))
            self.restore_recursively(".", gen.dirids, gen.fileids)
    
    def restore_recursively(self, to_dir, dirids, fileids):
        for fileid in fileids:
            self.restore_file(to_dir, fileid)
        for dirid in dirids:
            dirobj = self.store.get_object(dirid)
            dirname = os.path.join(to_dir, dirobj.basename)
            if not self.fs.exists(dirname):
                self.fs.mkdir(dirname)
            self.restore_recursively(dirname, dirobj.dirids,dirobj.fileids)

    def restore_file(self, dirname, fileid):
        fileobj = self.store.get_object(fileid)
        filename = os.path.join(dirname, fileobj.basename)
        f = self.fs.open(filename, 'w')
        for chunkid in fileobj.chunkids:
            chunk = self.store.get_object(chunkid)
            f.write(chunk.data)
        f.close()

