import pluginmgr

class Hello(pluginmgr.Plugin):

    def __init__(self, foo, bar=None):
        self.foo = foo
        self.bar = bar

    @property
    def version(self):
        return '0.0.1'
