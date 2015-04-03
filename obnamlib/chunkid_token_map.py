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


class ChunkIdTokenMap(object):

    '''Map chunk ids to repository tokens.

    This mapping is used to store the (chunk_id, token) pairs, until
    they can be added to the chunk indexes.

    '''

    def __init__(self):
        self._mapping = {}

    def add(self, chunk_id, token):
        self._mapping[chunk_id] = token

    def __contains__(self, chunk_id):
        return chunk_id in self._mapping

    def __iter__(self):
        for chunk_id in self._mapping:
            yield chunk_id, self._mapping[chunk_id]
