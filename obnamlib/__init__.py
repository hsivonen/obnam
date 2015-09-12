# Copyright (C) 2009-2015  Lars Wirzenius
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


import cliapp


__version__ = '1.17'


# Import _obnam if it is there. We need to be able to do things without
# it, especially at build time, while we're generating manual pages.
# If _obnam is not there, substitute a dummy that throws an exception
# if used.


class DummyExtension(object):
    def __getattr__(self, name):
        raise Exception('Trying to use _obnam, but that was not found.')
try:
    import obnamlib._obnam
except ImportError:
    _obnam = DummyExtension()


# Exceptions defined by Obnam itself. They should all be a subclass
# of obnamlib.ObnamError.

from .structurederror import StructuredError


class ObnamError(StructuredError):

    pass


DEFAULT_NODE_SIZE = 256 * 1024  # benchmarked on 2011-09-01
DEFAULT_CHUNK_SIZE = 1024 * 1024  # benchmarked on 2011-09-01
DEFAULT_UPLOAD_QUEUE_SIZE = 1024  # benchmarked on 2015-05-02
DEFAULT_LRU_SIZE = 256
DEFAULT_CHUNKIDS_PER_GROUP = 1024
DEFAULT_NAGIOS_WARN_AGE = '27h'
DEFAULT_NAGIOS_CRIT_AGE = '8d'

_MEBIBYTE = 1024**2
DEFAULT_DIR_OBJECT_CACHE_BYTES = 256 * _MEBIBYTE
DEFAULT_CHUNK_CACHE_BYTES = 1 * _MEBIBYTE

# The following values have been determined empirically on a laptop
# with an encrypted ext4 filesystem. Other values might be better for
# other situations.
IDPATH_DEPTH = 3
IDPATH_BITS = 12
IDPATH_SKIP = 13

# Maximum identifier for clients, chunks, files, etc. This is the largest
# unsigned 64-bit value. In various places we assume 64-bit field sizes
# for on-disk data structures.
MAX_ID = 2**64 - 1


option_group = {
    'perf': 'Performance tweaking',
    'devel': 'Development of Obnam itself',
}


from .sizeparse import SizeSyntaxError, UnitNameError, ByteSizeParser

from .encryption import (
    generate_symmetric_key,
    encrypt_symmetric,
    decrypt_symmetric,
    get_public_key,
    get_public_key_user_ids,
    Keyring,
    SecretKeyring,
    encrypt_with_keyring,
    decrypt_with_secret_keys,
    SymmetricKeyCache,
    EncryptionError,
    GpgError)

from .hooks import (
    Hook, MissingFilterError, NoFilterTagError, FilterHook, HookManager)
from .pluginbase import ObnamPlugin
from .vfs import (
    VirtualFileSystem,
    VfsFactory,
    VfsTests,
    LockFail,
    NEW_DIR_MODE,
    NEW_FILE_MODE)
from .vfs_local import LocalFS
from .fsck_work_item import WorkItem
from .repo_fs import RepositoryFS
from .lockmgr import LockManager
from .forget_policy import ForgetPolicy
from .app import App, ObnamIOError, ObnamSystemError
from .humanise import humanise_duration, humanise_size, humanise_speed
from .chunkid_token_map import ChunkIdTokenMap
from .pathname_excluder import PathnameExcluder
from .splitpath import split_pathname

from .obj_serialiser import serialise_object, deserialise_object
from .bag import Bag, BagIdNotSetError, make_object_id, parse_object_id
from .bag_store import BagStore, serialise_bag, deserialise_bag
from .blob_store import BlobStore

from .repo_factory import (
    RepositoryFactory,
    UnknownRepositoryFormat,
    UnknownRepositoryFormatWanted)
from .repo_interface import (
    RepositoryInterface,
    RepositoryInterfaceTests,
    RepositoryClientAlreadyExists,
    RepositoryClientDoesNotExist,
    RepositoryClientListNotLocked,
    RepositoryClientListLockingFailed,
    RepositoryClientLockingFailed,
    RepositoryClientNotLocked,
    RepositoryClientKeyNotAllowed,
    RepositoryClientGenerationUnfinished,
    RepositoryGenerationKeyNotAllowed,
    RepositoryGenerationDoesNotExist,
    RepositoryClientHasNoGenerations,
    RepositoryFileDoesNotExistInGeneration,
    RepositoryFileKeyNotAllowed,
    RepositoryChunkDoesNotExist,
    RepositoryChunkContentNotInIndexes,
    RepositoryChunkIndexesNotLocked,
    RepositoryChunkIndexesLockingFailed,
    repo_key_name,
    REPO_CLIENT_TEST_KEY,
    REPO_GENERATION_TEST_KEY,
    REPO_GENERATION_STARTED,
    REPO_GENERATION_ENDED,
    REPO_GENERATION_IS_CHECKPOINT,
    REPO_GENERATION_FILE_COUNT,
    REPO_GENERATION_TOTAL_DATA,
    REPO_GENERATION_INTEGER_KEYS,
    REPO_FILE_TEST_KEY,
    REPO_FILE_MODE,
    REPO_FILE_MTIME_SEC,
    REPO_FILE_MTIME_NSEC,
    REPO_FILE_ATIME_SEC,
    REPO_FILE_ATIME_NSEC,
    REPO_FILE_NLINK,
    REPO_FILE_SIZE,
    REPO_FILE_UID,
    REPO_FILE_USERNAME,
    REPO_FILE_GID,
    REPO_FILE_GROUPNAME,
    REPO_FILE_SYMLINK_TARGET,
    REPO_FILE_XATTR_BLOB,
    REPO_FILE_BLOCKS,
    REPO_FILE_DEV,
    REPO_FILE_INO,
    REPO_FILE_MD5,
    REPO_FILE_INTEGER_KEYS,
    metadata_file_key_mapping)

from .delegator import RepositoryDelegator, GenerationId

from .backup_progress import BackupProgress


#
# Repository format green-albatross specific modules.
#

from .fmt_ga import (
    RepositoryFormatGA,
    GAClientList,
    GAClient,
    GADirectory,
    GAImmutableError,
    create_gadirectory_from_dict,
    GATree,
    GAChunkStore,
    GAChunkIndexes)


#
# Repository format 6 specific modules.
#

from .metadata import (
    Metadata,
    read_metadata,
    set_metadata,
    SetMetadataError,
    metadata_fields)
from .fmt_6.repo_fmt_6 import RepositoryFormat6
from .fmt_6.repo_tree import RepositoryTree
from .fmt_6.chunklist import ChunkList
from .fmt_6.clientlist import ClientList
from .fmt_6.checksumtree import ChecksumTree
from .fmt_6.clientmetadatatree import ClientMetadataTree

__all__ = locals()
