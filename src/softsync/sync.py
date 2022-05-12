from abc import ABC, abstractmethod
from pathlib3x import Path

from typing import TYPE_CHECKING, Type, TypeVar, Tuple, Dict

from softsync.common import Root, Sync
from softsync.exception import SyncException

if TYPE_CHECKING:
    from softsync.context import SoftSyncContext


def sync(src_file: Path, src_ctx: "SoftSyncContext",
         dest_file: Path, dest_ctx: "SoftSyncContext") -> None:
    if dest_ctx.root.scheme.path_exists(dest_file):
        if dest_ctx.root.scheme.path_is_dir(dest_file):
            raise SyncException(f"destination is a directory: {dest_file}")
        if not dest_ctx.options.force:
            raise SyncException(f"destination file exists: {dest_file}")
        if not dest_ctx.options.dry_run:
            dest_ctx.root.scheme.path_delete(dest_file)
    if not dest_ctx.options.dry_run:
        dest_ctx.root.scheme.path_mkdir(dest_file.parent)
        StorageSync.for_schemes(src_ctx.root.scheme.name, dest_ctx.root.scheme.name) \
            .path_sync_to(src_ctx.root, src_file, dest_ctx.root, dest_file, *dest_ctx.options.sync or [])


class StorageSync(ABC):

    S = TypeVar("S", bound="StorageSync")
    __SYNCS: Dict[Tuple[str, str], Type[S]] = {}

    @staticmethod
    def register_sync(source: str, dest: str, cls: Type[S]):
        StorageSync.__SYNCS[(source, dest)] = cls

    @staticmethod
    def for_schemes(source: str, dest: str) -> "StorageSync":
        scheme_class = StorageSync.__SYNCS.get((source, dest), None)
        if scheme_class is None:
            raise SyncException(f"invalid sync: '{source}:{dest}' not supported")
        return scheme_class()

    @abstractmethod
    def path_symlink_to(self, src_root: Root, src_file: Path, dest_root: Root, dest_file: Path) -> None:
        ...

    @abstractmethod
    def path_hardlink_to(self, src_root: Root, src_file: Path, dest_root: Root, dest_file: Path) -> None:
        ...

    @abstractmethod
    def path_copy_to(self, src_root: Root, src_file: Path, dest_root: Root, dest_file: Path) -> None:
        ...

    @abstractmethod
    def path_sync_to(self, src_root: Root, src_file: Path, dest_root: Root, dest_file: Path, *modes: Sync) -> None:
        ...


class FileFileStorageSync(StorageSync):

    __INSTANCE: "FileFileStorageSync" = None

    def __new__(cls):
        if FileFileStorageSync.__INSTANCE is None:
            FileFileStorageSync.__INSTANCE = object.__new__(cls)
        return FileFileStorageSync.__INSTANCE

    def path_symlink_to(self, src_root: Root, src_file: Path, dest_root: Root, dest_file: Path) -> None:
        dest_file.symlink_to(src_file)

    def path_hardlink_to(self, src_root: Root, src_file: Path, dest_root: Root, dest_file: Path) -> None:
        src_file.link_to(dest_file)

    def path_copy_to(self, src_root: Root, src_file: Path, dest_root: Root, dest_file: Path) -> None:
        src_file.copy(dest_file)

    def path_sync_to(self, src_root: Root, src_file: Path, dest_root: Root, dest_file: Path, *modes: Sync) -> None:
        if not modes:
            modes = (Sync.HARDLINK, Sync.COPY)
        for mode in modes:
            if mode == Sync.SYMBOLIC:
                self.path_symlink_to(src_root, src_file, dest_root, dest_file)
                return
            if mode == Sync.HARDLINK:
                if src_root.mount == dest_root.mount:
                    self.path_hardlink_to(src_root, src_file, dest_root, dest_file)
                    return
            if mode == Sync.COPY:
                self.path_copy_to(src_root, src_file, dest_root, dest_file)
                return
        raise SyncException(f"failed to sync file: {src_file}")
