#!/usr/bin/python
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


class GenerateManpage(build):

    def run(self):
        build.run(self)
        print 'building manpages'
        for x in ['obnam', 'obnam-benchmark']:
            with open('%s.1' % x, 'w') as f:
                runcmd(['python', x, '--generate-manpage=%s.1.in' % x,
                        '--output=%s.1' % x], stdout=f)


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
        ('unit-only', 'u', 'run unit tests tests only?'),
        ('fast', 'f', 'run fast tests only?'),
        ('network', 'n', 'run network tests to localhost?'),
        ('network-only', 'N', 'only run network tests to localhost?'),
    ]

    def initialize_options(self):
        self.unit_only = False
        self.fast = False
        self.network = False
        self.network_only = False

    def finalize_options(self):
        pass

    def run(self):
        local = not self.network_only
        network = self.network or self.network_only
        fast = self.fast
        slow = not self.fast and not self.unit_only

        if local and (self.unit_only or fast):
            print "run unit tests"
            runcmd(['python', '-m', 'CoverageTestRunner',
                    '--ignore-missing-from=without-tests'])
            os.remove('.coverage')

        if local and fast:
            print "run black box tests"
            runcmd(['cmdtest', 'tests'])
            if got_yarn:
                runcmd(
                    ['yarn', '-s', 'yarns/obnam.sh'] +
                    glob.glob('yarns/*.yarn'))

        num_clients = '2'
        num_generations = '16'

        if local and slow:
            print "run locking tests"
            test_repo = tempfile.mkdtemp()
            runcmd(['./test-locking', num_clients,
                    num_generations, test_repo, test_repo])
            shutil.rmtree(test_repo)

        if local and slow:
            print "run crash test"
            runcmd(['./crash-test', '200'])

        if network and fast:
            print "run sftp tests"
            runcmd(['./test-sftpfs'])

        if network and fast:
            print "re-run black box tests using localhost networking"
            env = dict(os.environ)
            env['OBNAM_TEST_SFTP_ROOT'] = 'yes'
            env['OBNAM_TEST_SFTP_REPOSITORY'] = 'yes'
            runcmd(['cmdtest', 'tests'], env=env)

        if network and slow:
            print "re-run locking tests using localhost networking"
            test_repo = tempfile.mkdtemp()
            repo_url = 'sftp://localhost/%s' % test_repo
            runcmd(['./test-locking', num_clients,
                    num_generations, repo_url, test_repo])
            shutil.rmtree(test_repo)

        print "setup.py check done"


setup(name='obnam',
      version='1.4',
      description='Backup software',
      author='Lars Wirzenius',
      author_email='liw@liw.fi',
      url='http://liw.fi/obnam/',
      scripts=['obnam', 'obnam-benchmark', 'obnam-viewprof'],
      packages=['obnamlib', 'obnamlib.plugins'],
      ext_modules=[Extension('obnamlib._obnam', sources=['_obnammodule.c'])],
      data_files=[('share/man/man1', glob.glob('*.1'))],
      cmdclass={
        'build': GenerateManpage,
        'check': Check,
        'clean': CleanMore,
      },
     )
