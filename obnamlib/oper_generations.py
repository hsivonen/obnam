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


"""Operation to list generations in a backup store."""


import logging

import obnamlib


class ListGenerations(obnamlib.Operation):

    """List generations in the store."""
    
    name = "generations"
    
    def do_it(self, *ignored):
        app = self.get_application()
        host = app.load_host()
        context = app.get_context()
        gentimes = context.config.getboolean("backup", "generation-times")
        if gentimes:
            app.get_store().load_maps()
    
        gen_ids = host.get_generation_ids()
        for id in gen_ids:
            if gentimes:
                gen = obnamlib.io.get_object(context, id)
                if not gen:
                    logging.warning("Can't find info about generation %s" % id)
                else:
                    start = gen.get_start_time()
                    end = gen.get_end_time()
                    print id, obnamlib.format.timestamp(start), "--", \
                        obnamlib.format.timestamp(end)
            else:
                print id
