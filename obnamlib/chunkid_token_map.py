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
        if token not in self._mapping:
            self._mapping[token] = []
        self._mapping[token].append(chunk_id)

    def __contains__(self, token):
        return token in self._mapping

    def get(self, token):
        return self._mapping.get(token, [])

    def clear(self):
        self._mapping.clear()

    def __iter__(self):
        for token in self._mapping:
            for chunk_id in self._mapping[token]:
                yield chunk_id, token
