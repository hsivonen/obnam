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


import logging

import obnamlib


class BlockFactory(object):

    BLOCK_COOKIE = "blockhead\n"

    def update_mappings(self, mappings, objmap):
        assert objmap.kind == obnamlib.OBJMAP
        block_id = objmap.first_string(kind=obnamlib.BLOCKREF)
        assert block_id

        for cmp in objmap.children:
            if cmp.kind == obnamlib.OBJREF:
                mappings[block_id] = str(cmp)

    def decode_block(self, string):
        """Decode an encoded block.

        Return tuple with block ID, list of objects, and a dictionary
        of mappings.

        """

        if not string.startswith(self.BLOCK_COOKIE):
            raise obnamlib.Exception("Block does not start with cookie.")

        of = obnamlib.ObjectFactory()

        block_id = None
        objects = []
        mappings = obnamlib.Mapping()

        pos = len(self.BLOCK_COOKIE)
        while pos < len(string):
            cmp, pos = of.decode_component(string, pos)
            if cmp.kind == obnamlib.OBJECT:
                objects.append(of.construct_object(cmp))
            elif cmp.kind == obnamlib.OBJMAP:
                self.update_mappings(mappings, cmp)
            elif cmp.kind == obnamlib.BLKID:
                block_id = str(cmp)
            else:
                raise obnamlib.Exception("Unknown component kind %d" % 
                                         cmp.kind)

        logging.debug("decode_block id %s #objects %d #mappings %d" %
                      (block_id, len(objects), len(mappings)))
        return block_id, objects, mappings

    def mappings_to_components(self, mappings):
        """Create components that match mappings.
        
        The caller will then encode these as strings for writing to disk.
        
        """
        
        components = []

        by_block_id = {}
        for key, value in mappings.iteritems():
            by_block_id[key] = by_block_id.get(key, []) + [value]

        for key, values in by_block_id.iteritems():
            c = obnamlib.Component(kind=obnamlib.OBJMAP)
            c.children.append(obnamlib.BlockRef(key))
            for value in values:
                c.children.append(obnamlib.ObjRef(value))
            components.append(c)

        return components

    def encode_block(self, block_id, objects, mappings):
        """Encode a block."""

        of = obnamlib.ObjectFactory()

        parts = [self.BLOCK_COOKIE]

        id_component = obnamlib.BlockId(block_id)
        parts.append(of.encode_component(id_component))

        parts += [of.encode_component(c)
                  for c in self.mappings_to_components(mappings)]

        for obj in objects:
            parts.append(of.encode_object(obj))

        return "".join(parts)
