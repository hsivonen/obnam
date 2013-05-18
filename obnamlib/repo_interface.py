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

REPO_CLIENT_TEST_KEY            = 0     # string
REPO_GENERATION_TEST_KEY        = 1     # string

REPO_FILE_TEST_KEY              = 2     # string
REPO_FILE_MTIME                 = 3     # integer

REPO_FILE_INTEGER_KEYS = (
    REPO_FILE_MTIME,
)

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


class RepositoryGenerationKeyNotAllowed(obnamlib.Error):

    def __init__(self, format, client_name, key):
        self.msg = (
            'Client %s uses repository format %s '
            'which does not allow the key %s to be use for generations' %
            (format, client_name, key))


class RepositoryGenerationDoesNotExist(obnamlib.Error):

    def __init__(self, client_name):
        self.msg = (
            'Cannot find requested generation for client %s' %
            client_name)


class RepositoryClientHasNoGenerations(obnamlib.Error):

    def __init__(self, client_name):
        self.msg = 'Client %s has no generations' % client_name


class RepositoryFileDoesNotExistInGeneration(obnamlib.Error):

    def __init__(self, client_name, genspec, filename):
        self.msg = (
            'Client %s, generation %s does not have file %s' %
            (client_name, genspec, filename))


class RepositoryFileKeyNotAllowed(obnamlib.Error):

    def __init__(self, format, client_name, key):
        self.msg = (
            'Client %s uses repository format %s '
            'which does not allow the key %s to be use for files' %
            (client_name, format, key))


class RepositoryChunkDoesNotExist(obnamlib.Error):

    def __init__(self, chunk_id_as_string):
        self.msg = "Repository doesn't contain chunk %s" % chunk_id_as_string


class RepositoryChunkContentNotInIndexes(obnamlib.Error):

    def __init__(self):
        self.msg = "Repository chunk indexes do not contain content"


class RepositoryChunkIndexesNotLocked(obnamlib.Error):

    def __init__(self):
        self.msg = 'Repository chunk indexes are not locked'


class RepositoryChunkIndexesLockingFailed(obnamlib.Error):

    def __init__(self):
        self.msg = 'Repository chunk indexes are already locked'


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
    * All metadata is stored as key/value pairs, where the key is one
      of a strictly limited, version-specific list of allowed ones,
      and the value is a binary string or a 64-bit integer (the type
      depends on the key). All allowed keys are implicitly set to
      the empty string or 0 if not set otherwise.

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

    Generation and chunk identifiers, as returned by this API, are
    opaque objects, which may be compared for equality, but not for
    sorting. A generation id will include information to identify
    the client it belongs to, in order to make it unnecessary to
    always specify the client.

    File metadata (stat fields, etc) are stored using individual
    file keys:

        repo.set_file_key(gen_id, filename, REPO_FILE_KEY_MTIME, mtime)

    This is to allow maximum flexibility in how data is actually stored
    in the repository, and to make the least amount of assumptions
    that will hinder convertability between repository formats.
    However, storing them independently is likely to be epxensive,
    and so the implementation may actually pool file key changes to
    a file and only actually encode all of them, as a blob, when the
    API user is finished with a file. There is no API call to indicate
    that explicitly, but the API implementation can deduce it by noticing
    that another file's file key, or other metadata, gets set. This
    design aims to make the API as easy to use as possible, by avoiding
    an extra "I am finished with this file for now" method call.

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

    # Generations. The generation id identifies client as well.

    def get_allowed_generation_keys(self):
        '''Return list of all allowed keys for generations.'''
        raise NotImplementedError()

    def get_generation_key(self, generation_id, key):
        '''Return current value for a generation key.'''
        raise NotImplementedError()

    def set_generation_key(self, generation_id, key, value):
        '''Set a key/value pair for a given generation.'''
        raise NotImplementedError()

    def remove_generation(self, generation_id):
        '''Remove an existing generation.

        The removed generation may be the currently unfinished one.

        '''
        raise NotImplementedError()

    def get_generation_chunk_ids(self, generation_id):
        '''Return list of chunk ids used by a generation.

        Each file lists the chunks it uses, but iterating over all
        files is expensive. This method gives a potentially more
        efficient way of getting the information.

        '''
        raise NotImplementedError()

    def interpret_generation_spec(self, client_name, genspec):
        '''Return the generation id for a user-given specification.

        The specification is a string, and either gives the number
        of a generation, or is the word 'latest'.

        The return value is a generation id usable with the
        RepositoryInterface API.

        '''
        raise NotImplementedError()

    def make_generation_spec(self, gen_id):
        '''Return a generation spec that matches a given generation id.

        If we tell the user the returned string, and they later give
        it to interpret_generation_spec, the same generation id is
        returned.

        '''
        raise NotImplementedError()

    # Individual files and directories in a generation.

    def file_exists(self, generation_id, filename):
        '''Does a file exist in a generation?

        The filename should be the full path to the file.

        '''
        raise NotImplementedError()

    def add_file(self, generation_id, filename):
        '''Adds a file to the generation.

        Any metadata about the file needs to be added with
        set_file_key.

        '''
        raise NotImplementedError()

    def remove_file(self, generation_id, filename):
        '''Removes a file from the given generation.

        The generation MUST be the created, but not committed or
        unlocked generation.

        All the file keys associated with the file are also removed.

        '''
        raise NotImplementedError()

    def get_allowed_file_keys(self):
        '''Return list of allowed file keys for this format.'''
        raise NotImplementedError()

    def get_file_key(self, generation_id, filename, key):
        '''Return value for a file key, or empty string.

        The empty string is returned if no value has been set for the
        file key, or the file does not exist.

        '''
        raise NotImplementedError()

    def set_file_key(self, generation_id, filename, key, value):
        '''Set value for a file key.

        It is an error to set the value for a file key if the file does
        not exist yet.

        '''
        raise NotImplementedError()

    def get_file_chunk_ids(self, generation_id, filename):
        '''Get the list of chunk ids for a file.'''
        raise NotImplementedError()

    def clear_file_chunk_ids(self, generation_id, filename):
        '''Clear the list of chunk ids for a file.'''
        raise NotImplementedError()

    def append_file_chunk_id(self, generation_id, filename, chunk_id):
        '''Add a chunk id for a file.

        The chunk id is added to the end of the list of chunk ids,
        so file data ordering is preserved..

        '''
        raise NotImplementedError()

    def get_file_children(self, generation_id, filename):
        '''List contents of a directory.

        This returns a list of full pathnames for all the files in
        the repository that are direct children of the given file.
        This may fail if the given file is not a directory, but
        that is not guaranteed.

        '''
        raise NotImplementedError()

    # Chunks.

    def put_chunk_content(self, data):
        '''Add a new chunk into the repository.

        Return the chunk identifier.

        '''
        raise NotImplementedError()

    def get_chunk_content(self, chunk_id):
        '''Return the contents of a chunk, given its id.'''
        raise NotImplementedError()

    def has_chunk(self, chunk_id):
        '''Does a chunk (still) exist in the repository?'''
        raise NotImplementedError()

    def remove_chunk(self, chunk_id):
        '''Remove chunk from repository, but not chunk indexes.'''
        raise NotImplementedError()

    def lock_chunk_indexes(self):
        '''Locks chunk indexes for updates.'''
        raise NotImplementedError()

    def unlock_chunk_indexes(self):
        '''Unlocks chunk indexes without committing them.'''
        raise NotImplementedError()

    def force_chunk_indexex_lock(self):
        '''Forces a chunk index lock open and takes it for the caller.'''
        raise NotImplementedError()

    def commit_chunk_indexes(self):
        '''Commit changes to chunk indexes.'''
        raise NotImplementedError()

    def put_chunk_into_indexes(self, chunk_id, data, client_id):
        '''Adds a chunk to indexes.

        This does not do any de-duplication.

        The indexes map a chunk id to its checksum, and a checksum
        to both the chunk ids (possibly several!) and the client ids
        for the clients that use the chunk. The client ids are used
        to track when a chunk is no longer used by anyone and can
        be removed.

        '''
        raise NotImplementedError()

    def remove_chunk_from_indexes(self, chunk_id, client_id):
        '''Removes a chunk from indexes, given its id, for a given client.'''
        raise NotImplementedError()

    def find_chunk_id_by_content(self, data):
        '''Finds a chunk id given its content.

        This will raise RepositoryChunkContentNotInIndexes if the
        chunk is not in the indexes. Otherwise it will return one
        chunk id that has exactly the same content. If the indexes
        contain duplicate chunks, any one of the might be returned.

        '''
        raise NotImplementedError()

    # Fsck.

    def get_fsck_work_item(self):
        '''Return an fsck work item for checking this repository.

        The work item may spawn more items.

        '''
        raise NotImplementedError()


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

    def test_has_empty_string_for_client_test_key(self):
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

    def test_setting_unallowed_client_key_fails(self):
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

    # Operations on one generation.

    def create_generation(self):
        self.setup_client()
        self.repo.lock_client('fooclient')
        return self.repo.create_generation('fooclient')

    def test_has_list_of_allowed_generation_keys(self):
        self.assertEqual(type(self.repo.get_allowed_generation_keys()), list)

    def test_gets_all_allowed_generation_keys(self):
        gen_id = self.create_generation()
        for key in self.repo.get_allowed_generation_keys():
            value = self.repo.get_generation_key(gen_id, key)
            self.assertEqual(type(value), str)

    def test_has_empty_string_for_generation_test_key(self):
        gen_id = self.create_generation()
        value = self.repo.get_generation_key(
            gen_id, obnamlib.REPO_GENERATION_TEST_KEY)
        self.assertEqual(value, '')

    def test_sets_generation_key(self):
        gen_id = self.create_generation()
        self.repo.set_generation_key(
            gen_id, obnamlib.REPO_GENERATION_TEST_KEY, 'bar')
        value = self.repo.get_generation_key(
            gen_id, obnamlib.REPO_GENERATION_TEST_KEY)
        self.assertEqual(value, 'bar')

    def test_setting_unallowed_generation_key_fails(self):
        gen_id = self.create_generation()
        self.assertRaises(
            obnamlib.RepositoryGenerationKeyNotAllowed,
            self.repo.set_generation_key, gen_id, WRONG_KEY, '')

    def test_setting_generation_key_without_locking_fails(self):
        gen_id = self.create_generation()
        self.repo.commit_client('fooclient')
        self.assertRaises(
            obnamlib.RepositoryClientNotLocked,
            self.repo.set_generation_key,
            gen_id, obnamlib.REPO_GENERATION_TEST_KEY, 'bar')

    def test_committing_client_preserves_generation_key_changs(self):
        gen_id = self.create_generation()
        self.repo.set_generation_key(
            gen_id, obnamlib.REPO_GENERATION_TEST_KEY, 'bar')
        value = self.repo.get_generation_key(
            gen_id, obnamlib.REPO_GENERATION_TEST_KEY)
        self.repo.commit_client('fooclient')
        self.assertEqual(value, 'bar')

    def test_unlocking_client_undoes_generation_key_changes(self):
        gen_id = self.create_generation()
        self.repo.set_generation_key(
            gen_id, obnamlib.REPO_GENERATION_TEST_KEY, 'bar')
        self.repo.unlock_client('fooclient')
        value = self.repo.get_generation_key(
            gen_id, obnamlib.REPO_CLIENT_TEST_KEY)
        self.assertEqual(value, '')

    def test_removes_unfinished_generation(self):
        gen_id = self.create_generation()
        self.repo.remove_generation(gen_id)
        self.assertEqual(self.repo.get_client_generation_ids('fooclient'), [])

    def test_removes_finished_generation(self):
        gen_id = self.create_generation()
        self.repo.commit_client('fooclient')
        self.repo.lock_client('fooclient')
        self.repo.remove_generation(gen_id)
        self.assertEqual(self.repo.get_client_generation_ids('fooclient'), [])

    def test_removing_removed_generation_fails(self):
        gen_id = self.create_generation()
        self.repo.remove_generation(gen_id)
        self.assertRaises(
            obnamlib.RepositoryGenerationDoesNotExist,
            self.repo.remove_generation, gen_id)

    def test_removing_generation_without_client_lock_fails(self):
        gen_id = self.create_generation()
        self.repo.commit_client('fooclient')
        self.assertRaises(
            obnamlib.RepositoryClientNotLocked,
            self.repo.remove_generation, gen_id)

    def test_unlocking_client_forgets_generation_removal(self):
        gen_id = self.create_generation()
        self.repo.commit_client('fooclient')
        self.repo.lock_client('fooclient')
        self.repo.remove_generation(gen_id)
        self.repo.unlock_client('fooclient')
        self.assertEqual(
            self.repo.get_client_generation_ids('fooclient'),
            [gen_id])

    def test_committing_client_actually_removes_generation(self):
        gen_id = self.create_generation()
        self.repo.remove_generation(gen_id)
        self.repo.commit_client('fooclient')
        self.assertEqual(self.repo.get_client_generation_ids('fooclient'), [])

    def test_empty_generation_uses_no_chunk_ids(self):
        gen_id = self.create_generation()
        self.assertEqual(self.repo.get_generation_chunk_ids(gen_id), [])

    def test_interprets_latest_as_a_generation_spec(self):
        gen_id = self.create_generation()
        self.assertEqual(
            self.repo.interpret_generation_spec('fooclient', 'latest'),
            gen_id)

    def test_interpreting_latest_genspec_without_generations_fails(self):
        self.setup_client()
        self.assertRaises(
            obnamlib.RepositoryClientHasNoGenerations,
            self.repo.interpret_generation_spec, 'fooclient', 'latest')

    def test_interprets_generation_spec(self):
        gen_id = self.create_generation()
        genspec = self.repo.make_generation_spec(gen_id)
        self.assertEqual(
            self.repo.interpret_generation_spec('fooclient', genspec),
            gen_id)

    def test_interpreting_generation_spec_for_removed_generation_fails(self):
        # Note that we must have at least one generation, after removing
        # one.
        gen_id = self.create_generation()
        self.repo.commit_client('fooclient')
        self.repo.lock_client('fooclient')
        gen_id_2 = self.repo.create_generation('fooclient')
        genspec = self.repo.make_generation_spec(gen_id)
        self.repo.remove_generation(gen_id)
        self.assertRaises(
            obnamlib.RepositoryGenerationDoesNotExist,
            self.repo.interpret_generation_spec, 'fooclient', genspec)

    # Tests for individual files in a generation.

    def test_file_does_not_exist(self):
        gen_id = self.create_generation()
        self.assertFalse(self.repo.file_exists(gen_id, '/foo/bar'))

    def test_adds_file(self):
        gen_id = self.create_generation()
        self.repo.add_file(gen_id, '/foo/bar')
        self.assertTrue(self.repo.file_exists(gen_id, '/foo/bar'))

    def test_unlocking_forgets_file_add(self):
        gen_id = self.create_generation()
        self.repo.add_file(gen_id, '/foo/bar')
        self.repo.unlock_client('fooclient')
        self.assertFalse(self.repo.file_exists(gen_id, '/foo/bar'))

    def test_committing_remembers_file_add(self):
        gen_id = self.create_generation()
        self.repo.add_file(gen_id, '/foo/bar')
        self.repo.commit_client('fooclient')
        self.assertTrue(self.repo.file_exists(gen_id, '/foo/bar'))

    def test_creating_generation_clones_previous_one(self):
        gen_id = self.create_generation()
        self.repo.add_file(gen_id, '/foo/bar')
        self.repo.commit_client('fooclient')

        self.repo.lock_client('fooclient')
        gen_id_2 = self.repo.create_generation('fooclient')
        self.assertTrue(self.repo.file_exists(gen_id_2, '/foo/bar'))

    def test_removes_added_file_from_current_generation(self):
        gen_id = self.create_generation()
        self.repo.add_file(gen_id, '/foo/bar')
        self.repo.remove_file(gen_id, '/foo/bar')
        self.assertFalse(self.repo.file_exists(gen_id, '/foo/bar'))

    def test_unlocking_forgets_file_remova(self):
        gen_id = self.create_generation()
        self.repo.add_file(gen_id, '/foo/bar')
        self.repo.commit_client('fooclient')

        self.repo.lock_client('fooclient')
        gen_id_2 = self.repo.create_generation('fooclient')
        self.repo.remove_file(gen_id, '/foo/bar')
        self.repo.unlock_client('fooclient')

        self.assertTrue(self.repo.file_exists(gen_id, '/foo/bar'))

    def test_committing_remembers_file_removal(self):
        gen_id = self.create_generation()
        self.repo.add_file(gen_id, '/foo/bar')
        self.repo.commit_client('fooclient')

        self.repo.lock_client('fooclient')
        gen_id_2 = self.repo.create_generation('fooclient')
        self.assertTrue(self.repo.file_exists(gen_id_2, '/foo/bar'))
        self.repo.remove_file(gen_id_2, '/foo/bar')
        self.repo.commit_client('fooclient')

        self.assertTrue(self.repo.file_exists(gen_id, '/foo/bar'))
        self.assertFalse(self.repo.file_exists(gen_id_2, '/foo/bar'))

    def test_has_list_of_allowed_file_keys(self):
        self.assertEqual(type(self.repo.get_allowed_file_keys()), list)

    def test_gets_all_allowed_file_keys(self):
        gen_id = self.create_generation()
        self.repo.add_file(gen_id, '/foo/bar')
        for key in self.repo.get_allowed_file_keys():
            value = self.repo.get_file_key(gen_id, '/foo/bar', key)
            if key in REPO_FILE_INTEGER_KEYS:
                self.assertEqual(type(value), int)
            else:
                self.assertEqual(type(value), str)

    def test_has_empty_string_for_file_test_key(self):
        gen_id = self.create_generation()
        self.repo.add_file(gen_id, '/foo/bar')
        value = self.repo.get_file_key(
            gen_id, '/foo/bar', obnamlib.REPO_FILE_TEST_KEY)
        self.assertEqual(value, '')

    def test_get_file_key_fails_for_nonexistent_generation(self):
        gen_id = self.create_generation()
        self.repo.remove_generation(gen_id)
        self.assertRaises(
            obnamlib.RepositoryGenerationDoesNotExist,
            self.repo.get_file_key,
            gen_id, '/foo/bar', obnamlib.REPO_FILE_TEST_KEY)

    def test_get_file_key_fails_for_nonexistent_file(self):
        gen_id = self.create_generation()
        self.assertRaises(
            obnamlib.RepositoryFileDoesNotExistInGeneration,
            self.repo.get_file_key,
            gen_id, '/foo/bar', obnamlib.REPO_FILE_TEST_KEY)

    def test_sets_file_key(self):
        gen_id = self.create_generation()
        self.repo.add_file(gen_id, '/foo/bar')
        self.repo.set_file_key(
            gen_id, '/foo/bar', obnamlib.REPO_FILE_TEST_KEY, 'yoyo')
        value = self.repo.get_file_key(
            gen_id, '/foo/bar', obnamlib.REPO_FILE_TEST_KEY)
        self.assertEqual(value, 'yoyo')

    def test_setting_unallowed_file_key_fails(self):
        gen_id = self.create_generation()
        self.repo.add_file(gen_id, '/foo/bar')
        self.assertRaises(
            obnamlib.RepositoryFileKeyNotAllowed,
            self.repo.set_file_key, gen_id, '/foo/bar', WRONG_KEY, 'yoyo')

    def test_file_has_zero_mtime_by_default(self):
        gen_id = self.create_generation()
        self.repo.add_file(gen_id, '/foo/bar')
        value = self.repo.get_file_key(
            gen_id, '/foo/bar', obnamlib.REPO_FILE_MTIME)
        self.assertEqual(value, 0)

    def test_sets_file_mtime(self):
        gen_id = self.create_generation()
        self.repo.add_file(gen_id, '/foo/bar')
        self.repo.set_file_key(
            gen_id, '/foo/bar', obnamlib.REPO_FILE_MTIME, 123)
        value = self.repo.get_file_key(
            gen_id, '/foo/bar', obnamlib.REPO_FILE_MTIME)
        self.assertEqual(value, 123)

    def test_set_file_key_fails_for_nonexistent_generation(self):
        gen_id = self.create_generation()
        self.repo.remove_generation(gen_id)
        self.assertRaises(
            obnamlib.RepositoryGenerationDoesNotExist,
            self.repo.set_file_key,
            gen_id, '/foo/bar', obnamlib.REPO_FILE_TEST_KEY, 'yoyo')

    def test_setting_file_key_for_nonexistent_file_fails(self):
        gen_id = self.create_generation()
        self.assertRaises(
            obnamlib.RepositoryFileDoesNotExistInGeneration,
            self.repo.set_file_key,
            gen_id, '/foo/bar', obnamlib.REPO_FILE_TEST_KEY, 'yoyo')

    def test_removing_file_removes_all_its_file_keys(self):
        gen_id = self.create_generation()
        self.repo.add_file(gen_id, '/foo/bar')
        self.repo.set_file_key(
            gen_id, '/foo/bar', obnamlib.REPO_FILE_MTIME, 123)
        value = self.repo.get_file_key(
            gen_id, '/foo/bar', obnamlib.REPO_FILE_MTIME)
        self.assertEqual(value, 123)

        # FIXME : The ClientMetadataTree code does not handle, currently,
        # the same file being added, removed, then added back within
        # the same generation. This is a workaround, since I'm in the
        # middle of a refactoring and don't want to touch that class.
        self.repo.commit_client('fooclient')
        self.repo.lock_client('fooclient')
        gen_id = self.repo.create_generation('fooclient')

        # Remove the file. Key should be removed.
        self.repo.remove_file(gen_id, '/foo/bar')
        self.assertRaises(
            obnamlib.RepositoryFileDoesNotExistInGeneration,
            self.repo.get_file_key,
            gen_id, '/foo/bar', obnamlib.REPO_FILE_MTIME)

        # Add the file back. Key should still be removed.
        self.repo.add_file(gen_id, '/foo/bar')
        value = self.repo.get_file_key(
            gen_id, '/foo/bar', obnamlib.REPO_FILE_MTIME)
        self.assertEqual(value, 0)

    def test_unlocking_client_forgets_set_file_keys(self):
        gen_id = self.create_generation()
        self.repo.add_file(gen_id, '/foo/bar')
        self.repo.set_file_key(
            gen_id, '/foo/bar', obnamlib.REPO_FILE_TEST_KEY, 'yoyo')
        self.repo.unlock_client('fooclient')
        self.assertRaises(
            obnamlib.RepositoryGenerationDoesNotExist,
            self.repo.get_file_key,
            gen_id, '/foo/bar', obnamlib.REPO_FILE_TEST_KEY)

    def test_committing_client_remembers_set_file_keys(self):
        gen_id = self.create_generation()
        self.repo.add_file(gen_id, '/foo/bar')
        self.repo.set_file_key(
            gen_id, '/foo/bar', obnamlib.REPO_FILE_TEST_KEY, 'yoyo')
        self.repo.commit_client('fooclient')
        value = self.repo.get_file_key(
            gen_id, '/foo/bar', obnamlib.REPO_FILE_TEST_KEY)
        self.assertEqual(value, 'yoyo')

    def test_setting_file_key_does_not_affect_previous_generation(self):
        gen_id = self.create_generation()
        self.repo.add_file(gen_id, '/foo/bar')
        self.repo.set_file_key(
            gen_id, '/foo/bar', obnamlib.REPO_FILE_TEST_KEY, 'first')
        self.repo.commit_client('fooclient')

        self.repo.lock_client('fooclient')
        gen_id_2 = self.repo.create_generation('fooclient')
        self.repo.set_file_key(
            gen_id_2, '/foo/bar', obnamlib.REPO_FILE_TEST_KEY, 'second')
        self.repo.commit_client('fooclient')

        value = self.repo.get_file_key(
            gen_id, '/foo/bar', obnamlib.REPO_FILE_TEST_KEY)
        self.assertEqual(value, 'first')

        value_2 = self.repo.get_file_key(
            gen_id_2, '/foo/bar', obnamlib.REPO_FILE_TEST_KEY)
        self.assertEqual(value_2, 'second')

    def test_new_file_has_no_chunk_ids(self):
        gen_id = self.create_generation()
        self.repo.add_file(gen_id, '/foo/bar')
        self.assertEqual(self.repo.get_file_chunk_ids(gen_id, '/foo/bar'), [])

    def test_getting_file_chunk_ids_for_nonexistent_generation_fails(self):
        gen_id = self.create_generation()
        self.repo.remove_generation(gen_id)
        self.assertRaises(
            obnamlib.RepositoryGenerationDoesNotExist,
            self.repo.get_file_chunk_ids, gen_id, '/foo/bar')

    def test_getting_file_chunk_ids_for_nonexistent_file_fails(self):
        gen_id = self.create_generation()
        self.assertRaises(
            obnamlib.RepositoryFileDoesNotExistInGeneration,
            self.repo.get_file_chunk_ids, gen_id, '/foo/bar')

    def test_appends_one_file_chunk_id(self):
        gen_id = self.create_generation()
        self.repo.add_file(gen_id, '/foo/bar')
        self.repo.append_file_chunk_id(gen_id, '/foo/bar', 1)
        self.assertEqual(
            self.repo.get_file_chunk_ids(gen_id, '/foo/bar'),
            [1])

    def test_appends_two_file_chunk_ids(self):
        gen_id = self.create_generation()
        self.repo.add_file(gen_id, '/foo/bar')
        self.repo.append_file_chunk_id(gen_id, '/foo/bar', 1)
        self.repo.append_file_chunk_id(gen_id, '/foo/bar', 2)
        self.assertEqual(
            self.repo.get_file_chunk_ids(gen_id, '/foo/bar'),
            [1, 2])

    def test_appending_file_chunk_ids_in_nonexistent_generation_fails(self):
        gen_id = self.create_generation()
        self.repo.remove_generation(gen_id)
        self.assertRaises(
            obnamlib.RepositoryGenerationDoesNotExist,
            self.repo.append_file_chunk_id, gen_id, '/foo/bar', 1)

    def test_appending_file_chunk_ids_to_nonexistent_file_fails(self):
        gen_id = self.create_generation()
        self.assertRaises(
            obnamlib.RepositoryFileDoesNotExistInGeneration,
            self.repo.append_file_chunk_id, gen_id, '/foo/bar', 1)

    def test_adding_chunk_id_to_file_adds_it_to_generation_chunk_ids(self):
        gen_id = self.create_generation()
        self.repo.add_file(gen_id, '/foo/bar')
        self.repo.append_file_chunk_id(gen_id, '/foo/bar', 1)
        self.assertEqual(self.repo.get_generation_chunk_ids(gen_id), [1])

    def test_clears_file_chunk_ids(self):
        gen_id = self.create_generation()
        self.repo.add_file(gen_id, '/foo/bar')
        self.repo.append_file_chunk_id(gen_id, '/foo/bar', 1)
        self.repo.clear_file_chunk_ids(gen_id, '/foo/bar')
        self.assertEqual(self.repo.get_file_chunk_ids(gen_id, '/foo/bar'), [])

    def test_clearing_file_chunk_ids_in_nonexistent_generation_fails(self):
        gen_id = self.create_generation()
        self.repo.remove_generation(gen_id)
        self.assertRaises(
            obnamlib.RepositoryGenerationDoesNotExist,
            self.repo.clear_file_chunk_ids, gen_id, '/foo/bar')

    def test_clearing_file_chunk_ids_for_nonexistent_file_fails(self):
        gen_id = self.create_generation()
        self.assertRaises(
            obnamlib.RepositoryFileDoesNotExistInGeneration,
            self.repo.clear_file_chunk_ids, gen_id, '/foo/bar')

    def test_unlocking_child_forgets_modified_file_chunk_ids(self):
        gen_id = self.create_generation()
        self.repo.add_file(gen_id, '/foo/bar')
        self.repo.append_file_chunk_id(gen_id, '/foo/bar', 1)
        self.repo.commit_client('fooclient')

        self.repo.lock_client('fooclient')
        gen_id_2 = self.repo.create_generation('fooclient')
        self.repo.append_file_chunk_id(gen_id_2, '/foo/bar', 2)
        self.assertEqual(
            self.repo.get_file_chunk_ids(gen_id_2, '/foo/bar'),
            [1, 2])

        self.repo.unlock_client('fooclient')
        self.assertEqual(
            self.repo.get_file_chunk_ids(gen_id, '/foo/bar'),
            [1])

    def test_committing_child_remembers_modified_file_chunk_ids(self):
        gen_id = self.create_generation()
        self.repo.add_file(gen_id, '/foo/bar')
        self.repo.append_file_chunk_id(gen_id, '/foo/bar', 1)
        self.repo.commit_client('fooclient')

        self.repo.lock_client('fooclient')
        gen_id_2 = self.repo.create_generation('fooclient')
        self.repo.append_file_chunk_id(gen_id_2, '/foo/bar', 2)
        self.assertEqual(
            self.repo.get_file_chunk_ids(gen_id_2, '/foo/bar'),
            [1, 2])

        self.repo.commit_client('fooclient')
        self.assertEqual(
            self.repo.get_file_chunk_ids(gen_id, '/foo/bar'),
            [1])
        self.assertEqual(
            self.repo.get_file_chunk_ids(gen_id_2, '/foo/bar'),
            [1, 2])

    def test_new_file_has_no_children(self):
        gen_id = self.create_generation()
        self.repo.add_file(gen_id, '/foo/bar')
        self.assertEqual(self.repo.get_file_children(gen_id, '/foo/bar'), [])

    def test_gets_file_child(self):
        gen_id = self.create_generation()
        self.repo.add_file(gen_id, '/foo')
        self.repo.add_file(gen_id, '/foo/bar')
        self.assertEqual(
            self.repo.get_file_children(gen_id, '/foo'),
            ['/foo/bar'])

    def test_gets_only_immediate_child_for_file(self):
        gen_id = self.create_generation()
        self.repo.add_file(gen_id, '/')
        self.repo.add_file(gen_id, '/foo')
        self.repo.add_file(gen_id, '/foo/bar')
        self.assertEqual(
            self.repo.get_file_children(gen_id, '/'),
            ['/foo'])

    # Chunk and chunk indexes.

    def test_puts_chunk_into_repository(self):
        chunk_id = self.repo.put_chunk_content('foochunk')
        self.assertTrue(self.repo.has_chunk(chunk_id))
        self.assertEqual(self.repo.get_chunk_content(chunk_id), 'foochunk')

    def test_removes_chunk(self):
        chunk_id = self.repo.put_chunk_content('foochunk')
        self.repo.remove_chunk(chunk_id)
        self.assertFalse(self.repo.has_chunk(chunk_id))
        self.assertRaises(
            obnamlib.RepositoryChunkDoesNotExist,
            self.repo.get_chunk_content, chunk_id)

    def test_removing_nonexistent_chunk_fails(self):
        chunk_id = self.repo.put_chunk_content('foochunk')
        self.repo.remove_chunk(chunk_id)
        self.assertRaises(
            obnamlib.RepositoryChunkDoesNotExist,
            self.repo.remove_chunk, chunk_id)

    def test_adds_chunk_to_indexes(self):
        self.repo.lock_chunk_indexes()
        chunk_id = self.repo.put_chunk_content('foochunk')
        self.repo.put_chunk_into_indexes(chunk_id, 'foochunk', 123)
        self.assertEqual(
            self.repo.find_chunk_id_by_content('foochunk'), chunk_id)

    def test_removes_chunk_from_indexes(self):
        self.repo.lock_chunk_indexes()
        chunk_id = self.repo.put_chunk_content('foochunk')
        self.repo.put_chunk_into_indexes(chunk_id, 'foochunk', 123)
        self.repo.remove_chunk_from_indexes(chunk_id, 123)
        self.assertRaises(
            obnamlib.RepositoryChunkContentNotInIndexes,
            self.repo.find_chunk_id_by_content, 'foochunk')

    def test_putting_chunk_to_indexes_without_locking_them_fails(self):
        chunk_id = self.repo.put_chunk_content('foochunk')
        self.assertRaises(
            obnamlib.RepositoryChunkIndexesNotLocked,
            self.repo.put_chunk_into_indexes, chunk_id, 'foochunk', 123)

    def test_removing_chunk_from_indexes_without_locking_them_fails(self):
        chunk_id = self.repo.put_chunk_content('foochunk')
        self.repo.lock_chunk_indexes()
        self.repo.put_chunk_into_indexes(chunk_id, 'foochunk', 123)
        self.repo.commit_chunk_indexes()
        self.assertRaises(
            obnamlib.RepositoryChunkIndexesNotLocked,
            self.repo.remove_chunk_from_indexes, chunk_id, 123)

    def test_unlocking_chunk_indexes_forgets_changes(self):
        chunk_id = self.repo.put_chunk_content('foochunk')
        self.repo.lock_chunk_indexes()
        self.repo.put_chunk_into_indexes(chunk_id, 'foochunk', 123)
        self.repo.unlock_chunk_indexes()
        self.assertRaises(
            obnamlib.RepositoryChunkContentNotInIndexes,
            self.repo.find_chunk_id_by_content, 'foochunk')

    def test_committing_chunk_indexes_remembers_changes(self):
        chunk_id = self.repo.put_chunk_content('foochunk')
        self.repo.lock_chunk_indexes()
        self.repo.put_chunk_into_indexes(chunk_id, 'foochunk', 123)
        self.repo.commit_chunk_indexes()
        self.assertEqual(
            self.repo.find_chunk_id_by_content('foochunk'), chunk_id)

    def test_locking_chunk_indexes_twice_fails(self):
        self.repo.lock_chunk_indexes()
        self.assertRaises(
            obnamlib.RepositoryChunkIndexesLockingFailed,
            self.repo.lock_chunk_indexes)

    def test_unlocking_unlocked_chunk_indexes_fails(self):
        self.assertRaises(
            obnamlib.RepositoryChunkIndexesNotLocked,
            self.repo.unlock_chunk_indexes)

    def test_forces_chunk_index_lock(self):
        self.repo.lock_chunk_indexes()
        self.repo.force_chunk_indexes_lock()
        self.assertEqual(self.repo.unlock_chunk_indexes(), None)

    # Fsck.

    def test_returns_fsck_work_item(self):
        self.assertNotEqual(self.repo.get_fsck_work_item(), None)

