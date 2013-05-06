# repo_interface.py -- interface class for repository access
#
# Copyright 2013  Lars Wirzenius
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
#
# =*= License: GPL-3+ =*=


import unittest

import obnamlib


# The following is a canonical list of all keys that can be used with
# the repository interface for key/value pairs. Not all formats need
# to support all keys, but they all must support the test keys, for
# the test suite to function.

REPO_CLIENT_TEST_KEY = 0

# The following is a key that is NOT allowed for any repository format.

WRONG_KEY = -1


class RepositoryClientListLockingFailed(obnamlib.Error):

    def __init__(self):
        self.msg = 'Repository client list could not be locked'


class RepositoryClientListNotLocked(obnamlib.Error):

    def __init__(self):
        self.msg = 'Repository client list is not locked'


class RepositoryClientAlreadyExists(obnamlib.Error):

    def __init__(self, client_name):
        self.msg = 'Repository client %s already exists' % client_name


class RepositoryClientDoesNotExist(obnamlib.Error):

    def __init__(self, client_name):
        self.msg = 'Repository client %s does not exist' % client_name


class RepositoryClientLockingFailed(obnamlib.Error):

    def __init__(self, client_name):
        self.msg = 'Repository client %s could not be locked' % client_name


class RepositoryClientNotLocked(obnamlib.Error):

    def __init__(self, client_name):
        self.msg = 'Repository client %s is not locked' % client_name


class RepositoryClientKeyNotAllowed(obnamlib.Error):

    def __init__(self, format, client_name, key):
        self.msg = (
            'Client %s uses repository format %s '
            'which does not allow the key %s to be use for clients' %
            (format, client_name, key))


class RepositoryClientGenerationUnfinished(obnamlib.Error):

    def __init__(self, client_name):
        self.msg = (
            'Cannot start new generation for %s: '
            'previous one is not finished yet (programming error)' %
            client_name)


class RepositoryInterface(object):

    '''Abstract interface to Obnam backup repositories.

    An Obnam backup repository stores backups for backup clients.
    As development of Obnam progresses, the details of how things
    are stored can change. This is usually necessary for performance
    improvements.

    To allow Obnam to access, both for reading and writing, any
    version of the repository format, this class defines an interface
    for repository access. Every different version of the format
    implements a class with this interface, so that the rest of
    Obnam can just use the interface.

    The interface is suitably high level that using the repository
    is convenient, and that it allows a variety of implementations.
    At the same time it concentrates on the needs of repository
    access only.

    The interface also specifies the interface with which the
    implementation accesses the actual filesystem: it is the
    Obnam VFS layer.

        [rest of Obnam code]
                |
                | calls RepositoryInterface API
                |
                V
        [RepositoryFormatX implementing RepositoryInterface API]
                |
                | calls VFS API
                |
                V
        [FooFS implementing VirtualFileSystem API]

    The VFS API implementation is given to the RepositoryInterface
    implementation with the ``set_fs`` method.

    It must be stressed that ALL access to the repository go via
    an implemention of RepositoryInterface. Further, all the
    implementation classes must be instantiated via RepositoryFactory.

    The abstraction RepositoryInterface provides for repositories
    consists of a few key concepts:

    * A repository contains data about one or more clients.
    * For each client, there is some metadata, plus a list of generations.
    * For each generation, there is some metadata, plus a list of
      files (where directories are treated as files).
    * For each file, there is some metadata, plus a list of chunk
      identifiers.
    * File contents data is split into chunks, each given a unique
      identifier.
    * There is optionally some indexing for content based lookups of
      chunks (e.g., look up chunks based on an MD5 checksum).
    * There are three levels of locking: the list of clients,
      the per-client data (information about generations), and
      the chunk lookup indexes are all locked up individually.
    * All metadata is stored as key/value pairs, where the key is
      one of a strictly limited, version-specific list of allowed ones,
      and the value is a binary string. All allowed keys are
      implicitly set to the empty string if not set otherwise.

    Further, the repository format version implementation is given
    a directory in which it stores the repository, using any number
    of files it wishes. No other files will be in that directory.
    (RepositoryFactory creates the actual directory.) The only
    restriction is that within that directory, the
    ``metadata/format``file MUST be a plain text file (no encryption,
    compression), containing a single line, giving the format
    of the repository, as an arbitrary string. Each RepositoryInterface
    implementation will work with exactly one such format, and have
    a class attribute ``format`` which contains the string.

    There is no method to remove a repository. This is handled
    externally by removing the repository directory and all its files.
    Since that code is generic, it is not needed in the interface.

    Each RepositoryInterface implementation can have a custom
    initialiser. RepositoryFactory will know how to call it,
    giving it all the information it needs.

    '''

    # Operations on the repository itself.

    def set_fs(self, fs):
        '''Set the Obnam VFS instance for accessing the filesystem.'''
        raise NotImplementedError()

    def init_repo(self):
        '''Initialize a nearly-empty directory for this format version.

        The repository will contain the file ``metadata/format``,
        with the right contents, but nothing else.

        '''

        raise NotImplementedError()

    # Client list.

    def get_client_names(self):
        '''Return list of client names currently existing in the repository.'''
        raise NotImplementedError()

    def lock_client_list(self):
        '''Lock the client list for changes.'''
        raise NotImplementedError()

    def commit_client_list(self):
        '''Commit changes to client list and unlock it.'''
        raise NotImplementedError()

    def unlock_client_list(self):
        '''Forget changes to client list and unlock it.'''
        raise NotImplementedError()

    def force_client_list_lock(self):
        '''Force the client list lock.

        If the process that locked the client list is dead, this method
        forces the lock open and takes it for the calling process instead.
        Any uncommitted changes by the original locker will be lost.

        '''
        raise NotImplementedError()

    def add_client(self, client_name):
        '''Add a client to the client list.

        Raise RepositoryClientAlreadyExists if the client already exists.

        '''
        raise NotImplementedError()

    def remove_client(self, client_name):
        '''Remove a client from the client list.'''
        raise NotImplementedError()

    def rename_client(self, old_client_name, new_client_name):
        '''Rename a client to have a new name.'''
        raise NotImplementedError()

    # A particular client.

    def lock_client(self, client_name):
        '''Lock the client for changes.

        This lock must be taken for any changes to the per-client
        data, including any changes to backup generations for the
        client.

        '''
        raise NotImplementedError()

    def commit_client(self, client_name):
        '''Commit changes to client and unlock it.'''
        raise NotImplementedError()

    def unlock_client(self, client_name):
        '''Forget changes to client and unlock it.'''
        raise NotImplementedError()

    def force_client_lock(self, client_name):
        '''Force the client lock.

        If the process that locked the client is dead, this method
        forces the lock open and takes it for the calling process instead.
        Any uncommitted changes by the original locker will be lost.

        '''
        raise NotImplementedError()

    def get_allowed_client_keys(self):
        '''Return list of allowed per-client keys for thist format.'''
        raise NotImplementedError()

    def get_client_key(self, client_name, key):
        '''Return current value of a key for a given client.

        If not set explicitly, the value is the empty string.
        If the key is not in the list of allowed keys for this
        format, raise RepositoryClientKeyNotAllowed.

        '''
        raise NotImplementedError()

    def set_client_key(self, client_name, key, value):
        '''Set value for a per-client key.'''
        raise NotImplementedError()

    def get_client_generation_ids(self, client_name):
        '''Return a list of opague ids for generations in a client.

        The list is ordered: the first id in the list is the oldest
        generation. The ids needs not be sortable, and they may or
        may not be simple types.

        '''
        raise NotImplementedError()

    def create_generation(self, client_name):
        '''Start a new generation for a client.

        Return the generation id for the new generation. The id
        implicitly also identifies the client.

        '''
        raise NotImplementedError()

    ## Generations. The generation id identifies client as well.
    #def get_generation_keys(self, generation_id):
    #def get_generation_key_value(self, generation_id, key):
    #def set_generation_key_value(self, generation_id, key, value):
    #def remove_generation_key(self, generation_id, key):
    #def remove_generation(self, generation_id):
    #def get_chunk_ids_in_generation(self, generation_id):
    #def interpret_generation_spec(self, genspec): # returns generation id
    #def walk_generation(self, generation_id, filename): # generator

    ## Individual files and directories in a generation.
    #def file_exists(self, generation_id, filename):
    #def add_file(self, generation_id, filename):
    #def remove_file(self, generation_id, filename):
    #def get_file_keys(self, generation_id, filename):
    #def get_file_key_value(self, generation_id, filename, key):
    #def set_file_key_value(self, generation_id, filename, key, value):
    #def remove_file_key(self, generation_id, filename, key):
    #def get_file_chunk_ids(self, generation_id, filename):
    #def clear_file_chunk_ids(self, generation_id, filename):
    #def append_file_chunk_id(self, generation_id, filename, chunk_id):
    #def get_file_children(self, generation_id, filename):

    ## Chunks.
    #def put_chunk_content(self, data): # return new chunk_id
    #def get_chunk_content(self, chunk_id):
    #def lock_chunk_indexes(self):
    #def unlock_chunk_indexes(self):
    #def force_chunk_index_lock(self):
    #def put_chunk_into_indexes(self, chunk_id, data):
    #def find_chunk_id_by_content(self, data):
    #def remove_chunk(self, chunk_id):

    ## Fsck.
    #def get_fsck_work_items(self):


class RepositoryInterfaceTests(unittest.TestCase): # pragma: no cover

    '''Tests for implementations of RepositoryInterface.

    Each implementation of RepositoryInterface should have a corresponding
    test class, which inherits this class. The test subclass must set
    ``self.repo`` to an instance of the class to be tested. The repository
    must be empty and uninitialised.

    '''

    # Tests for repository level things.

    def test_has_format_attribute(self):
        self.assertEqual(type(self.repo.format), str)

    def test_has_set_fs_method(self):
        # We merely test that set_fs can be called.
        self.assertEqual(self.repo.set_fs(None), None)

    # Tests for the client list.

    def test_has_no_clients_initially(self):
        self.repo.init_repo()
        self.assertEqual(self.repo.get_client_names(), [])

    def test_adds_a_client(self):
        self.repo.init_repo()
        self.repo.lock_client_list()
        self.repo.add_client('foo')
        self.assertEqual(self.repo.get_client_names(), ['foo'])

    def test_renames_a_client(self):
        self.repo.init_repo()

        self.repo.lock_client_list()
        self.repo.add_client('foo')
        self.repo.commit_client_list()

        self.repo.lock_client_list()
        self.repo.rename_client('foo', 'bar')
        self.assertEqual(self.repo.get_client_names(), ['bar'])

    def test_removes_a_client(self):
        self.repo.init_repo()
        self.repo.lock_client_list()
        self.repo.add_client('foo')
        self.repo.remove_client('foo')
        self.assertEqual(self.repo.get_client_names(), [])

    def test_fails_adding_existing_client(self):
        self.repo.init_repo()
        self.repo.lock_client_list()
        self.repo.add_client('foo')
        self.assertRaises(
            obnamlib.RepositoryClientAlreadyExists,
            self.repo.add_client, 'foo')

    def test_fails_renaming_nonexistent_client(self):
        self.repo.init_repo()
        self.repo.lock_client_list()
        self.assertRaises(
            obnamlib.RepositoryClientDoesNotExist,
            self.repo.rename_client, 'foo', 'bar')

    def test_fails_renaming_to_existing_client(self):
        self.repo.init_repo()

        self.repo.lock_client_list()
        self.repo.add_client('foo')
        self.repo.add_client('bar')
        self.repo.commit_client_list()

        self.repo.lock_client_list()
        self.assertRaises(
            obnamlib.RepositoryClientAlreadyExists,
            self.repo.rename_client, 'foo', 'bar')

    def test_fails_removing_nonexistent_client(self):
        self.repo.init_repo()
        self.repo.lock_client_list()
        self.assertRaises(
            obnamlib.RepositoryClientDoesNotExist,
            self.repo.remove_client, 'foo')

    def test_raises_lock_error_if_adding_client_without_locking(self):
        self.repo.init_repo()
        self.assertRaises(
            obnamlib.RepositoryClientListNotLocked,
            self.repo.add_client, 'foo')

    def test_raises_lock_error_if_renaming_client_without_locking(self):
        self.repo.init_repo()
        self.repo.lock_client_list()
        self.repo.add_client('foo')
        self.repo.commit_client_list()
        self.assertRaises(
            obnamlib.RepositoryClientListNotLocked,
            self.repo.rename_client, 'foo', 'bar')

    def test_raises_lock_error_if_removing_client_without_locking(self):
        self.repo.init_repo()
        self.assertRaises(
            obnamlib.RepositoryClientListNotLocked,
            self.repo.remove_client, 'foo')

    def test_unlocking_client_list_does_not_add_client(self):
        self.repo.init_repo()
        self.repo.lock_client_list()
        self.repo.add_client('foo')
        self.repo.unlock_client_list()
        self.assertEqual(self.repo.get_client_names(), [])

    def test_unlocking_client_list_does_not_rename_client(self):
        self.repo.init_repo()

        self.repo.lock_client_list()
        self.repo.add_client('foo')
        self.repo.commit_client_list()

        self.repo.lock_client_list()
        self.repo.rename_client('foo', 'bar')
        self.repo.unlock_client_list()

        self.assertEqual(self.repo.get_client_names(), ['foo'])

    def test_unlocking_client_list_does_not_remove_client(self):
        self.repo.init_repo()

        self.repo.lock_client_list()
        self.repo.add_client('foo')
        self.repo.commit_client_list()

        self.repo.lock_client_list()
        self.repo.remove_client('foo')
        self.repo.unlock_client_list()

        self.assertEqual(self.repo.get_client_names(), ['foo'])

    def test_committing_client_list_adds_client(self):
        self.repo.init_repo()
        self.repo.lock_client_list()
        self.repo.add_client('foo')
        self.repo.commit_client_list()
        self.assertEqual(self.repo.get_client_names(), ['foo'])

    def test_committing_client_list_renames_client(self):
        self.repo.init_repo()

        self.repo.lock_client_list()
        self.repo.add_client('foo')
        self.repo.commit_client_list()

        self.repo.lock_client_list()
        self.repo.rename_client('foo', 'bar')
        self.repo.commit_client_list()

        self.assertEqual(self.repo.get_client_names(), ['bar'])

    def test_commiting_client_list_removes_client(self):
        self.repo.init_repo()

        self.repo.lock_client_list()
        self.repo.add_client('foo')
        self.repo.commit_client_list()

        self.repo.lock_client_list()
        self.repo.remove_client('foo')
        self.repo.commit_client_list()

        self.assertEqual(self.repo.get_client_names(), [])

    def test_commiting_client_list_removes_lock(self):
        self.repo.init_repo()

        self.repo.lock_client_list()
        self.repo.commit_client_list()

        self.repo.lock_client_list()
        self.assertEqual(self.repo.get_client_names(), [])

    def test_unlocking_client_list_removes_lock(self):
        self.repo.init_repo()

        self.repo.lock_client_list()
        self.repo.unlock_client_list()

        self.repo.lock_client_list()
        self.assertEqual(self.repo.get_client_names(), [])

    def test_locking_client_list_twice_fails(self):
        self.repo.init_repo()
        self.repo.lock_client_list()
        self.assertRaises(
            obnamlib.RepositoryClientListLockingFailed,
            self.repo.lock_client_list)

    def test_unlocking_client_list_when_unlocked_fails(self):
        self.repo.init_repo()
        self.assertRaises(
            obnamlib.RepositoryClientListNotLocked,
            self.repo.unlock_client_list)

    def test_committing_client_list_when_unlocked_fails(self):
        self.repo.init_repo()
        self.assertRaises(
            obnamlib.RepositoryClientListNotLocked,
            self.repo.commit_client_list)

    def test_forces_client_list_lock(self):
        self.repo.init_repo()
        self.repo.lock_client_list()
        self.repo.add_client('bar')
        self.repo.force_client_list_lock()
        self.repo.add_client('foo')
        self.assertEqual(self.repo.get_client_names(), ['foo'])

    # Tests for client specific stuff.

    def setup_client(self):
        self.repo.lock_client_list()
        self.repo.add_client('fooclient')
        self.repo.commit_client_list()

    def test_locking_client_twice_fails(self):
        self.setup_client()
        self.repo.lock_client('fooclient')
        self.assertRaises(
            obnamlib.RepositoryClientLockingFailed,
            self.repo.lock_client, 'fooclient')

    def test_unlocking_client_when_unlocked_fails(self):
        self.setup_client()
        self.assertRaises(
            obnamlib.RepositoryClientNotLocked,
            self.repo.unlock_client, 'fooclient')

    def test_committing_client_when_unlocked_fails(self):
        self.setup_client()
        self.assertRaises(
            obnamlib.RepositoryClientNotLocked,
            self.repo.commit_client, 'fooclient')

    def test_unlocking_nonexistent_client_fails(self):
        self.setup_client()
        self.assertRaises(
            obnamlib.RepositoryClientDoesNotExist,
            self.repo.unlock_client, 'notexist')

    def test_committing_nonexistent_client_fails(self):
        self.setup_client()
        self.assertRaises(
            obnamlib.RepositoryClientDoesNotExist,
            self.repo.commit_client, 'notexist')

    def test_unlocking_client_removes_lock(self):
        self.setup_client()
        self.repo.lock_client('fooclient')
        self.repo.unlock_client('fooclient')
        self.assertEqual(self.repo.lock_client('fooclient'), None)

    def test_committing_client_removes_lock(self):
        self.setup_client()
        self.repo.lock_client('fooclient')
        self.repo.commit_client('fooclient')
        self.assertEqual(self.repo.lock_client('fooclient'), None)

    def test_has_list_of_allowed_client_keys(self):
        self.assertEqual(type(self.repo.get_allowed_client_keys()), list)

    def test_gets_all_allowed_client_keys(self):
        self.setup_client()
        for key in self.repo.get_allowed_client_keys():
            value = self.repo.get_client_key('fooclient', key)
            self.assertEqual(type(value), str)

    def test_has_empty_string_for_test_key(self):
        self.setup_client()
        value = self.repo.get_client_key(
            'fooclient', obnamlib.REPO_CLIENT_TEST_KEY)
        self.assertEqual(value, '')

    def test_sets_client_key(self):
        self.setup_client()
        self.repo.lock_client('fooclient')
        self.repo.set_client_key(
            'fooclient', obnamlib.REPO_CLIENT_TEST_KEY, 'bar')
        value = self.repo.get_client_key(
            'fooclient', obnamlib.REPO_CLIENT_TEST_KEY)
        self.assertEqual(value, 'bar')

    def test_setting_unallowed_key_fails(self):
        self.setup_client()
        self.repo.lock_client('fooclient')
        self.assertRaises(
            obnamlib.RepositoryClientKeyNotAllowed,
            self.repo.set_client_key, 'fooclient', WRONG_KEY, '')

    def test_setting_client_key_without_locking_fails(self):
        self.setup_client()
        self.assertRaises(
            obnamlib.RepositoryClientNotLocked,
            self.repo.set_client_key,
            'fooclient', obnamlib.REPO_CLIENT_TEST_KEY, 'bar')

    def test_committing_client_preserves_key_changs(self):
        self.setup_client()
        self.repo.lock_client('fooclient')
        self.repo.set_client_key(
            'fooclient', obnamlib.REPO_CLIENT_TEST_KEY, 'bar')
        value = self.repo.get_client_key(
            'fooclient', obnamlib.REPO_CLIENT_TEST_KEY)
        self.repo.commit_client('fooclient')
        self.assertEqual(value, 'bar')

    def test_unlocking_client_undoes_key_changes(self):
        self.setup_client()
        self.repo.lock_client('fooclient')
        self.repo.set_client_key(
            'fooclient', obnamlib.REPO_CLIENT_TEST_KEY, 'bar')
        self.repo.unlock_client('fooclient')
        value = self.repo.get_client_key(
            'fooclient', obnamlib.REPO_CLIENT_TEST_KEY)
        self.assertEqual(value, '')

    def test_getting_client_key_for_unknown_client_fails(self):
        self.setup_client()
        self.assertRaises(
            obnamlib.RepositoryClientDoesNotExist,
            self.repo.get_client_key, 'notexistclient',
            obnamlib.REPO_CLIENT_TEST_KEY)

    def test_new_client_has_no_generations(self):
        self.setup_client()
        self.assertEqual(self.repo.get_client_generation_ids('fooclient'), [])

    def test_creates_new_generation(self):
        self.setup_client()
        self.repo.lock_client('fooclient')
        new_id = self.repo.create_generation('fooclient')
        self.assertEqual(
            self.repo.get_client_generation_ids('fooclient'),
            [new_id])

    def test_creating_generation_fails_current_generation_unfinished(self):
        self.setup_client()
        self.repo.lock_client('fooclient')
        self.repo.create_generation('fooclient')
        self.assertRaises(
            obnamlib.RepositoryClientGenerationUnfinished,
            self.repo.create_generation, 'fooclient')

    def test_creating_generation_fails_if_client_is_unlocked(self):
        self.setup_client()
        self.assertRaises(
            obnamlib.RepositoryClientNotLocked,
            self.repo.create_generation, 'fooclient')

    def test_unlocking_client_removes_created_generation(self):
        self.setup_client()
        self.repo.lock_client('fooclient')
        new_id = self.repo.create_generation('fooclient')
        self.repo.unlock_client('fooclient')
        self.assertEqual(self.repo.get_client_generation_ids('fooclient'), [])

    def test_committing_client_keeps_created_generation(self):
        self.setup_client()
        self.repo.lock_client('fooclient')
        new_id = self.repo.create_generation('fooclient')
        self.repo.commit_client('fooclient')
        self.assertEqual(
            self.repo.get_client_generation_ids('fooclient'),
            [new_id])

