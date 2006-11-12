class ExceptionBase(Exception):

    def __str__(self):
        return self._msg


