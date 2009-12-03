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

import obnamlib


# Implementation plan:
# 1. Back up everything, every time.
# 2. Back up only changed files, but completely.
# 3. Back up changes using rsync + looking up of chunks via checksums.



class BackupPlugin(obnamlib.ObnamPlugin):

    def enable(self):
        self.app.register_command('backup', self.backup)
        self.app.config.new_list(['root'], 'what to backup')
        
    def backup(self, args):
        roots = self.app.config['root'] + args
        self.app.hooks.call('status', 'roots %s' % roots)
        fsf = obnamlib.VfsFactory()
        storefs = fsf.new(self.app.config['store'])
        self.store = obnamlib.Store(storefs)
        for root in roots:
            self.fs = fsf.new(root)
            self.fs.connect()
            self.backup_something(root)
            self.fs.close()

    def backup_something(self, root):
        if self.fs.isdir(root):
            self.backup_dir(root)
        else:
            self.backup_file(root)

    def backup_file(self, root):
        self.app.hooks.call('status', 'backing up file %s' % root)
        stat_result = self.fs.lstat(root)
        fileobj = obnamlib.File(basename=os.path.basename(root),
                                metadata=stat_result)
        self.store.put_object(fileobj)
        return fileobj

    def backup_dir(self, root):
        self.app.hooks.call('status', 'backing up dir %s' % root)
        for basename in self.fs.listdir(root):
            fullname = os.path.join(root, basename)
            self.backup_something(fullname)

