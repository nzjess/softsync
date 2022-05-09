from .__main__ import cli
from .storage import FileStorageScheme


# register file:// storage scheme as standard
FileStorageScheme()


def run():
    cli()
