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


import hashlib
import logging
import os

import obnamlib


class NotFound(obnamlib.Exception):

    pass


class ObjectQueue(list):

    """Queue of outgoing objects.
    
    There needs to be two queues, one for metadata and one for file
    contents objects.
    
    """
    
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
        for o in self:
            for c in o.components:
                size += approx_size(c)
        return size
    

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
    
    A store open only for reading must be closed by calling the close
    method. This ensure the (network) transport gets shut down properly.

    """

    def __init__(self, url, mode):
        self.url = url
        progress = obnamlib.ProgressReporter(silent=True)
        self.fs = obnamlib.VfsFactory().new(url, progress)
        self.fs.connect()
        self.mode = mode
        self.factory = obnamlib.ObjectFactory()
        self.block_factory = obnamlib.BlockFactory()
        self.object_queue = ObjectQueue()
        self.content_queue = ObjectQueue()
        self.put_hook = None
        self.idgen = obnamlib.BlockIdGenerator(3, 1024)
        self.transformations = []
        self.objcache = obnamlib.ObjectCache()

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
        # The new mappings are kept separately for metadata and content
        # blocks.
        self.new_mappings = {}
        self.new_content_mappings = {}

    def close(self): # pragma: no cover
        self.fs.close()

    def check_mode(self, mode):
        if mode not in ["r", "w"]:
            raise obnamlib.Exception("Unknown Store mode '%s'" % mode)

    def assert_readwrite_mode(self):
        if self.mode != "w":
            raise obnamlib.Exception("Store not in read-write mode")

    def new_object(self, kind):
        self.assert_readwrite_mode()
        return self.factory.new_object(kind=kind)

    def transform_to_fs(self, block): # pragma: no cover
        """Apply transformations to a block about to be written."""
        for t in self.transformations:
            block = t.to_fs(block)
        return block

    def transform_from_fs(self, block): # pragma: no cover
        """Apply transformations to a block that has been read."""
        for t in reversed(self.transformations):
            block = t.from_fs(block)
        return block

    def get_block(self, blockid): # pragma: no cover
        """Read a given block from the filesystem, and de-transform it."""
        logging.debug("Get block %s" % blockid)
        return self.transform_from_fs(self.fs.cat(blockid))

    def put_block(self, blockid, block, overwrite=False): # pragma: no cover
        """Write a block to the filesystem, after transforming it."""
        logging.debug("Put block %s" % blockid)
        if overwrite:
            self.fs.overwrite_file(blockid, self.transform_to_fs(block))
        else:
            self.fs.write_file(blockid, self.transform_to_fs(block))

    def find_block(self, host, id):
        """Find the block in which an object resides.
        
        If no matching block is found, raise NotFound().
        This will load in new mappings from disk, as necessary.
        For that, we need the host, since mappings are per host.
        
        """

        logging.debug("find_block %s" % id)
        
        # Perhaps we know the answer already?
        if id in self.objmap:
            logging.debug("find_block objmap hit for %s" % id)
            return self.objmap[id]
        else:
            logging.debug("find_block objmap miss for %s" % id)
            
        # Load mapping blocks until we find something.
        logging.debug("find_block: host %s" % host.id)
        logging.debug("find_block: maprefs %s" % repr(host.maprefs))
        logging.debug("find_block: contmaprefs %s" % repr(host.contmaprefs))
        for mapref in host.maprefs + host.contmaprefs:
            logging.debug("find_block: mapref %s" % mapref)
            encoded = self.get_block(mapref)
            blkid, objs, mappings = self.block_factory.decode_block(encoded)
            self.objmap.update(mappings)
            if id in self.objmap:
                logging.debug("find_block: found %s in %s" % (id, mapref))
                return self.objmap[id]

        # Bummer.
        logging.debug("find_block: can't find %s" % id)
        raise NotFound("Object %s not found in store" % id)

    def get_object(self, host, id):
        """Return the object with a given id.
        
        The object will be loaded from disk first, if necessary.
        
        """
        
        logging.debug("get_object %s" % id)
        assert id is not None
        
        obj = self.objcache.get(id)
        if obj: # pragma: no cover
            logging.debug("get_object objcache hit for %s" % id)
            return obj
        else: # pragma: no cover
            logging.debug("get_object objcache miss for %s" % id)
        
        block_id = self.find_block(host, id)
        encoded = self.get_block(block_id)
        block_id, objs, mappings = self.block_factory.decode_block(encoded)
        found = None
        for obj in objs:
            self.objcache.put(obj)
            if id == obj.id:
                found = obj

        if not found:
            raise obnamlib.NotFound("Object %s not found in block %s" % 
                                    (id, block_id))
        self.objcache.put(found)
        return found

    def put_object(self, obj):
        """Put an object into the store.
        
        The object may not be accessible until commit has been called.
        
        """

        self.assert_readwrite_mode()
        if obj.kind == obnamlib.FILEPART:
            self.content_queue.append(obj)
        else:
            self.object_queue.append(obj)
        
        if self.put_hook is not None:
            self.put_hook()

    @property
    def unpushed_size(self):
        """Return approximate size of unpushed objects."""
        
        return (self.object_queue.unpushed_size + 
                self.content_queue.unpushed_size)

    def get_host(self, host_id):
        """Return the host object for the host with the given id."""
        
        if self.fs.exists(host_id):
            encoded = self.get_block(host_id)
            blkid, objs, mappings = self.block_factory.decode_block(encoded)
            for obj in objs:
                if obj.id == host_id:
                    return obj
            raise NotFound("Cannot find host object %s" % host_id)
        else:
            host = self.new_object(kind=obnamlib.HOST)
            host.id = host_id
            return host

    def push_queue(self, host, queue, mappings):
        """Push queued objects into one or more blocks.

        The objects will be collected into one or more blocks, and
        the block of each object will be stored in mapping blocks.
        The mapping block will be generated by the commit method.
        Until commit is called, the mappings will be temporarily stored
        in memory, sorted by the host object, in the appropriate mappings
        dictionary.
        
        """

        if queue:
            block_id = self.idgen.new_id()
            logging.debug("push_queue: block_id %s" % block_id)
            encoded = self.block_factory.encode_block(block_id,  queue,  {})
            self.put_block(block_id, encoded)
            for obj in queue:
                if host not in mappings:
                    mappings[host] = obnamlib.Mapping()
                mappings[host][obj.id] = block_id
            del queue[:]

    def push_objects(self, host):
        if self.object_queue:
            logging.debug("push_objects")
            self.push_queue(host, self.object_queue, self.new_mappings)

    def push_content_objects(self, host):
        if self.content_queue:
            logging.debug("push_content_objects")
            self.push_queue(host, self.content_queue, self.new_content_mappings)

    def push_mappings(self, host, maprefs, new_mappings):
        """Generate and push out a new mapping block with all new objects.
        
        The block id of the new mapping block is added to the host's
        maprefs. The caller needs to ensure the host gets committed for
        the mapping block to be useful for later runs.
        
        """

        if host not in new_mappings:
            return
        mappings = new_mappings[host]
        if mappings:
            block_id = self.idgen.new_id()
            encoded = self.block_factory.encode_block(block_id, [], mappings)
            self.put_block(block_id, encoded)
            maprefs.append(block_id)
            del new_mappings[host]

    def push_new_mappings(self, host):
        self.push_mappings(host, host.maprefs, self.new_mappings)

    def push_new_content_mappings(self, host): # pragma: no cover
        self.push_mappings(host, host.contmaprefs, self.new_content_mappings)

    def commit(self, host, close=True):
        """Commit all changes made to a specific host."""

        self.assert_readwrite_mode()
        
        # First, push out all queued objects.
        self.push_objects(host)
        self.push_content_objects(host)

        # Next, push out a new mapping block for all the new objects.
        # This adds a new MAPREF to the host object.
        self.push_new_mappings(host)
        self.push_new_content_mappings(host)

        # Finally, push the recently modified host object out.
        encoded = self.block_factory.encode_block(host.id, [host], {})
        self.put_block(host.id, encoded, overwrite=True)
        
        if close:
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
        for contpart_ref in cont.filecontentspartrefs:
            contpart = self.get_object(host, contpart_ref)
            for c in contpart.components:
                assert c.kind in (obnamlib.FILEPARTREF, obnamlib.SUBFILEPART)
                if c.kind == obnamlib.FILEPARTREF:
                    part = self.get_object(host, str(c))
                    output.write(part.data)
                else:
                    filepart = self.get_object(host, c.filepartref)
                    data = filepart.find_strings(kind=obnamlib.FILECHUNK)[0]
                    output.write(data[c.offset:c.offset + c.length])

    def make_rsyncsigparts(self, content, siggen, rsync_block_size, new_data):
        sigs = siggen.buffered_block_signature(new_data, rsync_block_size)
        if sigs:
            rsyncsigpart = self.new_object(kind=obnamlib.RSYNCSIGPART)
            rsyncsigpart.components += sigs
            self.put_object(rsyncsigpart)
            content.rsyncsigpartrefs += [rsyncsigpart.id]

    def put_contents(self, f, rsynclookuptable, chunk_size, rsync_block_size,
                     prevcont):
        """Write contents of open file to store.
        
        The contents of the file will be split into chunks of `chunk_size`
        bytes. Each chunk gets placed in a FILEPART object. Finally,
        and FILECONTENTS object is created, put into the store, and
        returned.
        
        rsynclookuptable is an instance of obnamlib.RsyncLookupTable,
        containing the signature data for the previous version of the
        file. It may be None.
        
        rsync_block_size is the size of rsync block sizes for signature
        computation.
        
        """

        content = self.new_object(kind=obnamlib.FILECONTENTS)
        content_part = self.new_object(kind=obnamlib.FILECONTENTSPART)
        md5 = hashlib.md5()
        siggen = obnamlib.RsyncSignatureGenerator()
        
        if not rsynclookuptable:
            rsynclookuptable = obnamlib.RsyncLookupTable()

        deltagen = obnamlib.RsyncDeltaGenerator(rsync_block_size,
                                                rsynclookuptable,
                                                chunk_size)

        while True:
            data = f.read(chunk_size)

            md5.update(data)
            self.make_rsyncsigparts(content, siggen, rsync_block_size, data)

            for x in deltagen.feed(data):
                assert x.kind in (obnamlib.FILECHUNK, obnamlib.SUBFILEPART)
                if x.kind == obnamlib.FILECHUNK:
                    filepart = self.new_object(kind=obnamlib.FILEPART)
                    filepart.components.append(x)
                    self.put_object(filepart)
                    sfp = obnamlib.SubFilePart()
                    sfp.filepartref = filepart.id
                    sfp.offset = 0
                    sfp.length = len(str(x))
                    content_part.components += [sfp]
                else: # pragma: no cover
                    assert prevcont is not None
                    for sftp in prevcont.find_fileparts(x.offset, x.length):
                        content_part.components += [sfp]

            if not data:
                break

        self.make_rsyncsigparts(content, siggen, rsync_block_size, "")

        self.put_object(content_part)
        content.add_filecontentspartref(content_part.id)
        content.md5 = md5.digest()
        self.put_object(content)
        return content

