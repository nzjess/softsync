from abc import ABC, abstractmethod
from collections import namedtuple
from pathlib3x import Path

from typing import Dict, Generator, Type, TypeVar, ContextManager, IO

from softsync.exception import SchemeException


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
            raise SchemeException(f"invalid scheme: '{url.scheme}' not supported")
        return scheme_class(url)

    def __init__(self, url: namedtuple):
        self.__name = url.scheme

    @property
    def name(self):
        return self.__name

    @abstractmethod
    def resolve_root(self, url: namedtuple) -> (str, Path, str):
        ...

    @abstractmethod
    def exists(self, path: Path) -> bool:
        ...

    @abstractmethod
    def is_dir(self, path: Path) -> bool:
        ...

    @abstractmethod
    def is_file(self, path: Path) -> bool:
        ...

    @abstractmethod
    def list_files(self, path: Path) -> Generator[Path, None, None]:
        ...

    @abstractmethod
    def list_dirs(self, path: Path) -> Generator[Path, None, None]:
        ...

    @abstractmethod
    def mkdir(self, path: Path) -> None:
        ...

    @abstractmethod
    def open(self, path: Path, mode: str) -> ContextManager[IO]:
        ...

    @abstractmethod
    def delete(self, path) -> None:
        ...


class FileStorageScheme(StorageScheme):

    __INSTANCE: "FileStorageScheme" = None

    def __new__(cls, url: namedtuple):
        if url.params or url.query or url.fragment:
            raise SchemeException(f"invalid root, failed to parse: {url}")
        if FileStorageScheme.__INSTANCE is None:
            FileStorageScheme.__INSTANCE = object.__new__(cls)
        return FileStorageScheme.__INSTANCE

    def __init__(self, url: namedtuple):
        super().__init__(url)

    def resolve_root(self, url: namedtuple) -> (str, Path, str):
        path = Path(f"{url.netloc}{url.path}").resolve()
        # TODO resolve mount point
        mount = ""
        # https://www.geeksforgeeks.org/python-os-path-ismount-method/
        # https://stackoverflow.com/questions/4453602/how-to-find-the-mountpoint-a-file-resides-on
        location = str(path)
        return mount, path, location

    def exists(self, path: Path) -> bool:
        return path.exists()

    def is_dir(self, path: Path) -> bool:
        return path.is_dir()

    def is_file(self, path: Path) -> bool:
        return path.is_file()

    def list_files(self, path: Path) -> Generator[Path, None, None]:
        for entry in Path(path).iterdir():
            if entry.is_file():
                yield entry

    def list_dirs(self, path: Path) -> Generator[Path, None, None]:
        for entry in Path(path).iterdir():
            if entry.is_dir():
                yield entry

    def mkdir(self, path: Path) -> None:
        return path.mkdir(exist_ok=True)

    def open(self, path: Path, mode: str) -> ContextManager[IO]:
        return path.open(mode=mode)

    def delete(self, path) -> None:
        path.unlink()
