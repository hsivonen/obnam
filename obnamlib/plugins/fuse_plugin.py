# Copyright (C) 2013  Valery Yundin
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


import os
import stat
import sys
import logging
import errno
import struct

import tracing

import obnamlib

try:
    import fuse
    fuse.fuse_python_api = (0, 2)
except ImportError:
    # This is a workaround to allow us to fake a fuse module, so that
    # this plugin file can be imported. If the module isn't there, the
    # plugin won't work, and it will tell the user it won't work, but
    # at least Obnam won't crash at startup.
    class Bunch:
        def __init__(self, **kwds):
            self.__dict__.update(kwds)
    fuse = Bunch(Fuse = object)


class ObnamFuseOptParse(object):

    '''Option parsing class for FUSE.'''

    # NOTE: This class MUST set self.fuse_args.mountpoint.

    obnam = None

    def __init__(self, *args, **kw):
        if 'fuse_args' in kw:
            self.fuse_args = kw.pop('fuse_args')
        else:
            self.fuse_args = fuse.FuseArgs()
        if 'fuse' in kw:
            self.fuse = kw.pop('fuse')

    def parse_args(self, args=None, values=None):
        self.fuse_args.mountpoint = self.obnam.app.settings['to']
        for opt in self.obnam.app.settings['fuse-opt']:
            if opt == '-f':
                self.fuse_args.setmod('foreground')
            else:
                self.fuse_args.add(opt)
        if not hasattr(self.fuse_args, 'ro'):
            self.fuse_args.add('ro')


class ObnamFuseFile(object):

    fs = None  # points to active ObnamFuse object

    direct_io = False   # do not use direct I/O on this file.
    keep_cache = True   # cached file data need not to be invalidated.

    # Flags that indicate the caller wants to write to the file.
    # Since we're read-only, we'll have to fail the request.
    write_flags = (
        os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_TRUNC | 
        os.O_APPEND)
    
    def __init__(self, path, flags, *mode):
        tracing.trace('path=%r', path)
        tracing.trace('flags=%r', flags)
        tracing.trace('mode=%r', mode)

        self.path = path

        if flags & self.write_flags:
            raise IOError(errno.EROFS, 'Read only filesystem')

        if path == '/.pid':
            self.read = self.read_pid
            self.release = self.release_pid
            return

        try:
            self.metadata = self.fs.get_metadata(path)
        except:
            logging.error('Unexpected exception', exc_info=True)
            raise

        # if not a regular file return EINVAL
        if not stat.S_ISREG(self.metadata.st_mode):
            raise IOError(errno.EINVAL, 'Invalid argument')
        
    def read_pid(self, length, offset):
        tracing.trace('length=%r', length)
        tracing.trace('offset=%r', offset)
        pid = str(os.getpid())
        if length < len(pid) or offset != 0:
            return ''
        else:
            return pid

    def release_pid(self, flags):
        self.fs.root_refresh()
        return 0

    def fgetattr(self):
        tracing.trace('called')
        return self.fs.getattr(self.path)

    def read(self, length, offset):
        tracing.trace('self.path=%r', self.path)
        tracing.trace('length=%r', length)
        tracing.trace('offset=%r', offset)

        if length == 0 or offset >= self.metadata.st_size:
            return ''

        gen, repopath = self.fs.get_gen_path(self.path)

        # The file's data content may be stored in the per-client B-tree.
        # If so, we retrieve the data from there.
        contents = self.fs.obnam.repo.get_file_data(gen, repopath)
        if contents is not None:
            return contents[offset:offset+length]

        # Otherwise, the file has a list of chunks, and we need to
        # find the right ones and return data from them. Note that we
        # can't compute a seek: there is no guarantee all the chunks
        # are of the same size. The user may have changed the chunk
        # size setting between each backup run. Thus, we have to
        # iterate over the list of chunk ids for the file, until we
        # find the right place.
        #
        # This is, obviously, not good for performance.
        #
        # Note that previous code here did the wrong thing by assuming
        # the chunk size was fixed, except for the last chunk for any
        # file.

        chunkids = self.fs.obnam.repo.get_file_chunks(gen, repopath)
        output = []
        output_length = 0
        chunk_pos_in_file = 0
        for chunkid in chunkids:
            contents = self.fs.obnam.repo.get_chunk(chunkid)
            if chunk_pos_in_file + len(contents) >= offset:
                start = offset - chunk_pos_in_file
                n = length - output_length
                data = contents[start : n]
                output.append(data)
                output_length += len(data)
                assert output_length <= length
                if output_length == length:
                    break
            chunk_pos_in_file += len(contents)

        return ''.join(output)

    def release(self, flags):
        tracing.trace('flags=%r', flags)
        return 0

    def fsync(self, isfsyncfile):
        tracing.trace('called')
        return 0

    def flush(self):
        tracing.trace('called')
        return 0

    def ftruncate(self, size):
        tracing.trace('size=%r', size)
        return 0

    def lock(self, cmd, owner, **kw):
        tracing.trace('cmd=%r', cmd)
        tracing.trace('owner=%r', owner)
        tracing.trace('kw=%r', kw)
        raise IOError(errno.EOPNOTSUPP, 'Operation not supported')


class ObnamFuse(fuse.Fuse):

    '''FUSE main class.'''

    MAX_METADATA_CACHE = 512

    def __init__(self, *args, **kw):
        self.obnam = kw['obnam']
        ObnamFuseFile.fs = self
        self.file_class = ObnamFuseFile
        self.metadatacache = {}
        self.sizecache = {}
        self.rootlist = None
        self.rootstat = None
        self.init_root()
        fuse.Fuse.__init__(self, *args, **kw)

    def root_refresh(self):
        tracing.trace('called')

        try:
            self.obnam.reopen()
            generations = [gen for gen in self.obnam.repo.list_generations()
                           if not self.obnam.repo.get_is_checkpoint(gen)]
            tracing.trace('found %d generations', len(generations))
            self.rootstat, self.rootlist = self.multiple_root_list(generations)
            self.metadatacache.clear()
        except:
            logging.exception('Unexpected exception')
            raise

    def get_metadata(self, path):
        tracing.trace('path=%r', path)

        if path not in self.metadatacache:
            if len(self.metadatacache) > self.MAX_METADATA_CACHE:
                self.metadatacache.clear()
            metadata = self.obnam.repo.get_metadata(*self.get_gen_path(path))
            self.metadatacache[path] = metadata
            # FUSE does not allow negative timestamps, truncate to zero
            if metadata.st_atime_sec < 0:
                metadata.st_atime_sec = 0
            if metadata.st_mtime_sec < 0:
                metadata.st_mtime_sec = 0

        return self.metadatacache[path]

    def get_stat(self, path):
        tracing.trace('path=%r', path)
        metadata = self.get_metadata(path)
        st = fuse.Stat()
        st.st_mode = metadata.st_mode
        st.st_dev = metadata.st_dev
        st.st_nlink = metadata.st_nlink
        st.st_uid = metadata.st_uid
        st.st_gid = metadata.st_gid
        st.st_size = metadata.st_size
        st.st_atime = metadata.st_atime_sec
        st.st_mtime = metadata.st_mtime_sec
        st.st_ctime = st.st_mtime
        return st

    def multiple_root_list(self, generations):
        rootlist = {}
        used_generations = []
        for gen in generations:
            path = '/' + str(gen)
            try:
                genstat = self.get_stat(path)
                start, end = self.obnam.repo.get_generation_times(gen)
                genstat.st_ctime = genstat.st_mtime = end
                rootlist[path] = genstat
                used_generations.append(gen)
            except obnamlib.Error:
                pass

        assert used_generations

        latest = used_generations[-1]
        laststat = rootlist['/' + str(latest)]
        rootstat = fuse.Stat(**laststat.__dict__)

        laststat = fuse.Stat(target=str(latest), **laststat.__dict__)
        laststat.st_mode &= ~(stat.S_IFDIR | stat.S_IFREG)
        laststat.st_mode |= stat.S_IFLNK
        rootlist['/latest'] = laststat

        pidstat = fuse.Stat(**rootstat.__dict__)
        pidstat.st_mode = (
            stat.S_IFREG | stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        rootlist['/.pid'] = pidstat

        return (rootstat, rootlist)

    def init_root(self):
        repo = self.obnam.repo

        # we need the list of all real (non-checkpoint) generations
        generations = [gen for gen in repo.list_generations()
                       if not repo.get_is_checkpoint(gen)]

        def gen_path_0(path):
            if path.count('/') == 1:
                gen = path[1:]
                return (int(gen), '/')
            else:
                gen, repopath = path[1:].split('/', 1)
                return (int(gen), '/' + repopath)
        self.get_gen_path = gen_path_0

        self.rootstat, self.rootlist = self.multiple_root_list(generations)
        tracing.trace('multiple rootlist=%r', self.rootlist)

    def getattr(self, path):
        try:
            if path.count('/') == 1:
                if path == '/':
                    return self.rootstat
                elif path in self.rootlist:
                    return self.rootlist[path]
                else:
                    raise obnamlib.Error('ENOENT')
            else:
                return self.get_stat(path)
        except obnamlib.Error:
            raise IOError(errno.ENOENT, 'No such file or directory')
        except:
            logging.error('Unexpected exception', exc_info=True)
            raise

    def readdir(self, path, fh):
        tracing.trace('path=%r', path)
        tracing.trace('fh=%r', fh)
        try:
            if path == '/':
                listdir = [x[1:] for x in self.rootlist.keys()]
            else:
                listdir = self.obnam.repo.listdir(*self.get_gen_path(path))
            return [fuse.Direntry(name) for name in ['.', '..'] + listdir]
        except obnamlib.Error:
            raise IOError(errno.EINVAL, 'Invalid argument')
        except:
            logging.error('Unexpected exception', exc_info=True)
            raise

    def readlink(self, path):
        try:
            statdata = self.rootlist.get(path)
            if statdata and hasattr(statdata, 'target'):
                return statdata.target
            metadata = self.get_metadata(path)
            if metadata.islink():
                return metadata.target
            else:
                raise IOError(errno.EINVAL, 'Invalid argument')
        except obnamlib.Error:
            raise IOError(errno.ENOENT, 'No such file or directory')
        except:
            logging.error('Unexpected exception', exc_info=True)
            raise

    def statfs(self):
        tracing.trace('called')
        try:
            repo = self.obnam.repo

            blocks = sum(repo.client.get_generation_data(gen)
                         for gen in repo.list_generations())
            files = sum(repo.client.get_generation_file_count(gen)
                        for gen in repo.list_generations())

            stv = fuse.StatVfs()
            stv.f_bsize   = 65536
            stv.f_frsize  = 0
            stv.f_blocks  = blocks/65536
            stv.f_bfree   = 0
            stv.f_bavail  = 0
            stv.f_files   = files
            stv.f_ffree   = 0
            stv.f_favail  = 0
            stv.f_flag    = 0
            stv.f_namemax = 255
            #raise OSError(errno.ENOSYS, 'Unimplemented')
            return stv
        except:
            logging.error('Unexpected exception', exc_info=True)
            raise

    def getxattr(self, path, name, size):
        tracing.trace('path=%r', path)
        tracing.trace('name=%r', name)
        tracing.trace('size=%r', size)
        try:
            try:
                metadata = self.get_metadata(path)
            except ValueError:
                return 0
            if not metadata.xattr:
                return 0
            blob = metadata.xattr
            sizesize = struct.calcsize('!Q')
            name_blob_size = struct.unpack('!Q', blob[:sizesize])[0]
            name_blob = blob[sizesize : sizesize + name_blob_size]
            name_list = name_blob.split('\0')[:-1]
            if name in name_list:
                value_blob = blob[sizesize + name_blob_size : ]
                idx = name_list.index(name)
                fmt = '!' + 'Q' * len(name_list)
                lengths_size = sizesize * len(name_list)
                lengths_list = struct.unpack(fmt, value_blob[:lengths_size])
                if size == 0:
                    return lengths_list[idx]
                pos = lengths_size + sum(lengths_list[:idx])
                value = value_blob[pos:pos + lengths_list[idx]]
                return value
        except obnamlib.Error:
            raise IOError(errno.ENOENT, 'No such file or directory')
        except:
            logging.error('Unexpected exception', exc_info=True)
            raise

    def listxattr(self, path, size):
        tracing.trace('path=%r', path)
        tracing.trace('size=%r', size)
        try:
            metadata = self.get_metadata(path)
            if not metadata.xattr:
                return 0
            blob = metadata.xattr
            sizesize = struct.calcsize('!Q')
            name_blob_size = struct.unpack('!Q', blob[:sizesize])[0]
            if size == 0:
                return name_blob_size
            name_blob = blob[sizesize : sizesize + name_blob_size]
            return name_blob.split('\0')[:-1]
        except obnamlib.Error:
            raise IOError(errno.ENOENT, 'No such file or directory')
        except:
            logging.error('Unexpected exception', exc_info=True)
            raise

    def fsync(self, path, isFsyncFile):
        return 0

    def chmod(self, path, mode):
        raise IOError(errno.EROFS, 'Read only filesystem')

    def chown(self, path, uid, gid):
        raise IOError(errno.EROFS, 'Read only filesystem')

    def link(self, targetPath, linkPath):
        raise IOError(errno.EROFS, 'Read only filesystem')

    def mkdir(self, path, mode):
        raise IOError(errno.EROFS, 'Read only filesystem')

    def mknod(self, path, mode, dev):
        raise IOError(errno.EROFS, 'Read only filesystem')

    def rename(self, oldPath, newPath):
        raise IOError(errno.EROFS, 'Read only filesystem')

    def rmdir(self, path):
        raise IOError(errno.EROFS, 'Read only filesystem')

    def symlink(self, targetPath, linkPath):
        raise IOError(errno.EROFS, 'Read only filesystem')

    def truncate(self, path, size):
        raise IOError(errno.EROFS, 'Read only filesystem')

    def unlink(self, path):
        raise IOError(errno.EROFS, 'Read only filesystem')

    def utime(self, path, times):
        raise IOError(errno.EROFS, 'Read only filesystem')

    def write(self, path, buf, offset):
        raise IOError(errno.EROFS, 'Read only filesystem')

    def setxattr(self, path, name, val, flags):
        raise IOError(errno.EROFS, 'Read only filesystem')

    def removexattr(self, path, name):
        raise IOError(errno.EROFS, 'Read only filesystem')


class MountPlugin(obnamlib.ObnamPlugin):

    '''Mount backup repository as a user-space filesystem.

    At the momemnt only a specific generation can be mounted

    '''

    def enable(self):
        mount_group = obnamlib.option_group['mount'] = 'Mounting with FUSE'
        self.app.add_subcommand('mount', self.mount, arg_synopsis='[ROOT]')
        self.app.settings.string_list(
            ['fuse-opt'],
            'options to pass directly to Fuse',
            metavar='FUSE',
            group=mount_group)

    def mount(self, args):
        '''Mount a backup repository as a FUSE filesystem.

        This subcommand allows you to access backups in an Obnam
        backup repository as normal files and directories. Each
        backed up file or directory can be viewed directly, using
        a graphical file manager or command line tools.

        Example: To mount your backup repository:

        mkdir my-fuse
        obnam mount --to my-fuse

        You can then access the backup using commands such as these:

        ls -l my-fuse
        ls -l my-fuse/latest
        diff -u my-fuse/latest/home/liw/README ~/README
        
        You can also restore files by copying them from the
        my-fuse directory:

        cp -a my-fuse/12765/Maildir ~/Maildir.restored

        To un-mount:

        fusermount -u my-fuse

        '''

        if not hasattr(fuse, 'fuse_python_api'):
            raise obnamlib.Error('Failed to load module "fuse", '
                                 'try installing python-fuse')
        self.app.settings.require('repository')
        self.app.settings.require('client-name')
        self.app.settings.require('to')
        self.cwd = os.getcwd()
        self.repo = self.app.open_repository()
        self.repo.open_client(self.app.settings['client-name'])

        logging.debug(
            'FUSE Mounting %s@%s:/ to %s',
            self.app.settings['client-name'],
            self.app.settings['generation'],
            self.app.settings['to'])

        try:
            ObnamFuseOptParse.obnam = self
            fs = ObnamFuse(obnam=self, parser_class=ObnamFuseOptParse)
            fs.flags = 0
            fs.multithreaded = 0
            fs.parse()
            fs.main()
        except fuse.FuseError, e:
            raise obnamlib.Error(repr(e))

        self.repo.fs.close()

    def reopen(self):
        try:
            os.chdir(self.cwd)
        except OSError:
            pass
        self.repo.fs.close()
        self.repo = self.app.open_repository()
        self.repo.open_client(self.app.settings['client-name'])
