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
        self.fs = obnamlib.VfsFactory().new(url)
        self.fs.connect()
        self.mode = mode
        self.factory = obnamlib.ObjectFactory()
        self.block_factory = obnamlib.BlockFactory()
        self.object_queue = []
        self.put_hook = None
        self.idgen = obnamlib.BlockIdGenerator(3, 1024)

        # We keep the object to block mappings we know about in
        # self.objmap. We add new mappings there as we learn about
        # them. For performance reasons, we don't fill the mapping
        # dictionary completely at start-up, since on a typical
        # run we don't need most of them.
        self.objmap = obnamlib.Mapping()

        # We keep track of new mappings separaterly from self.objmap.
        # This allows us to write out a new mapping block with just
        # those mappings, in push_new_mappings (called from commit).
        # Because we allow the caller to use several host objects
        # in the same store (concurrently at run time, even), we
        # keep the obnamlib.Mapping dicts for each host in the
        # self.new_mappings dictionary, indexed by the host.
        self.new_mappings = {}

    def check_mode(self, mode):
        if mode not in ["r", "w"]:
            raise obnamlib.Exception("Unknown Store mode '%s'" % mode)

    def assert_readwrite_mode(self):
        if self.mode != "w":
            raise obnamlib.Exception("Store not in read-write mode")

    def new_object(self, kind):
        self.assert_readwrite_mode()
        return self.factory.new_object(kind=kind)
        
    def find_block(self, host, id):
        """Find the block in which an object resides.
        
        If no matching block is found, raise NotFound().
        This will load in new mappings from disk, as necessary.
        For that, we need the host, since mappings are per host.
        
        """
        
        # Perhaps we know the answer already?
        if id in self.objmap:
            return self.objmap[id]
            
        # Load mapping blocks until we find something.
        for mapref in host.maprefs:
            encoded = self.fs.cat(mapref)
            blkid, objs, mappings = self.block_factory.decode_block(encoded)
            self.objmap.update(mappings)
            if id in self.objmap:
                return self.objmap[id]

        # Bummer.
        raise NotFound("Object %s not found in store" % id)

    def get_object(self, host, id):
        """Return the object with a given id.
        
        The object will be loaded from disk first, if necessary.
        
        """
        
        block_id = self.find_block(host, id)
        encoded = self.fs.cat(block_id)
        block_id, objs, mappings = self.block_factory.decode_block(encoded)
        for obj in objs:
            if obj.id == id:
                return obj
        
        raise obnamlib.NotFound("Object %s not found in store" % id)

    def put_object(self, obj):
        """Put an object into the store.
        
        The object may not be accessible until commit has been called.
        
        """

        self.assert_readwrite_mode()
        self.object_queue.append(obj)
        
        if self.put_hook is not None:
            self.put_hook()

    @property
    def unpushed_size(self):
        """Return approximate size of unpushed objects."""
        
        def approx_size(c):
            """Return approximate size of component."""
            if obnamlib.cmp_kinds.is_composite(c.kind):
                return sum(approx_size(kid) for kid in c.children)
            else:
                return len(str(c))

        size = 0        
        for o in self.object_queue:
            for c in o.components:
                size += approx_size(c)
        return size

    def get_host(self, host_id):
        """Return the host object for the host with the given id."""
        
        if self.fs.exists(host_id):
            encoded = self.fs.cat(host_id)
            blkid, objs, mappings = self.block_factory.decode_block(encoded)
            for obj in objs:
                if obj.id == host_id:
                    return obj
            raise NotFound("Cannot find host object %s" % host_id)
        else:
            host = self.new_object(kind=obnamlib.HOST)
            host.id = host_id
            return host

    def add_mapping(self, host, objid, blockid):
        """Remember block in which an object is stored."""
        if host not in self.new_mappings:
            self.new_mappings[host] = obnamlib.Mapping()
        self.new_mappings[host][objid] = blockid

    def push_objects(self, host):
        """Push queued objects into one or more blocks.

        The objects will be collected into one or more blocks, and
        the block of each object will be stored in mapping blocks.
        The mapping block will be generated by the commit method.
        Until commit is called, the mappings will be temporarily stored
        in memory, sorted by the host object, in the new_mappings
        dictionary.
        
        """

        if self.object_queue:
            block_id = self.idgen.new_id()
            encoded = self.block_factory.encode_block(block_id, 
                                                      self.object_queue, 
                                                      {})
            self.fs.write_file(block_id, encoded)
            for obj in self.object_queue:
                self.add_mapping(host, obj.id, block_id)
            self.object_queue = []

    def push_new_mappings(self, host):
        """Generate and push out a new mapping block with all new objects.
        
        The block id of the new mapping block is added to the host's
        maprefs. The caller needs to ensure the host gets committed for
        the mapping block to be useful for later runs.
        
        """

        if host not in self.new_mappings:
            return
        mappings = self.new_mappings[host]
        if mappings:
            block_id = self.idgen.new_id()
            encoded = self.block_factory.encode_block(block_id, [], mappings)
            self.fs.write_file(block_id, encoded)
            host.maprefs.append(block_id)
            self.new_mappings[host] = obnamlib.Mapping()

    def commit(self, host):
        """Commit all changes made to a specific host."""

        self.assert_readwrite_mode()
        
        # First, push out all queued objects.
        self.push_objects(host)

        # Next, push out a new mapping block for all the new objects.
        # This adds a new MAPREF to the host object.
        self.push_new_mappings(host)

        # Finally, push the recently modified host object out.
        encoded = self.block_factory.encode_block(host.id, [host], {})
        self.fs.overwrite_file(host.id, encoded)
        self.fs.close()

    def cat(self, host, output, cont_id, delta_id):
        """Write file contents to an open file.
        
        This method will reproduce the contents of a regular file and
        write it to the output file. If cont_id is not None, then the
        entire contents is assumed to be in the corresponding FILECONT
        object. Otherwise, nothing is output.
        
        delta_id will be used in the future.
        
        Arguments:
        host -- the host whose files are being used
        output -- the open file to which data will be written (only the
                  write method is used)
        cont_id -- reference to FILECONT object
        delta_id -- reference to DELTA object
        
        """
        
        if not cont_id:
            return
            
        cont = self.get_object(host, cont_id)
        for part_id in cont.part_ids:
            part = self.get_object(host, part_id)
            output.write(part.data)

    def put_contents(self, file, size):
        """Write contents of open file to store.
        
        The contents of the file will be split into chunks of `size`
        bytes. Each chunk gets placed in a FILEPART object. Finally,
        and FILECONTENTS object is created, put into the store, and
        returned.
        
        """

        content = self.new_object(kind=obnamlib.FILECONTENTS)
        while True:
            data = file.read(size)
            if not data:
                break
            part = self.new_object(kind=obnamlib.FILEPART)
            part.data = data
            self.put_object(part)
            content.add(part.id)
        self.put_object(content)
        return content
