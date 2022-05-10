from abc import ABC, abstractmethod
from collections import namedtuple

from pathlib3x import Path

from typing import Dict, Any, Iterable, Type, TypeVar

from softsync.exception import StorageSchemeException


class StorageScheme(ABC):

    S = TypeVar("S", bound="StorageScheme")
    __SCHEMES: Dict[str, Type[S]] = {}

    @staticmethod
    def register_scheme(scheme_name: str, cls: Type[S]):
        StorageScheme.__SCHEMES[scheme_name] = cls

    @staticmethod
    def for_url(url: namedtuple) -> "StorageScheme":
        scheme_class = StorageScheme.__SCHEMES.get(url.scheme, None)
        if scheme_class is None:
            raise StorageSchemeException(f"invalid scheme: '{url.scheme}' not supported")
        return scheme_class(url)

    def __init__(self, url: namedtuple):
        self.__name = url.scheme

    def __str__(self):
        return self.name

    @property
    def name(self):
        return self.__name

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

    __INSTANCE = None

    def __new__(cls, url: namedtuple):
        if url.params or url.query or url.fragment:
            raise StorageSchemeException(f"invalid root, failed to parse: {url}")
        if FileStorageScheme.__INSTANCE is None:
            FileStorageScheme.__INSTANCE = object.__new__(cls)
        return FileStorageScheme.__INSTANCE

    def __init__(self, url: namedtuple):
        super().__init__(url)

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
