# Copyright (C) 2008, 2009  Lars Wirzenius <liw@liw.fi>
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


def str_or_ref(klass):
    return lambda s, c: klass(s)


def varint(klass):
    return lambda s, c: klass(obnamlib.varint.decode(s, 0)[0])


def object_kind_factory(string, children):
    return obnamlib.ObjectKind(obnamlib.varint.decode(string, 0)[0])


def stat_factory(string, children):
    return obnamlib.Stat(obnamlib.decode_stat(string))


def find(children, kind):
    for c in children:
        if c.kind == kind:
            return str(c)
    return None


def composite_factory(klass):
    return lambda s, c: klass(c)


def file_factory(string, children):
    stat = obnamlib.decode_stat(find(children, obnamlib.STAT))
    return obnamlib.File(find(children, obnamlib.FILENAME), 
                         stat=stat,
                         contref=find(children, obnamlib.CONTREF), 
                         sigref=find(children, obnamlib.SIGREF),
                         deltaref=find(children, obnamlib.DELTAREF), 
                         symlink_target=find(children, obnamlib.SYMLINKTARGET),
                         owner=find(children, obnamlib.OWNER),
                         group=find(children, obnamlib.GROUP))


class ComponentFactory(object):

    components = {
        obnamlib.OBJID:         str_or_ref(obnamlib.ObjectId),
        obnamlib.OBJKIND:       object_kind_factory,
        obnamlib.BLKID:         str_or_ref(obnamlib.BlockId),
        obnamlib.FILECHUNK:     str_or_ref(obnamlib.FileChunk),
        obnamlib.OBJECT:        composite_factory(obnamlib.ObjectComponent),
        obnamlib.OBJMAP:        composite_factory(obnamlib.ObjMap),
        obnamlib.CONTREF:       str_or_ref(obnamlib.ContRef),
        obnamlib.FILENAME:      str_or_ref(obnamlib.FileName),
        obnamlib.SIGDATA:       str_or_ref(obnamlib.SigData),
        obnamlib.SIGREF:        str_or_ref(obnamlib.SigRef),
        obnamlib.GENREF:        str_or_ref(obnamlib.GenRef),
        obnamlib.OBJREF:        str_or_ref(obnamlib.ObjRef),
        obnamlib.BLOCKREF:      str_or_ref(obnamlib.BlockRef),
        obnamlib.MAPREF:        str_or_ref(obnamlib.MapRef),
        obnamlib.FILEPARTREF:   str_or_ref(obnamlib.FilePartRef),
        obnamlib.FORMATVERSION: str_or_ref(obnamlib.FormatVersion),
        obnamlib.FILE:          file_factory,
        obnamlib.FILELISTREF:   str_or_ref(obnamlib.FileListRef),
        obnamlib.CONTMAPREF:    str_or_ref(obnamlib.ContMapRef),
        obnamlib.DELTAREF:      str_or_ref(obnamlib.DeltaRef),
        obnamlib.DELTADATA:     str_or_ref(obnamlib.DeltaData),
        obnamlib.STAT:          stat_factory,
        obnamlib.GENSTART:      str_or_ref(obnamlib.GenStart),
        obnamlib.GENEND:        str_or_ref(obnamlib.GenEnd),
        obnamlib.DELTAPARTREF:  str_or_ref(obnamlib.DeltaPartRef),
        obnamlib.DIRREF:        str_or_ref(obnamlib.DirRef),
        obnamlib.FILEGROUPREF:  str_or_ref(obnamlib.FileGroupRef),
        obnamlib.SNAPSHOTGEN:   str_or_ref(obnamlib.SnapshotGen),
        obnamlib.SYMLINKTARGET: str_or_ref(obnamlib.SymlinkTarget),
        obnamlib.OWNER:         str_or_ref(obnamlib.Owner),
        obnamlib.GROUP:         str_or_ref(obnamlib.Group),
        obnamlib.CHECKSUMS:     composite_factory(obnamlib.Checksums),
        obnamlib.ADLER32:       str_or_ref(obnamlib.Adler32),
        obnamlib.MD5:           str_or_ref(obnamlib.Md5),
        obnamlib.SIGBLOCKSIZE:  varint(obnamlib.SigBlockSize),
        obnamlib.OFFSET:        varint(obnamlib.Offset),
        obnamlib.LENGTH:        varint(obnamlib.Length),
        obnamlib.SUBFILEPART:   composite_factory(obnamlib.SubFilePart),
        obnamlib.RSYNCSIGPARTREF: str_or_ref(obnamlib.RsyncSigPartRef),
        obnamlib.FILECONTENTSPARTREF: 
                                str_or_ref(obnamlib.FileContentsPartRef),
        }

    def new_component(self, kind, string=None, children=None):
        if kind not in self.components:
            raise obnamlib.Exception("Don't know component kind %s" % kind)
        return self.components[kind](string, children)
