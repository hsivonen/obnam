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


"""Operation to show contents of generations in a backup store."""


import logging
import time

import obnam


class ShowGenerations(obnam.Operation):

    """Show contents of generations specified by user."""
    
    name = "show-generations"
    
    def format_period(self, start, end):
        """Format time period in a format that is easy to read for humans"""
        start = time.localtime(start)
        end = time.localtime(end)
        if start[0:3] == end[0:3]:
            return "%s %s - %s" % \
                (time.strftime("%Y-%m-%d", start),
                 time.strftime("%H:%M", start),
                 time.strftime("%H:%M", end))
        else:
            return "%s %s - %s %s" % \
                (time.strftime("%Y-%m-%d", start),
                 time.strftime("%H:%M", start),
                 time.strftime("%Y-%m-%d", end),
                 time.strftime("%H:%M", end))

    def format_generation_period(self, gen):
        """Return human readable string to show the period of a generation"""
        start_time = gen.get_start_time()
        end_time = gen.get_end_time()
        return self.format_period(start_time, end_time)
    
    def do_it(self, gen_ids):
        app = self.get_application()
        context = app.get_context()
        host = app.load_host()
        app.load_maps()
    
        pretty = True
        for gen_id in gen_ids:
            gen = obnam.io.get_object(context, gen_id)
            if not gen:
                logging.warning("Can't find generation %s" % gen_id)
                continue
            print "Generation: %s %s" % (gen_id, 
                                         self.format_generation_period(gen))
    
            fl_id = gen.get_filelistref()
            fl = obnam.io.get_object(context, fl_id)
            if not fl:
                logging.warning("Can't find file list object %s" % fl_id)
                continue
            list = []
            for c in fl.find_by_kind(obnam.cmp.FILE):
                filename = c.first_string_by_kind(obnam.cmp.FILENAME)
                if pretty:
                    list.append((obnam.format.inode_fields(c), filename))
                else:
                    print " ".join(obnam.format.inode_fields(c)), filename
    
            if pretty:
                widths = []
                for fields, _ in list:
                    for i in range(len(fields)):
                        if i >= len(widths):
                            widths.append(0)
                        widths[i] = max(widths[i], len(fields[i]))
        
                for fields, filename in list:
                    cols = []
                    for i in range(len(widths)):
                        if i < len(fields):
                            x = fields[i]
                        else:
                            x = ""
                        cols.append("%*s" % (widths[i], x))
                    print "  ", " ".join(cols), filename
