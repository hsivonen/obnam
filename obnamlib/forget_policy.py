# Copyright (C) 2010-2014  Lars Wirzenius
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


import re

import obnamlib


class ForgetPolicySyntaxError(obnamlib.ObnamError):

    msg = 'Forget policy syntax error: {policy}'


class DuplicatePeriodError(obnamlib.ObnamError):

    msg = 'Forget policy may not duplicate period ({period}): {policy}'


class SeparatorError(obnamlib.ObnamError):

    msg = ('Forget policy must have rules separated by commas, '
           'see position {position}: {policy}')


class ForgetPolicy(object):

    '''Parse and interpret a policy for what to forget and what to keep.

    See documentation for the --keep option for details.

    '''

    periods = {
        'h': 'hourly',
        'd': 'daily',
        'w': 'weekly',
        'm': 'monthly',
        'y': 'yearly',
    }

    rule_pat = re.compile(r'(?P<count>\d+)(?P<period>(h|d|w|m|y))')

    def parse(self, optarg):
        '''Parse the argument of --keep.

        Return a dictionary indexed by 'hourly', 'daily', 'weekly',
        'monthly', 'yearly', and giving the number of generations
        to keep for each time period.

        '''

        remaining = optarg
        m = self.rule_pat.match(remaining)
        if not m:
            raise ForgetPolicySyntaxError(policy=optarg)

        result = dict((y, None) for x, y in self.periods.iteritems())
        while m:
            count = int(m.group('count'))
            period = self.periods[m.group('period')]
            if result[period] is not None:
                raise DuplicatePeriodError(period=period, policy=optarg)
            result[period] = count
            remaining = remaining[m.end():]
            if not remaining:
                break
            if not remaining.startswith(','):
                position = len(optarg) - len(remaining) + 1
                raise SeparatorError(position=position, policy=optarg)
            remaining = remaining[1:]
            m = self.rule_pat.match(remaining)

        result.update((x, 0) for x, y in result.iteritems() if y is None)
        return result

    def last_in_each_period(self, period, genlist):
        formats = {
            'hourly': '%Y-%m-%d %H',
            'daily': '%Y-%m-%d',
            'weekly': '%Y-%W',
            'monthly': '%Y-%m',
            'yearly': '%Y',
        }

        matches = []
        for genid, dt in genlist:
            formatted = dt.strftime(formats[period])
            if not matches:
                matches.append((genid, formatted))
            elif matches[-1][1] == formatted:
                matches[-1] = (genid, formatted)
            else:
                matches.append((genid, formatted))
        return [genid for genid, formatted in matches]

    def match(self, rules, genlist):
        '''Match a parsed ruleset against a list of generations and times.

        The ruleset should be of the form returned by the parse method.

        genlist should be a list of generation identifiers and timestamps.
        Identifiers can be anything, timestamps should be an instance
        of datetime.datetime, with no time zone (it is ignored).

        genlist should be in ascending order by time: oldest one first.

        Return value is all those pairs from genlist that should be
        kept (i.e., which match the rules).

        '''

        result_ids = set()
        for period in rules:
            genids = self.last_in_each_period(period, genlist)
            if rules[period]:
                for genid in genids[-rules[period]:]:
                    result_ids.add(genid)

        return [(genid, dt) for genid, dt in genlist
                if genid in result_ids]
