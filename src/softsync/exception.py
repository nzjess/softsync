import typing

if typing.TYPE_CHECKING:
    from softsync.context import SoftSyncContext


class SoftSyncException(Exception):
    pass


class CommandException(SoftSyncException):
    pass


class ContextException(SoftSyncException):
    def __init__(self, message: str, source: "SoftSyncContext" = None):
        super().__init__(message)
        self.__source = source

    @property
    def source(self):
        return self.__source


class ContextCorruptException(ContextException):
    pass
