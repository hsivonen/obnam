#!/usr/bin/env python
# Copyright (C) 2008-2012  Lars Wirzenius <liw@liw.fi>
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
import shutil
import subprocess
import sys
import tempfile


# We need to know whether we can run yarn. We do this by checking
# the python-markdown version: if it's new enough, we assume yarn
# is available, and if it isn't, yarn won't be available since it
# won't work with old versions (e.g., the one in Debian squeeze.)

try:
    import markdown
except ImportError:
    got_yarn = False
else:
    if (hasattr(markdown, 'extensions') and
        hasattr(markdown.extensions, 'Extension')):
        got_yarn = True
    else:
        got_yarn = False


def runcmd(*args, **kwargs):
    try:
        subprocess.check_call(*args, **kwargs)
    except subprocess.CalledProcessError, e:
        sys.stderr.write('ERROR: %s\n' % str(e))
        sys.exit(1)


class Build(build):

    def run(self):
        build.run(self)

        print 'building manpages'
        for x in ['obnam']:
            with open('%s.1' % x, 'w') as f:
                runcmd(['python', x, '--generate-manpage=%s.1.in' % x,
                        '--output=%s.1' % x], stdout=f)


class BuildDocs(Command):

    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        print 'building manual'
        runcmd(['make', '-C', 'manual'])

        print 'building yarns'
        runcmd(['make', '-C', 'yarns'])


class CleanMore(clean):

    def run(self):
        clean.run(self)
        for x in ['obnam.1', 'obnam-benchmark.1', '.coverage',
                  'obnamlib/_obnam.so']:
            if os.path.exists(x):
                os.remove(x)
        self.remove_pyc('obnamlib')
        self.remove_pyc('test-plugins')
        if os.path.isdir('build'):
            shutil.rmtree('build')

    def remove_pyc(self, rootdir):
        for dirname, subdirs, basenames in os.walk(rootdir):
            for x in [os.path.join(dirname, base)
                       for base in basenames
                       if base.endswith('.pyc')]:
                os.remove(x)

class Check(Command):

    user_options = [
        ('unit-tests', 'u', 'run unit tests?'),
        ('yarns', 'y', 'run yarn tests locally?'),
        ('lock-tests', 'l', 'run lock tests locally?'),
        ('network-lock-tests', 'L', 'run lock tests against localhost?'),
        ('crash-tests', 'c', 'run crash tests?'),
        ('sftp-tests', 's', 'run sftp tests against localhost?'),
    ]

    def set_all_options(self, new_value):
        self.unit_tests = new_value
        self.yarns = new_value
        self.lock_tests = new_value
        self.network_lock_tests = new_value
        self.crash_tests = new_value
        self.sftp_tests = new_value

    def initialize_options(self):
        self.set_all_options(False)

    def finalize_options(self):
        any_set = (
            self.unit_tests or
            self.yarns or
            self.lock_tests or
            self.network_lock_tests or
            self.crash_tests or
            self.sftp_tests)
        if not any_set:
            self.set_all_options(True)

    def run(self):
        if self.unit_tests:
            print "run unit tests"
            runcmd(['python', '-m', 'CoverageTestRunner',
                    '--ignore-missing-from=without-tests'])
            os.remove('.coverage')

        if self.yarns and got_yarn:
            runcmd(
                ['yarn', '-s', 'yarns/obnam.sh'] +
                glob.glob('yarns/*.yarn'))

        num_clients = '2'
        num_generations = '16'

        if self.lock_tests:
            print "run local locking tests"
            test_repo = tempfile.mkdtemp()
            runcmd(['./test-locking', num_clients,
                    num_generations, test_repo, test_repo])
            shutil.rmtree(test_repo)

        if self.crash_tests:
            print "run crash test"
            runcmd(['./crash-test', '200'])

        if self.sftp_tests:
            print "run sftp tests"
            runcmd(['./test-sftpfs'])

        if self.network_lock_tests:
            print "re-run locking tests using localhost networking"
            test_repo = tempfile.mkdtemp()
            repo_url = 'sftp://localhost/%s' % test_repo
            runcmd(['./test-locking', num_clients,
                    num_generations, repo_url, test_repo])
            shutil.rmtree(test_repo)

        print "setup.py check done"


setup(name='obnam',
      version='1.7.4',
      description='Backup software',
      author='Lars Wirzenius',
      author_email='liw@liw.fi',
      url='http://liw.fi/obnam/',
      scripts=['obnam', 'obnam-viewprof'],
      packages=['obnamlib', 'obnamlib.plugins', 'obnamlib.fmt_6'],
      ext_modules=[Extension('obnamlib._obnam', sources=['_obnammodule.c'])],
      data_files=[('share/man/man1', glob.glob('*.1'))],
      cmdclass={
        'build': Build,
        'docs': BuildDocs,
        'check': Check,
        'clean': CleanMore,
      },
     )
