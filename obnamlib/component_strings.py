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


import obnamlib


# This module contains the component classes that are just for simple
# string values. They don't need any extra testing. There are, however,
# so many of them that it's pointless putting each in its own module.


class Adler32(obnamlib.StringComponent):

    string_kind = obnamlib.ADLER32


class BlockId(obnamlib.StringComponent):

    string_kind = obnamlib.BLKID


class BlockRef(obnamlib.StringComponent):

    string_kind = obnamlib.BLOCKREF


class ContMapRef(obnamlib.StringComponent):

    string_kind = obnamlib.CONTMAPREF


class ContRef(obnamlib.StringComponent):

    string_kind = obnamlib.CONTREF


class DeltaData(obnamlib.StringComponent):

    string_kind = obnamlib.DELTADATA


class DeltaPartRef(obnamlib.StringComponent):

    string_kind = obnamlib.DELTAPARTREF


class DeltaRef(obnamlib.StringComponent):

    string_kind = obnamlib.DELTAREF


class DirRef(obnamlib.StringComponent):

    string_kind = obnamlib.DIRREF


class FileChunk(obnamlib.StringComponent):

    string_kind = obnamlib.FILECHUNK


class FileGroupRef(obnamlib.StringComponent):

    string_kind = obnamlib.FILEGROUPREF


class FileListRef(obnamlib.StringComponent):

    string_kind = obnamlib.FILELISTREF


class FileName(obnamlib.StringComponent):

    string_kind = obnamlib.FILENAME


class FilePartRef(obnamlib.StringComponent):

    string_kind = obnamlib.FILEPARTREF


class FormatVersion(obnamlib.StringComponent):

    string_kind = obnamlib.FORMATVERSION


class GenEnd(obnamlib.StringComponent):

    string_kind = obnamlib.GENEND


class GenRef(obnamlib.StringComponent):

    string_kind = obnamlib.GENREF


class GenStart(obnamlib.StringComponent):

    string_kind = obnamlib.GENSTART


class MapRef(obnamlib.StringComponent):

    string_kind = obnamlib.MAPREF


class Md5(obnamlib.StringComponent):

    string_kind = obnamlib.MAPREF


class ObjectId(obnamlib.StringComponent):

    string_kind = obnamlib.OBJID


class ObjRef(obnamlib.StringComponent):

    string_kind = obnamlib.OBJREF


class SigData(obnamlib.StringComponent):

    string_kind = obnamlib.SIGDATA


class SigRef(obnamlib.StringComponent):

    string_kind = obnamlib.SIGREF


class SnapshotGen(obnamlib.StringComponent):

    string_kind = obnamlib.SNAPSHOTGEN


class SymlinkTarget(obnamlib.StringComponent):

    string_kind = obnamlib.SYMLINKTARGET
    
class Owner(obnamlib.StringComponent):

    string_kind = obnamlib.OWNER
    
class Group(obnamlib.StringComponent):

    string_kind = obnamlib.GROUP

