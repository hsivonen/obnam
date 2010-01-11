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
import time

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
        started = int(time.time())
        roots = self.app.config['root'] + args
        fsf = obnamlib.VfsFactory()
        storefs = fsf.new(self.app.config['store'])
        self.store = obnamlib.Store(storefs)
        self.done = 0
        self.total = 0
        rootobjs = []
        for root in roots:
            self.fs = fsf.new(root)
            self.fs.connect()
            rootobjs.append(self.backup_something(self.fs.abspath('.')))
            self.fs.close()
        self.app.hooks.call('progress-found-file', None, 0)
        ended = int(time.time())

        self.finish(rootobjs, started, ended)

    def backup_something(self, root):
        if self.fs.isdir(root):
            return self.backup_dir(root)
        else:
            return self.backup_file(root)

    def backup_file(self, root):
        metadata = obnamlib.read_metadata(self.fs, root)
        self.app.hooks.call('progress-found-file', root, metadata.st_size)
        if stat.S_ISREG(metadata.st_mode):
            chunks = self.backup_file_contents(root)
        else:
            chunks = []
        fileobj = obnamlib.File(basename=os.path.basename(root),
                                metadata=metadata,
                                chunkids=[c.id for c in chunks])
        self.store.put_object(fileobj)
        return fileobj

    def backup_file_contents(self, filename):
        chunks = []
        f = self.fs.open(filename, 'r')
        while True:
            data = f.read(self.app.config['chunk-size'])
            if not data:
                break
            chunk = obnamlib.Chunk(data=data)
            self.store.put_object(chunk)
            chunks.append(chunk)
            self.app.hooks.call('progress-data-done', len(data))
        f.close()
        return chunks

    def backup_dir(self, root):
        fileids = []
        dirids = []
        for basename in self.fs.listdir(root):
            fullname = os.path.join(root, basename)
            obj = self.backup_something(fullname)
            if isinstance(obj, obnamlib.File):
                fileids.append(obj.id)
            else:
                dirids.append(obj.id)
        dirobj = obnamlib.Dir(basename=os.path.basename(root),
                              metadata=obnamlib.read_metadata(self.fs, root),
                              dirids=dirids,
                              fileids=fileids)
        self.store.put_object(dirobj)
        return dirobj

    def finish(self, rootobjs, started, ended):
        fileids = [o.id for o in rootobjs if isinstance(o, obnamlib.File)]
        dirids = [o.id for o in rootobjs if isinstance(o, obnamlib.Dir)]
        gen = obnamlib.Generation(fileids=fileids, dirids=dirids,
                                  started=started, ended=ended)
        self.store.put_object(gen)
        host = obnamlib.Host(hostname=self.app.config['hostname'], 
                             genids=[gen.id])
        self.store.put_object(host)
        rootobj = obnamlib.Root(hostids=[host.id])
        rootobj.id = 0
        self.store.put_object(rootobj)

