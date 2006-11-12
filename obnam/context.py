import obnam.config
import obnam.mapping
import obnam.obj


class Context:

    def __init__(self):
        self.config = obnam.config.default_config()
        self.cache = None
        self.be = None
        self.map = obnam.mapping.create()
        self.contmap = obnam.mapping.create()
        self.oq = obnam.obj.object_queue_create()
        self.content_oq = obnam.obj.object_queue_create()


def create():
    """Create a new context object"""
    return Context()
