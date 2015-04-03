# Copyright (C) 2015  Lars Wirzenius
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


import logging
import os
import stat

import obnamlib


class ExcludeCachesPlugin(obnamlib.ObnamPlugin):

    def enable(self):
        backup_group = obnamlib.option_group['backup'] = 'Backing up'

        self.app.settings.boolean(
            ['exclude-caches'],
            'exclude directories (and their subdirs) '
            'that contain a CACHEDIR.TAG file (see '
            'http://www.brynosaurus.com/cachedir/spec.html for what '
            'it needs to contain, and http://liw.fi/cachedir/ for a '
            'helper tool)',
            group=backup_group)

        self.app.hooks.add_callback('config-loaded', self.config_loaded)

    def config_loaded(self):
        if self.app.settings['exclude-caches']:
            self.app.hooks.add_callback('backup-exclude', self.exclude)

    def exclude(self, fs=None, pathname=None, stat_result=None, exclude=None,
                **kwargs):
        if stat.S_ISDIR(stat_result.st_mode):
            tag_filename = 'CACHEDIR.TAG'
            tag_contents = 'Signature: 8a477f597d28d172789f06886806bc55'
            tag_path = os.path.join(pathname, 'CACHEDIR.TAG')
            if fs.exists(tag_path):
                # Can't use with, because Paramiko's SFTPFile does not work.
                f = fs.open(tag_path, 'rb')
                data = f.read(len(tag_contents))
                f.close()
                if data == tag_contents:
                    logging.debug('Excluding (cache dir): %s' % pathname)
                    return False
