from enum import Enum
from pathlib3x import Path
from urllib.parse import urlparse

from typing import Optional, List

from softsync.scheme import StorageScheme
from softsync.exception import SoftSyncException, CommandException


class Sync(Enum):

    SYMBOLIC = 1
    HARDLINK = 2
    COPY = 3

    @staticmethod
    def as_list(sync: str, delim: str = ","):
        return [Sync[name.strip().upper()] for name in sync.split(delim)] \
            if sync else []


class Options:

    def __init__(self,
                 force: bool = False,
                 recursive: bool = False,
                 reconstruct: bool = False,
                 sync: List[Sync] = None,
                 verbose: bool = False,
                 dry_run: bool = False,
                 ):
        self.__force = force
        self.__recursive = recursive
        self.__reconstruct = reconstruct
        self.__sync = sync
        self.__verbose = verbose
        self.__dry_run = dry_run

        # TODO add support for recursive option
        if self.recursive:
            raise CommandException("recursive option not implemented, yet")

    @property
    def force(self) -> bool:
        return self.__force

    @property
    def recursive(self) -> bool:
        return self.__recursive

    @property
    def sync(self) -> List[Sync]:
        return self.__sync

    @property
    def reconstruct(self) -> bool:
        return self.__reconstruct

    @property
    def verbose(self) -> bool:
        return self.__verbose

    @property
    def dry_run(self) -> bool:
        return self.__dry_run

    def __repr__(self):
        return f"force: {self.force}\n" \
               f"recursive: {self.recursive}\n" \
               f"reconstruct: {self.reconstruct}\n" \
               f"sync: {self.sync}\n" \
               f"verbose: {self.verbose}\n" \
               f"dry_run: {self.dry_run}"


class Root:

    def __init__(self, spec: str):
        if spec.find("://") == -1:
            spec = f"file://{spec}"
        try:
            url = urlparse(spec)
            self.__scheme = StorageScheme.for_url(url)
            self.__mount, self.__path, self.__location = self.__scheme.resolve_root(url)
            if self.__scheme.exists(self.__path) and (
                    self.__scheme.is_file(self.__path) or not self.__scheme.is_dir(self.__path)):
                raise SoftSyncException(f"invalid root: {self.__path} is not a directory")
        except SoftSyncException:
            raise
        except Exception as e:
            raise SoftSyncException(f"failed to create root: {e}")

    def __str__(self):
        return f"{self.scheme.name}://{self.__location}"

    def __eq__(self, other):
        return self.__class__ == other.__class__ and \
               self.scheme.name == other.scheme.name and \
               self.mount == other.mount and \
               self.path == other.path

    def __ne__(self, other):
        return not self == other

    @property
    def scheme(self) -> StorageScheme:
        return self.__scheme

    @property
    def mount(self) -> str:
        return self.__mount

    @property
    def path(self) -> Path:
        return self.__path


def parse_roots(roots: str) -> (Root, Optional[Root]):
    roots = roots.strip()
    if not roots:
        raise CommandException("invalid root, empty")
    if roots.find("*") >= 0 or roots.find("?") >= 0:
        raise CommandException("invalid root, invalid chars")
    roots = roots.replace("://", "*")
    roots = roots.replace(":\\", "?")
    roots = roots.split(":")
    if len(roots) > 2:
        raise CommandException("invalid roots: expected 1 or 2 components")
    roots = [r.replace("*", "://") for r in roots]
    roots = [r.replace("?", ":\\") for r in roots]
    src_root = Root(roots[0])
    dest_root = None
    if len(roots) == 2:
        dest_root = Root(roots[1])
    return src_root, dest_root


def split_path(root: Root, path: Path) -> (Path, Optional[str]):
    if path.is_absolute():
        raise CommandException(f"invalid path: {path} cannot be absolute")
    if len(path.parts) == 0:
        return path, None
    for i, part in enumerate(path.parts):
        if part == "..":
            raise CommandException(f"invalid path: {path} cannot contain relative components")
        if i < len(path.parts) - 1:
            if is_glob_pattern(part):
                raise CommandException(f"invalid path: {path} cannot contain glob pattern in parent path")
    full_path = root.path / path
    if root.scheme.exists(full_path):
        if root.scheme.is_dir(full_path):
            return path, None
        else:
            return path.parent, path.name
    if is_glob_pattern(path.name) or path.suffix != "":  # heuristic
        return path.parent, path.name
    return path, None


def resolve_path(path: Path) -> Path:
    resolved = []
    for part in path.parts:
        if part == "..":
            resolved.pop()
        else:
            resolved.append(part)
    return Path(*resolved)


def check_paths_are_disjoint(path1: Path, path2: Path) -> bool:
    return not path1.is_relative_to(path2) and \
           not path2.is_relative_to(path1)


def is_glob_pattern(name: str) -> bool:
    return name.find("*") != -1 or \
           name.find("?") != -1
