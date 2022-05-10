from .__main__ import cli
from .storage import StorageScheme, FileStorageScheme


# register file:// storage scheme as standard
StorageScheme.register_scheme("file", FileStorageScheme)


def run():
    cli()
