
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


class ObjtreeCommand(obnamlib.CommandLineCommand):

    """Print a graphviz .dot file of the object DAG.
    
    To use the file:
    
        obnam objtree host.id store.path > foo.dot
        dot -Tpng -o foo.png foo.dot
        eog foo.png
    
    """

    def quotechar(self, char):
        if char == '"':
            return '\\"'
        else:
            return char

    def quote(self, name):
        return '"%s"' % "".join(self.quotechar(c) for c in name)

    def label(self, obj):
        label = "%s" % obnamlib.obj_kinds.nameof(obj.kind)
        if obj.kind == obnamlib.DIR:
            label += "<br/>%s" % obj.name
        return label

    def find_refs(self, obj):
        result = []
        obj.prepare_for_encoding()
        for c in obj.components:
            if obnamlib.cmp_kinds.is_ref(c.kind):
                result.append(str(c))
        obj.post_decoding_hook()
        return result

    def objtree(self): # pragma: no cover
        print "digraph abstract {"
        refs = self.host.genrefs[:]
        while refs:
            ref = refs[0]
            obj = self.store.get_object(self.host, ref)
            print '  %s [ label=<%s> ];' % (self.quote(ref), self.label(obj))
            more_refs = self.find_refs(obj)
            for target in more_refs:
                print "  %s -> %s;" % (self.quote(ref), self.quote(target))
            refs = refs[1:] + more_refs
        print "}"
    
    def run(self, options, args, progress): # pragma: no cover
        self.store = obnamlib.Store(options.store, "r")
        self.store.transformations = obnamlib.choose_transformations(options)
        self.host = self.store.get_host(options.host)
        self.objtree()
        self.store.close()
