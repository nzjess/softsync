
class SoftSyncException(Exception):
    pass


class CommandException(SoftSyncException):
    pass


class ContextException(SoftSyncException):
    pass


class ContextCorruptException(ContextException):
    pass
