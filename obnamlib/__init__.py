
# Copyright (C) 2008  Lars Wirzenius <liw@liw.fi>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
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


VERSION = "x.y"


import _obnam

from exception import BackupException as Exception

from cfg import Config

from kinds import Kinds
from component import Component, StringComponent, CompositeComponent
from component_kinds import ComponentKinds
cmp_kinds = ComponentKinds()
cmp_kinds.add_all()
cmp_kinds.add_to_obnamlib()
from component_file import File
from component_stat import Stat
from component_strings import (Adler32,
                               BlockId, 
                               BlockRef,
                               ContMapRef,
                               ContRef,
                               DeltaData,
                               DeltaPartRef,
                               DeltaRef,
                               DirRef,
                               FileChunk, 
                               FileGroupRef,
                               FileListRef,
                               FileName,
                               FilePartRef,
                               FormatVersion,
                               GenEnd, 
                               GenRef,
                               GenStart,
                               Group,
                               Length,
                               MapRef,
                               Md5,
                               ObjectId, 
                               ObjRef,
                               Offset,
                               Owner,
                               RsyncSigPartRef,
                               SigData,
                               SigRef,
                               SnapshotGen,
                               SymlinkTarget)
from component_composites import (Checksums, 
                                  ObjectComponent, 
                                  ObjMap)
from component_objkind import ObjectKind
from component_oldfilesubstring import OldFileSubString
from component_sigblocksize import SigBlockSize
from component_factory import ComponentFactory

from object import Object
from object_kinds import ObjectKinds
obj_kinds = ObjectKinds()
obj_kinds.add_all()
obj_kinds.add_to_obnamlib()
from object_dir import Dir
from object_filecontents import FileContents
from object_filegroup import FileGroup
from object_filelist import FileList
from object_filepart import FilePart
from object_gen import Generation
from object_host import Host
from object_rsyncsigpart import RsyncSigPart
from object_factory import ObjectFactory

from object_cache import ObjectCache

from block_factory import BlockFactory
from block_id_generator import BlockIdGenerator
from block_transformation import block_transformations, choose_transformations

from mapping import Mapping

from store import Store, NotFound

from lookupper import Lookupper

from store_walker import StoreWalker

from ui import UserInterface

from vfs import VirtualFileSystem, VfsFactory
from vfs_local import LocalFS
from vfs_sftp import SftpFS

from app import BackupApplication

from ui_cli import CommandLineUI, CommandLineCommand
from ui_cli_backup import BackupCommand
from ui_cli_restore import RestoreCommand
from ui_cli_cat import CatCommand
from ui_cli_fsck import FsckCommand
from ui_cli_generations import GenerationsCommand
from ui_cli_help import HelpCommand
from ui_cli_objtree import ObjtreeCommand
from ui_cli_show import ShowGenerationsCommand
from ui_cli_showobjs import ShowobjsCommand
from ui_cli_signature import SignatureCommand
from ui_cli_delta import DeltaCommand
from ui_cli_patch import PatchCommand
from ui_cli_diskusage import DiskUsageCommand

from progress import ProgressReporter

from statutils import decode_stat, make_stat
from formatutils import format_size, format_time

import varint

from obsync import Obsync

