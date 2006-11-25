import ConfigParser
import optparse


def default_config():
    """Return a ConfigParser object with the default builtin configuration"""
    items = (
        ("backup", "host-id", "testhost"),
        ("backup", "block-size", "%d" % (64 * 1024)),
        ("backup", "cache", "tmp.cache"),
        ("backup", "store", "tmp.store"),
        ("backup", "ssh-key", "ssh-key"),
        ("backup", "target-dir", "."),
        ("backup", "object-cache-size", "0"),
        ("backup", "log-level", "warning"),
    )
    
    config = ConfigParser.RawConfigParser()
    for section, item, value in items:
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
    
    parser.add_option("--log-level",
                      metavar="LEVEL",
                      help="set log level to LEVEL, one of debug, info, " +
                           "warning, error, critical (default is warning)")
    
    parser.add_option("--ssh-key",
                      metavar="FILE",
                      help="read ssh private key from FILE (and public key " +
                           "from FILE.pub)")

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
    if options.log_level:
        config.set("backup", "log-level", options.log_level)
    if options.ssh_key:
        config.set("backup", "ssh-key", options.ssh_key)

    return args
