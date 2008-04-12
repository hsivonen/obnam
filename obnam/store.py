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


"""Abstraction for storing backup data, for Obnam."""


import obnam


class Store:

    def __init__(self, context):
        self._context = context
        self._host = None

    def get_host_block(self):
        """Return current host block, or None if one is not known.
        
        You must call fetch_host_block to fetch the host block first.
        
        """

        return self._host

    def fetch_host_block(self):
        """Fetch host block from store, if one exists.
        
        If a host block does not exist, it is not an error. A new
        host block is then created.
        
        """
        
        host_id = self._context.config.get("backup", "host-id")
        self._host = obnam.obj.HostBlockObject(host_id=host_id)

    def commit_host_block(self):
        """Commit the current host block to the store.
        
        If no host block exists, create one. If one already exists,
        update it with new info.
        
        """
        
        pass
