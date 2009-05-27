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


import uuid

import obnamlib


class ObjectFactory(object):

    classes = {
        obnamlib.DELTA: obnamlib.Delta,
        obnamlib.DELTAPART: obnamlib.DeltaPart,
        obnamlib.DIR: obnamlib.Dir,
        obnamlib.FILECONTENTS: obnamlib.FileContents,
        obnamlib.FILELIST: obnamlib.FileList,
        obnamlib.FILEGROUP: obnamlib.FileGroup,
        obnamlib.FILEPART: obnamlib.FilePart,
        obnamlib.GEN: obnamlib.Generation,
        obnamlib.HOST: obnamlib.Host,
        obnamlib.SIG: obnamlib.Signature,
        }

    def __init__(self):
        self.cmp_factory = obnamlib.ComponentFactory()

    def new_id(self):
        return str(uuid.uuid4())

    def new_object(self, kind):
        if kind not in self.classes:
            raise obnamlib.Exception("Don't know object kind %s" % kind)
        return self.classes[kind](id=self.new_id())

    def encode_component(self, cmp):
        if obnamlib.cmp_kinds.is_composite(cmp.kind):
            content = "".join(self.encode_component(x) for x in cmp.children)
        else:
            content = str(cmp)
        length = obnamlib.varint.encode(len(content))
        kind = obnamlib.varint.encode(cmp.kind)
        return "%s%s%s" % (length, kind, content)

    def decode_component(self, str, pos):
        assert pos < len(str)

        size, pos = obnamlib.varint.decode(str, pos)
        kind, pos = obnamlib.varint.decode(str, pos)
        
        content = str[pos:pos+size]
        pos += size

        if obnamlib.cmp_kinds.is_composite(kind):
            children = self.decode_all_components(content)
            cmp = self.cmp_factory.new_component(kind, children=children)
        else:
            cmp = self.cmp_factory.new_component(kind=kind, string=content)
        
        return cmp, pos

    def decode_all_components(self, str, pos=0):
        list = []
        while pos < len(str):
            cmp, pos = self.decode_component(str, pos)
            list.append(cmp)
        return list

    def encode_object(self, obj):
        obj.prepare_for_encoding()

        id = obnamlib.ObjectId(obj.id)
        kind = obnamlib.ObjectKind(obj.kind)

        cmp = obnamlib.ObjectComponent([id, kind] + obj.components)
        return self.encode_component(cmp)

    def construct_object(self, cmp):
        assert cmp.kind == obnamlib.OBJECT

        temp = cmp.first_string(kind=obnamlib.OBJKIND)
        kind, dummy = obnamlib.varint.decode(temp, 0)

        obj = self.new_object(kind=kind)
        obj.id = cmp.first_string(kind=obnamlib.OBJID)
        obj.components = [c 
                          for c in cmp.children
                          if c.kind not in [obnamlib.OBJID, obnamlib.OBJKIND]]
        obj.post_decoding_hook()

        return obj

    def decode_object(self, str, pos):
        cmp, pos = self.decode_component(str, pos)
        return self.construct_object(cmp), pos