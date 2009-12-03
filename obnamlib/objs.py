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


from obnamlib import (BackupObject, TYPE_ID, TYPE_ID_LIST, TYPE_INT, TYPE_STR,
                      MetadataObject)


class Chunk(BackupObject):

    '''Some file data.'''
    
    fields = (('data', TYPE_STR),)


class File(MetadataObject):

    '''A non-directory filesystem entry.'''

    fields = (('basename', TYPE_STR),
              ('chunkids', TYPE_ID_LIST))

