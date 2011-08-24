#!/usr/bin/python
# Copyright (C) 2008-2011  Lars Wirzenius <liw@liw.fi>
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
from distutils.cmd import Command
from distutils.command.build import build
from distutils.command.clean import clean
import glob
import os
import subprocess

class GenerateManpage(build):

    def run(self):
        build.run(self)
        print 'building manpages'
        for x in ['obnam', 'obnam-benchmark']:
            with open('%s.1' % x, 'w') as f:
                subprocess.check_call(['python', x,
                                       '--generate-manpage=%s.1.in' % x,
                                       '--output=%s.1' % x], stdout=f)


class CleanMore(clean):

    def run(self):
        clean.run(self)
        for x in ['blackboxtest.log', 'blackboxtest-obnam.log',
                  'obnam.1', 'obnam-benchmark.1',
                  'obnamlib/_obnam.so']:
            if os.path.exists(x):
                os.remove(x)
        self.remove_pyc('obnamlib')
        self.remove_pyc('test-plugins')
        
    def remove_pyc(self, rootdir):
        for dirname, subdirs, basenames in os.walk(rootdir):
            for x in [os.path.join(dirname, base)
                       for base in basenames
                       if base.endswith('.pyc')]:
                os.remove(x)

class Check(Command):

    user_options = [
        ('fast', 'f', 'run fast tests only?'),
        ('network', 'n', 'run network tests to localhost?'),
    ]

    def initialize_options(self):
        self.fast = False
        self.network = False

    def finalize_options(self):
        pass

    def run(self):
        subprocess.check_call(['python', '-m', 'CoverageTestRunner',
                               '--ignore-missing-from=without-tests'])
        os.remove('.coverage')
        if self.fast:
            return

        subprocess.check_call(['python', 'blackboxtest'])

        if self.network:
            subprocess.check_call(['./test-sftpfs'])

            env = dict(os.environ)
            env['OBNAM_TEST_SFTP_ROOT'] = 'yes'
            env['OBNAM_TEST_SFTP_REPOSITORY'] = 'yes'
            subprocess.check_call(['./blackboxtest'], env=env)


setup(name='obnam',
      version='0.21',
      description='Backup software',
      author='Lars Wirzenius',
      author_email='liw@liw.fi',
      url='http://braawi.org/obnam/',
      scripts=['obnam', 'obnam-benchmark'],
      packages=['obnamlib', 'obnamlib.plugins'],
      ext_modules=[Extension('obnamlib._obnam', sources=['_obnammodule.c'])],
      data_files=[('share/man/man1', glob.glob('*.1'))],
      cmdclass={
        'build': GenerateManpage,
        'check': Check,
        'clean': CleanMore,
      },
     )
