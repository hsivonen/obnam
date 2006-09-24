"""Wibbr - a backup program"""


import ConfigParser
import optparse
import subprocess


def default_config():
    """Return a ConfigParser object with the default builtin configuration"""
    items = (
        ("wibbr", "block-size", "%d" * (64 * 1024)),
        ("wibbr", "cache-dir", "cache-dir"),
        ("wibbr", "local-store", "local-store"),
    )
    
    config = ConfigParser.RawConfigParser()
    for section, item, value in items:
        if not config.has_section(section):
            config.add_section(section)
        config.set(section, item, value)
    
    return config


def parse_args(config, argv):
    parser = optparse.OptionParser()
    
    parser.add_option("--block-size",
                      type="int",
                      metavar="SIZE",
                      help="Make blocks that are about SIZE kilobytes")
    
    parser.add_option("--cache-dir",
                      metavar="DIR",
                      help="Store cached blocks in DIR")
    
    parser.add_option("--local-store",
                      metavar="DIR",
                      help="Use DIR for local block storage (not caching)")

    (options, args) = parser.parse_args(argv)
    
    if options.block_size:
        config.set("wibbr", "block-size", "%d" % options.block_size)
    if options.cache_dir:
        config.set("wibbr", "cache-dir", options.cache_dir)
    if options.local_store:
        config.set("wibbr", "local-store", options.local_store)


def compute_signature(filename):
    """Compute an rsync signature for 'filename'"""
    p = subprocess.Popen(["rdiff", "--", "signature", filename, "-"],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    (stdout, stderr) = p.communicate(None)
    if p.returncode == 0:
        return stdout
    else:
        return False
