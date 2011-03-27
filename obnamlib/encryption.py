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
import subprocess
import tempfile


def generate_symmetric_key(numbits):
    '''Generate a random key of at least numbits for symmetric encryption.'''
    
    bytes = (numbits + 7) / 8
    f = open('/dev/random', 'rb')
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

