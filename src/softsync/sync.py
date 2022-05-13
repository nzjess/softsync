from abc import ABC, abstractmethod
from pathlib3x import Path
from tempfile import mkdtemp
from typing import TYPE_CHECKING, Type, TypeVar, Dict, Union, Tuple

from softsync.common import FILE_SCHEME, Root, Sync
from softsync.exception import SyncException

if TYPE_CHECKING:
    from softsync.context import SoftSyncContext


def sync(src_file: Path, src_ctx: "SoftSyncContext",
         dest_file: Path, dest_ctx: "SoftSyncContext") -> None:
    if dest_ctx.root.scheme.exists(dest_file):
        if dest_ctx.root.scheme.is_dir(dest_file):
            raise SyncException(f"destination is a directory: {dest_file}")
        if not dest_ctx.options.force:
            raise SyncException(f"destination file exists: {dest_file}")
        if not dest_ctx.options.dry_run:
            dest_ctx.root.scheme.delete(dest_file)
    if not dest_ctx.options.dry_run:
        dest_ctx.root.scheme.mkdir(dest_file.parent)
        StorageSync.for_schemes(src_ctx.root.scheme.name, dest_ctx.root.scheme.name) \
            .sync(src_ctx.root, src_file, dest_ctx.root, dest_file, *dest_ctx.options.sync or [])


class StorageSync(ABC):

    S = TypeVar("S", bound="StorageSync")
    __SYNC_TYPES: Dict[Union[Tuple[str, str], Tuple[str, str, str]], Type[S]] = {}
    __SYNC_INSTANCES: Dict[Tuple[str, str], "StorageSync"] = {}

    @staticmethod
    def register_sync(src_scheme: str, dest_scheme: str, cls: Type[S]):
        StorageSync.__SYNC_TYPES[(src_scheme, dest_scheme)] = cls

    @staticmethod
    def register_via_file_sync(src_scheme: str, dest_scheme: str, cls: Type[S]):
        StorageSync.__SYNC_TYPES[(src_scheme, FILE_SCHEME, dest_scheme)] = cls

    @staticmethod
    def for_schemes(src_scheme: str, dest_scheme: str) -> "StorageSync":
        scheme_key = (src_scheme, dest_scheme)
        sync_instance = StorageSync.__SYNC_INSTANCES.get(scheme_key, None)
        if sync_instance is not None:
            return sync_instance
        sync_class = StorageSync.__SYNC_TYPES.get(scheme_key, None)
        if sync_class is None:
            via_file_scheme_key = (src_scheme, FILE_SCHEME, dest_scheme)
            sync_class = StorageSync.__SYNC_TYPES.get(via_file_scheme_key, None)
        if sync_class is not None:
            sync_instance = sync_class(src_scheme, dest_scheme)
            StorageSync.__SYNC_INSTANCES[scheme_key] = sync_instance
            return sync_instance
        raise SyncException(f"invalid sync: '{src_scheme}:{dest_scheme}' not supported")

    @abstractmethod
    def symlink(self, src_root: Root, src_file: Path, dest_root: Root, dest_file: Path) -> None:
        ...

    @abstractmethod
    def hardlink(self, src_root: Root, src_file: Path, dest_root: Root, dest_file: Path) -> None:
        ...

    @abstractmethod
    def copy(self, src_root: Root, src_file: Path, dest_root: Root, dest_file: Path) -> None:
        ...

    @abstractmethod
    def sync(self, src_root: Root, src_file: Path, dest_root: Root, dest_file: Path, *modes: Sync) -> None:
        ...


class FileFileStorageSync(StorageSync):

    __INSTANCE: "FileFileStorageSync" = None

    def __new__(cls, src_scheme: str, dest_scheme: str):
        if FileFileStorageSync.__INSTANCE is None:
            FileFileStorageSync.__INSTANCE = object.__new__(cls)
        return FileFileStorageSync.__INSTANCE

    def __init__(self, src_scheme: str, dest_scheme: str):
        pass

    def symlink(self, src_root: Root, src_file: Path, dest_root: Root, dest_file: Path) -> None:
        dest_file.symlink_to(src_file)

    def hardlink(self, src_root: Root, src_file: Path, dest_root: Root, dest_file: Path) -> None:
        src_file.link_to(dest_file)

    def copy(self, src_root: Root, src_file: Path, dest_root: Root, dest_file: Path) -> None:
        src_file.copy(dest_file)

    def sync(self, src_root: Root, src_file: Path, dest_root: Root, dest_file: Path, *modes: Sync) -> None:
        if not modes:
            modes = (Sync.HARDLINK, Sync.COPY)
        for mode in modes:
            if mode == Sync.SYMBOLIC:
                self.symlink(src_root, src_file, dest_root, dest_file)
                return
            if mode == Sync.HARDLINK:
                if src_root.mount == dest_root.mount:
                    self.hardlink(src_root, src_file, dest_root, dest_file)
                    return
            if mode == Sync.COPY:
                self.copy(src_root, src_file, dest_root, dest_file)
                return
        raise SyncException(f"failed to sync file: {src_file}")


class ViaFileStorageSync(StorageSync):

    ___tmp_file_root: Root = None

    @staticmethod
    def __get_tmp_file_root() -> Root:
        if ViaFileStorageSync.___tmp_file_root is None:
            ViaFileStorageSync.___tmp_file_root = Root(mkdtemp())
        return ViaFileStorageSync.___tmp_file_root

    def __init__(self, src_scheme: str, dest_scheme: str):
        self.__src_sync = StorageSync.for_schemes(src_scheme, FILE_SCHEME)
        self.__dest_sync = StorageSync.for_schemes(FILE_SCHEME, dest_scheme)

    def symlink(self, src_root: Root, src_file: Path, dest_root: Root, dest_file: Path) -> None:
        raise NotImplementedError()

    def hardlink(self, src_root: Root, src_file: Path, dest_root: Root, dest_file: Path) -> None:
        raise NotImplementedError()

    def copy(self, src_root: Root, src_file: Path, dest_root: Root, dest_file: Path) -> None:
        tmp_file_root = ViaFileStorageSync.__get_tmp_file_root()
        tmp_file = tmp_file_root.path.joinpath(dest_file.name)
        try:
            self.__src_sync.copy(src_root, src_file, tmp_file_root, tmp_file)
            self.__dest_sync.copy(tmp_file_root, tmp_file, dest_root, dest_file)
        finally:
            tmp_file_root.scheme.delete(tmp_file)

    def sync(self, src_root: Root, src_file: Path, dest_root: Root, dest_file: Path, *modes: Sync) -> None:
        if not modes or Sync.COPY in modes:
            self.copy(src_root, src_file, dest_root, dest_file)
            return
        raise SyncException(f"failed to sync file: {src_file}")
