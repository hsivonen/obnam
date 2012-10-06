# Copyright (C) 2009-2011  Lars Wirzenius
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


__version__ = '1.2'



# Import _obnam if it is there. We need to be able to do things without
# it, especially at build time, while we're generating manual pages.
# If _obnam is not there, substitute a dummy that throws an exception
# if used.
class DummyExtension(object):
    def __getattr__(self, name):
        raise Exception('Trying to use _obnam, but that was not found.')
try:
    import _obnam
except ImportError:
    _obnam = DummyExtension()

from pluginmgr import PluginManager


class Error(cliapp.AppException):
    pass


DEFAULT_NODE_SIZE = 256 * 1024 # benchmarked on 2011-09-01
DEFAULT_CHUNK_SIZE = 1024 * 1024 # benchmarked on 2011-09-01
DEFAULT_UPLOAD_QUEUE_SIZE = 1024
DEFAULT_LRU_SIZE = 500
DEFAULT_CHUNKIDS_PER_GROUP = 1024
DEFAULT_NAGIOS_WARN_AGE = '27h'
DEFAULT_NAGIOS_CRIT_AGE = '8d'

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


from sizeparse import SizeSyntaxError, UnitNameError, ByteSizeParser

from encryption import (generate_symmetric_key,
                        encrypt_symmetric,
                        decrypt_symmetric,
                        get_public_key,
                        Keyring,
                        SecretKeyring,
                        encrypt_with_keyring,
                        decrypt_with_secret_keys,
                        SymmetricKeyCache)

from hooks import Hook, MissingFilterError, FilterHook, HookManager
from pluginbase import ObnamPlugin
from vfs import VirtualFileSystem, VfsFactory, VfsTests
from vfs_local import LocalFS
from metadata import (read_metadata, set_metadata, Metadata, metadata_fields,
                      metadata_verify_fields, encode_metadata, decode_metadata)
from repo_tree import RepositoryTree
from chunklist import ChunkList
from clientlist import ClientList
from checksumtree import ChecksumTree
from clientmetadatatree import ClientMetadataTree
from lockmgr import LockManager
from repo import Repository, LockFail, BadFormat
from forget_policy import ForgetPolicy
from app import App

__all__ = locals()
