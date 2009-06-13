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


class ShowobjsCommand(obnamlib.CommandLineCommand):

    """Show object info for all objects for host."""

    def showcmp(self, cmp, indent=0):
        s = " " * (indent * 2)
        print s+"component:", obnamlib.cmp_kinds.nameof(cmp.kind),
        if obnamlib.cmp_kinds.is_plain(cmp.kind):
            print repr(str(cmp))
        elif obnamlib.cmp_kinds.is_ref(cmp.kind):
            print repr(str(cmp))
        elif obnamlib.cmp_kinds.is_composite(cmp.kind):
            print
            for c in cmp.children:
                self.showcmp(c, indent+1)

    def showobj(self, obj):
        print "id:", obj.id
        print "kind:", obnamlib.obj_kinds.nameof(obj.kind)
        obj.prepare_for_encoding()
        for c in obj.components:
            self.showcmp(c)
        print

    def find_refs(self, obj):
        result = []
        obj.prepare_for_encoding()
        for c in obj.components:
            if obnamlib.cmp_kinds.is_ref(c.kind):
                result.append(str(c))
        obj.post_decoding_hook()
        return result

    def showobjs(self): # pragma: no cover
        self.showobj(self.host)
        refs = self.host.genrefs[:]
        seen = set(self.host.id)
        while refs:
            ref = refs[0]
            refs = refs[1:]
            if ref not in seen:
                try:
                    obj = self.store.get_object(self.host, ref)
                except obnamlib.NotFound:
                    print "ERROR: Object id %s not found" % ref
                else:
                    self.showobj(obj)
                    refs += self.find_refs(obj)
                seen.add(ref)
    
    def run(self, options, args, progress): # pragma: no cover
        self.store = obnamlib.Store(options.store, "r")
        self.store.transformations = obnamlib.choose_transformations(options)
        self.host = self.store.get_host(options.host)
        self.showobjs()
        self.store.close()
