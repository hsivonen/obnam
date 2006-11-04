import wibbrlib.config
import wibbrlib.mapping
import wibbrlib.obj


class Context:

    def __init__(self):
        self.config = wibbrlib.config.default_config()
        self.cache = None
        self.be = None
        self.map = wibbrlib.mapping.create()
        self.contmap = wibbrlib.mapping.create()
        self.oq = wibbrlib.obj.object_queue_create()
        self.content_oq = wibbrlib.obj.object_queue_create()


def create():
    """Create a new context object"""
    return Context()
