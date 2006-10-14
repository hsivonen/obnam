class Context:

    def __init__(self):
        self.config = None
        self.cache = None
        self.be = None
        self.map = None
        self.oq = None


def create():
    """Create a new context object"""
    return Context()
