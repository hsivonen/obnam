# Copyright (C) 2009  Lars Wirzenius
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


class Hook(object):

    '''A hook.'''

    def __init__(self):
        self.callbacks = []
        
    def add_callback(self, callback):
        '''Add a callback to this hook.
        
        Return an identifier that can be used to remove this callback.

        '''

        if callback not in self.callbacks:
            self.callbacks.append(callback)
        return callback
        
    def call_callbacks(self, *args, **kwargs):
        '''Call all callbacks with the given arguments.'''
        for callback in self.callbacks:
            callback(*args, **kwargs)
        
    def remove_callback(self, callback_id):
        '''Remove a specific callback.'''
        if callback_id in self.callbacks:
            self.callbacks.remove(callback_id)


class FilterHook(Hook):

    '''A hook which filters data through callbacks.
    
    Every hook of this type accepts exactly one argument.
    Each callback gets the return value of the previous one as its
    argument. The caller gets the value of the final callback.
    
    '''
    
    def call_callbacks(self, data):
        for callback in self.callbacks:
            data = callback(data)
        return data


class HookManager(object):

    '''Manage the set of hooks the application defines.'''
    
    def __init__(self):
        self.hooks = {}
        
    def new(self, name):
        '''Create a new hook.
        
        If a hook with that name already exists, nothing happens.
        
        '''

        if name not in self.hooks:
            self.hooks[name] = Hook()

    def new_filter(self, name):
        '''Create a new filter hook.'''
        if name not in self.hooks:
            self.hooks[name] = FilterHook()

    def add_callback(self, name, callback):
        '''Add a callback to a named hook.'''
        return self.hooks[name].add_callback(callback)
        
    def remove_callback(self, name, callback_id):
        '''Remove a specific callback from a named hook.'''
        self.hooks[name].remove_callback(callback_id)
        
    def call(self, name, *args, **kwargs):
        '''Call callbacks for a named hook, using given arguments.'''
        return self.hooks[name].call_callbacks(*args, **kwargs)

