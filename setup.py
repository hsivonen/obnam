#!/usr/bin/python
# Copyright (C) 2008  Lars Wirzenius <liw@liw.fi>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
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

from distutils.core import setup, Extension
import glob

setup(name='obnam',
      version='0.10',
      description='Backup software',
      author='Lars Wirzenius',
      author_email='liw@liw.fi',
      url='http://braawi.org/obnam/',
      scripts=['obnam'],
      packages=['obnamlib'],
      ext_modules=[Extension('_obnam', sources=['_obnammodule.c'])],
      data_files=[('share/man/man1', glob.glob('*.1'))],
     )
