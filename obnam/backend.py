# Copyright (C) 2006, 2007  Lars Wirzenius <liw@iki.fi>
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


"""Backup program backend for communicating with the backup server."""


import logging
import os
import pwd
import stat
import urlparse

# Python define os.O_BINARY only on Windows, but since we want to be portable,
# we want to use it every time. Thus, if it doesn't exist, we define it as
# zero, which should not disturb anyone.
if "O_BINARY" not in dir(os):
    os.O_BINARY = 0

import paramiko

import uuid
import obnam.cache
import obnam.cmp
import obnam.map
import obnam.obj


# Block filenames are created using the following scheme:
#
# For each backup run, we create one directory, named by a UUID. Inside
# this directory we create sub-directories, named by sequential integers,
# up to a certain number of levels. The actual block files are created at
# the lowest level, and we create the next lowest level directory when
# we've reached some maximum of files in the directory.
#
# The rationale is that having too many files in one directory makes all
# operations involving that directory slow, in many filesystems, because
# of linear searches. By putting, say, only 256 files per directory, we
# can keep things reasonably fast. However, if we create a a lot of blocks,
# we'll end up creating a lot of directories, too. Thus, several levels of
# directories are needed.
#
# With 256 files per directory, and three levels of directories, and one
# megabyte per block file, we can create 16 terabytes of backup data without
# exceeding contraints. After that, we get more than 256 entries per
# directory, making things slow, but it'll still work.

MAX_BLOCKS_PER_DIR = 256
LEVELS = 3


def parse_store_url(url):
    """Parse a store url
    
    The url must either be a plain pathname, or it starts with sftp://
    and specifies a remote store. Return a tuple username, host, port,
    path, where elements can be None if they are meant to be the default
    or are not relevant.
    
    Note that we follow the bzr (and lftp?) syntax: sftp://foo/bar is an
    absolute path, /foo, and sftp://foo/~/bar is "bar" relative to the
    user's home directory.
    
    """
    
    # urlparse in Python 2.4 doesn't know, by default, that sftp uses
    # a netloc
    if "sftp" not in urlparse.uses_netloc:
        urlparse.uses_netloc.append("sftp")
    
    user = host = port = path = None
    (scheme, netloc, path, query, fragment) = urlparse.urlsplit(url)
    
    if scheme == "sftp":
        if "@" in netloc:
            (user, netloc) = netloc.split("@", 1)
        if ":" in netloc:
            (host, port) = netloc.split(":", 1)
            port = int(port)
        else:
            host = netloc
        if path.startswith("/~/"):
            path = path[3:]
    else:
        path = url
    
    return user, host, port, path


class Backend:

    def __init__(self, config, cache):
        self.config = config
        self.url = config.get("backup", "store")

        self.user, self.host, self.port, self.path = parse_store_url(self.url)
        if self.user is None:
            self.user = get_default_user()
        if self.port is None:
            self.port = 22 # 22 is the default port for ssh

        self.blockdir = None
        self.dircounts = [0] * LEVELS
        self.sftp_transport = None
        self.sftp_client = None
        self.bytes_read = 0
        self.bytes_written = 0
        self.progress = None
        self.cache = cache
        self.blockdir = str(uuid.uuid4())
    
    def set_progress_reporter(self, progress):
        """Set progress reporter to be used"""
        self.progress = progress
        
    def get_bytes_read(self):
        """Return number of bytes read from the store during this run"""
        return self.bytes_read
    
    def get_bytes_written(self):
        """Return number of bytes written to the store during this run"""
        return self.bytes_written

    def increment_dircounts(self):
        """Increment the counter for lowest dir level, and more if need be"""
        level = len(self.dircounts) - 1
        while level >= 0:
            self.dircounts[level] += 1
            if self.dircounts[level] <= MAX_BLOCKS_PER_DIR:
                break
            self.dircounts[level] = 0
            level -= 1
        
    def generate_block_id(self):
        """Generate a new identifier for the block, when stored remotely"""
        self.increment_dircounts()
        id = self.blockdir
        for i in self.dircounts:
            id = os.path.join(id, "%d" % i)
        return id

    def block_remote_pathname(self, block_id):
        """Return pathname on server for a given block id"""
        return os.path.join(self.path, block_id)

    def use_gpg(self):
        """Should we use gpg to encrypt/decrypt blocks?"""
        no_gpg = self.config.getboolean("backup", "no-gpg")
        if no_gpg:
            return False
        encrypt_to = self.config.get("backup", "gpg-encrypt-to").strip()
        return encrypt_to
    
    def upload(self, block_id, block):
        logging.debug("Uploading block %s" % block_id)
        if self.use_gpg():
            logging.debug("Encrypting block %s before upload" % block_id)
            encrypted = obnam.gpg.encrypt(self.config, block)
            if encrypted is None:
                logging.error("Can't encrypt block for upload, " +
                              "not uploading it")
                return None
            block = encrypted
        logging.debug("Uploading block %s (%d bytes)" % (block_id, len(block)))
        self.really_upload(block_id, block)
        self.bytes_written += len(block)
        if self.progress:
            self.progress.update_uploaded(self.bytes_written)
        return None

    def download(self, block_id):
        """Download a block from the remote server
        
        Return the unparsed block (a string), or an exception for errors.
        
        """
        
        logging.debug("Downloading block %s" % block_id)
        block = self.really_download(block_id)
        if type(block) != type(""):
            logging.warning("Download failed, returning exception")
            return block # it's an exception

        self.bytes_read += len(block)
        if self.progress:
            self.progress.update_downloaded(self.bytes_read)
        
        if self.use_gpg():
            logging.debug("Decoding downloaded block %s before using it" %
                          block_id)
            decrypted = obnam.gpg.decrypt(self.config, block)
            if decrypted is None:
                logging.error("Can't decrypt downloaded block, not using it")
                return None
            block = decrypted
        
        return block
    
    def remove(self, block_id):
        """Remove a block from the remote server"""
        pathname = self.block_remote_pathname(block_id)
        try:
            self.remove_pathname(pathname)
        except IOError:
            # We ignore any errors in removing a file.
            pass
    

class SftpBackend(Backend):

    def connect_sftp(self):
        """Connect to the server, unless already connected"""
        if self.sftp_transport is None:
            ssh_key_file = self.config.get("backup", "ssh-key")
            logging.debug("Getting private key from %s" % ssh_key_file)
            pkey = paramiko.DSSKey.from_private_key_file(ssh_key_file)
    
            logging.debug("Connecting to sftp server: host=%s, port=%d" % 
                          (self.host, self.port))
            self.sftp_transport = paramiko.Transport((self.host, self.port))
    
            logging.debug("Authenticating as user %s" % self.user)
            self.sftp_transport.connect(username=self.user, pkey=pkey)
    
            logging.debug("Opening sftp client")
            self.sftp_client = self.sftp_transport.open_sftp_client()
    
    def sftp_makedirs(self, dirname, mode=0777):
        """Create dirname, if it doesn't exist, and all its parents, too"""
        stack = []
        while dirname:
            stack.append(dirname)
            dirname2 = os.path.dirname(dirname)
            if dirname2 == dirname:
                dirname = None
            else:
                dirname = dirname2
    
        while stack:
            dirname, stack = stack[-1], stack[:-1]
            try:
                self.sftp_client.lstat(dirname).st_mode
            except IOError:
                exists = False
            else:
                exists = True
            if not exists:
                logging.debug("Creating remote directory %s" % dirname)
                self.sftp_client.mkdir(dirname, mode=mode)
    
    def really_upload(self, block_id, block):
        self.connect_sftp()
        pathname = self.block_remote_pathname(block_id)
        self.sftp_makedirs(os.path.dirname(pathname))
        self.sftp_client.chmod(pathname, 0600)
        f = self.sftp_client.file(pathname, "w")
        f.write(block)
        f.close()
    
    def really_download(self, block_id):
        try:
            self.connect_sftp()
            f = self.sftp_client.file(self.block_remote_pathname(block_id), 
                                      "r")
            block = f.read()
            f.close()
            if self.config.get("backup", "cache"):
                self.cache.put_block(block_id, block)
        except IOError, e:
            logging.warning("I/O error: %s" % str(e))
            return e
        return block
    
    def sftp_listdir_abs(self, dirname):
        """Like SFTPClient's listdir_attr, but absolute pathnames"""
        items = self.sftp_client.listdir_attr(dirname)
        for item in items:
            item.filename = os.path.join(dirname, item.filename)
        return items
    
    def sftp_recursive_listdir(self, dirname="."):
        """Similar to SFTPClient's listdir_attr, but recursively"""
        list = []
        logging.debug("sftp: listing files in %s" % dirname)
        unprocessed = self.sftp_listdir_abs(dirname)
        while unprocessed:
            item, unprocessed = unprocessed[0], unprocessed[1:]
            if stat.S_ISDIR(item.st_mode):
                logging.debug("sftp: listing files in %s" % item.filename)
                unprocessed += self.sftp_listdir_abs(item.filename)
            elif stat.S_ISREG(item.st_mode):
                list.append(item.filename)
        return list
    
    def list(self):
        """Return list of all files on the remote server"""
        return self.sftp_recursive_listdir(self.path)
    
    def remove_pathname(self, pathname):
        self.sftp_client.remove(pathname)


class FileBackend(Backend):

    def really_upload(self, block_id, block):
        dir_full = os.path.join(self.path, os.path.dirname(block_id))
        if not os.path.isdir(dir_full):
            os.makedirs(dir_full, 0700)
        fd = os.open(self.block_remote_pathname(block_id), 
                     os.O_WRONLY | os.O_CREAT | os.O_BINARY,
                     0600)
        f = os.fdopen(fd, "w")
        f.write(block)
        f.close()

    def really_download(self, block_id):
        try:
            f = file(self.block_remote_pathname(block_id), "r")
            block = f.read()
            f.close()
        except IOError, e:
            return e
        return block
    
    def list(self):
        """Return list of all files on the remote server"""
        list = []
        for dirpath, _, filenames in os.walk(self.path):
            if dirpath.startswith(self.path):
                dirpath = dirpath[len(self.path):]
                if dirpath.startswith(os.sep):
                    dirpath = dirpath[len(os.sep):]
            list += [os.path.join(dirpath, x) for x in filenames]
        return list
    
    def remove_pathname(self, pathname):
        """Remove a block from the remote server"""
        if os.path.exists(pathname):
            os.remove(pathname)
    
        
def get_default_user():
    """Return the username of the current user"""
    if "LOGNAME" in os.environ:
        return os.environ["LOGNAME"]
    else:
        return pwd.getpwuid(os.getuid())[0]


def init(config, cache):
    """Initialize the subsystem and return an opaque backend object"""
    _, host, _, _ = parse_store_url(config.get("backup", "store"))
    if host is None:
        return FileBackend(config, cache)
    else:
        return SftpBackend(config, cache)
