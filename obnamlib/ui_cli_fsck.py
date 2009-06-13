# Copyright (C) 2009  Lars Wirzenius <liw@liw.fi>
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
import os
import sys

import obnamlib


class FsckCommand(obnamlib.CommandLineCommand):

    """Verify that all objects in host block are found, recursively."""

    def assertEqual(self, value1, value2, msg=None):
        if value1 != value2:
            sys.stdout.write("FSCK ERROR: ")
            if msg:
                sys.stdout.write("%s: " % msg)
            sys.stdout.write("%s\n" % ("%s != %s" % (value1, value2)))
            self.ok = False

    def assertNotEqual(self, value1, value2, msg=None):
        if value1 == value2:
            if msg:
                sys.stdout.write("%s: " % msg)
            sys.stdout.write("%s\n" % ("%s == %s" % (value1, value2)))
            self.ok = False

    def check_block_id(self, components, block_id):
        """Check that block id matches what it should be."""
        ids = [c for c in components if c.kind == obnamlib.BLKID]
        self.assertEqual(len(ids), 1, "block must have exactly one block id")
        self.assertEqual(str(ids[0]), block_id, 
                         "block id must match filename")

    def objnames(self, kinds):
        return set(obnamlib.obj_kinds.nameof(kind) for kind in kinds)

    def check_block_unity_of_purpose(self, components):
        """Check that block contains only one style of data.
        
        For example, only file metadata, only mappings, or only
        file content data, or only the host block.
        
        """

        ignored = (obnamlib.BLKID,)
        c_kinds = [c.kind for c in components if c.kind not in ignored]
        self.assertEqual(set(c_kinds), set([c_kinds[0]]), 
                         "component kinds all equal in block")
        
        o_components = [c for c in components if c.kind == obnamlib.OBJECT]
        o_kinds = []
        for c in o_components:
            for cc in c.children:
                if cc.kind == obnamlib.OBJKIND:
                    o_kind, pos = obnamlib.varint.decode(str(cc), 0)
                    o_kinds.append(o_kind)

        if obnamlib.HOST in o_kinds:
            self.assertEqual(self.objnames(o_kinds), 
                             self.objnames([obnamlib.HOST]),
                             "host block must only contain host object")
            self.assertEqual(len(o_kinds), 1, 
                             "host block must contain exactly one host object")
        elif obnamlib.FILEPART in o_kinds:
            self.assertEqual(self.objnames(o_kinds), 
                             self.objnames([obnamlib.FILEPART]),
                            "block with file contents must contain "
                            "only file content objects")
        
    def check_block(self, block_id):
        """Check that a block looks OK."""

        logging.debug("Checking block %s" % block_id)
        blob = self.store.get_block(block_id)
        
        cookie = obnamlib.BlockFactory.BLOCK_COOKIE
        self.assertEqual(cookie, blob[:len(cookie)],
                         "block must start with cookie")
        
        of = obnamlib.ObjectFactory()
        pos = len(cookie)
        components = []
        while pos < len(blob):
            comp, pos = of.decode_component(blob, pos)
            components.append(comp)

        self.check_block_id(components, block_id)
        self.check_block_unity_of_purpose(components)

    def find_blocks(self):
        """Generator for all block ids in store."""
        for dirname, x, filenames in self.store.fs.depth_first("."):
            for filename in filenames:
                if not filename.endswith(".bak"):
                    pathname = os.path.join(dirname, filename)
                    assert pathname.startswith("./")
                    yield pathname[2:] # strip leading ./

    def check_file(self, f):
        self.assertNotEqual(f.owner, None)
        self.assertNotEqual(f.group, None)

    def check_filegroup(self, fg):
        self.assertNotEqual(len(fg.files), 0, "FILEGROUP must contain files")
        for f in fg.files:
            self.check_file(f)

    def check_object(self, obj):
        dict = {
            obnamlib.FILEGROUP: self.check_filegroup,
        }
        
        if obj.kind in dict:
            dict[obj.kind](obj)

    def fsck(self): # pragma: no cover
        self.ok = True

        seen = set(self.host.id)
        refs = self.host.genrefs[:]
        while refs:
            ref = refs[0]
            refs = refs[1:]
            logging.debug("fsck: getting object %s" % ref)
            seen.add(ref)
            try:
                obj = self.store.get_object(self.host, ref)
            except obnamlib.NotFound:
                logging.error("fsck: object %s not found" % ref)
            else:
                self.check_object(obj)
                refs += [x for x in obj.find_refs() if x not in seen]

        for block_id in self.find_blocks():
            self.check_block(block_id)

        if self.ok:
            logging.info("fsck OK")
        else:
            logging.warning("fsck found problems")
        return self.ok
    
    def run(self, options, args, progress): # pragma: no cover
        self.store = obnamlib.Store(options.store, "r")
        self.store.transformations = obnamlib.choose_transformations(options)
        self.host = self.store.get_host(options.host)
        ok = self.fsck()
        self.store.close()
        if not ok:
            sys.exit(1)
