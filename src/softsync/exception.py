from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from softsync.context import SoftSyncContext, FileEntry


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
    def __init__(self, message: str, conflicts: List["FileEntry"], source: "SoftSyncContext" = None):
        super().__init__(message, source)
        self.__conflicts = conflicts

    @property
    def conflicts(self):
        return self.__conflicts


class StorageSchemeException(SoftSyncException):
    pass
