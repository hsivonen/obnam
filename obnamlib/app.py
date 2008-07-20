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

import obnamlib



# Maximum number of files per file group we create.
MAX_PER_FILEGROUP = 16


class Application:

    """Main program logic for Obnam, a backup application."""

    def __init__(self, context):
        self._context = context
        self._exclusion_strings = []
        self._exclusion_regexps = []
        self._filelist = None
        self._prev_gen = None
        self._store = obnamlib.Store(self._context)
        self._total = 0
        self._latest_snapshot = 0
        
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

    def update_file(self, filename):
        self._total += 1
        context = self.get_context()
        context.progress.update_total_files(self._total)
        context.progress.update_current_action(filename)

    def add_to_total_files(self, count):
        self._total += count
        self.get_context().progress.update_total_files(self._total)

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
        strings = [s.strip() for s in strings if s.strip()]
        if self._exclusion_strings != strings:
            self._exclusion_strings = strings
            self._exclusion_regexps = []
            for string in strings:
                logging.debug("Compiling exclusion pattern '%s'" % string)
                self._exclusion_regexps.append(re.compile(string))
        
        return self._exclusion_regexps

    def prune(self, dirname, dirnames, filenames):
        """Remove excluded items from dirnames and filenames.
        
        Because this is called by obnamlib.walk.depth_first, the lists
        are modified in place.
        
        """
        
        self._prune_one_list(dirname, dirnames)
        self._prune_one_list(dirname, filenames)

    def _prune_one_list(self, dirname, basenames):
        """Prune one list of basenames based on exlusion list.
        
        Because this is called from self.prune, the list is modified
        in place.
        
        """

        dirname = obnamlib.io.unsolve(self._context, dirname)

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

    def time_for_snapshot(self):
        """Is it time for a snapshot generation to be made?"""
        context = self.get_context()
        threshold = context.config.getint("backup", "snapshot-bytes")
        if threshold == 0:
            return False
        bytes_written = context.be.get_bytes_written() - self._latest_snapshot
        return bytes_written >= threshold
        
    def snapshot_done(self):
        """Mark we did a snapshot generation at this point in the upload."""
        bytes_written = self.get_context().be.get_bytes_written()
        self._latest_snapshot = bytes_written

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

    def filegroup_is_unchanged(self, dirname, fg, filenames, stat=os.lstat):
        """Is a filegroup unchanged from the previous generation?
        
        Given a filegroup and a list of files in the given directory,
        return True if all files in the filegroup are unchanged from
        the previous generation.
        
        The optional stat argument can be used by unit tests to
        override the use of os.lstat.
        
        """
        
        for old_name in fg.get_names():
            if old_name not in filenames:
                return False    # file has been deleted

            old_stat = fg.get_stat(old_name)
            new_stat = stat(os.path.join(dirname, old_name))
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
        
        logging.debug("Setting previous generation FILELIST.")
        self._filelist = filelist

    def get_previous_generation(self):
        """Get the previous generation for a backup run."""
        return self._prev_gen

    def set_previous_generation(self, gen):
        """Set the previous generation for a backup run."""
        self._prev_gen = gen

    def find_file_by_name(self, filename):
        """Find a backed up file given its filename.
        
        Return FILE component, or None if no file with the given name
        could be found.
        
        """
        
        if self._filelist:
            fc = self._filelist.find(filename)
            if fc != None:
                return fc
        
        return None

    def compute_signature(self, filename):
        """Compute rsync signature for a filename.
        
        Return the identifier. Put the signature object in the queue to
        be uploaded.
        
        """

        logging.debug("Computing rsync signature for %s" % filename)
        sigdata = obnamlib.rsync.compute_signature(self._context, filename)
        id = obnamlib.obj.object_id_new()
        sig = obnamlib.obj.SignatureObject(id=id, sigdata=sigdata)
        self.get_store().queue_object(sig)
        return sig

    def unchanged_groups(self, dirname, filegroups,filenames, stat=os.lstat):
        """Return list of filegroups that are unchanged.
        
        The filenames and stat arguments have the same meaning as 
        for the filegroup_is_unchanged method.
        
        """
        
        unchanged = []
        
        for filegroup in filegroups:
            if self.filegroup_is_unchanged(dirname, filegroup, filenames, 
                                           stat=stat):
                unchanged.append(filegroup)

        logging.debug("There are %d unchanged filegroups in %s" %
                      (len(unchanged), dirname))
        return unchanged

    def get_file_in_previous_generation(self, pathname):
        """Return non-directory file in previous generation, or None."""
        if self._filelist: #pragma: no cover
            logging.debug("Have FILELIST, searching it for %s" % pathname)
            file = self.find_file_by_name(pathname)
            if file:
                logging.debug("Found in prevgen FILELIST: %s" % pathname)
                return file
            else:
                logging.debug("Not found in FILELIST.")
        else:
            logging.debug("No FILELIST for previous generation.")
        gen = self.get_previous_generation()
        if gen:
            logging.debug("Looking up file in previous gen: %s" % pathname)
            return self.get_store().lookup_file(gen, pathname)
        else:
            logging.debug("No previous gen in which to find %s" % pathname)
            return None

    def _reuse_existing(self, old_file): #pragma: no cover
        logging.debug("Re-using existing file contents: %s" %
                      old_file.first_string_by_kind(obnamlib.cmp.FILENAME))
        return (old_file.first_string_by_kind(obnamlib.cmp.CONTREF),
                old_file.first_string_by_kind(obnamlib.cmp.SIGREF),
                old_file.first_string_by_kind(obnamlib.cmp.DELTAREF))

    def _get_old_sig(self, old_file): #pragma: no cover
        old_sigref = old_file.first_string_by_kind(obnamlib.cmp.SIGREF)
        if not old_sigref:
            return None
        old_sig = self.get_store().get_object(old_sigref)
        if not old_sig:
            return None
        return old_sig.first_string_by_kind(obnamlib.cmp.SIGDATA)

    def _compute_delta(self, old_file, filename): #pragma: no cover
        old_sig_data = self._get_old_sig(old_file)
        if old_sig_data:
            logging.debug("Computing delta for %s" % filename)
            old_contref = old_file.first_string_by_kind(obnamlib.cmp.CONTREF)
            old_deltaref = old_file.first_string_by_kind(obnamlib.cmp.DELTAREF)
            deltapart_ids = obnamlib.rsync.compute_delta(self.get_context(),
                                                      old_sig_data, filename)
            delta_id = obnamlib.obj.object_id_new()
            delta = obnamlib.obj.DeltaObject(id=delta_id, 
                                          deltapart_refs=deltapart_ids, 
                                          cont_ref=old_contref, 
                                          delta_ref=old_deltaref)
            self.get_store().queue_object(delta)
            
            sig = self.compute_signature(filename)

            return None, sig.get_id(), delta.get_id()
        else:
            logging.debug("Signature for previous version not found for %s" %
                          filename)
            return self._backup_new(filename)

    def _backup_new(self, filename):
        logging.debug("Storing new file %s" % filename)
        contref = obnamlib.io.create_file_contents_object(self._context, 
                                                       filename)
        sig = self.compute_signature(filename)
        sigref = sig.get_id()
        deltaref = None
        return contref, sigref, deltaref

    def add_to_filegroup(self, fg, filename):
        """Add a file to a filegroup."""
        logging.debug("Backing up %s" % filename)
        self.update_file(filename)
        st = os.lstat(filename)
        if stat.S_ISREG(st.st_mode):
            unsolved = obnamlib.io.unsolve(self.get_context(), filename)
            old_file = self.get_file_in_previous_generation(unsolved)
            if old_file: #pragma: no cover
                old_st = old_file.first_by_kind(obnamlib.cmp.STAT)
                old_st = obnamlib.cmp.parse_stat_component(old_st)
                if self.file_is_unchanged(old_st, st):
                    contref, sigref, deltaref = self._reuse_existing(old_file)
                else:
                    contref, sigref, deltaref = self._compute_delta(old_file,
                                                                    filename)
            else:
                contref, sigref, deltaref = self._backup_new(filename)
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
                id = obnamlib.obj.object_id_new()
                list.append(obnamlib.obj.FileGroupObject(id=id))
            self.add_to_filegroup(list[-1], filename)
            if self.time_for_snapshot():
                break
                
        self.get_store().queue_objects(list)
        return list

    def _make_absolute(self, basename, relatives):
        return [os.path.join(basename, name) for name in relatives]

    def get_dir_in_previous_generation(self, dirname):
        """Return directory in previous generation, or None."""
        gen = self.get_previous_generation()
        if gen:
            logging.debug("Looking up in previous generation: %s" % dirname)
            return self.get_store().lookup_dir(gen, dirname)
        else:
            logging.debug("No previous generation to search for %s" % dirname)
            return None

    def select_files_to_back_up(self, dirname, filenames, stat=os.lstat):
        """Select files to backup in a directory, compared to previous gen.
        
        Look up the directory in the previous generation, and see which
        files need backing up compared to that generation.
        
        Return list of unchanged filegroups, plus list of filenames
        that need backing up.
        
        """

        unsolved = obnamlib.io.unsolve(self.get_context(), dirname)
        logging.debug("Selecting files to backup in %s (unsolved)" % unsolved)
        logging.debug("There are %d filenames currently" % len(filenames)) 
               
        filenames = filenames[:]
        old_dir = self.get_dir_in_previous_generation(unsolved)
        if old_dir:
            logging.debug("Found directory in previous generation")
            old_groups = [self.get_store().get_object(id)
                          for id in old_dir.get_filegrouprefs()]
            filegroups = self.unchanged_groups(dirname, old_groups, filenames, 
                                               stat=stat)
            for fg in filegroups:
                for name in fg.get_names():
                    filenames.remove(name)
    
            return filegroups, filenames
        else:
            logging.debug("Did not find directory in previous generation")
            return [], filenames

    def backup_one_dir(self, dirname, subdirs, filenames, is_root=False):
        """Back up non-recursively one directory.
        
        Return obnamlib.obj.DirObject that refers to the directory.
        
        subdirs is the list of subdirectories (as DirObject) for this
        directory.

        """
        
        logging.debug("Backing up non-recursively: %s" % dirname)
        filegroups, filenames = self.select_files_to_back_up(dirname, 
                                                             filenames)
        logging.debug("Selected %d existing file groups, %d filenames" %
                      (len(filegroups), len(filenames)))
        self.add_to_total_files(sum(len(fg.get_files()) for fg in filegroups))

        filenames = self._make_absolute(dirname, filenames)

        filegroups += self.make_filegroups(filenames)
        filegrouprefs = [fg.get_id() for fg in filegroups]

        dirrefs = [subdir.get_id() for subdir in subdirs]

        basename = os.path.basename(dirname)
        if not basename and dirname.endswith(os.sep):
            basename = os.path.basename(dirname[:-len(os.sep)])
        assert basename
        logging.debug("Creating DirObject, basename: %s" % basename)
        if is_root:
            name = obnamlib.io.unsolve(self.get_context(), dirname)
        else:
            name = basename
        dir = obnamlib.obj.DirObject(id=obnamlib.obj.object_id_new(),
                                  name=name,
                                  stat=os.lstat(dirname),
                                  dirrefs=dirrefs,
                                  filegrouprefs=filegrouprefs)

        unsolved = obnamlib.io.unsolve(self.get_context(), dirname)
        old_dir = self.get_dir_in_previous_generation(unsolved)
        if old_dir and self.dir_is_unchanged(old_dir, dir): #pragma: no cover
            logging.debug("Dir is unchanged: %s" % dirname)
            return old_dir
        else:
            logging.debug("Dir has changed: %s" % dirname)
            self.get_store().queue_object(dir)
            return dir

    def make_snapshot_dir(self, dirname, subdirs, is_root): #pragma: no cover
        """Like backup_one_dir, but use data only from previous generation."""

        logging.debug("Making snapshot directory: %s" % dirname)

        unsolved = obnamlib.io.unsolve(self.get_context(), dirname)
        old_dir = self.get_dir_in_previous_generation(unsolved)
        if old_dir:
            logging.debug("Found directory in previous generation")
            filegroups = [self.get_store().get_object(id)
                          for id in old_dir.get_filegrouprefs()]
            old_dirrefs = [dirref for dirref in old_dir.get_dirrefs()]
        else:
            logging.debug("Did not find directory in previous generation")
            filegroups = []
            old_dirrefs = []

        filegrouprefs = [fg.get_id() for fg in filegroups]
        dirrefs = [subdir.get_id() for subdir in subdirs]
        
        for dirref in old_dirrefs:
            if dirref not in dirrefs:
                dirrefs.append(dirref)

        basename = os.path.basename(dirname)
        if not basename and dirname.endswith(os.sep):
            basename = os.path.basename(dirname[:-len(os.sep)])
        assert basename
        logging.debug("Creating DirObject, basename: %s" % basename)
        if is_root:
            name = obnamlib.io.unsolve(self.get_context(), dirname)
        else:
            name = basename
        dir = obnamlib.obj.DirObject(id=obnamlib.obj.object_id_new(),
                                  name=name,
                                  stat=os.lstat(dirname),
                                  dirrefs=dirrefs,
                                  filegrouprefs=filegrouprefs)

        self.get_store().queue_object(dir)
        return dir
        

    def backup_one_root(self, root):
        """Backup one root for the next generation."""

        logging.debug("Backing up root %s" % root)
        
        resolved = obnamlib.io.resolve(self._context, root)
        logging.debug("Root resolves to %s" % resolved)
        
        if not os.path.isdir(resolved):
            raise obnamlib.ObnamException("Not a directory: %s" % root)
            # FIXME: This needs to be able to handle non-directories, too!
        
        subdirs_for_dir = {}
        root_object = None
        
        for tuple in obnamlib.walk.depth_first(resolved, prune=self.prune):
            dirname, dirnames, filenames = tuple
            filenames.sort()
            logging.debug("Walked to directory %s" % dirname)
            logging.debug("  with dirnames: %s" % dirnames)
            logging.debug("  and filenames: %s" % filenames)
            self.get_context().progress.update_current_action(dirname)

            subdirs = subdirs_for_dir.get(dirname, [])
            
            is_root = (dirname == resolved)
            
            dir = self.backup_one_dir(dirname, subdirs, filenames, 
                                      is_root=is_root)

            if not is_root:
                parent = os.path.dirname(dirname)
                if parent not in subdirs_for_dir:
                    subdirs_for_dir[parent] = []
                subdirs_for_dir[parent].append(dir)
            else:
                root_object = dir

            if dirname in subdirs_for_dir:
                del subdirs_for_dir[dirname]

            self._total += 1 + len(filenames)
            self.get_context().progress.update_total_files(self._total)
            
            if self.time_for_snapshot(): #pragma: no cover
                # Fill in parent directories with old data + known changes
                while dirname != resolved:
                    dirname = os.path.dirname(dirname)
                    is_root = (dirname == resolved)
                    subdirs = subdirs_for_dir.get(dirname, [])
                    dir = self.make_snapshot_dir(dirname, subdirs, is_root)
                    if not is_root:
                        parent = os.path.dirname(dirname)
                        if parent not in subdirs_for_dir:
                            subdirs_for_dir[parent] = []
                        subdirs_for_dir[parent].append(dir)
                    else:
                        root_object = dir
                break

        return root_object

    def _make_generation(self, start, root_objs, is_snapshot):
        end = int(time.time())

        dirrefs = [o.get_id() for o in root_objs]
        gen = obnamlib.obj.GenerationObject(id=obnamlib.obj.object_id_new(),
                                         dirrefs=dirrefs, start=start,
                                         end=end, is_snapshot=is_snapshot)
        self.get_store().queue_object(gen)
        return gen

    def backup(self, roots):
        """Backup all the roots."""

        start = int(time.time())
        root_objs = []
        self._total = 0
        prevgen = self.get_previous_generation()
        for root in roots:
            while True:
                self.set_previous_generation(prevgen)
                o = self.backup_one_root(root)
                if self.time_for_snapshot(): #pragma: no cover
                    logging.debug("Making a snapshot generation")
                    gen = self._make_generation(start, root_objs + [o], True)
                    self.snapshot_done()
                    yield gen
                    prevgen = gen
                else:
                    break
            root_objs.append(o)

        yield self._make_generation(start, root_objs, False)

