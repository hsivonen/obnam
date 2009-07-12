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


import obnamlib


class FileContents(obnamlib.Object):

    """Store the full contents of a file."""

    kind = obnamlib.FILECONTENTS

    def __init__(self, id):
        obnamlib.Object.__init__(self, id=id)

    def get_md5(self): # pragma: no cover
        strings = self.find_strings(kind=obnamlib.MD5)
        if strings:
            return strings[0]
        else:
            return None

    def set_md5(self, value): # pragma: no cover
        self.extract(kind=obnamlib.MD5)
        self.components += [obnamlib.Md5(value)]
        
    md5 = property(get_md5, set_md5)

    def add_filecontentspartref(self, ref):
        c = obnamlib.FileContentsPartRef(ref)
        self.components.append(c)

    @property
    def filecontentspartrefs(self):
        return self.find_strings(kind=obnamlib.FILECONTENTSPARTREF)
        
    def add_rsyncsigpartref(self, ref): # pragma: no cover
        c = obnamlib.RsyncSigPartRef(ref)
        self.components.append(c)

    def get_rsyncsigpartrefs(self): # pragma: no cover
        return self.find_strings(kind=obnamlib.RSYNCSIGPARTREF)

    def set_rsyncsigpartrefs(self, new_refs): # pragma: no cover
        self.extract(kind=obnamlib.RSYNCSIGPARTREF)
        self.components += [obnamlib.RsyncSigPartRef(x) for x in new_refs]
        
    rsyncsigpartrefs = property(get_rsyncsigpartrefs, set_rsyncsigpartrefs)

    def find_fileparts(self, offset, length): # pragma: no cover
        """Find the parts of a file that contain a sub-string.
        
        This is a generator. It will return a series of obnamlib.SubFilePart
        instances that refer to the FileParts that contain the sub-string
        of the whole contents of the file starting at byte offset offset,
        and being length bytes.
        
        The length of the sub-string will be shorter than length if 
        offset+length is past the end of the file.

        """
        
        subfileparts = self.find(kind=obnamlib.SUBFILEPART)

        # Skip stuff before offset.
        while subfileparts and subfileparts[0].length <= offset:
            del subfileparts[0]
                
        # Generate first part, which may be partial.
        assert not subfileparts or length <= subfileparts[0].length
        if subfileparts and offset > 0:
            sfp = obnamlib.SubFilePart()
            sfp.filepartref = subfileparts[0].filepartref
            more_offset = subfileparts[0].offset + offset
            sfp.offset = subfileparts[0].offset + offset
            sfp.length = min(subfileparts[0].length - more_offset, length)
            length -= sfp.length
            del subfileparts[0]
            yield sftp
               
        # Genereate complete existing parts as long as possible.
        while subfileparts and subfileparts[0].length >= length:
            yield subfileparts[0]
            length -= subfileparts[0].length
            del subfileparts[0]
                
        # Generate final partial part.
        assert not subfileparts or length < subfileparts[0].length
        if subfileparts and length > 0:
            sfp = obnamlib.SubFilePart()
            sfp.filepartref = subfileparts[0].filepartref
            sfp.offset = subfileparts[0].offset
            sfp.length = length
            yield sfp

