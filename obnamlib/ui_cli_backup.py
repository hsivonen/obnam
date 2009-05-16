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


import logging
import os
import stat

import obnamlib


class DummyLookupper:

    def get_dir(self, name):
        raise obnamlib.NotFound(name)


class BackupCommand(object):

    """A sub-command for the command line interface to back up some data."""

    PART_SIZE = 256 * 1024

    def backup_new_symlink(self, relative_path, stat):
        """Backup a new symlink."""
        target = self.fs.readlink(relative_path)
        fc = obnamlib.File(os.path.basename(relative_path), stat, 
                           symlink_target=target)
        return fc

    def backup_new_other(self, path, st):
        """Backup a new thing that is not a symlink or regular file."""
        return obnamlib.File(os.path.basename(path), st)

    def backup_new_file(self, path, st):
        """Back up a completely new file."""
        
        f = self.fs.open(path, "r")
        content = self.store.put_contents(f, self.PART_SIZE)
        f.close()
        fc = obnamlib.File(os.path.basename(path), st, content.id, None, None)
        return fc

    def backup_new_files_as_groups(self, relative_paths, lstat=None):
        """Back a set of new files as a new FILEGROUP."""
        if lstat is None: # pragma: no cover
            lstat = self.fs.lstat
        fg = self.store.new_object(kind=obnamlib.FILEGROUP)
        for path in relative_paths:
            st = lstat(path)
            fc = None
            if stat.S_ISREG(st.st_mode):
                fc = self.backup_new_file(path, st)
            elif stat.S_ISLNK(st.st_mode):
                fc = self.backup_new_symlink(path, st)
            else:
                fc = self.backup_new_other(path, st)
            fg.components.append(fc)
        self.store.put_object(fg)
        return [fg]

    def new_dir(self, relative_path, st, subdirs, filegroups):
        """Create a new obnamlib.Dir."""
        dir = self.store.new_object(obnamlib.DIR)
        dir.name = os.path.basename(relative_path)
        dir.stat = st
        dir.dirrefs = [x.id for x in subdirs]
        dir.fgrefs = [x.id for x in filegroups]
        self.store.put_object(dir)
        return dir

    def find_reusable_filegroups(self, prevdir, dirname, filenames): # pragma: no cover
        """Find filegroups that can be re-used from previous generation.
        
        Return list of filegroups and list of filenames NOT in those groups.
        
        """
        
        filegroups = []
        for fgref in prevdir.fgrefs:
            fg = self.store.get_object(self.host, fgref)
            for name in fg.names:
                if (name not in filenames or
                    not self.same_file(dirname, name, fg)):
                    break
            else:
                filegroups.append(fg)
                filenames = [x for x in filenames if x not in fg.names]

        return filegroups, filenames

    def same_file(self, dirname, basename, fg): # pragma: no cover
        """Is the file on disk the same as in the filegroup?"""
        fullname = os.path.join(dirname, basename)
        st = self.fs.lstat(fullname)
        return self.same_stat(st, fg.get_stat(basename))

    def same_filegroups(self, prevdir, filegroups): # pragma: no cover
        """Does prevdir have exactly those filegroups?"""
        return set(prevdir.fgrefs) == set(x.id for x in filegroups)
        
    def same_subdirs(self, prevdir, subdirs): # pragma: no cover
        """Does prevdir have exactly those sub-directories?"""
        return set(prevdir.dirrefs) == set(x.id for x in subdirs)

    def same_stat(self, stat1, stat2): # pragma: no cover
        """Are two stats identical for all the relevant values?"""
        return (stat1.st_mode  == stat2.st_mode and
                stat1.st_dev   == stat2.st_dev and
                stat1.st_nlink == stat2.st_nlink and
                stat1.st_uid   == stat2.st_uid and
                stat1.st_gid   == stat2.st_gid and
                stat1.st_size  == stat2.st_size and
                stat1.st_mtime == stat2.st_mtime)

    def backup_existing_dir(self, prevdir, relative_path, st, subdirs, 
                            filenames): # pragma: no cover
        """Back up a directory that exists in the previous generation."""

        logging.debug("Directory EXISTS in previous gen: %s" % relative_path)

        filegroups, filenames = self.find_reusable_filegroups(prevdir, 
                                                              relative_path,
                                                              filenames)
        if (not filenames and
            self.same_filegroups(prevdir, filegroups) and
            self.same_subdirs(prevdir, subdirs) and
            self.same_stat(prevdir.stat, st)):
            return prevdir
        else:
            if filenames:
                fullnames = [os.path.join(relative_path, x) for x in filenames]
                filegroups += self.backup_new_files_as_groups(fullnames)
            return self.new_dir(relative_path, st, subdirs, filegroups)

    def backup_new_dir(self, relative_path, st, subdirs, filenames):
        """Back up a new directory."""
        logging.debug("Directory is NEW: %s" % relative_path)
        fullnames = [os.path.join(relative_path, x) for x in filenames]
        filegroups = self.backup_new_files_as_groups(fullnames)
        return self.new_dir(relative_path, st, subdirs, filegroups)

    def get_dir_in_prevgen(self, relative_path):
        """Return obnamlib.Dir in previous generation, or None."""
        try:
            return self.prevgen_lookupper.get_dir(relative_path)
        except obnamlib.NotFound:
            return None

    def backup_dir(self, relative_path, subdirs, filenames, lstat=None):
        """Back up a single directory, non-recursively.

        subdirs is a list of obnamlib.Dir objects for the direct
        subdirectories of the target directory. They must have been
        backed up already.

        """

        logging.debug("Backing up directory %s" % relative_path)

        if lstat is None: # pragma: no cover
            lstat = self.fs.lstat
        st = lstat(relative_path)

        prevdir = self.get_dir_in_prevgen(relative_path)
        logging.debug("backup_dir: prevdir=%s" % repr(prevdir))
        if prevdir: # pragma: no cover
            dir = self.backup_existing_dir(prevdir, relative_path, st,
                                           subdirs, filenames)
        else:
            dir = self.backup_new_dir(relative_path, st, subdirs, filenames)

        return dir

    def backup_recursively(self, root):
        """Back up a directory, recursively."""
        
        logging.debug("Backing up recursively: %s" % root)

        # We traverse the directory tree depth-first. When we get to a
        # directory, we need to know its subdirectories. We keep them
        # in this dict, which is indexed by the directory pathname.
        # The value is a list of obnamlib.Dir objects.
        subdirs = {}

        for dirname, dirnames, filenames in self.fs.depth_first(root):
            logging.info("Backing up %s" % dirname)
            list = subdirs.pop(dirname, [])
            dir = self.backup_dir(dirname, list, filenames)
            if dirname == root:
                root_object = dir
            else:
                parent = os.path.dirname(dirname)
                subdirs[parent] = subdirs.get(parent, []) + [dir]

        return root_object

    def list_ancestors(self, pathname):
        """Return list of pathnames of ancestors of a given name."""
        
        pathname = os.path.normpath(pathname)
        ancestors = []
        while pathname and pathname != os.sep:
            parent = os.path.dirname(pathname)
            if parent:
                ancestors.append(parent)
            pathname = parent
        return ancestors

    def fake_ancestors(self, root_list): # pragma: no cover
        """Create fake obnamlib.Dir entries for all ancestors of roots.
        
        Return the fake obnamlib.Dir for the root of the filesystem.
        
        """
        
        ancestors = {}
        
        result = set()
        
        for root_name, root_obj in root_list:
            descendant = root_obj
            ancestor_list = self.list_ancestors(root_name)
            for ancestor in ancestor_list:
                if ancestor in ancestors:
                    dir = ancestors[ancestor]
                else:
                    dir = self.store.new_object(obnamlib.DIR)
                    dir.name = os.path.basename(ancestor) or ancestor
                    dir.stat = self.fs.lstat(ancestor)
                    ancestors[ancestor] = dir
                dir.dirrefs.append(descendant.id)
                descendant = dir
            if ancestor_list:
                result.add(ancestors[ancestor_list[-1]])
            else:
                result.add(root_obj)

        for path in ancestors:
            self.store.put_object(ancestors[path])

        return result

    def backup_generation(self, roots):
        """Back up a generation."""

        gen = self.store.new_object(obnamlib.GEN)

        dirs = [x for x in roots if self.fs.isdir(x)]
        nondirs = [x for x in roots if x not in dirs]

        root_list = []
        for root in dirs:
            root_list.append((root, self.backup_recursively(root)))
        dirlist = self.fake_ancestors(root_list)
        gen.dirrefs = [x.id for x in dirlist]

        gen.fgrefs += [x.id for x in self.backup_new_files_as_groups(nondirs)]

        self.store.put_object(gen)

        return gen

    def backup(self, host_id, roots):
        logging.debug("Backing up: host %s, roots %s" % 
                      (host_id, " ".join(roots)))
        self.host = self.store.get_host(host_id)
        if self.host.genrefs: # pragma: no cover
            prevgenref = self.host.genrefs[-1]
            logging.debug("Found previous generation %s" % prevgenref)
            prevgen = self.store.get_object(self.host, prevgenref)
            self.prevgen_lookupper = obnamlib.Lookupper(self.store, self.host, 
                                                        prevgen)
        else:
            logging.debug("Using DummyLookupper")
            self.prevgen_lookupper = DummyLookupper()
        gen = self.backup_generation(roots)
        self.host.genrefs.append(gen.id)
        self.store.commit(self.host)

    def __call__(self, config, args): # pragma: no cover
        host_id = args[0]
        store_url = args[1]
        roots = args[2:]

        self.store = obnamlib.Store(store_url, "w")
        self.fs = obnamlib.LocalFS("/")

        roots = [os.path.abspath(root) for root in roots]
        self.backup(host_id, roots)
