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
import time

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
        self._store = obnam.Store(self._context)
        
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

    def get_store(self):
        """Get the Store for the backup application."""
        return self._store

    def load_host(self):
        """Load the host block into memory."""
        self.get_store().fetch_host_block()
        return self.get_store().get_host_block()

    def get_exclusion_regexps(self):
        """Return list of regexp to exclude things from backup."""
        
        config = self.get_context().config
        strings = config.getvalues("backup", "exclude")
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

        dirname = obnam.io.unsolve(self._context, dirname)

        i = 0
        while i < len(basenames):
            path = os.path.join(dirname, basenames[i])
            for regexp in self.get_exclusion_regexps():
                if regexp.search(path):
                    logging.debug("Excluding %s" % path)
                    logging.debug("  based on %s" % regexp.pattern)
                    del basenames[i]
                    break
            else:
                i += 1

    def file_is_unchanged(self, stat1, stat2):
        """Is a file unchanged from the previous generation?
        
        Given the stat results from the previous generation and the
        current file, return True if the file is identical from the
        previous generation (i.e., no new data to back up).
        
        """
        
        fields = ("mode", "dev", "nlink", "uid", "gid", "size", "mtime")
        for field in fields:
            field = "st_" + field
            if getattr(stat1, field) != getattr(stat2, field):
                return False
        return True

    def filegroup_is_unchanged(self, fg, filenames, stat=os.stat):
        """Is a filegroup unchanged from the previous generation?
        
        Given a filegroup and a list of files in the current directory,
        return True if all files in the filegroup are unchanged from
        the previous generation.
        
        The optional stat argument can be used by unit tests to
        override the use of os.stat.
        
        """
        
        for old_name in fg.get_names():
            if old_name not in filenames:
                return False    # file has been deleted

            old_stat = fg.get_stat(old_name)
            new_stat = stat(old_name)
            if not self.file_is_unchanged(old_stat, new_stat):
                return False    # file has changed

        return True             # everything seems to be as before

    def dir_is_unchanged(self, old, new):
        """Has a directory changed since the previous generation?
        
        Return True if a directory, or its files or subdirectories,
        has changed since the previous generation.
        
        """
        
        return (old.get_name() == new.get_name() and
                self.file_is_unchanged(old.get_stat(), new.get_stat()) and
                sorted(old.get_dirrefs()) == sorted(new.get_dirrefs()) and
                sorted(old.get_filegrouprefs()) == 
                    sorted(new.get_filegrouprefs()))

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
                stat = fc.first_by_kind(obnam.cmp.STAT)
                cont = fc.first_string_by_kind(obnam.cmp.CONTREF)
                sig = fc.first_string_by_kind(obnam.cmp.SIGREF)
                d = fc.first_string_by_kind(obnam.cmp.DELTAREF)
                return obnam.cmp.parse_stat_component(stat), cont, sig, d
        
        return None

    def compute_signature(self, filename):
        """Compute rsync signature for a filename.
        
        Return the identifier. Put the signature object in the queue to
        be uploaded.
        
        """

        sigdata = obnam.rsync.compute_signature(self._context, filename)
        id = obnam.obj.object_id_new()
        sig = obnam.obj.SignatureObject(id=id, sigdata=sigdata)
        self.get_store().queue_object(sig)
        return sig

    def find_unchanged_filegroups(self, filegroups, filenames, stat=os.stat):
        """Return list of filegroups that are unchanged.
        
        The filenames and stat arguments have the same meaning as 
        for the filegroup_is_unchanged method.
        
        """
        
        unchanged = []
        
        for filegroup in filegroups:
            if self.filegroup_is_unchanged(filegroup, filenames, stat=stat):
                unchanged.append(filegroup)
        
        return unchanged

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
        fg.add_file(os.path.basename(filename), st, contref, sigref, deltaref)

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
                
        self.get_store().queue_objects(list)
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


        self.get_store().queue_object(dir)
        return dir

    def backup_one_root(self, root):
        """Backup one root for the next generation."""

        logging.debug("Backing up root %s" % root)
        
        resolved = obnam.io.resolve(self._context, root)
        logging.debug("Root resolves to %s" % resolved)
        
        if not os.path.isdir(resolved):
            raise obnam.ObnamException("Not a directory: %s" % root)
            # FIXME: This needs to be able to handle non-directories, too!
        
        subdirs_for_dir = {}
        root_object = None
        
        for tuple in obnam.walk.depth_first(resolved, prune=self.prune):
            dirname, dirnames, filenames = tuple
            logging.debug("Walked to directory %s" % dirname)
            logging.debug("  with dirnames: %s" % dirnames)
            logging.debug("  and filenames: %s" % filenames)

            subdirs = subdirs_for_dir.get(dirname, [])
            
            dir = self.backup_one_dir(dirname, subdirs, filenames)

            if obnam.io.unsolve(self._context, dirname) != root:
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

        start = int(time.time())
        root_objs = []
        for root in roots:
            root_objs.append(self.backup_one_root(root))
        end = int(time.time())

        dirrefs = [o.get_id() for o in root_objs]
        gen = obnam.obj.GenerationObject(id=obnam.obj.object_id_new(),
                                         dirrefs=dirrefs, start=start,
                                         end=end)
        self.get_store().queue_object(gen)
        return gen
