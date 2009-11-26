# Copyright (C) 2009  Lars Wirzenius
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import obnamlib


class ObnamPlugin(obnamlib.pluginmgr.Plugin):

    '''Base class for plugins in Obnam.'''

    def __init__(self, app):
        self.app = app
        self.callback_ids = []

    def add_callback(self, name, callback):
        cb_id = self.app.hooks.add_callback(name, callback)
        self.callback_ids.append((name, cb_id))
        
    def disable_wrapper(self):
        for name, cb_id in self.callback_ids:
            self.app.hooks.remove_callback(name, cb_id)
        self.callback_ids = []
        self.disable()
        
    def enable(self):
        pass
        
    def disable(self):
        pass

