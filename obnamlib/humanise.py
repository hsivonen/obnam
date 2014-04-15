# Copyright 2014  Lars Wirzenius
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


def humanise_duration(seconds):
    duration_string = ''
    if seconds >= 3600:
        duration_string += '%dh' % int(seconds/3600)
        seconds %= 3600
    if seconds >= 60:
        duration_string += '%dm' % int(seconds/60)
        seconds %= 60
    if seconds > 0:
        duration_string += '%ds' % round(seconds)
    return duration_string


def humanise_size(size):
    size_table = [
        (1024**4, 'TiB'),
        (1024**3, 'GiB'),
        (1024**2, 'MiB'),
        (1024**1, 'KiB'),
        (0, 'B')
    ]

    for size_base, size_unit in size_table:
        if size >= size_base:
            if size_base > 0:
                size_amount = int(float(size) / float(size_base))
            else:
                size_amount = float(size)
            return size_amount, size_unit
    raise Exception("This can't happen: size=%r" % size)


def humanise_speed(size, duration):
    speed_table = [
        (1024**3, 'GiB/s'),
        (1024**2, 'MiB/s'),
        (1024**1, 'KiB/s'),
        (0, 'B/s')
    ]

    speed = float(size) / duration
    for speed_base, speed_unit in speed_table:
        if speed >= speed_base:
            if speed_base > 0:
                speed_amount = speed / speed_base
            else:
                speed_amount = speed
            return speed_amount, speed_unit
    raise Exception(
        "This can't happen: size=%r duration=%r" % (size, duration))
