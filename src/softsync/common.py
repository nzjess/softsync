import os
from pathlib import Path
from urllib.parse import urlparse

from softsync.exception import CommandException


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
            self.__scheme = url.scheme
            self.__path = f"{url.netloc}{url.path}"
            if self.__scheme == "file":
                self.__path = str(Path(self.__path).resolve())
                if os.path.exists(self.__path) and not os.path.isdir(self.__path):
                    raise CommandException(f"invalid root: {self.__path} is not a directory")
        except CommandException:
            raise
        except Exception:
            raise CommandException("invalid root: could not parse")

    def __str__(self):
        return f"{self.__scheme}://{self.__path}"

    def __eq__(self, other):
        return self.__scheme == other.__scheme and \
               self.__path == other.__path

    @property
    def scheme(self) -> str:
        return self.__scheme

    @property
    def path(self) -> str:
        return self.__path


class Roots:
    def __init__(self, roots: str):
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
            if not check_dirs_are_disjoint(self.__src.path, self.__dest.path):
                raise CommandException("invalid roots, 'src' and 'dest' must be disjoint")
        else:
            raise CommandException("invalid root, too many components")
        if self.__src.scheme != "file" or (self.__dest is not None and self.__dest.scheme != "file"):
            raise CommandException("invalid root(s), must have file scheme")

    def __str__(self):
        return f"{self.__src}:{self.__dest}"

    @property
    def src(self) -> Root:
        return self.__src

    @property
    def dest(self) -> Root:
        return self.__dest


def is_file_pattern(name: str) -> bool:
    return name.find("*") != -1 or \
           name.find("?") != -1


def normalise_path(root: str, path: str) -> (str, str):
    path = path.strip()
    if path.startswith(os.sep):
        raise CommandException("invalid path, cannot be absolute")
    if path.startswith("." + os.sep):
        path = path[2:]
    has_trailing_slash = path.endswith(os.sep)
    if has_trailing_slash:
        path = path[:-1]
    if path == ".":
        return path, None
    components = path.split(os.sep)
    for i, component in enumerate(components):
        if component == "." or component == "..":
            raise CommandException("invalid path, cannot contain relative components")
        if has_trailing_slash or i < len(components) - 1:
            if is_file_pattern(component):
                raise CommandException("invalid path, invalid matching patterns")
    split = path.rsplit(os.sep, 1)
    full_path = os.path.join(root, path)
    if os.path.exists(full_path):
        if os.path.isdir(full_path):
            return path, None
        elif has_trailing_slash:
            raise CommandException("invalid path, directory path cannot point to a file")
        else:
            if len(split) == 1:
                return ".", path
            else:
                return split[0], split[1]
    if has_trailing_slash:
        return path, None
    rsplit = path if len(split) == 1 else split[1]
    if is_file_pattern(rsplit) or rsplit.find(".") != -1:  # heuristic
        if len(split) == 1:
            return ".", path
        else:
            return split[0], split[1]
    return path, None


def check_dirs_are_disjoint(path1: str, path2: str) -> bool:
    path1 = __normalise_dir_path_for_disjoint_comparison(path1)
    path2 = __normalise_dir_path_for_disjoint_comparison(path2)
    return \
        not path1.startswith(path2) and \
        not path2.startswith(path1)


def __normalise_dir_path_for_disjoint_comparison(path: str) -> str:
    if path != "." and not path.startswith(os.sep):
        path = "./" + path
    return path + os.sep
