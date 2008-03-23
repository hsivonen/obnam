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

import obnam


class UnknownGeneration(obnam.ObnamException):

    def __init__(self, gen_id):
        self._msg = "Can't find generation %s" % gen_id


class Restore(obnam.Operation):

    """Restore specified files (or all) from a specified generation."""
    
    name = "restore"

    def hardlink_key(self, st):
        """Compute key into hardlink lookup table from stat result"""
        return "%d/%d" % (st.st_ino, st.st_dev)

    def create_filesystem_object(self, hardlinks, full_pathname, inode):
        context = self.get_application().get_context()
        logging.debug("Creating filesystem object %s" % full_pathname)
        stat_component = inode.first_by_kind(obnam.cmp.STAT)
        st = obnam.cmp.parse_stat_component(stat_component)
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
            cont_id = inode.first_string_by_kind(obnam.cmp.CONTREF)
            if cont_id:
                obnam.io.copy_file_contents(context, fd, cont_id)
            else:
                delta_id = inode.first_string_by_kind(obnam.cmp.DELTAREF)
                obnam.io.reconstruct_file_contents(context, fd, delta_id)
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

    def do_it(self, args):
        gen_id = args[0]
        files = args[1:]
        logging.debug("Restoring generation %s" % gen_id)
        logging.debug("Restoring files: %s" % ", ".join(files))
    
        app = self.get_application()
        context = app.get_context()
        host = app.load_host()
    
        app.load_maps()
        app.load_content_maps()
    
        logging.debug("Getting generation object")    
        gen = obnam.io.get_object(context, gen_id)
        if gen is None:
            raise UnknownGeneration(gen_id)
        
        target = context.config.get("backup", "target-dir")
        logging.debug("Restoring files under %s" % target)
    
        logging.debug("Getting list of files in generation")
        fl_id = gen.get_filelistref()
        fl = obnam.io.get_object(context, fl_id)
        if not fl:
            logging.warning("Cannot find file list object %s" % fl_id)
            return
    
        logging.debug("Restoring files")
        list = []
        hardlinks = {}
        for c in fl.find_by_kind(obnam.cmp.FILE):
            pathname = c.first_string_by_kind(obnam.cmp.FILENAME)
    
            if not self.restore_requested(files, pathname):
                logging.debug("Restore of %s not requested" % pathname)
                continue
    
            logging.debug("Restoring %s" % pathname)
    
            if pathname.startswith(os.sep):
                pathname = "." + pathname
            full_pathname = os.path.join(target, pathname)
    
            self.create_filesystem_object(hardlinks, full_pathname, c)
            list.append((full_pathname, c))
    
        logging.debug("Fixing permissions")
        list.sort()
        for full_pathname, inode in list:
            obnam.io.set_inode(full_pathname, inode)
