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


import unittest

import obnamlib


class MetadataCodingTests(unittest.TestCase):

    def equal(self, meta1, meta2):
        for name in dir(meta1):
            if name in obnamlib.metadata_fields:
                value1 = getattr(meta1, name)
                value2 = getattr(meta2, name)
                self.assertEqual(
                    value1,
                    value2,
                    'attribute %s must be equal (%s vs %s)' %
                    (name, value1, value2))

    def test_round_trip(self):
        metadata = obnamlib.Metadata(
            st_mode=1,
            st_mtime_sec=2,
            st_mtime_nsec=12756,
            st_nlink=3,
            st_size=4,
            st_uid=5,
            st_blocks=6,
            st_dev=7,
            st_gid=8,
            st_ino=9,
            st_atime_sec=10,
            st_atime_nsec=123,
            groupname='group',
            username='user',
            target='target',
            md5='checksum')
        encoded = obnamlib.fmt_6.metadata_codec.encode_metadata(metadata)
        decoded = obnamlib.fmt_6.metadata_codec.decode_metadata(encoded)
        self.equal(metadata, decoded)

    def test_round_trip_for_None_values(self):
        metadata = obnamlib.Metadata()
        encoded = obnamlib.fmt_6.metadata_codec.encode_metadata(metadata)
        decoded = obnamlib.fmt_6.metadata_codec.decode_metadata(encoded)
        for name in dir(metadata):
            if name in obnamlib.metadata_fields:
                self.assertEqual(getattr(decoded, name), None,
                                 'attribute %s must be None' % name)

    def test_round_trip_for_maximum_values(self):
        unsigned_max = 2**64 - 1
        signed_max = 2**63 - 1
        metadata = obnamlib.Metadata(
            st_mode=unsigned_max,
            st_mtime_sec=signed_max,
            st_mtime_nsec=unsigned_max,
            st_nlink=unsigned_max,
            st_size=signed_max,
            st_uid=unsigned_max,
            st_blocks=signed_max,
            st_dev=unsigned_max,
            st_gid=unsigned_max,
            st_ino=unsigned_max,
            st_atime_sec=signed_max,
            st_atime_nsec=unsigned_max)
        encoded = obnamlib.fmt_6.metadata_codec.encode_metadata(metadata)
        decoded = obnamlib.fmt_6.metadata_codec.decode_metadata(encoded)
        self.equal(metadata, decoded)
