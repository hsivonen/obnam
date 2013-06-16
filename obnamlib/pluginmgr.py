# Copyright (C) 2009  Lars Wirzenius <liw@liw.fi>
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


'''A generic plugin manager.

The plugin manager finds files with plugins and loads them. It looks
for plugins in a number of locations specified by the caller. To add
a plugin to be loaded, it is enough to put it in one of the locations,
and name it *_plugin.py. (The naming convention is to allow having
other modules as well, such as unit tests, in the same locations.)

'''


import imp
import inspect
import os


class Plugin(object):

    '''Base class for plugins.

    A plugin MUST NOT have any side effects when it is instantiated.
    This is necessary so that it can be safely loaded by unit tests,
    and so that a user interface can allow the user to disable it,
    even if it is installed, with no ill effects. Any side effects
    that would normally happen should occur in the enable() method,
    and be undone by the disable() method. These methods must be
    callable any number of times.

    The subclass MAY define the following attributes:

    * name
    * description
    * version
    * required_application_version

    name is the user-visible identifier for the plugin. It defaults
    to the plugin's classname.

    description is the user-visible description of the plugin. It may
    be arbitrarily long, and can use pango markup language. Defaults
    to the empty string.

    version is the plugin version. Defaults to '0.0.0'. It MUST be a
    sequence of integers separated by periods. If several plugins with
    the same name are found, the newest version is used. Versions are
    compared integer by integer, starting with the first one, and a
    missing integer treated as a zero. If two plugins have the same
    version, either might be used.

    required_application_version gives the version of the minimal
    application version the plugin is written for. The first integer
    must match exactly: if the application is version 2.3.4, the
    plugin's required_application_version must be at least 2 and
    at most 2.3.4 to be loaded. Defaults to 0.

    '''

    @property
    def name(self):
        return self.__class__.__name__

    @property
    def description(self):
        return ''

    @property
    def version(self):
        return '0.0.0'

    @property
    def required_application_version(self):
        return '0.0.0'

    def enable_wrapper(self):
        '''Enable plugin.

        The plugin manager will call this method, which then calls the
        enable method. Plugins should implement the enable method.
        The wrapper method is there to allow an application to provide
        an extended base class that does some application specific
        magic when plugins are enabled or disabled.

        '''

        self.enable()

    def disable_wrapper(self):
        '''Corresponds to enable_wrapper, but for disabling a plugin.'''
        self.disable()

    def enable(self):
        '''Enable the plugin.'''
        raise NotImplemented()

    def disable(self):
        '''Disable the plugin.'''
        raise NotImplemented()


class PluginManager(object):

    '''Manage plugins.

    This class finds and loads plugins, and keeps a list of them that
    can be accessed in various ways.

    The locations are set via the locations attribute, which is a list.

    When a plugin is loaded, an instance of its class is created. This
    instance is initialized using normal and keyword arguments specified
    in the plugin manager attributes plugin_arguments and
    plugin_keyword_arguments.

    The version of the application using the plugin manager is set via
    the application_version attribute. This defaults to '0.0.0'.

    '''

    suffix = '_plugin.py'

    def __init__(self):
        self.locations = []
        self._plugins = None
        self._plugin_files = None
        self.plugin_arguments = []
        self.plugin_keyword_arguments = {}
        self.application_version = '0.0.0'

    @property
    def plugin_files(self):
        if self._plugin_files is None:
            self._plugin_files = self.find_plugin_files()
        return self._plugin_files

    @property
    def plugins(self):
        if self._plugins is None:
            self._plugins = self.load_plugins()
        return self._plugins

    def __getitem__(self, name):
        for plugin in self.plugins:
            if plugin.name == name:
                return plugin
        raise KeyError('Plugin %s is not known' % name)

    def find_plugin_files(self):
        '''Find files that may contain plugins.

        This finds all files named *_plugin.py in all locations.
        The returned list is sorted.

        '''

        pathnames = []

        for location in self.locations:
            try:
                basenames = os.listdir(location)
            except os.error:
                continue
            for basename in basenames:
                s = os.path.join(location, basename)
                if s.endswith(self.suffix) and os.path.exists(s):
                    pathnames.append(s)

        return sorted(pathnames)

    def load_plugins(self):
        '''Load plugins from all plugin files.'''

        plugins = dict()

        for pathname in self.plugin_files:
            for plugin in self.load_plugin_file(pathname):
                if plugin.name in plugins:
                    p = plugins[plugin.name]
                    if self.is_older(p.version, plugin.version):
                        plugins[plugin.name] = plugin
                else:
                    plugins[plugin.name] = plugin

        return plugins.values()

    def is_older(self, version1, version2):
        '''Is version1 older than version2?'''
        return self.parse_version(version1) < self.parse_version(version2)

    def load_plugin_file(self, pathname):
        '''Return plugin classes in a plugin file.'''

        name, ext = os.path.splitext(os.path.basename(pathname))
        f = file(pathname, 'r')
        module = imp.load_module(name, f, pathname,
                                 ('.py', 'r', imp.PY_SOURCE))
        f.close()

        plugins = []
        for dummy, member in inspect.getmembers(module, inspect.isclass):
            if issubclass(member, Plugin):
                p = member(*self.plugin_arguments,
                           **self.plugin_keyword_arguments)
                if self.compatible_version(p.required_application_version):
                    plugins.append(p)

        return plugins

    def compatible_version(self, required_application_version):
        '''Check that the plugin is version-compatible with the application.

        This checks the plugin's required_application_version against
        the declared application version and returns True if they are
        compatible, and False if not.

        '''

        req = self.parse_version(required_application_version)
        app = self.parse_version(self.application_version)

        return app[0] == req[0] and app >= req

    def parse_version(self, version):
        '''Parse a string represenation of a version into list of ints.'''

        return [int(s) for s in version.split('.')]

    def enable_plugins(self, plugins=None):
        '''Enable all or selected plugins.'''

        for plugin in plugins or self.plugins:
            plugin.enable_wrapper()

    def disable_plugins(self, plugins=None):
        '''Disable all or selected plugins.'''

        for plugin in plugins or self.plugins:
            plugin.disable_wrapper()

