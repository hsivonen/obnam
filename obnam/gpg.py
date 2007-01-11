# Copyright (C) 2006  Lars Wirzenius <liw@iki.fi>
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


"""GPG stuff for making backups"""


import logging
import os
import subprocess
import tempfile


import obnam


def encrypt(config, data):
    """Encrypt data according to config"""

    logging.debug("Encrypting data with gpg")

    (fd, tempname) = tempfile.mkstemp()
    os.write(fd, data)
    os.close(fd)

    cat = ["cat", tempname]

    gpg = ["gpg", "-q", "--encrypt"]
    gpg += ["--homedir=%s" % config.get("backup", "gpg-home")]
    recipients = config.get("backup", "gpg-encrypt-to").split(" ")
    gpg += ["-r%s" % x for x in recipients]
    signer = config.get("backup", "gpg-sign-with")
    if signer:
        gpg += ["--sign", "-u%s" % signer]

    pids, stdin_fd, stdout_fd = obnam.rsync.start_pipeline(cat, gpg)
    os.close(stdin_fd)
    encrypted = obnam.rsync.read_until_eof(stdout_fd)
    exit = obnam.rsync.wait_pipeline(pids)
    
    os.remove(tempname)
    
    if exit == 0:
        logging.debug("Encryption OK")    
        return encrypted
    else:
        logging.warning("GPG failed to encrypt: exit code %d" % exit)
        return None


def indent_string(str, indent=2):
    """Indent all lines in a string with 'indent' spaces"""
    return "".join([(" " * indent) + x for x in str.split("\n")])


def decrypt(config, data):
    """Decrypt data according to config"""
    
    logging.debug("Decrypting with gpg")

    (fd, tempname) = tempfile.mkstemp()
    os.write(fd, data)
    os.close(fd)

    gpg = ["gpg", "-q", "--decrypt"]
    gpg += ["--homedir=%s" % config.get("backup", "gpg-home")]
    gpg += [tempname]

    p = subprocess.Popen(gpg, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (decrypted, stderr_data) = p.communicate()

    os.remove(tempname)

    if p.returncode == 0:
        logging.debug("Decryption OK")
        return decrypted
    else:
        logging.warning("GPG failed to decrypt: exit code %d" % p.returncode)
        if stderr_data:
            logging.warning("GPG stderr output:\n%s" % 
                            indent_string(stderr_data))
        return None
