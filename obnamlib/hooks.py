# Copyright (C) 2009-2015  Lars Wirzenius
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


'''Hooks with callbacks.

In order to de-couple parts of the application, especially when plugins
are used, hooks can be used. A hook is a location in the application
code where plugins may want to do something. Each hook has a name and
a list of callbacks. The application defines the name and the location
where the hook will be invoked, and the plugins (or other parts of the
application) will register callbacks.

'''


import logging
import tracing

import obnamlib


class Hook(object):

    '''A hook.'''

    EARLY_PRIORITY = 250
    DEFAULT_PRIORITY = 500
    LATE_PRIORITY = 750

    def __init__(self):
        self.callbacks = []
        self.priorities = {}

    def add_callback(self, callback, priority=DEFAULT_PRIORITY):
        '''Add a callback to this hook.

        Return an identifier that can be used to remove this callback.

        '''

        if callback not in self.callbacks:
            self.priorities[callback] = priority
            self.callbacks.append(callback)
            self.callbacks.sort(
                lambda x, y: cmp(self.priorities[x], self.priorities[y]))

        return callback

    def call_callbacks(self, *args, **kwargs):
        '''Call all callbacks with the given arguments.'''
        for callback in self.callbacks:
            callback(*args, **kwargs)

    def remove_callback(self, callback_id):
        '''Remove a specific callback.'''
        if callback_id in self.callbacks:
            self.callbacks.remove(callback_id)
            del self.priorities[callback_id]


class MissingFilterError(obnamlib.ObnamError):

    msg = 'Unknown filter tag: {tagname}'


class NoFilterTagError(obnamlib.ObnamError):

    msg = 'No filter tag found'


class FilterHook(Hook):

    '''A hook which filters data through callbacks.

    Every hook of this type accepts a piece of data as its first argument
    Each callback gets the return value of the previous one as its
    argument. The caller gets the value of the final callback.

    Other arguments (with or without keywords) are passed as-is to
    each callback.

    '''

    def __init__(self):
        Hook.__init__(self)
        self.bytag = {}

    def add_callback(self, callback, priority=Hook.DEFAULT_PRIORITY):
        assert(hasattr(callback, "tag"))
        assert(hasattr(callback, "filter_read"))
        assert(hasattr(callback, "filter_write"))
        self.bytag[callback.tag] = callback
        return Hook.add_callback(self, callback, priority)

    def remove_callback(self, callback_id):
        Hook.remove_callback(self, callback_id)
        del self.bytag[callback_id.tag]

    def call_callbacks(self, data, *args, **kwargs):
        raise NotImplementedError()

    def run_filter_read(self, data, *args, **kwargs):

        def filter_next_tag(data):
            split = data.split('\0', 1)
            if len(split) == 1:
                raise NoFilterTagError()
            tag, remaining = split
            if tag == '':
                return False, remaining
            if tag not in self.bytag:
                raise MissingFilterError(tagname=repr(tag))
            callback = self.bytag[tag]
            return True, callback.filter_read(remaining, *args, **kwargs)

        more = True
        while more:
            more, data = filter_next_tag(data)
        return data

    def run_filter_write(self, data, *args, **kwargs):
        tracing.trace('called')
        data = "\0" + data
        for filt in self.callbacks:
            tracing.trace('calling %s' % filt)
            new_data = filt.filter_write(data, *args, **kwargs)
            assert new_data is not None, \
                filt.tag + ": Returned None from filter_write()"
            if data != new_data:
                tracing.trace('filt.tag=%s' % filt.tag)
                data = filt.tag + "\0" + new_data
        tracing.trace('done')
        return data


class HookManager(object):

    '''Manage the set of hooks the application defines.'''

    def __init__(self):
        self.hooks = {}
        self.filters = {}

    def new(self, name):
        '''Create a new hook.

        If a hook with that name already exists, nothing happens.

        '''

        if name not in self.hooks:
            self.hooks[name] = Hook()

    def new_filter(self, name):
        '''Create a new filter hook.'''
        if name not in self.filters:
            self.filters[name] = FilterHook()

    def add_callback(self, name, callback, priority=Hook.DEFAULT_PRIORITY):
        '''Add a callback to a named hook.'''
        if name in self.hooks:
            return self.hooks[name].add_callback(callback, priority)
        else:
            return self.filters[name].add_callback(callback, priority)

    def remove_callback(self, name, callback_id):
        '''Remove a specific callback from a named hook.'''
        if name in self.hooks:
            self.hooks[name].remove_callback(callback_id)
        else:
            self.filters[name].remove_callback(callback_id)

    def call(self, name, *args, **kwargs):
        '''Call callbacks for a named hook, using given arguments.'''
        self.hooks[name].call_callbacks(*args, **kwargs)

    def filter_read(self, name, *args, **kwargs):
        '''Run reader filter for named filter, using given arguments.'''
        return self.filters[name].run_filter_read(*args, **kwargs)

    def filter_write(self, name, *args, **kwargs):
        '''Run writer filter for named filter, using given arguments.'''
        return self.filters[name].run_filter_write(*args, **kwargs)
