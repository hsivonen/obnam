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
        self.app.register_command('restore', self.restore)
        self.app.config.new_string(['to'], 'where to restore')
        self.app.config.new_string(['generation'], 
                                   'which generation to restore')
        self.app.config['generation'] = 'latest'

    def restore(self, args):
        logging.debug('restoring generation %s' % 
                        self.app.config['generation'])
        if not self.app.config['generation']:
            raise obnamlib.AppException('--generation option must be used '
                                        'with restore')

        logging.debug('restoring to %s' % self.app.config['to'])
        if not self.app.config['to']:
            raise obnamlib.AppException('--to option must be used '
                                        'with restore')
    
        logging.debug('restoring what: %s' % repr(args))
        if not args:
            logging.debug('no args given, so restoring everything')
            args = ['/']
    
        fs = self.app.fsf.new(self.app.config['store'])
        self.store = obnamlib.Store(fs)
        self.store.open_host(self.app.config['hostname'])
        self.fs = self.app.fsf.new(self.app.config['to'])

        self.hardlinks = Hardlinks()
        
        gen = self.store.genspec(self.app.config['generation'])
        for arg in args:
            metadata = self.store.get_metadata(gen, arg)
            if metadata.isdir():
                self.restore_recursively(gen, '.', arg)
            else:
                dirname = os.path.dirname(arg)
                if not self.fs.exists('./' + dirname):
                    self.fs.makedirs('./' + dirname)
                self.restore_file(gen, '.', arg)

    def restore_recursively(self, gen, to_dir, root):
        logging.debug('restoring dir %s' % root)
        if not self.fs.exists('./' + root):
            self.fs.makedirs('./' + root)
        for basename in self.store.listdir(gen, root):
            full = os.path.join(root, basename)
            metadata = self.store.get_metadata(gen, full)
            if metadata.isdir():
                self.restore_recursively(gen, to_dir, full)
            else:
                self.restore_file(gen, to_dir, full)
        metadata = self.store.get_metadata(gen, root)
        obnamlib.set_metadata(self.fs, './' + root, metadata)

    def restore_file(self, gen, to_dir, filename):
        metadata = self.store.get_metadata(gen, filename)
        if metadata.islink():
            self.restore_symlink(gen, to_dir, filename, metadata)
        elif metadata.st_nlink > 1:
            link = self.hardlinks.filename(metadata)
            if link:
                self.restore_hardlink(to_dir, filename, link, metadata)
            else:
                self.hardlinks.add(filename, metadata)
                self.restore_regular_file(gen, to_dir, filename, metadata)
        else:
            self.restore_regular_file(gen, to_dir, filename, metadata)
    
    def restore_hardlink(self, to_dir, filename, link, metadata):
        logging.debug('restoring hardlink %s to %s' % (filename, link))
        to_filename = os.path.join(to_dir, './' + filename)
        to_link = os.path.join(to_dir, './' + link)
        logging.debug('to_filename: %s' % to_filename)
        logging.debug('to_link: %s' % to_link)
        self.fs.link(to_link, to_filename)
        self.hardlinks.forget(metadata)
        
    def restore_symlink(self, gen, to_dir, filename, metadata):
        logging.debug('restoring symlink %s' % filename)
        to_filename = os.path.join(to_dir, './' + filename)
        obnamlib.set_metadata(self.fs, to_filename, metadata)
        
    def restore_regular_file(self, gen, to_dir, filename, metadata):
        logging.debug('restoring regular %s' % filename)
        to_filename = os.path.join(to_dir, './' + filename)
        f = self.fs.open(to_filename, 'w')

        chunkids = self.store.get_file_chunks(gen, filename)
        if chunkids:
            self.restore_chunks(f, chunkids)
        else:
            cgids = self.store.get_file_chunk_groups(gen, filename)
            for cgid in cgids:
                chunkids = self.store.get_chunk_group(cgid)
                self.restore_chunks(f, chunkids)

        f.close()
        obnamlib.set_metadata(self.fs, to_filename, metadata)

    def restore_chunks(self, f, chunkids):
        for chunkid in chunkids:
            data = self.store.get_chunk(chunkid)
            f.write(data)

