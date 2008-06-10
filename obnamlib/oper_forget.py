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


"""Operation to forget generations from backup store."""


import logging

import obnamlib


class Forget(obnamlib.Operation):

    """Forget specified generations."""
    
    name = "forget"

    def do_it(self, forgettable_ids):
        logging.debug("Forgetting generations: %s" % " ".join(forgettable_ids))
    
        logging.debug("forget: Loading and decoding host block")
        app = self.get_application()
        context = app.get_context()
        host = app.load_host()
        gen_ids = host.get_generation_ids()
        map_block_ids = host.get_map_block_ids()    
        contmap_block_ids = host.get_contmap_block_ids()    
    
        app.get_store().load_maps()
        app.get_store().load_content_maps()
    
        logging.debug("forget: Forgetting each id")
        for id in forgettable_ids:
            if id in gen_ids:
                gen_ids.remove(id)
            else:
                print "Warning: Generation", id, "is not known"
    
        logging.debug("forget: Uploading new host block")
        host_id = context.config.get("backup", "host-id")
        host2 = obnamlib.obj.HostBlockObject(host_id=host_id, gen_ids=gen_ids, 
                                          map_block_ids=map_block_ids,
                                          contmap_block_ids=contmap_block_ids)
        block = host2.encode()
        obnamlib.io.upload_host_block(context, block)
    
        logging.debug("forget: Forgetting garbage")
        obnamlib.io.collect_garbage(context, block)
