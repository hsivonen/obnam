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


"""Main program for Obnam."""


import logging
import os
import re
import stat

import obnam



# Maximum number of files per file group we create.
MAX_PER_FILEGROUP = 16


class Application:

    """Main program logic for Obnam, a backup application."""

    def __init__(self, context):
        self._context = context
        self._exclusion_strings = []
        self._exclusion_regexps = []
        self._filelist = None
        self._host = None
        
        # When we traverse the file system tree while making a backup,
        # we process children before the parent. This is necessary for
        # functional updates of trees. For every directory, we need
        # to keep track of its children. This dict is used for that.
        # It is indexed by the absolute path to the directory, and
        # contains a list of the subdirectories in that directory.
        # When we're done with a directory (i.e., we generate its
        # DirObject), we remove the directory from this dict. This
        # means that we need only data for one path from the root of
        # the directory tree to the current directory, not for the
        # entire directory tree.
        self._subdirs = {}

    def get_context(self):
        """Get the context for the backup application."""
        return self._context

    def get_host(self):
        """Return currently active host object, or None if none is active."""
        return self._host

    def load_host(self):
        """Load the host block into memory."""
        if not self._host:
            host_block = obnam.io.get_host_block(self._context)
            if host_block:
                self._host = obnam.obj.create_host_from_block(host_block)
            else:
                id = self._context.config.get("backup", "host-id")
                self._host = obnam.obj.HostBlockObject(host_id=id)
        return self._host

    def load_maps(self):
        """Load non-content map blocks."""
        ids = self._host.get_map_block_ids()
        logging.info("Decoding %d mapping blocks" % len(ids))
        obnam.io.load_maps(self._context, self._context.map, ids)

    def load_content_maps(self):
        """Load content map blocks."""
        ids = self._host.get_contmap_block_ids()
        logging.info("Decoding %d content mapping blocks" % len(ids))
        obnam.io.load_maps(self._context, self._context.contmap, ids)

    def get_exclusion_regexps(self):
        """Return list of regexp to exclude things from backup."""
        
        config = self.get_context().config
        strings = config.get("backup", "exclude")
        if self._exclusion_strings != strings:
            for string in strings:
                logging.debug("Compiling exclusion pattern '%s'" % string)
                self._exclusion_regexps.append(re.compile(string))
        
        return self._exclusion_regexps

    def prune(self, dirname, dirnames, filenames):
        """Remove excluded items from dirnames and filenames.
        
        Because this is called by obnam.walk.depth_first, the lists
        are modified in place.
        
        """
        
        self._prune_one_list(dirname, dirnames)
        self._prune_one_list(dirname, filenames)

    def _prune_one_list(self, dirname, basenames):
        """Prune one list of basenames based on exlusion list.
        
        Because this is called from self.prune, the list is modified
        in place.
        
        """

        i = 0
        while i < len(basenames):
            path = os.path.join(dirname, basenames[i])
            for regexp in self.get_exclusion_regexps():
                if regexp.search(path):
                    del basenames[i]
                    break
            else:
                i += 1

    def set_prevgen_filelist(self, filelist):
        """Set the Filelist object from the previous generation.
        
        This is used when looking up files in previous generations. We
        only look at one generation's Filelist, since they're big. Note
        that Filelist objects are the _old_ way of storing file meta
        data, and we will no use better ways that let us look further
        back in history.
        
        """
        
        self._filelist = filelist

    def find_file_by_name(self, filename):
        """Find a backed up file given its filename.
        
        Return tuple (STAT, CONTREF, SIGREF, DELTAREF), where the
        references may be None, or None instead of the entire tuple
        if no file with the given name could be found.
        
        """
        
        if self._filelist:
            fc = self._filelist.find(filename)
            if fc != None:
                subs = fc.get_subcomponents()
                stat = obnam.cmp.first_by_kind(subs, obnam.cmp.STAT)
                cont = obnam.cmp.first_string_by_kind(subs, obnam.cmp.CONTREF)
                sig = obnam.cmp.first_string_by_kind(subs, obnam.cmp.SIGREF)
                d = obnam.cmp.first_string_by_kind(subs, obnam.cmp.DELTAREF)
                return obnam.cmp.parse_stat_component(stat), cont, sig, d
        
        return None

    def enqueue(self, objs):
        """Push objects to the object queue."""
        for obj in objs:
            obnam.io.enqueue_object(self._context, self._context.oq,
                                    self._context.map, obj.get_id(), 
                                    obj.encode(), True)

    def compute_signature(self, filename):
        """Compute rsync signature for a filename.
        
        Return the identifier. Put the signature object in the queue to
        be uploaded.
        
        """

        sigdata = obnam.rsync.compute_signature(self._context, filename)
        id = obnam.obj.object_id_new()
        sig = obnam.obj.SignatureObject(id=id, sigdata=sigdata)
        self.enqueue([sig])
        return sig

    def add_to_filegroup(self, fg, filename):
        """Add a file to a filegroup."""
        self._context.progress.update_current_action(filename)
        st = os.stat(filename)
        if stat.S_ISREG(st.st_mode):
            contref = obnam.io.create_file_contents_object(self._context, 
                                                           filename)
            sig = self.compute_signature(filename)
            sigref = sig.get_id()
            deltaref = None
        else:
            contref = None
            sigref = None
            deltaref = None
        fg.add_file(filename, st, contref, sigref, deltaref)

    def make_filegroups(self, filenames):
        """Make list of new FILEGROUP objects.
        
        Return list of object identifiers to the FILEGROUP objects.
        
        """

        list = []
        for filename in filenames:
            if (not list or
                len(list[-1].get_files()) >= MAX_PER_FILEGROUP):
                id = obnam.obj.object_id_new()
                list.append(obnam.obj.FileGroupObject(id=id))
            self.add_to_filegroup(list[-1], filename)
                
        self.enqueue(list)
        return list

    def _make_absolute(self, basename, relatives):
        return [os.path.join(basename, name) for name in relatives]

    def backup_one_dir(self, dirname, subdirs, filenames):
        """Back up non-recursively one directory.
        
        Return obnam.obj.DirObject that refers to the directory.
        
        subdirs is the list of subdirectories (as DirObject) for this
        directory.

        """

        filenames = self._make_absolute(dirname, filenames)
        filegroups = self.make_filegroups(filenames)
        filegrouprefs = [fg.get_id() for fg in filegroups]

        dirrefs = [subdir.get_id() for subdir in subdirs]

        dir = obnam.obj.DirObject(id=obnam.obj.object_id_new(),
                                  name=os.path.basename(dirname),
                                  stat=os.stat(dirname),
                                  dirrefs=dirrefs,
                                  filegrouprefs=filegrouprefs)


        self.enqueue([dir])
        return dir

    def backup_one_root(self, root):
        """Backup one root for the next generation."""
        
        if not os.path.isdir(root):
            raise obnam.ObnamException("Not a directory: %s" % root)
            # FIXME: This needs to be able to handle non-directories, too!
        
        subdirs_for_dir = {}
        root_object = None
        
        for tuple in obnam.walk.depth_first(root, prune=self.prune):
            dirname, dirnames, filenames = tuple

            subdirs = subdirs_for_dir.get(dirname, [])
            
            dir = self.backup_one_dir(dirname, subdirs, filenames)

            if dirname != root:
                parent = os.path.dirname(dirname)
                if parent not in subdirs_for_dir:
                    subdirs_for_dir[parent] = []
                subdirs_for_dir[parent].append(dir)
            else:
                root_object = dir

            if dirname in subdirs_for_dir:
                del subdirs_for_dir[dirname]

        return root_object

    def backup(self, roots):
        """Backup all the roots."""

        root_objs = []
        for root in roots:
            root_objs.append(self.backup_one_root(root))

        dirrefs = [o.get_id() for o in root_objs]
        gen = obnam.obj.GenerationObject(id=obnam.obj.object_id_new(),
                                         dirrefs=dirrefs)
        self.enqueue([gen])
        return gen
