# Copyright (C) 2008  Lars Wirzenius <liw@iki.fi>
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


"""Operation to restore from backup."""


import logging
import os
import stat

import obnamlib


class UnknownGeneration(obnamlib.ObnamException):

    def __init__(self, gen_id):
        self._msg = "Can't find generation %s" % gen_id


class Restore(obnamlib.Operation):

    """Restore specified files (or all) from a specified generation."""
    
    name = "restore"

    def hardlink_key(self, st):
        """Compute key into hardlink lookup table from stat result"""
        return "%d/%d" % (st.st_ino, st.st_dev)

    def create_filesystem_object(self, hardlinks, full_pathname, inode):
        context = self.get_application().get_context()
        logging.debug("Creating filesystem object %s" % full_pathname)
        stat_component = inode.first_by_kind(obnamlib.cmp.STAT)
        st = obnamlib.cmp.parse_stat_component(stat_component)
        mode = st.st_mode
    
        if st.st_nlink > 1 and not stat.S_ISDIR(mode):
            key = self.hardlink_key(st)
            if key in hardlinks:
                existing_link = hardlinks[key]
                os.link(existing_link, full_pathname)
                return
            else:
                hardlinks[key] = full_pathname
    
        if stat.S_ISDIR(mode):
            if not os.path.exists(full_pathname):
                os.makedirs(full_pathname, 0700)
        elif stat.S_ISREG(mode):
            basedir = os.path.dirname(full_pathname)
            if not os.path.exists(basedir):
                os.makedirs(basedir, 0700)
            fd = os.open(full_pathname, os.O_WRONLY | os.O_CREAT, 0)
            cont_id = inode.first_string_by_kind(obnamlib.cmp.CONTREF)
            if cont_id:
                obnamlib.io.copy_file_contents(context, fd, cont_id)
            else:
                delta_id = inode.first_string_by_kind(obnamlib.cmp.DELTAREF)
                obnamlib.io.reconstruct_file_contents(context, fd, delta_id)
            os.close(fd)

    def restore_requested(self, files, pathname):
        """Return True, if pathname should be restored"""
        
        # If there is no explicit file list, restore everything.
        if not files:
            return True
            
        # If the pathname is specified explicitly, restore it.
        if pathname in files:
            return True
            
        # Otherwise, if there's an explicitly specified filename that is a
        # prefix of directory parts in the pathname, restore it. That is,
        # if files is ["foo/bar"], then restore "foo/bar/baz", but not
        # "foo/barbell".
        for x in files:
            if pathname.startswith(x) and x.endswith(os.sep):
                return True
            if pathname.startswith(x + os.sep):
                return True
                
        # Nope, don't restore it.
        return False

    def restore_single_item(self, hardlinks, target, pathname, inode):
        logging.debug("Restoring %s" % pathname)

        if pathname.startswith(os.sep):
            pathname = "." + pathname
        full_pathname = os.path.join(target, pathname)

        self.create_filesystem_object(hardlinks, full_pathname, inode)
        return full_pathname

    def fix_permissions(self, list):
        logging.debug("Fixing permissions")
        list.sort()
        for full_pathname, inode in list:
            obnamlib.io.set_inode(full_pathname, inode)

    def restore_from_filelist(self, target, fl, files):
        logging.debug("Restoring files from FILELIST")
        list = []
        hardlinks = {}

        for c in fl.find_by_kind(obnamlib.cmp.FILE):
            pathname = c.first_string_by_kind(obnamlib.cmp.FILENAME)
    
            if not self.restore_requested(files, pathname):
                logging.debug("Restore of %s not requested" % pathname)
                continue
    
            full_pathname = self.restore_single_item(hardlinks, target, 
                                                     pathname, c)
            list.append((full_pathname, c))

        self.fix_permissions(list)

    def restore_from_filegroups(self, target, hardlinks, list, parent, 
                                filegrouprefs, files):
        for ref in filegrouprefs:
            fg = obnamlib.io.get_object(self.app.get_context(), ref)
            if not fg:
                logging.warning("Cannot find FILEGROUP object %s" % ref)
            else:
                for name in fg.get_names():
                    if parent:
                        name2 = os.path.join(parent, name)
                    if self.restore_requested(files, name2):
                        file = fg.get_file(name)
                        full_pathname = self.restore_single_item(hardlinks,
                                            target, name2, file)
                        list.append((full_pathname, file))
                    else:
                        logging.debug("Restore of %s not requested" % name2)

    def restore_from_dirs(self, target, hardlinks, list, parent, dirrefs, 
                          files):
        for ref in dirrefs:
            dir = obnamlib.io.get_object(self.app.get_context(), ref)
            if not dir:
                logging.warning("Cannot find DIR object %s" % ref)
            else:
                name = dir.get_name()
                if parent:
                    name = os.path.join(parent, name)
                if self.restore_requested(files, name):
                    st = dir.first_by_kind(obnamlib.cmp.STAT)
                    st = obnamlib.cmp.parse_stat_component(st)
                    file = \
                        obnamlib.filelist.create_file_component_from_stat(
                            dir.get_name(), st, None, None, None)
                    full_pathname = self.restore_single_item(hardlinks,
                                                             target, name,
                                                             file)
                    list.append((full_pathname, file))
                    self.restore_from_filegroups(target, hardlinks, list, 
                                                 name,
                                                 dir.get_filegrouprefs(),
                                                 files)
                    self.restore_from_dirs(target, hardlinks, list, name,
                                           dir.get_dirrefs(), files)
                else:
                    logging.debug("Restore of %s not requested" % name)

    def restore_from_dirs_and_filegroups(self, target, gen, files):
        hardlinks = {}
        list = []
        self.restore_from_filegroups(target, hardlinks, list, None, 
                                     gen.get_filegrouprefs(), files)
        self.restore_from_dirs(target, hardlinks, list, 
                               None, gen.get_dirrefs(), files)
        self.fix_permissions(list)

    def do_it(self, args):
        gen_id = args[0]
        files = args[1:]
        logging.debug("Restoring generation %s" % gen_id)
        logging.debug("Restoring files: %s" % ", ".join(files))
    
        self.app = app = self.get_application()
        context = app.get_context()
        host = app.load_host()
    
        app.get_store().load_maps()
        app.get_store().load_content_maps()
    
        logging.debug("Getting generation object")    
        gen = obnamlib.io.get_object(context, gen_id)
        if gen is None:
            raise UnknownGeneration(gen_id)
        
        target = context.config.get("backup", "target-dir")
        logging.debug("Restoring files under %s" % target)
    
        fl_id = gen.get_filelistref()
        if fl_id:
            logging.debug("Getting list of files in generation")
            fl = obnamlib.io.get_object(context, fl_id)
            if not fl:
                logging.warning("Cannot find file list object %s" % fl_id)
            else:
                self.restore_from_filelist(target, fl, files)
        else:
            self.restore_from_dirs_and_filegroups(target, gen, files)
