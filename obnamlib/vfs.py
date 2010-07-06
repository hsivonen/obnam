# Copyright (C) 2008, 2010  Lars Wirzenius <liw@liw.fi>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


import os
import urlparse

import obnamlib


class VirtualFileSystem(object):

    '''A virtual filesystem interface.
    
    The backup program needs to access both local and remote files.
    To make it easier to support all kinds of files both locally and
    remotely, we use a custom virtual filesystem interface so that
    all filesystem access is done the same way. This way, we can
    easily support user data and backup stores in any combination of
    local and remote filesystems.

    This class defines the interface for such virtual filesystems.
    Sub-classes will actually implement the interface.

    When a VFS is instantiated, it is bound to a base URL. When
    accessing the virtual filesystem, all paths are then given
    relative to the base URL. The Unix syntax for files is used
    for the relative paths: directory components separated by
    slashes, and an initial slash indicating the root of the
    filesystem (in this case, the base URL).

    '''

    def __init__(self, baseurl):
        self.written = 0

    def connect(self):
        '''Connect to filesystem.'''
        
    def close(self):
        '''Close connection to filesystem.'''

    def reinit(self, new_baseurl):
        '''Go back to the beginning.
        
        This behaves like instantiating a new instance, but possibly
        faster for things like SftpFS. If there is a network
        connection already open, it will be reused.
        
        '''

    def abspath(self, pathname):
        '''Return absolute version of pathname.'''
        return os.path.abspath(os.path.join(self.getcwd(), pathname))

    def getcwd(self):
        '''Return current working directory as absolute pathname.'''
        
    def chdir(self, pathname):
        '''Change current working directory to pathname.'''

    def listdir(self, pathname):
        '''Return list of basenames of entities at pathname.'''

    def lock(self, lockname):
        '''Create a lock file with the given name.'''

    def unlock(self, lockname):
        '''Remove a lock file.'''

    def exists(self, pathname):
        '''Does the file or directory exist?'''

    def isdir(self, pathname):
        '''Is it a directory?'''

    def mkdir(self, pathname):
        '''Create a directory.
        
        Parent directories must already exist.
        
        '''
        
    def makedirs(self, pathname):
        '''Create a directory, and missing parents.'''

    def rmdir(self, pathname):
        '''Remove an empty directory.'''

    def rmtree(self, dirname):
        '''Remove a directory tree, including its contents.'''
        for dirname, dirnames, basenames in self.depth_first(dirname):
            for basename in basenames:
                self.remove(os.path.join(dirname, basename))
            self.rmdir(dirname)

    def remove(self, pathname):
        '''Remove a file.'''

    def rename(self, old, new):
        '''Rename a file.'''

    def lstat(self, pathname):
        '''Like os.lstat.'''

    def chown(self, pathname, uid, gid):
        '''Like os.chown.'''

    def chmod(self, pathname, mode):
        '''Like os.chmod.'''

    def lutimes(self, pathname, atime, mtime):
        '''Like lutimes(2).'''

    def link(self, existing_path, new_path):
        '''Like os.link.'''

    def readlink(self, symlink):
        '''Like os.readlink.'''

    def symlink(self, source, destination):
        '''Like os.symlink.'''

    def open(self, pathname, mode):
        '''Open a file, like the builtin open() or file() function.

        The return value is a file object like the ones returned
        by the builtin open() function.

        '''

    def cat(self, pathname):
        '''Return the contents of a file.'''

    def write_file(self, pathname, contents):
        '''Write a new file.

        The file must not yet exist. The file is written atomically,
        so that the given name will only exist when the file is
        completely written.
        
        Any directories in pathname will be created if necessary.

        '''

    def overwrite_file(self, pathname, contents, make_backup=True):
        '''Like write_file, but overwrites existing file.

        The old file isn't immediately lost, it gets renamed with
        a backup suffix. The backup file is removed if make_backup is
        set to False (default is True).

        '''

    def depth_first(self, top, prune=None):
        '''Walk a directory tree depth-first, except for unwanted subdirs.
        
        This is, essentially, 'os.walk(top, topdown=False)', except that
        if the prune argument is set, we call it before descending to 
        sub-directories to allow it to remove any directories and files
        the caller does not want to know about.
        
        If set, prune must be a function that gets three arguments (current
        directory, list of sub-directory names, list of files in directory),
        and must modify the two lists _in_place_. For example:
        
        def prune(dirname, dirnames, filenames):
            if '.bzr' in dirnames:
                dirnames.remove('.bzr')
        
        The dirnames and filenames lists contain basenames, relative to
        dirname.
        
        top is relative to VFS root, and so is the returned directory name.
        
        '''

        names = self.listdir(top)
        dirs = []
        nondirs = []
        for name in names:
            if self.isdir(os.path.join(top, name)):
                dirs.append(name)
            else:
                nondirs.append(name)
        if prune:
            prune(top, dirs, nondirs)
        for name in dirs:
            path = os.path.join(top, name)
            for x in self.depth_first(path, prune=prune):
                yield x
        yield top, dirs, nondirs
        
        
class VfsFactory:

    '''Create new instances of VirtualFileSystem.'''
    
    def new(self, url):
        '''Create a new VFS appropriate for a given URL.'''
        scheme, netloc, path, params, query, fragment = urlparse.urlparse(url)
        if scheme == 'sftp':
            return obnamlib.SftpFS(url)
        else:
            return obnamlib.LocalFS(url)
            
            
class VfsTests(object): # pragma: no cover

    '''Re-useable tests for VirtualFileSystem implementations.
    
    The base class can't be usefully instantiated itself.
    Instead you are supposed to sub-class it and implement the API in
    a suitable way for yourself.
    
    This class implements a number of tests that the API implementation
    must pass. The implementation's own test class should inherit from
    this class, and unittest.TestCase.
    
    The test sub-class should define a setUp method that sets the following:
    
    * self.fs to an instance of the API implementation sub-class
    * self.basepath to the path to the base of the filesystem
    
    basepath must be operable as a pathname using os.path tools. If
    the VFS implemenation operates remotely and wants to operate on a
    URL like 'http://domain/path' as the baseurl, then basepath must be
    just the path portion of the URL.
    
    '''

    def test_joins_relative_path_ok(self):
        self.assertEqual(self.fs.join('foo'), 
                         os.path.join(self.basepath, 'foo'))

    def test_join_treats_absolute_path_as_absolute(self):
        self.assertEqual(self.fs.join('/foo'), '/foo')

    def test_abspath_returns_input_for_absolute_path(self):
        self.assertEqual(self.fs.abspath('/foo/bar'), '/foo/bar')

    def test_abspath_returns_absolute_path_for_relative_input(self):
        self.assertEqual(self.fs.abspath('foo'),
                         os.path.join(self.dirname, 'foo'))

    def test_abspath_normalizes_path(self):
        self.assertEqual(self.fs.abspath('foo/..'), self.dirname)

    def test_reinit_works(self):
        self.fs.reinit('.')
        self.assertEqual(self.fs.cwd, os.getcwd())

    def test_getcwd_returns_dirname(self):
        self.assertEqual(self.fs.getcwd(), self.dirname)

    def test_chdir_changes_only_fs_cwd_not_process_cwd(self):
        process_cwd = os.getcwd()
        self.fs.chdir('/')
        self.assertEqual(self.fs.getcwd(), '/')
        self.assertEqual(os.getcwd(), process_cwd)

    def test_chdir_to_nonexistent_raises_exception(self):
        self.assertRaises(OSError, self.fs.chdir, '/foobar')

    def test_chdir_to_relative_works(self):
        pathname = os.path.join(self.dirname, 'foo')
        os.mkdir(pathname)
        self.fs.chdir('foo')
        self.assertEqual(self.fs.getcwd(), pathname)

    def test_chdir_to_dotdot_works(self):
        pathname = os.path.join(self.dirname, 'foo')
        os.mkdir(pathname)
        self.fs.chdir('foo')
        self.fs.chdir('..')
        self.assertEqual(self.fs.getcwd(), self.dirname)

