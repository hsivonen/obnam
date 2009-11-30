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


import _obnam
from pluginmgr import PluginManager

class AppException(Exception):
    pass

from hooks import Hook, HookManager
from cfg import Configuration
from interp import Interpreter
from pluginbase import ObnamPlugin
from vfs import VirtualFileSystem, VfsFactory
from vfs_local import LocalFS
from obj import BackupObject, TYPE_ID, TYPE_ID_LIST, TYPE_INT, TYPE_STR
from app import App
