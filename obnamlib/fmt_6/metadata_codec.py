# Copyright (C) 2009-2014  Lars Wirzenius
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


import struct

import obnamlib


metadata_format = struct.Struct('!Q' +  # flags
                                'Q' +   # st_mode
                                'qQ' +  # st_mtime_sec and _nsec
                                'qQ' +  # st_atime_sec and _nsec
                                'Q' +   # st_nlink
                                'Q' +   # st_size
                                'Q' +   # st_uid
                                'Q' +   # st_gid
                                'Q' +   # st_dev
                                'Q' +   # st_ino
                                'Q' +   # st_blocks
                                'Q' +   # len of groupname
                                'Q' +   # len of username
                                'Q' +   # len of symlink target
                                'Q' +   # len of md5
                                'Q' +   # len of xattr
                                '')

def encode_metadata(metadata):
    flags = 0
    for i, name in enumerate(obnamlib.metadata_fields):
        if getattr(metadata, name) is not None:
            flags |= (1 << i)

    try:
        packed = metadata_format.pack(flags,
                                      metadata.st_mode or 0,
                                      metadata.st_mtime_sec or 0,
                                      metadata.st_mtime_nsec or 0,
                                      metadata.st_atime_sec or 0,
                                      metadata.st_atime_nsec or 0,
                                      metadata.st_nlink or 0,
                                      metadata.st_size or 0,
                                      metadata.st_uid or 0,
                                      metadata.st_gid or 0,
                                      metadata.st_dev or 0,
                                      metadata.st_ino or 0,
                                      metadata.st_blocks or 0,
                                      len(metadata.groupname or ''),
                                      len(metadata.username or ''),
                                      len(metadata.target or ''),
                                      len(metadata.md5 or ''),
                                      len(metadata.xattr or ''))
    except TypeError, e: # pragma: no cover
        logging.error('ERROR: Packing error due to %s' % str(e))
        logging.error('ERROR: st_mode=%s' % repr(metadata.st_mode))
        logging.error('ERROR: st_mtime_sec=%s' % repr(metadata.st_mtime_sec))
        logging.error(
            'ERROR: st_mtime_nsec=%s' % repr(metadata.st_mtime_nsec))
        logging.error('ERROR: st_atime_sec=%s' % repr(metadata.st_atime_sec))
        logging.error(
            'ERROR: st_atime_nsec=%s' % repr(metadata.st_atime_nsec))
        logging.error('ERROR: st_nlink=%s' % repr(metadata.st_nlink))
        logging.error('ERROR: st_size=%s' % repr(metadata.st_size))
        logging.error('ERROR: st_uid=%s' % repr(metadata.st_uid))
        logging.error('ERROR: st_gid=%s' % repr(metadata.st_gid))
        logging.error('ERROR: st_dev=%s' % repr(metadata.st_dev))
        logging.error('ERROR: st_ino=%s' % repr(metadata.st_ino))
        logging.error('ERROR: st_blocks=%s' % repr(metadata.st_blocks))
        logging.error('ERROR: groupname=%s' % repr(metadata.groupname))
        logging.error('ERROR: username=%s' % repr(metadata.username))
        logging.error('ERROR: target=%s' % repr(metadata.target))
        logging.error('ERROR: md5=%s' % repr(metadata.md5))
        logging.error('ERROR: xattr=%s' % repr(metadata.xattr))
        raise
    return (packed +
             (metadata.groupname or '') +
             (metadata.username or '') +
             (metadata.target or '') +
             (metadata.md5 or '') +
             (metadata.xattr or ''))


def decode_metadata(encoded):

    items = metadata_format.unpack_from(encoded)
    flags = items[0]
    pos = [1, metadata_format.size]
    metadata = obnamlib.Metadata()

    def is_present(field):
        i = obnamlib.metadata_fields.index(field)
        return (flags & (1 << i)) != 0

    def decode(field, num_items, inc_offset, getvalue):
        if is_present(field):
            value = getvalue(pos[0], pos[1])
            setattr(metadata, field, value)
            if inc_offset:
                pos[1] += len(value)
        pos[0] += num_items

    def decode_integer(field):
        decode(field, 1, False, lambda i, o: items[i])

    def decode_string(field):
        decode(field, 1, True, lambda i, o: encoded[o:o + items[i]])

    decode_integer('st_mode')
    decode_integer('st_mtime_sec')
    decode_integer('st_mtime_nsec')
    decode_integer('st_atime_sec')
    decode_integer('st_atime_nsec')
    decode_integer('st_nlink')
    decode_integer('st_size')
    decode_integer('st_uid')
    decode_integer('st_gid')
    decode_integer('st_dev')
    decode_integer('st_ino')
    decode_integer('st_blocks')
    decode_string('groupname')
    decode_string('username')
    decode_string('target')
    decode_string('md5')
    decode_string('xattr')

    return metadata
