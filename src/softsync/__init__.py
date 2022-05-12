from .__main__ import cli
from .scheme import StorageScheme, FileStorageScheme
from .sync import StorageSync, FileFileStorageSync

# register file:// storage scheme and sync as standard
FILE_SCHEME = "file"
StorageScheme.register_scheme(FILE_SCHEME, FileStorageScheme)
StorageSync.register_sync(FILE_SCHEME, FILE_SCHEME, FileFileStorageSync)


def run():
    cli()
