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


class ShowPlugin(obnamlib.ObnamPlugin):

    '''Show information about data in the backup store.
    
    This implements commands for listing contents of root and host
    objects, or the contents of a backup generation.
    
    '''

    def enable(self):
        self.app.register_command('hosts', self.hosts)
        self.app.register_command('generations', self.generations)
        self.app.register_command('ls', self.ls)

    def open_store(self):
        fsf = obnamlib.VfsFactory()
        self.store = obnamlib.Store(fsf.new(self.app.config['store']))

    def hosts(self, args):
        self.open_store()
        rootobj = self.store.get_object(0)
        for hostid in rootobj.hostids:
            hostobj = self.store.get_object(hostid)
            print hostobj.hostname
    
    def generations(self, args):
        pass
    def ls(self, args):
        pass
