from abc import ABC, abstractmethod
from pathlib3x import Path

from typing import Any, Iterable

from softsync.exception import StorageSchemeException


class StorageScheme(ABC):

    __SCHEMES = {}

    def __init__(self):
        StorageScheme.__SCHEMES[self.name] = self

    @staticmethod
    def for_name(name: str) -> "StorageScheme":
        scheme = StorageScheme.__SCHEMES.get(name, None)
        if scheme is None:
            raise StorageSchemeException(f"invalid scheme: '{name}' not supported")
        return scheme

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def path_resolve(self, path: Path) -> Path:
        ...

    @abstractmethod
    def path_exists(self, path: Path) -> bool:
        ...

    @abstractmethod
    def path_is_dir(self, path: Path) -> bool:
        ...

    @abstractmethod
    def path_is_file(self, path: Path) -> bool:
        ...

    @abstractmethod
    def path_listdir(self, path: Path) -> Iterable[Any]:
        ...

    @abstractmethod
    def path_mkdir(self, path: Path) -> None:
        ...

    @abstractmethod
    def path_open(self, path: Path, mode: str) -> Any:
        ...

    @abstractmethod
    def path_symlink_to(self, source: Path, target: Path) -> None:
        ...

    @abstractmethod
    def path_hardlink_to(self, source: Path, target: Path) -> None:
        ...

    @abstractmethod
    def path_unlink(self, path) -> None:
        ...


class FileStorageScheme(StorageScheme):

    @property
    def name(self) -> str:
        return "file"

    def path_resolve(self, path: Path) -> Path:
        return path.resolve()

    def path_exists(self, path: Path) -> bool:
        return path.exists()

    def path_is_dir(self, path: Path) -> bool:
        return path.is_dir()

    def path_is_file(self, path: Path) -> bool:
        return path.is_file()

    def path_listdir(self, path: Path) -> Iterable[Any]:
        return path.iterdir()

    def path_mkdir(self, path: Path) -> None:
        return path.mkdir(exist_ok=True)

    def path_open(self, path: Path, mode: str) -> Any:
        return path.open(mode=mode)

    def path_symlink_to(self, source: Path, target: Path) -> None:
        target.symlink_to(source)

    def path_hardlink_to(self, source: Path, target: Path) -> None:
        source.link_to(target)

    def path_unlink(self, path) -> None:
        path.unlink()
