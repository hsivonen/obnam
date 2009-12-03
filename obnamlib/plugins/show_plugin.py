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

    def open_root(self):
        return self.store.get_object(0)

    def open_host(self):
        hostname = self.app.config['hostname']
        rootobj = self.open_root()
        for hostid in rootobj.hostids:
            hostobj = self.store.get_object(hostid)
            if hostobj.hostname == hostname:
                return hostobj
        raise obnamlib.AppException('Host %s not found in store' % hostname)

    def hosts(self, args):
        self.open_store()
        rootobj = self.open_root()
        for hostid in rootobj.hostids:
            hostobj = self.store.get_object(hostid)
            print hostobj.hostname
    
    def generations(self, args):
        self.open_store()
        hostobj = self.open_host()
        for genid in hostobj.genids:
            print genid

    def ls(self, args):
        pass
