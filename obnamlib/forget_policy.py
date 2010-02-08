# Copyright (C) 2010  Lars Wirzenius
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
        
        m = self.rule_pat.match(optarg)
        if not m:
            raise obnamlib.Error('Forget policy syntax error: %s' % optarg)
        count = int(m.group('count'))
        period = self.periods[m.group('period')]
        
        result = dict((y, 0) for x, y in self.periods.iteritems())
        result[period] = count
        return result
