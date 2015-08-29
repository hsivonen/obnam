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
import re

import obnamlib


class ExcludePathnamesPlugin(obnamlib.ObnamPlugin):

    def enable(self):
        backup_group = obnamlib.option_group['backup'] = 'Backing up'

        self.app.settings.string_list(
            ['exclude'],
            'regular expression for pathnames to '
            'exclude from backup (can be used multiple '
            'times)',
            group=backup_group)

        self.app.settings.string_list(
            ['exclude-from'],
            'read exclude patterns from FILE',
            metavar='FILE',
            group=backup_group)

        self.app.settings.string_list(
            ['include'],
            'regular expression for pathnames to include from backup '
            'even if it matches an exclude rule '
            '(can be used multiple times)',
            group=backup_group)

        self.app.hooks.add_callback('config-loaded', self.config_loaded)

    def config_loaded(self):
        self.app.hooks.add_callback('backup-exclude', self.exclude)
        self.pathname_excluder = obnamlib.PathnameExcluder()
        self.patterns_have_been_compiled = False

    def exclude(self, pathname=None, stat_result=None, exclude=None,
                progress=None, **kwargs):

        if not self.patterns_have_been_compiled:
            self.compile_exclusion_patterns(progress)
            self.compile_inclusion_patterns(progress)
            self.patterns_have_been_compiled = True

        is_excluded, regexp = self.pathname_excluder.exclude(pathname)
        if is_excluded:
            logging.debug('Exclude (pattern): %s', pathname)
            exclude[0] = True
        elif regexp is not None:
            logging.debug('Include due to regexp: %s', pathname)

    def compile_exclusion_patterns(self, progress):
        regexps = self.read_patterns_from_files(
            self.app.settings['exclude-from'])

        regexps.extend(self.app.settings['exclude'])

        # Ignore log file, except don't exclude the words cliapp uses
        # for not logging or for logging to syslog.
        log = self.app.settings['log']
        if log and log not in ('none', 'syslog'):
            regexps.append(log)

        logging.debug('Compiling exclusion patterns')
        self.compile_regexps(
            regexps, self.pathname_excluder.exclude_regexp, progress)

    def compile_inclusion_patterns(self, progress):
        logging.debug('Compiling inclusion patterns')
        self.compile_regexps(
            self.app.settings['include'],
            self.pathname_excluder.allow_regexp,
            progress)

    def compile_regexps(self, regexps, compiler, progress):
        for regexp in regexps:
            if not regexp:
                logging.debug('Ignoring empty pattern')
                continue
            logging.debug('Regular expression: %s', regexp)
            try:
                compiler(regexp)
            except re.error as e:
                msg = ('error compiling regular expression "%s": %s' %
                       (regexp, e))
                logging.error(msg)
                progress.error(msg)

    def read_patterns_from_files(self, filenames):
        patterns = []
        for filename in filenames:
            with open(filename) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        patterns.append(line)
        return patterns
