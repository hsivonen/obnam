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


"""Abstraction for storing backup data, for Obnam."""


import logging

import obnam


class ObjectNotFoundInStore(obnam.exception.ObnamException):

    def __init__(self, id):
        self._msg = "Object %s not found in store" % id


class Store:

    def __init__(self, context):
        self._context = context
        self._host = None

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
            host_block = obnam.io.get_host_block(self._context)
            if host_block:
                self._host = obnam.obj.create_host_from_block(host_block)
            else:
                id = self._context.config.get("backup", "host-id")
                self._host = obnam.obj.HostBlockObject(host_id=id)
        return self._host


    def load_maps(self):
        """Load non-content map blocks."""
        ids = self._host.get_map_block_ids()
        logging.info("Decoding %d mapping blocks" % len(ids))
        obnam.io.load_maps(self._context, self._context.map, ids)

    def load_content_maps(self):
        """Load content map blocks."""
        ids = self._host.get_contmap_block_ids()
        logging.info("Decoding %d content mapping blocks" % len(ids))
        obnam.io.load_maps(self._context, self._context.contmap, ids)

    def _update_map_helper(self, map):
        """Create new mapping blocks of a given kind, and upload them.
        
        Return list of block ids for the new blocks.

        """

        if obnam.map.get_new(map):
            id = self._context.be.generate_block_id()
            logging.debug("Creating mapping block %s" % id)
            block = obnam.map.encode_new_to_block(map, id)
            self._context.be.upload_block(id, block, True)
            return [id]
        else:
            logging.debug("No new mappings, no new mapping block")
            return []

    def _update_maps(self):
        """Create new object mapping blocks and upload them."""
        logging.debug("Creating new mapping block for normal mappings")
        return self._update_map_helper(self._context.map)

    def _update_content_maps(self):
        """Create new content object mapping blocks and upload them."""
        logging.debug("Creating new mapping block for content mappings")
        return self._update_map_helper(self._context.contmap)

    def commit_host_block(self):
        """Commit the current host block to the store.
        
        If no host block exists, create one. If one already exists,
        update it with new info.
        
        NOTE that after this operation the host block has changed,
        and you need to call get_host_block again.
        
        """

        obnam.io.flush_all_object_queues(self._context)
    
        logging.info("Creating new mapping blocks")
        host = self.get_host_block()
        map_ids = host.get_map_block_ids() + self._update_maps()
        contmap_ids = (host.get_contmap_block_ids() + 
                       self._update_content_maps())
        
        logging.info("Creating new host block")
        gen_ids = host.get_generation_ids()
        host2 = obnam.obj.HostBlockObject(host_id=host.get_id(), 
                                          gen_ids=gen_ids, 
                                          map_block_ids=map_ids,
                                          contmap_block_ids=contmap_ids)
        obnam.io.upload_host_block(self._context, host2.encode())

        self._host = host2

    def queue_object(self, object):
        """Queue an object for upload to the store.
        
        It won't necessarily be committed (i.e., uploaded, etc) until
        you call commit_host_block. Until it is committed, you may not
        call get_object on it.
        
        """
        
        obnam.io.enqueue_object(self._context, self._context.oq,
                                self._context.map, object.get_id(), 
                                object.encode(), True)

    def get_object(self, id):
        """Get an object from the store.
        
        If the object cannot be found, raise an exception.
        
        """

        object = obnam.io.get_object(self._context, id)
        if object:
            return object
        raise ObjectNotFoundInStore(id)
