# Copyright 2011  Lars Wirzenius
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
import shutil
import subprocess
import tempfile


def generate_symmetric_key(numbits, filename='/dev/random'):
    '''Generate a random key of at least numbits for symmetric encryption.'''
    
    bytes = (numbits + 7) / 8
    f = open(filename, 'rb')
    key = f.read(bytes)
    f.close()
    
    # Passphrase should not contain newlines. Hex encode?
    
    return key
    
    
def _gpg_pipe(args, data, passphrase):
    '''Pipe things through gpg.
    
    With the right args, this can be either an encryption or a decryption
    operation.
    
    For safety, we give the passphrase to gpg via a file descriptor.
    The argument list is modified to include the relevant options for that.
    
    The data is fed to gpg via a temporary file, readable only by
    the owner, to avoid congested pipes.
    
    '''
    
    # Open pipe for passphrase, and write it there. If passphrase is
    # very long (more than 4 KiB by default), this might block. A better
    # implementation would be to have a loop around select(2) to do pipe
    # I/O when it can be done without blocking. Patches most welcome.

    keypipe = os.pipe()
    os.write(keypipe[1], passphrase + '\n')
    os.close(keypipe[1])
    
    # Write the data to temporary file. Remove its name at once, so that
    # if we crash, it gets removed automatically by the kernel.
    
    datafd, dataname = tempfile.mkstemp()
    os.remove(dataname)
    os.write(datafd, data)
    os.lseek(datafd, 0, 0)
    
    # Actually run gpg.
    
    argv = ['gpg', '--passphrase-fd', str(keypipe[0]), '-q', '--batch'] + args
    p = subprocess.Popen(argv, stdin=datafd, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    out, err = p.communicate()
    
    os.close(keypipe[0])
    os.close(datafd)
    
    # Return output data, or deal with errors.
    if p.returncode: # pragma: no cover
        raise Exception(err)
        
    return out
    
    
def encrypt_with_symmetric_key(cleartext, key):
    '''Encrypt data with symmetric encryption.'''
    return _gpg_pipe(['-c'], cleartext, key)
    
    
def decrypt_with_symmetric_key(encrypted, key):
    '''Decrypt encrypted data with symmetric encryption.'''
    return _gpg_pipe(['-d'], encrypted, key)


def _gpg(args, stdin='', gpghome=None):
    '''Run gpg and return its output.'''
    
    env = dict()
    env.update(os.environ)
    if gpghome is not None:
        env['GNUPGHOME'] = gpghome
    
    argv = ['gpg', '-q', '--no-tty', '--batch'] + args
    p = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, env=env)
    out, err = p.communicate(stdin)
    
    # Return output data, or deal with errors.
    if p.returncode: # pragma: no cover
        raise Exception(err)
        
    return out


def get_public_key(keyid, gpghome=None):
    '''Return the ASCII armored export form of a given public key.'''
    return _gpg(['--export', '--armor', keyid], gpghome=gpghome)



class Keyring(object):

    '''A simplistic representation of GnuPG keyrings.
    
    Just enough functionality for obnam's purposes.
    
    '''
    
    def __init__(self, encoded=''):
        self._encoded = encoded
        self._gpghome = None
        self._keyids = None
        
    def _setup(self):
        self._gpghome = tempfile.mkdtemp()
        f = open(self._pubring, 'wb')
        f.write(self._encoded)
        f.close()
        
    def _cleanup(self):
        shutil.rmtree(self._gpghome)
        self._gpghome = None
        
    @property
    def _pubring(self):
        return os.path.join(self._gpghome, 'pubring.gpg')
        
    def _real_keyids(self):
        self._setup()
        output = _gpg(['--list-keys', '--with-colons'], gpghome=self._gpghome)
        self._cleanup()
        
        keyids = []
        for line in output.splitlines():
            fields = line.split(':')
            if len(fields) >= 5 and fields[0] == 'pub':
                keyids.append(fields[4])
        return keyids
        
    def keyids(self):
        if self._keyids is None:
            self._keyids = self._real_keyids()
        return self._keyids
        
    def __str__(self):
        return self._encoded
        
    def __contains__(self, keyid):
        return keyid in self.keyids()
        
    def _reread_pubring(self):
        f = open(self._pubring, 'rb')
        self._encoded = f.read()
        f.close()
        self._keyids = None
        
    def add(self, key):
        self._setup()
        _gpg(['--import'], stdin=key, gpghome=self._gpghome)
        self._reread_pubring()
        self._cleanup()
        
    def remove(self, keyid):
        self._setup()
        _gpg(['--delete-key', '--yes', keyid], gpghome=self._gpghome)
        self._reread_pubring()
        self._cleanup()

