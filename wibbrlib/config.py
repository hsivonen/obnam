import ConfigParser
import optparse


def default_config():
    """Return a ConfigParser object with the default builtin configuration"""
    items = (
        ("wibbr", "host-id", "testhost"),
        ("wibbr", "block-size", "%d" % (64 * 1024)),
        ("wibbr", "cache-dir", "tmp.cachedir"),
        ("wibbr", "local-store", "tmp.local-store"),
        ("wibbr", "target-dir", "."),
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
                      help="Make blocks that are about SIZE kilobytes")
    
    parser.add_option("--cache",
                      metavar="DIR",
                      help="Store cached blocks in DIR")
    
    parser.add_option("--store",
                      metavar="DIR",
                      help="Use DIR for local block storage (not caching)")
    
    parser.add_option("--target", "-C",
                      metavar="DIR",
                      help="Resolve filenames relative to DIR")

    (options, args) = parser.parse_args(argv)
    
    if options.block_size:
        config.set("wibbr", "block-size", "%d" % options.block_size)
    if options.cache:
        config.set("wibbr", "cache-dir", options.cache)
    if options.store:
        config.set("wibbr", "local-store", options.store)
    if options.target:
        config.set("wibbr", "target-dir", options.target)

    return args
