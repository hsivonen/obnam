import ConfigParser


def default_config():
    """Return a ConfigParser object with the default builtin configuration"""
    items = (
        ("wibbr", "host-id", "testhost"),
        ("wibbr", "block-size", "%d" % (64 * 1024)),
        ("wibbr", "cache-dir", "tmp.cachedir"),
        ("wibbr", "local-store", "tmp.local-store"),
        ("wibbr", "restore-target", "tmp.restore"),
    )
    
    config = ConfigParser.RawConfigParser()
    for section, item, value in items:
        if not config.has_section(section):
            config.add_section(section)
        config.set(section, item, value)
    
    return config
