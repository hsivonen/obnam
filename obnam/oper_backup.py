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


"""A backup operation for Obnam."""


import logging

import obnam


class Backup(obnam.Operation):

    """Backup files the user has specified."""
    
    name = "backup"
    
    def do_it(self, roots):
        logging.info("Starting backup")
        logging.info("Getting and decoding host block")
        app = self.get_application()
        host = app.load_host()
        app.get_store().load_maps()
        # We don't need to load in file data, therefore we don't load
        # the content map blocks.

        old_gen_ids = host.get_generation_ids()
        if old_gen_ids:
            prev_gen = app.get_store().get_object(old_gen_ids[-1])
            app.set_previous_generation(prev_gen)
                
        gen = app.backup(roots)
        
        app.get_store().commit_host_block([gen])
    
        logging.info("Backup done")
