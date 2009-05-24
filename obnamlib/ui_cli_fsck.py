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

import obnamlib


class FsckCommand(obnamlib.CommandLineCommand):

    """Verify that all objects in host block are found, recursively."""

    def check_filegroup(self, fg):
        assert len(fg.files) > 0, "FILEGROUP must contain files"

    def check_object(self, obj):
        dict = {
            obnamlib.FILEGROUP: self.check_filegroup,
        }
        
        if obj.kind in dict:
            dict[obj.kind](obj)

    def find_refs(self, obj):
        result = []
        obj.prepare_for_encoding()
        for c in obj.components:
            if obnamlib.cmp_kinds.is_ref(c.kind):
                result.append(str(c))
        return result

    def fsck(self): # pragma: no cover
        refs = self.host.genrefs[:]
        while refs:
            ref = refs[0]
            refs = refs[1:]
            logging.debug("fsck: getting object %s" % ref)
            obj = self.store.get_object(self.host, ref)
            self.check_object(obj)
            refs += self.find_refs(obj)
        logging.info("fsck OK")
    
    def run(self, options, args): # pragma: no cover
        self.store = obnamlib.Store(options.store, "r")
        self.host = self.store.get_host(options.host)
        self.fsck()
        self.store.close()
