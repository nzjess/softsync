
class SoftSyncException(Exception):
    pass


class CommandException(SoftSyncException):
    pass


class ContextException(SoftSyncException):
    def __init__(self, message, source=None):
        super().__init__(message)
        self.__source = source

    @property
    def source(self):
        return self.__source


class ContextCorruptException(ContextException):
    pass
