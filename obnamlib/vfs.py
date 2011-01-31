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


import errno
import os
import stat
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
        self.baseurl = baseurl
        self.bytes_read = 0
        self.bytes_written = 0

    def connect(self):
        '''Connect to filesystem.'''
        
    def close(self):
        '''Close connection to filesystem.'''

    def reinit(self, new_baseurl, create=False):
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
        if self.isdir(dirname):
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
            is_dir = False
            try:
                st = self.lstat(os.path.join(top, name))
            except OSError, e:
                if e.errno != errno.ENOENT:
                    raise
            else:
                is_dir = stat.S_ISDIR(st.st_mode)
            if is_dir:
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

    def __init__(self):
        self.implementations = {}
        
    def register(self, scheme, implementation):
        if scheme in self.implementations:
            raise obnamlib.Error('URL scheme %s already registered' % scheme)
        self.implementations[scheme] = implementation

    def new(self, url):
        '''Create a new VFS appropriate for a given URL.'''
        scheme, netloc, path, params, query, fragment = urlparse.urlparse(url)
        if scheme in self.implementations:
            return self.implementations[scheme](url)
        raise obnamlib.Error('Unknown VFS type %s' % url)
            
            
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
    
    The directory indicated by basepath must exist, but must be empty
    at start.
    
    '''

    def test_abspath_returns_input_for_absolute_path(self):
        self.assertEqual(self.fs.abspath('/foo/bar'), '/foo/bar')

    def test_abspath_returns_absolute_path_for_relative_input(self):
        self.assertEqual(self.fs.abspath('foo'),
                         os.path.join(self.basepath, 'foo'))

    def test_abspath_normalizes_path(self):
        self.assertEqual(self.fs.abspath('foo/..'), self.basepath)

    def test_reinit_works(self):
        self.fs.chdir('/')
        self.fs.reinit(self.fs.baseurl)
        self.assertEqual(self.fs.getcwd(), self.basepath)

    def test_reinit_to_nonexistent_filename_raises_OSError(self):
        self.assertRaises(OSError, self.fs.reinit, '/thisdoesnotexist')

    def test_reinit_creates_target_if_requested(self):
        self.fs.chdir('/')
        new_baseurl = os.path.join(self.fs.baseurl, 'newdir')
        new_basepath = os.path.join(self.basepath, 'newdir')
        self.fs.reinit(new_baseurl, create=True)
        self.assertEqual(self.fs.getcwd(), new_basepath)

    def test_getcwd_returns_dirname(self):
        self.assertEqual(self.fs.getcwd(), self.basepath)

    def test_chdir_changes_only_fs_cwd_not_process_cwd(self):
        process_cwd = os.getcwd()
        self.fs.chdir('/')
        self.assertEqual(self.fs.getcwd(), '/')
        self.assertEqual(os.getcwd(), process_cwd)

    def test_chdir_to_nonexistent_raises_exception(self):
        self.assertRaises(OSError, self.fs.chdir, '/foobar')

    def test_chdir_to_relative_works(self):
        pathname = os.path.join(self.basepath, 'foo')
        os.mkdir(pathname)
        self.fs.chdir('foo')
        self.assertEqual(self.fs.getcwd(), pathname)

    def test_chdir_to_dotdot_works(self):
        pathname = os.path.join(self.basepath, 'foo')
        os.mkdir(pathname)
        self.fs.chdir('foo')
        self.fs.chdir('..')
        self.assertEqual(self.fs.getcwd(), self.basepath)

    def test_creates_lock_file(self):
        self.fs.lock('lock')
        self.assert_(self.fs.exists('lock'))

    def test_second_lock_fails(self):
        self.fs.lock('lock')
        self.assertRaises(Exception, self.fs.lock, 'lock')

    def test_lock_raises_oserror_without_eexist(self):
        def raise_it(relative_path, contents):
            e = OSError()
            e.errno = errno.EAGAIN
            raise e
        self.fs.write_file = raise_it
        self.assertRaises(OSError, self.fs.lock, 'foo')

    def test_unlock_removes_lock(self):
        self.fs.lock('lock')
        self.fs.unlock('lock')
        self.assertFalse(self.fs.exists('lock'))

    def test_exists_returns_false_for_nonexistent_file(self):
        self.assertFalse(self.fs.exists('foo'))

    def test_exists_returns_true_for_existing_file(self):
        self.fs.write_file('foo', '')
        self.assert_(self.fs.exists('foo'))

    def test_isdir_returns_false_for_nonexistent_file(self):
        self.assertFalse(self.fs.isdir('foo'))

    def test_isdir_returns_false_for_nondir(self):
        self.fs.write_file('foo', '')
        self.assertFalse(self.fs.isdir('foo'))

    def test_isdir_returns_true_for_existing_dir(self):
        self.fs.mkdir('foo')
        self.assert_(self.fs.isdir('foo'))

    def test_listdir_raises_oserror_if_directory_does_not_exist(self):
        self.assertRaises(OSError, self.fs.listdir, 'foo')

    def test_mkdir_raises_oserror_if_directory_exists(self):
        self.assertRaises(OSError, self.fs.mkdir, '.')

    def test_mkdir_raises_oserror_if_parent_does_not_exist(self):
        self.assertRaises(OSError, self.fs.mkdir, 'foo/bar')
    
    def test_makedirs_raises_oserror_when_directory_exists(self):
        self.fs.mkdir('foo')
        self.assertRaises(OSError, self.fs.makedirs, 'foo')
    
    def test_makedirs_creates_directory_when_parent_exists(self):
        self.fs.makedirs('foo')
        self.assert_(self.fs.isdir('foo'))
    
    def test_makedirs_creates_directory_when_parent_does_not_exist(self):
        self.fs.makedirs('foo/bar')
        self.assert_(self.fs.isdir('foo/bar'))

    def test_rmdir_removes_directory(self):
        self.fs.mkdir('foo')
        self.fs.rmdir('foo')
        self.assertFalse(self.fs.exists('foo'))

    def test_rmdir_raises_oserror_if_directory_does_not_exist(self):
        self.assertRaises(OSError, self.fs.rmdir, 'foo')

    def test_rmdir_raises_oserror_if_directory_is_not_empty(self):
        self.fs.mkdir('foo')
        self.fs.write_file('foo/bar', '')
        self.assertRaises(OSError, self.fs.rmdir, 'foo')

    def test_rmtree_removes_directory_tree(self):
        self.fs.mkdir('foo')
        self.fs.write_file('foo/bar', '')
        self.fs.rmtree('foo')
        self.assertFalse(self.fs.exists('foo'))

    def test_rmtree_is_silent_when_target_does_not_exist(self):
        self.assertEqual(self.fs.rmtree('foo'), None)

    def test_remove_removes_file(self):
        self.fs.write_file('foo', '')
        self.fs.remove('foo')
        self.assertFalse(self.fs.exists('foo'))

    def test_remove_raises_oserror_if_file_does_not_exist(self):
        self.assertRaises(OSError, self.fs.remove, 'foo')

    def test_rename_renames_file(self):
        self.fs.write_file('foo', 'xxx')
        self.fs.rename('foo', 'bar')
        self.assertFalse(self.fs.exists('foo'))
        self.assertEqual(self.fs.cat('bar'), 'xxx')

    def test_rename_raises_oserror_if_file_does_not_exist(self):
        self.assertRaises(OSError, self.fs.rename, 'foo', 'bar')

    def test_rename_works_if_target_exists(self):
        self.fs.write_file('foo', 'foo')
        self.fs.write_file('bar', 'bar')
        self.fs.rename('foo', 'bar')
        self.assertEqual(self.fs.cat('bar'), 'foo')

    def test_lstat_returns_result(self):
        self.assert_(self.fs.lstat('.'))

    def test_lstat_raises_oserror_for_nonexistent_entry(self):
        self.assertRaises(OSError, self.fs.lstat, 'notexists')

    def test_chmod_sets_permissions_correctly(self):
        self.fs.mkdir('foo')
        self.fs.chmod('foo', 0777)
        self.assertEqual(self.fs.lstat('foo').st_mode & 0777, 0777)

    def test_chmod_raises_oserror_for_nonexistent_entry(self):
        self.assertRaises(OSError, self.fs.chmod, 'notexists', 0)

    def test_lutimes_sets_times_correctly(self):
        self.fs.mkdir('foo')
        self.fs.lutimes('foo', 1, 2)
        self.assertEqual(self.fs.lstat('foo').st_atime, 1)
        self.assertEqual(self.fs.lstat('foo').st_mtime, 2)

    def test_lutimes_raises_oserror_for_nonexistent_entry(self):
        self.assertRaises(OSError, self.fs.lutimes, 'notexists', 1, 2)

    def test_link_creates_hard_link(self):
        self.fs.write_file('foo', 'foo')
        self.fs.link('foo', 'bar')
        st1 = self.fs.lstat('foo')
        st2 = self.fs.lstat('bar')
        self.assertEqual(st1, st2)

    def test_symlink_creates_soft_link(self):
        self.fs.symlink('foo', 'bar')
        target = self.fs.readlink('bar')
        self.assertEqual(target, 'foo')

    def test_symlink_raises_oserror_if_name_exists(self):
        self.fs.write_file('foo', 'foo')
        self.assertRaises(OSError, self.fs.symlink, 'bar', 'foo')

    def test_opens_existing_file_ok(self):
        self.fs.write_file('foo', '')
        self.assert_(self.fs.open('foo', 'w'))

    def test_open_fails_for_nonexistent_file(self):
        self.assertRaises(IOError, self.fs.open, 'foo', 'r')

    def test_cat_reads_existing_file_ok(self):
        self.fs.write_file('foo', 'bar')
        self.assertEqual(self.fs.cat('foo'), 'bar')

    def test_cat_fails_for_nonexistent_file(self):
        self.assertRaises(IOError, self.fs.cat, 'foo')
    
    def test_has_read_nothing_initially(self):
        self.assertEqual(self.fs.bytes_read, 0)
    
    def test_cat_updates_bytes_read(self):
        self.fs.write_file('foo', 'bar')
        self.fs.cat('foo')
        self.assertEqual(self.fs.bytes_read, 3)

    def test_write_fails_if_file_exists_already(self):
        self.fs.write_file('foo', 'bar')
        self.assertRaises(OSError, self.fs.write_file, 'foo', 'foobar')

    def test_write_creates_missing_directories(self):
        self.fs.write_file('foo/bar', 'yo')
        self.assertEqual(self.fs.cat('foo/bar'), 'yo')

    def test_write_leaves_existing_file_intact(self):
        self.fs.write_file('foo', 'bar')
        try:
            self.fs.write_file('foo', 'foobar')
        except OSError:
            pass
        self.assertEqual(self.fs.cat('foo'), 'bar')

    def test_overwrite_creates_new_file_ok(self):
        self.fs.overwrite_file('foo', 'bar')
        self.assertEqual(self.fs.cat('foo'), 'bar')

    def test_overwrite_renames_existing_file(self):
        self.fs.write_file('foo', 'bar')
        self.fs.overwrite_file('foo', 'foobar')
        self.assert_(self.fs.exists('foo.bak'))

    def test_overwrite_removes_existing_bak_file(self):
        self.fs.write_file('foo', 'bar')
        self.fs.write_file('foo.bak', 'baz')
        self.fs.overwrite_file('foo', 'foobar')
        self.assertEqual(self.fs.cat('foo.bak'), 'bar')

    def test_overwrite_removes_bak_file(self):
        self.fs.write_file('foo', 'bar')
        self.fs.overwrite_file('foo', 'foobar', make_backup=False)
        self.assertFalse(self.fs.exists('foo.bak'))

    def test_overwrite_is_ok_without_bak(self):
        self.fs.overwrite_file('foo', 'foobar', make_backup=False)
        self.assertFalse(self.fs.exists('foo.bak'))

    def test_overwrite_replaces_existing_file(self):
        self.fs.write_file('foo', 'bar')
        self.fs.overwrite_file('foo', 'foobar')
        self.assertEqual(self.fs.cat('foo'), 'foobar')
    
    def test_has_written_nothing_initially(self):
        self.assertEqual(self.fs.bytes_written, 0)
    
    def test_write_updates_written(self):
        self.fs.write_file('foo', 'foo')
        self.assertEqual(self.fs.bytes_written, 3)
    
    def test_overwrite_updates_written(self):
        self.fs.overwrite_file('foo', 'foo')
        self.assertEqual(self.fs.bytes_written, 3)

    def set_up_depth_first(self):
        self.dirs = ['foo', 'foo/bar', 'foobar']
        self.dirs = [os.path.join(self.basepath, x) for x in self.dirs]
        for dirname in self.dirs:
            self.fs.mkdir(dirname)
        self.dirs.insert(0, self.basepath)
        self.fs.symlink('foo', 'symfoo')
    
    def test_depth_first_finds_all_dirs(self):
        self.set_up_depth_first()
        dirs = [x[0] for x in self.fs.depth_first(self.basepath)]
        self.failUnlessEqual(sorted(dirs), sorted(self.dirs))

    def prune(self, dirname, dirnames, filenames):
        if 'foo' in dirnames:
            dirnames.remove('foo')

    def test_depth_first_finds_all_airs_except_the_pruned_one(self):
        self.set_up_depth_first()
        correct = [x 
                   for x in self.dirs 
                   if not x.endswith('/foo') and not '/foo/' in x]
        dirs = [x[0] 
                for x in self.fs.depth_first(self.basepath, prune=self.prune)]
        self.failUnlessEqual(sorted(dirs), sorted(correct))

    def test_depth_first_raises_oserror_if_directory_does_not_exist(self):
        self.assertRaises(OSError, list, self.fs.depth_first('notexist'))

