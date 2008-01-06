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


"""Walk a directory tree."""


import os


def depth_first(top, prune=None):
    """Walk a directory tree depth-first, except for unwanted subdirs.
    
    This is, essentially, 'os.walk(top, topdown=False)', except that
    if the prune argument is set, we call it before descending to 
    sub-directories to allow it to remove any directories and files
    the caller does not want to know about.
    
    If set, prune must be a function that gets three arguments (current
    directory, list of sub-directory names, list of files in directory),
    and must modify the two lists _in_place_. For example:
    
        def prune(dirname, dirnames, filenames):
            if ".bzr" in dirnames:
                dirnames.remove(".bzr")
                
    The dirnames and filenames lists contain basenames, relative to
    dirname.
    
    """

    # We walk topdown, since that's the only way os.walk allows us to
    # do any pruning. We use os.walk to get the exact same error handling
    # and other logic it uses.
    for dirname, dirnames, filenames in os.walk(top):

        # Prune. This modifies dirnames and filenames in place.
        if prune:
            prune(dirname, dirnames, filenames)

        # Make a duplicate of the dirnames, then empty the existing list.
        # This way, os.walk won't try to walk to subdirectories. We'll
        # do that manually.
        real_dirnames = dirnames[:]
        del dirnames[:]

        # Process subdirectories, recursively.
        for subdirname in real_dirnames:
            subdirpath = os.path.join(dirname, subdirname)
            for x in depth_first(subdirpath, prune=prune):
                yield x

        # Return current directory last.
        yield dirname, real_dirnames, filenames
