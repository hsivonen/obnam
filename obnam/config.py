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


"""Obnam configuration and option handling"""


import ConfigParser
import optparse

import obnam.defaultconfig


def default_config():
    """Return a ConfigParser object with the default builtin configuration"""
    config = ConfigParser.RawConfigParser()
    for section, item, value in obnam.defaultconfig.items:
        if not config.has_section(section):
            config.add_section(section)
        config.set(section, item, value)
    
    return config


def parse_options(config, argv):
    """Parse command line arguments and set config values accordingly"""
    parser = optparse.OptionParser()
    
    parser.add_option("--block-size",
                      type="int",
                      metavar="SIZE",
                      help="make blocks that are about SIZE kilobytes")
    
    parser.add_option("--cache",
                      metavar="DIR",
                      help="store cached blocks in DIR")
    
    parser.add_option("--store",
                      metavar="DIR",
                      help="use DIR for local block storage (not caching)")
    
    parser.add_option("--target", "-C",
                      metavar="DIR",
                      help="resolve filenames relative to DIR")
    
    parser.add_option("--object-cache-size",
                      metavar="COUNT",
                      help="set object cache maximum size to COUNT objects" +
                           " (default depends on block size")
    
    parser.add_option("--log-file",
                      metavar="FILE",
                      help="append log messages to FILE")
    
    parser.add_option("--log-level",
                      metavar="LEVEL",
                      help="set log level to LEVEL, one of debug, info, " +
                           "warning, error, critical (default is warning)")
    
    parser.add_option("--ssh-key",
                      metavar="FILE",
                      help="read ssh private key from FILE (and public key " +
                           "from FILE.pub)")
    
    parser.add_option("--odirect-read",
                      metavar="PROGRAM",
                      help="use PROGRAM to read contents of plain files " +
                           "(default is helper that avoids buffer cache)")
    
    parser.add_option("--gpg-home",
                      metavar="DIR",
                      help="use DIR as the location for GnuPG keyrings and " +
                           "other data files")
    
    parser.add_option("--gpg-encrypt-to",
                      metavar="KEYID", 
                      action="append",
                      help="add KEYID to list of keys to use for encryption")
    
    parser.add_option("--gpg-sign-with",
                      metavar="KEYID",
                      help="sign backups with KEYID")
    
    parser.add_option("--no-gpg", action="store_true", default=False,
                      help="don't use gpg at all")
    
    parser.add_option("--use-psyco",
                      action="store_true", default=False,
                      help="use the psyco Python extension, if available")

    (options, args) = parser.parse_args(argv)
    
    if options.block_size:
        config.set("backup", "block-size", "%d" % options.block_size)
    if options.cache:
        config.set("backup", "cache", options.cache)
    if options.store:
        config.set("backup", "store", options.store)
    if options.target:
        config.set("backup", "target-dir", options.target)
    if options.object_cache_size:
        config.set("backup", "object-cache-size", options.object_cache_size)
    if options.log_file:
        config.set("backup", "log-file", options.log_file)
    if options.log_level:
        config.set("backup", "log-level", options.log_level)
    if options.ssh_key:
        config.set("backup", "ssh-key", options.ssh_key)
    if options.odirect_read:
        config.set("backup", "odirect-read", options.odirect_read)
    if options.gpg_home:
        config.set("backup", "gpg-home", options.gpg_home)
    if options.gpg_encrypt_to:
        config.set("backup", "gpg-encrypt-to", 
                   " ".join(options.gpg_encrypt_to))
    if options.gpg_sign_with:
        config.set("backup", "gpg-sign-with", options.gpg_sign_with)
    if options.no_gpg:
        config.set("backup", "no-gpg", "true")
    if options.use_psyco:
        try:
            import psyco
            psyco.profile()
        except ImportError:
            pass

    return args
