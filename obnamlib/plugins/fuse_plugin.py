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

    def __init__(self, path, flags, *mode):
        tracing.trace('path=%r', path)
        tracing.trace('flags=%r', flags)
        tracing.trace('mode=%r', mode)

        if ((flags & os.O_WRONLY) or (flags & os.O_RDWR) or
            (flags & os.O_CREAT) or (flags & os.O_EXCL) or
            (flags & os.O_TRUNC) or (flags & os.O_APPEND)):
            raise IOError(errno.EROFS, 'Read only filesystem')

        self.path = path

        if path == '/.pid' and self.fs.obnam.app.settings['viewmode'] == 'multiple':
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
        
        self.chunkids = None
        self.chunksize = None
        self.lastdata = None
        self.lastblock = None

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

        try:
            if length == 0 or offset >= self.metadata.st_size:
                return ''

            repo = self.fs.obnam.repo
            gen, repopath = self.fs.get_gen_path(self.path)

            # if stored inside B-tree
            contents = repo.get_file_data(gen, repopath)
            if contents is not None:
                return contents[offset:offset+length]

            # stored in chunks
            if not self.chunkids:
                self.chunkids = repo.get_file_chunks(gen, repopath)

            if len(self.chunkids) == 1:
                if not self.lastdata:
                    self.lastdata = repo.get_chunk(self.chunkids[0])
                return self.lastdata[offset:offset+length]
            else:
                chunkdata = None
                if not self.chunksize:
                    # take the cached value as the first guess for chunksize
                    self.chunksize = self.fs.sizecache.get(gen, self.fs.chunksize)
                    blocknum = offset/self.chunksize
                    blockoffs = offset - blocknum*self.chunksize

                    # read a chunk if guessed blocknum and chunksize make sense
                    if blocknum < len(self.chunkids):
                        chunkdata = repo.get_chunk(self.chunkids[blocknum])
                    else:
                        chunkdata = ''

                    # check if chunkdata is of expected length
                    validate = min(self.chunksize, self.metadata.st_size - blocknum*self.chunksize)
                    if validate != len(chunkdata):
                        if blocknum < len(self.chunkids)-1:
                            # the length of all but last chunks is chunksize
                            self.chunksize = len(chunkdata)
                        else:
                            # guessing failed, get the length of the first chunk
                            self.chunksize = len(repo.get_chunk(self.chunkids[0]))
                        chunkdata = None

                    # save correct chunksize
                    self.fs.sizecache[gen] = self.chunksize

                if not chunkdata:
                    blocknum = offset/self.chunksize
                    blockoffs = offset - blocknum*self.chunksize
                    if self.lastblock == blocknum:
                        chunkdata = self.lastdata
                    else:
                        chunkdata = repo.get_chunk(self.chunkids[blocknum])

                output = []
                while True:
                    output.append(chunkdata[blockoffs:blockoffs+length])
                    readlength = len(chunkdata) - blockoffs
                    if length > readlength and blocknum < len(self.chunkids)-1:
                        length -= readlength
                        blocknum += 1
                        blockoffs = 0
                        chunkdata = repo.get_chunk(self.chunkids[blocknum])
                    else:
                        self.lastblock = blocknum
                        self.lastdata = chunkdata
                        break
                return ''.join(output)
        except (OSError, IOError), e:
            tracing.trace('expected exception: %r', e)
            raise
        except:
            logging.exception('Unexpected exception')
            raise

    def release(self, flags):
        tracing.trace('flags=%r', flags)
        self.lastdata = None
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
    '''FUSE main class

    '''

    MAX_METADATA_CACHE = 512

    def root_refresh(self):
        tracing.trace('called')
        if self.obnam.app.settings['viewmode'] == 'multiple':
            try:
                self.obnam.reopen()
                repo = self.obnam.repo
                generations = [gen for gen in repo.list_generations()
                                if not repo.get_is_checkpoint(gen)]
                tracing.trace('found %d generations', len(generations))
                self.rootstat, self.rootlist = self.multiple_root_list(generations)
                self.metadatacache.clear()
            except:
                logging.exception('Unexpected exception')
                raise

    def get_metadata(self, path):
        tracing.trace('path=%r', path)
        try:
            return self.metadatacache[path]
        except KeyError:
            if len(self.metadatacache) > self.MAX_METADATA_CACHE:
                self.metadatacache.clear()
            metadata = self.obnam.repo.get_metadata(*self.get_gen_path(path))
            self.metadatacache[path] = metadata
            # FUSE does not allow negative timestamps, truncate to zero
            if metadata.st_atime_sec < 0:
                metadata.st_atime_sec = 0
            if metadata.st_mtime_sec < 0:
                metadata.st_mtime_sec = 0
            return metadata

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

    def single_root_list(self, gen):
        repo = self.obnam.repo
        mountroot = self.obnam.mountroot
        rootlist = {}
        for entry in repo.listdir(gen, mountroot):
            path = '/' + entry
            rootlist[path] = self.get_stat(path)
        rootstat = self.get_stat('/')
        return (rootstat, rootlist)

    def multiple_root_list(self, generations):
        repo = self.obnam.repo
        mountroot = self.obnam.mountroot
        rootlist = {}
        used_generations = []
        for gen in generations:
            path = '/' + str(gen)
            try:
                genstat = self.get_stat(path)
                start, end = repo.get_generation_times(gen)
                genstat.st_ctime = genstat.st_mtime = end
                rootlist[path] = genstat
                used_generations.append(gen)
            except obnamlib.Error:
                pass

        if not used_generations:
            raise obnamlib.Error('No generations found for %s' % mountroot)

        latest = used_generations[-1]
        laststat = rootlist['/' + str(latest)]
        rootstat = fuse.Stat(**laststat.__dict__)

        laststat = fuse.Stat(target=str(latest), **laststat.__dict__)
        laststat.st_mode &= ~(stat.S_IFDIR | stat.S_IFREG)
        laststat.st_mode |= stat.S_IFLNK
        rootlist['/latest'] = laststat

        pidstat = fuse.Stat(**rootstat.__dict__)
        pidstat.st_mode = stat.S_IFREG | stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
        rootlist['/.pid'] = pidstat

        return (rootstat, rootlist)

    def init_root(self):
        repo = self.obnam.repo
        mountroot = self.obnam.mountroot
        generations = self.obnam.app.settings['generation']

        if self.obnam.app.settings['viewmode'] == 'single':
            if len(generations) != 1:
                raise obnamlib.Error(
                    'The single mode wants exactly one generation option')

            gen = repo.genspec(generations[0])
            if mountroot == '/':
                self.get_gen_path = lambda path: (gen, path)
            else:
                self.get_gen_path = (lambda path : path == '/'
                                        and (gen, mountroot)
                                        or (gen, mountroot + path))

            self.rootstat, self.rootlist = self.single_root_list(gen)
            tracing.trace('single rootlist=%r', self.rootlist)
        elif self.obnam.app.settings['viewmode'] == 'multiple':
            # we need the list of all real (non-checkpoint) generations
            if len(generations) == 1:
                generations = [gen for gen in repo.list_generations()
                               if not repo.get_is_checkpoint(gen)]

            if mountroot == '/':
                def gen_path_0(path):
                    if path.count('/') == 1:
                        gen = path[1:]
                        return (int(gen), mountroot)
                    else:
                        gen, repopath = path[1:].split('/', 1)
                        return (int(gen), mountroot + repopath)
                self.get_gen_path = gen_path_0
            else:
                def gen_path_n(path):
                    if path.count('/') == 1:
                        gen = path[1:]
                        return (int(gen), mountroot)
                    else:
                        gen, repopath = path[1:].split('/', 1)
                        return (int(gen), mountroot + '/' + repopath)
                self.get_gen_path = gen_path_n

            self.rootstat, self.rootlist = self.multiple_root_list(generations)
            tracing.trace('multiple rootlist=%r', self.rootlist)
        else:
            raise obnamlib.Error('Unknown value for viewmode')

    def __init__(self, *args, **kw):
        self.obnam = kw['obnam']
        ObnamFuseFile.fs = self
        self.file_class = ObnamFuseFile
        self.metadatacache = {}
        self.chunksize = self.obnam.app.settings['chunk-size']
        self.sizecache = {}
        self.rootlist = None
        self.rootstat = None
        self.init_root()
        fuse.Fuse.__init__(self, *args, **kw)

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
            if self.obnam.app.settings['viewmode'] == 'multiple':
                blocks = sum(repo.client.get_generation_data(gen)
                            for gen in repo.list_generations())
                files = sum(repo.client.get_generation_file_count(gen)
                            for gen in repo.list_generations())
            else:
                gen = self.get_gen_path('/')[0]
                blocks = repo.client.get_generation_data(gen)
                files = repo.client.get_generation_file_count(gen)
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
        self.app.add_subcommand('mount', self.mount,
                                arg_synopsis='[ROOT]')
        self.app.settings.choice(['viewmode'],
                                 ['single', 'multiple'],
                                 '"single" directly mount specified generation, '
                                 '"multiple" mount all generations as separate directories',
                                 metavar='MODE',
                                 group=mount_group)
        self.app.settings.string_list(['fuse-opt'],
                                      'options to pass directly to Fuse',
                                      metavar='FUSE', group=mount_group)

    def mount(self, args):
        '''Mount a backup repository as a FUSE filesystem.

        This subcommand allows you to access backups in an Obnam
        backup repository as normal files and directories. Each
        backed up file or directory can be viewed directly, using
        a graphical file manager or command line tools.

        Example: To mount your backup repository:

        mkdir my-fuse
        obnam mount --viewmode multiple --to my-fuse

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

        self.mountroot = (['/'] + self.app.settings['root'] + args)[-1]
        if self.mountroot != '/':
            self.mountroot = self.mountroot.rstrip('/')

        logging.debug(
            'FUSE Mounting %s@%s:%s to %s',
            self.app.settings['client-name'],
            self.app.settings['generation'],
            self.mountroot, self.app.settings['to'])

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
