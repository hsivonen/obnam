import obnam.config
import obnam.map
import obnam.obj


class Context:

    def __init__(self):
        self.config = obnam.config.default_config()
        self.cache = None
        self.be = None
        self.map = obnam.map.create()
        self.contmap = obnam.map.create()
        self.oq = obnam.obj.queue_create()
        self.content_oq = obnam.obj.queue_create()


def create():
    """Create a new context object"""
    return Context()
