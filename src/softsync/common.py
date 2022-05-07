from pathlib3x import Path
from urllib.parse import urlparse

from typing import Optional, Union, Tuple

from softsync.storage import StorageScheme
from softsync.exception import SoftSyncException, CommandException


class Options:
    def __init__(self,
                 force: bool = False,
                 recursive: bool = False,
                 symbolic: bool = False,
                 verbose: bool = False,
                 dry_run: bool = False):
        self.__force = force
        self.__recursive = recursive
        self.__symbolic = symbolic
        self.__verbose = verbose
        self.__dry_run = dry_run

    @property
    def force(self):
        return self.__force

    @property
    def recursive(self):
        return self.__recursive

    @property
    def symbolic(self):
        return self.__symbolic

    @property
    def verbose(self):
        return self.__verbose

    @property
    def dry_run(self):
        return self.__dry_run

    def __repr__(self):
        return f"force: {self.force}\n" \
               f"recursive: {self.recursive}\n" \
               f"symbolic: {self.symbolic}\n" \
               f"verbose: {self.verbose}\n" \
               f"dry_run: {self.dry_run}"


class Root:
    def __init__(self, spec: str):
        if spec.find("://") == -1:
            spec = f"file://{spec}"
        try:
            url = urlparse(spec)
            if url.params or url.query or url.fragment:
                raise CommandException(f"invalid root: '{spec}': invalid format")
            self.__scheme = StorageScheme.for_name(url.scheme)
            self.__path = self.__scheme.path_resolve(Path(f"{url.netloc}{url.path}"))
            if self.__scheme.path_exists(self.__path) and (
                    self.__scheme.path_is_file(self.__path) or not self.__scheme.path_is_dir(self.__path)):
                raise CommandException(f"invalid root: {self.__path} is not a directory")
        except SoftSyncException:
            raise
        except Exception:
            raise CommandException("invalid root: could not parse")

    def __str__(self):
        return f"{self.__scheme}://{self.__path}"

    def __eq__(self, other):
        return self.__scheme == other.__scheme and \
               self.__path == other.__path

    def __ne__(self, other):
        return not self == other

    @property
    def scheme(self) -> StorageScheme:
        return self.__scheme

    @property
    def path(self) -> Path:
        return self.__path


class Roots:
    def __init__(self, roots: Union[str, Root, Tuple[Root, Root]]):
        if isinstance(roots, str):
            roots = roots.strip()
            if not roots:
                raise CommandException("invalid root, empty")
            if roots.find("*") >= 0 or roots.find("?") >= 0:
                raise CommandException("invalid root, invalid chars")
            roots = roots.replace("://", "*")
            roots = roots.replace(":\\", "?")
            roots = roots.split(":")
            roots = [r.replace("*", "://") for r in roots]
            roots = [r.replace("?", ":\\") for r in roots]
            self.__src = Root(roots[0])
            self.__dest = None
            if len(roots) == 1:
                pass
            elif len(roots) == 2:
                self.__dest = Root(roots[1])
            else:
                raise CommandException("invalid roots: expected 1 or 2 components")
        elif isinstance(roots, Root):
            self.__src = roots
            self.__dest = None
        elif isinstance(roots, tuple):
            if len(roots) == 2:
                self.__src = roots[0]
                self.__dest = roots[1]
            else:
                raise CommandException("invalid roots: expected 2 components")
        else:
            raise ValueError(f"invalid type for roots: {type(roots)}")
        if self.__dest is not None:
            if self.__dest.scheme.name != "file":
                raise CommandException("'dest' root must have 'file://' scheme")
            if self.__src.scheme == self.__dest.scheme:
                if not check_paths_are_disjoint(self.__src.path, self.__dest.path):
                    raise CommandException("'src' and 'dest' roots must be disjoint")

    def __str__(self):
        return f"{self.__src}:{self.__dest}"

    @property
    def src(self) -> Root:
        return self.__src

    @property
    def dest(self) -> Root:
        return self.__dest


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
    if root.scheme.path_exists(full_path):
        if root.scheme.path_is_dir(full_path):
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
