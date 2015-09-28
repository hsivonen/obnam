# Copyright 2015  Lars Wirzenius
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
