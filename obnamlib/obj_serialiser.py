# Copyright 2015  Lars Wirzenius
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
#
# =*= License: GPL-3+ =*=


import struct


# Constants for encoding the type of a value.

_NONE = 'n'
_INT = 'i'
_BOOL = 'b'
_STR = 's'
_LIST = 'L'
_DICT = 'D'


# The struct.pack format for encoding a length, and the size of the
# encoded length.

_length_fmt = '!Q'
_length_size = struct.calcsize(_length_fmt)


def serialise_object(obj):
    func = _serialisers[type(obj)]
    return func(obj)


def deserialise_object(serialised):
    type_byte = serialised[0]
    # We skip decoding of the value length, since we can assume all of
    # the rest of the value is to be decoded.
    value = serialised[1 + _length_size:]

    func = _deserialisers[serialised[0]]
    return func(value)


# The length of a value.

_length_fmt = '!Q'
_length_size = struct.calcsize(_length_fmt)

def _serialise_length(num_bytes):
    return struct.pack(_length_fmt, num_bytes)

def _deserialise_length(serialised):
    return struct.unpack(_length_fmt, serialised)[0]


# None.

_none_size_encoded = _serialise_length(0)

def _serialise_none(obj):
    return _NONE + _none_size_encoded

def _deserialise_none(serialised):
    return None


# Integers. They are arbitrarily large and signed.

def _serialise_integer(obj):
    s = str(obj)
    return _INT + _serialise_length(len(s)) + s

def _deserialise_integer(serialised):
    return int(serialised)


# Booleans.

_bool_fmt = '!c'
_bool_size_serialised = _serialise_length(struct.calcsize(_bool_fmt))

def _serialise_bool(obj):
    return (_BOOL + _bool_size_serialised +
            struct.pack(_bool_fmt, chr(int(obj))))

def _deserialise_bool(obj):
    return bool(ord(struct.unpack(_bool_fmt, obj)[0]))


# Strings (byte strings).

def _serialise_str(obj):
    return _STR + _serialise_length(len(obj)) + obj

def _deserialise_str(obj):
    return obj


# Lists.

def _serialise_list(obj):
    items = ''.join(serialise_object(item) for item in obj)
    return _LIST + _serialise_length(len(items)) + items

def _deserialise_list(serialised):
    items = []
    pos = 0
    while pos < len(serialised):
        length = _extract_length(serialised, pos)
        end = _next_object(pos, length)
        items.append(deserialise_object(serialised[pos:end]))
        pos = end
    return items

def _extract_length(serialised, pos):
    start = pos + 1
    end = start + _length_size
    return _deserialise_length(serialised[start:end])

def _next_object(pos, length):
    return pos + 1 + _length_size + length


# Dicts.

def _serialise_dict(obj):
    pairs = ''.join(
        _serialise_str(key) + serialise_object(value)
        for key, value in obj.iteritems())
    return _DICT + _serialise_length(len(pairs)) + pairs

def _deserialise_dict(serialised):
    result = {}
    pos = 0
    while pos < len(serialised):
        key, pos = _deserialise_prefix(serialised, pos)
        value, pos = _deserialise_prefix(serialised, pos)
        result[key] = value
    return result

def _deserialise_prefix(serialised, pos):
    length = _extract_length(serialised, pos)
    end = _next_object(pos, length)
    return deserialise_object(serialised[pos:end]), end


# A lookup table for serialisation functions for each type.

_serialisers = {
    type(None): _serialise_none,
    int: _serialise_integer,
    long: _serialise_integer,
    bool: _serialise_bool,
    str: _serialise_str,
    list: _serialise_list,
    dict: _serialise_dict,
}


# A lookup table for de-serialisation functions for each type.

_deserialisers = {
    _NONE: _deserialise_none,
    _INT: _deserialise_integer,
    _BOOL: _deserialise_bool,
    _STR: _deserialise_str,
    _LIST: _deserialise_list,
    _DICT: _deserialise_dict,
}
