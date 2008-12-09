# Copyright (C) 2008  Lars Wirzenius <liw@liw.fi>
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

import obnamlib


class NotFound(obnamlib.Exception):

    pass


class Store(object):

    """Persistent storage of obnamlib.Objects.

    This class stores obnamlib.Objects persistently: on local disk or
    on a remote server. The I/O operations happen through a virtual
    file system (obnamlib.VFS), and this class takes care of grouping
    objects into blocks, and retrieving individual objects in an
    efficient manner.

    A store is identified via a URL. It can be opened either
    read-only, or read-write. A store may contain backup data for many
    hosts. Each host can be opened read-write at most once at a given
    time, but different hosts can be opened read-write at the same
    time.

    A store that is open for both reading and writing must be closed
    by calling the commit method. Otherwise no changes to the store
    will be accessible. The host object is only written in commit, and
    since all the other objects are found via the host object, they
    cannot be accessed without the new host object. They may, however,
    be uploaded before the commit.

    """

    def __init__(self, url, mode):
        self.url = url
        self.fs = obnamlib.LocalFS(url)
        self.mode = mode
        self.factory = obnamlib.ObjectFactory()
        self.objects = []

    def check_mode(self, mode):
        if mode not in ["r", "w"]:
            raise obnamlib.Exception("Unknown Store mode '%s'" % mode)

    def assert_readwrite_mode(self):
        if self.mode != "w":
            raise obnamlib.Exception("Store not in read-write mode")

    def new_object(self, kind):
        self.assert_readwrite_mode()
        return self.factory.new_object(kind=kind)

    def get_object(self, id):
        for obj in self.objects:
            if obj.id == id:
                return obj
        if self.fs.exists(id):
            encoded = self.fs.cat(id)
            obj, pos = self.factory.decode_object(encoded, pos=0)
            self.objects.append(obj)
            if obj.id == id:
                return obj
        raise obnamlib.NotFound("Object %s not found in store" % id)

    def put_object(self, obj):
        self.assert_readwrite_mode()
        for obj2 in self.objects:
            if obj2.id == obj.id:
                raise obnamlib.Exception("Object %s already in store" % 
                                         obj.id)
        self.objects.append(obj)

    def get_host(self, host_id):
        """Return the host object for the host with the given id."""
        try:
            host = self.get_object(host_id)
        except NotFound:
            host = self.new_object(kind=obnamlib.HOST)
            host.id = host_id
        return host

    def put_host(self, host):
        """Put (possibly updated) host object back into store."""
        if host in self.objects:
            self.objects.remove(host)
        self.put_object(host)

    def commit(self):
        self.assert_readwrite_mode()
        for obj in self.objects:
            encoded = self.factory.encode_object(obj)
            if obj.kind == obnamlib.HOST:
                self.fs.overwrite_file(obj.id, encoded)
            else:
                self.fs.write_file(obj.id, encoded)
