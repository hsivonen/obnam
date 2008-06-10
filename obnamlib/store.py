# Copyright (C) 2008  Lars Wirzenius <liw@iki.fi>
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


"""Abstraction for storing backup data, for obnamlib."""


import logging
import os

import obnamlib


class ObjectNotFoundInStore(obnamlib.exception.ObnamException):

    def __init__(self, id):
        self._msg = "Object %s not found in store" % id


class Store:

    def __init__(self, context):
        self._context = context
        self._host = None

    def close(self):
        """Close connection to the store.
        
        You must not use this store instance for anything after
        closing it.
        
        """
        
        self._context.be.close()

    def get_host_block(self):
        """Return current host block, or None if one is not known.
        
        You must call fetch_host_block to fetch the host block first.
        
        """

        return self._host

    def fetch_host_block(self):
        """Fetch host block from store, if one exists.
        
        If a host block does not exist, it is not an error. A new
        host block is then created.
        
        """
        
        if not self._host:
            host_block = obnamlib.io.get_host_block(self._context)
            if host_block:
                self._host = obnamlib.obj.create_host_from_block(host_block)
            else:
                id = self._context.config.get("backup", "host-id")
                self._host = obnamlib.obj.HostBlockObject(host_id=id)
        return self._host


    def load_maps(self):
        """Load non-content map blocks."""
        ids = self._host.get_map_block_ids()
        logging.info("Decoding %d mapping blocks" % len(ids))
        obnamlib.io.load_maps(self._context, self._context.map, ids)

    def load_content_maps(self):
        """Load content map blocks."""
        ids = self._host.get_contmap_block_ids()
        logging.info("Decoding %d content mapping blocks" % len(ids))
        obnamlib.io.load_maps(self._context, self._context.contmap, ids)

    def _update_map_helper(self, map):
        """Create new mapping blocks of a given kind, and upload them.
        
        Return list of block ids for the new blocks.

        """

        if obnamlib.map.get_new(map):
            id = self._context.be.generate_block_id()
            logging.debug("Creating mapping block %s" % id)
            block = obnamlib.map.encode_new_to_block(map, id)
            self._context.be.upload_block(id, block, True)
            return [id]
        else:
            logging.debug("No new mappings, no new mapping block")
            return []

    def update_maps(self):
        """Create new object mapping blocks and upload them."""
        logging.debug("Creating new mapping block for normal mappings")
        return self._update_map_helper(self._context.map)

    def update_content_maps(self):
        """Create new content object mapping blocks and upload them."""
        logging.debug("Creating new mapping block for content mappings")
        return self._update_map_helper(self._context.contmap)

    def commit_host_block(self, new_generations):
        """Commit the current host block to the store.
        
        If no host block exists, create one. If one already exists,
        update it with new info.
        
        NOTE that after this operation the host block has changed,
        and you need to call get_host_block again.
        
        """

        obnamlib.io.flush_all_object_queues(self._context)
    
        logging.info("Creating new mapping blocks")
        host = self.get_host_block()
        map_ids = host.get_map_block_ids() + self.update_maps()
        contmap_ids = (host.get_contmap_block_ids() + 
                       self.update_content_maps())
        
        logging.info("Creating new host block")
        gen_ids = (host.get_generation_ids() + 
                   [gen.get_id() for gen in new_generations])
        host2 = obnamlib.obj.HostBlockObject(host_id=host.get_id(), 
                                          gen_ids=gen_ids, 
                                          map_block_ids=map_ids,
                                          contmap_block_ids=contmap_ids)
        obnamlib.io.upload_host_block(self._context, host2.encode())

        self._host = host2

    def queue_object(self, object):
        """Queue an object for upload to the store.
        
        It won't necessarily be committed (i.e., uploaded, etc) until
        you call commit_host_block. Until it is committed, you may not
        call get_object on it.
        
        """
        
        obnamlib.io.enqueue_object(self._context, self._context.oq,
                                self._context.map, object.get_id(), 
                                object.encode(), True)

    def queue_objects(self, objects):
        """Queue a list of objects for upload to the store.
        
        See queue_object for information about what queuing means.
        
        """
        
        for object in objects:
            self.queue_object(object)

    def get_object(self, id):
        """Get an object from the store.
        
        If the object cannot be found, raise an exception.
        
        """

        object = obnamlib.io.get_object(self._context, id)
        if object:
            return object
        raise ObjectNotFoundInStore(id)

    def parse_pathname(self, pathname):
        """Return list of components in pathname."""

        list = []
        while pathname:
            dirname = os.path.dirname(pathname)
            basename = os.path.basename(pathname)
            if basename:
                list.insert(0, basename)
            elif dirname == os.sep:
                list.insert(0, "/")
                dirname = ""
            pathname = dirname

        return list

    def _lookup_dir_from_refs(self, dirrefs, parts):
        for ref in dirrefs:
            dir = self.get_object(ref)
            if dir.get_name() == parts[0]:
                parts = parts[1:]
                if parts:
                    dirrefs = dir.get_dirrefs()
                    return self._lookup_dir_from_refs(dirrefs, parts)
                else:
                    return dir
        return None

    def lookup_dir(self, generation, pathname):
        """Return a DirObject that corresponds to pathname in a generation.
        
        Look up the directory in the generation. If it does not exist,
        return None.
        
        """

        dirrefs = generation.get_dirrefs()
        parts = self.parse_pathname(pathname)
        
        for dirref in dirrefs:
            dir = self.get_object(dirref)
            name = dir.get_name()
            if name == pathname:
                return dir
            else:
                if not name.endswith(os.sep):
                    name += os.sep
                if pathname.startswith(name):
                    subpath = pathname[len(name):]
                    subparts = self.parse_pathname(subpath)
                    return self._lookup_dir_from_refs(dir.get_dirrefs(),
                                                      subparts)

        return self._lookup_dir_from_refs(dirrefs, parts)

    def lookup_file(self, generation, pathname):
        """Find a non-directory thingy in a generation.
        
        Return a FILE component that corresponds to the filesystem entity
        in question. If not found, return None.
        
        """

        dirname = os.path.dirname(pathname)
        if dirname:
            dir = self.lookup_dir(generation, dirname)
            if dir:
                basename = os.path.basename(pathname)
                for id in dir.get_filegrouprefs():
                    fg = self.get_object(id)
                    file = fg.get_file(basename)
                    if file:
                        return file
        
        return None
