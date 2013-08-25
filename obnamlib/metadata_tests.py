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


import os
import stat
import tempfile
import unittest
import platform

import obnamlib


class FakeFS(object):

    def __init__(self):
        self.st_atime_sec = 1
        self.st_atime_nsec = 11
        self.st_blocks = 2
        self.st_dev = 3
        self.st_gid = 4
        self.st_ino = 5
        self.st_mode = 6
        self.st_mtime_sec = 7
        self.st_mtime_nsec = 71
        self.st_nlink = 8
        self.st_size = 9
        self.st_uid = 10
        self.groupname = 'group'
        self.username = 'user'
        self.target = 'target'

    def lstat(self, filename):
        return self

    def readlink(self, filename):
        return 'target'

    def getpwuid(self, uid):
        return (self.username, None, self.st_uid, self.st_gid,
                None, None, None)

    def getgrgid(self, gid):
        return (self.groupname, None, self.st_gid, None)

    def fail_getpwuid(self, uid):
        raise KeyError(uid)

    def fail_getgrgid(self, gid):
        raise KeyError(gid)

    def llistxattr(self, filename):
        return []


class MetadataTests(unittest.TestCase):

    def test_sets_mtime_from_kwarg(self):
        metadata = obnamlib.Metadata(st_mtime_sec=123)
        self.assertEqual(metadata.st_mtime_sec, 123)

    def test_isdir_returns_false_for_regular_file(self):
        metadata = obnamlib.Metadata(st_mode=stat.S_IFREG)
        self.assertFalse(metadata.isdir())

    def test_isdir_returns_true_for_directory(self):
        metadata = obnamlib.Metadata(st_mode=stat.S_IFDIR)
        self.assert_(metadata.isdir())

    def test_isdir_returns_false_when_st_mode_is_not_set(self):
        metadata = obnamlib.Metadata()
        self.assertFalse(metadata.isdir())

    def test_islink_returns_false_for_regular_file(self):
        metadata = obnamlib.Metadata(st_mode=stat.S_IFREG)
        self.assertFalse(metadata.islink())

    def test_islink_returns_true_for_symlink(self):
        metadata = obnamlib.Metadata(st_mode=stat.S_IFLNK)
        self.assert_(metadata.islink())

    def test_islink_returns_false_when_st_mode_is_not_set(self):
        metadata = obnamlib.Metadata()
        self.assertFalse(metadata.islink())

    def test_isfile_returns_true_for_regular_file(self):
        metadata = obnamlib.Metadata(st_mode=stat.S_IFREG)
        self.assert_(metadata.isfile())

    def test_isfile_returns_false_when_st_mode_is_not_set(self):
        metadata = obnamlib.Metadata()
        self.assertFalse(metadata.isfile())

    def test_has_no_md5_by_default(self):
        metadata = obnamlib.Metadata()
        self.assertEqual(metadata.md5, None)

    def test_sets_md5(self):
        metadata = obnamlib.Metadata(md5='checksum')
        self.assertEqual(metadata.md5, 'checksum')

    def test_is_equal_to_itself(self):
        metadata = obnamlib.Metadata(st_mode=stat.S_IFREG)
        self.assertEqual(metadata, metadata)

    def test_less_than_works(self):
        m1 = obnamlib.Metadata(st_size=1)
        m2 = obnamlib.Metadata(st_size=2)
        self.assert_(m1 < m2)

    def test_greater_than_works(self):
        m1 = obnamlib.Metadata(st_size=1)
        m2 = obnamlib.Metadata(st_size=2)
        self.assert_(m2 > m1)


class ReadMetadataTests(unittest.TestCase):

    def setUp(self):
        self.fakefs = FakeFS()

    def test_returns_stat_fields_correctly(self):
        metadata = obnamlib.read_metadata(self.fakefs, 'foo',
                                          getpwuid=self.fakefs.getpwuid,
                                          getgrgid=self.fakefs.getgrgid)
        fields = ['st_atime_sec','st_atime_nsec', 'st_blocks', 'st_dev',
                  'st_gid', 'st_ino', 'st_mode', 'st_mtime_sec',
                  'st_mtime_nsec', 'st_nlink', 'st_size', 'st_uid',
                  'groupname', 'username']
        for field in fields:
            self.assertEqual(getattr(metadata, field),
                             getattr(self.fakefs, field),
                             field)

    def test_returns_symlink_fields_correctly(self):
        self.fakefs.st_mode |= stat.S_IFLNK;
        metadata = obnamlib.read_metadata(self.fakefs, 'foo',
                                          getpwuid=self.fakefs.getpwuid,
                                          getgrgid=self.fakefs.getgrgid)
        fields = ['st_mode', 'target']
        for field in fields:
            self.assertEqual(getattr(metadata, field),
                             getattr(self.fakefs, field),
                             field)

    def test_reads_username_as_None_if_lookup_fails(self):
        metadata = obnamlib.read_metadata(self.fakefs, 'foo',
                                          getpwuid=self.fakefs.fail_getpwuid,
                                          getgrgid=self.fakefs.fail_getgrgid)
        self.assertEqual(metadata.username, None)


class SetMetadataTests(unittest.TestCase):

    def setUp(self):
        self.metadata = obnamlib.Metadata()
        self.metadata.st_atime_sec = 12765
        self.metadata.st_atime_nsec = 0
        self.metadata.st_mode = 42 | stat.S_IFREG
        self.metadata.st_mtime_sec = 10**9
        self.metadata.st_mtime_nsec = 0
        self.metadata.st_uid = 1234
        self.metadata.st_gid = 5678

        fd, self.filename = tempfile.mkstemp()
        os.close(fd)
        # On some systems (e.g. FreeBSD) /tmp is apparently setgid and
        # default gid of files is therefore not the user's gid.
        os.chown(self.filename, os.getuid(), os.getgid())

        self.fs = obnamlib.LocalFS('/')
        self.fs.connect()

        self.uid_set = None
        self.gid_set = None
        self.fs.lchown = self.fake_lchown

        obnamlib.set_metadata(self.fs, self.filename, self.metadata)

        self.st = os.stat(self.filename)

    def tearDown(self):
        self.fs.close()
        os.remove(self.filename)

    def fake_lchown(self, filename, uid, gid):
        self.uid_set = uid
        self.gid_set = gid

    def test_sets_atime(self):
        self.assertEqual(self.st.st_atime, self.metadata.st_atime_sec)

    def test_sets_mode(self):
        self.assertEqual(self.st.st_mode, self.metadata.st_mode)

    def test_sets_mtime(self):
        self.assertEqual(self.st.st_mtime, self.metadata.st_mtime_sec)

    def test_does_not_set_uid_when_not_running_as_root(self):
        self.assertEqual(self.st.st_uid, os.getuid())

    def test_does_not_set_gid_when_not_running_as_root(self):
        self.assertEqual(self.st.st_gid, os.getgid())

    def test_sets_uid_when_running_as_root(self):
        obnamlib.set_metadata(self.fs, self.filename, self.metadata,
                              getuid=lambda: 0)
        self.assertEqual(self.uid_set, self.metadata.st_uid)

    def test_sets_gid_when_running_as_root(self):
        obnamlib.set_metadata(self.fs, self.filename, self.metadata,
                              getuid=lambda: 0)
        self.assertEqual(self.gid_set, self.metadata.st_gid)

    def test_sets_symlink_target(self):
        self.fs.remove(self.filename)
        self.metadata.st_mode = 0777 | stat.S_IFLNK;
        self.metadata.target = 'target'
        obnamlib.set_metadata(self.fs, self.filename, self.metadata)
        self.assertEqual(self.fs.readlink(self.filename), 'target')

    def test_sets_symlink_mtime_perms(self):
        self.fs.remove(self.filename)
        self.metadata.st_mode = 0777 | stat.S_IFLNK;
        self.metadata.target = 'target'
        obnamlib.set_metadata(self.fs, self.filename, self.metadata)
        st = os.lstat(self.filename)
        self.assertEqual(st.st_mode, self.metadata.st_mode)
        self.assertEqual(st.st_mtime, self.metadata.st_mtime_sec)


class MetadataCodingTests(unittest.TestCase):

    def equal(self, meta1, meta2):
        for name in dir(meta1):
            if name in obnamlib.metadata.metadata_fields:
                value1 = getattr(meta1, name)
                value2 = getattr(meta2, name)
                self.assertEqual(
                    value1,
                    value2,
                    'attribute %s must be equal (%s vs %s)' %
                        (name, value1, value2))

    def test_round_trip(self):
        metadata = obnamlib.metadata.Metadata(st_mode=1,
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
        encoded = obnamlib.encode_metadata(metadata)
        decoded = obnamlib.decode_metadata(encoded)
        self.equal(metadata, decoded)

    def test_round_trip_for_None_values(self):
        metadata = obnamlib.metadata.Metadata()
        encoded = obnamlib.encode_metadata(metadata)
        decoded = obnamlib.decode_metadata(encoded)
        for name in dir(metadata):
            if name in obnamlib.metadata.metadata_fields:
                self.assertEqual(getattr(decoded, name), None,
                                 'attribute %s must be None' % name)

    def test_round_trip_for_maximum_values(self):
        unsigned_max = 2**64 - 1
        signed_max = 2**63 - 1
        metadata = obnamlib.metadata.Metadata(
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
        encoded = obnamlib.encode_metadata(metadata)
        decoded = obnamlib.decode_metadata(encoded)
        self.equal(metadata, decoded)

