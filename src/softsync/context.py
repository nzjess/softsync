import json
import re
import fnmatch
from pathlib3x import Path

from typing import List, Dict, Union, Optional, Callable, Pattern, Any

from softsync.common import Root, Options
from softsync.common import resolve_path
from softsync.exception import ContextException, ContextCorruptException


SOFTSYNC_MANIFEST_FILENAME = ".softsync"
SOFTLINKS_KEY = "softlinks"


class FileEntry:
    def __init__(self, name: str, link: Optional[Union[Path, str]] = None):
        self.__name = name
        self.__link = link if isinstance(link, Path) else Path(link) if link is not None else None

    @property
    def name(self) -> str:
        return self.__name

    @property
    def link(self) -> Path:
        return self.__link

    def is_soft(self) -> bool:
        return self.link is not None

    def __repr__(self) -> str:
        if self.is_soft():
            return f"{self.name} -> {self.link}"
        else:
            return f"{self.name}"

    @property
    def json(self) -> Dict[str, str]:
        return {
            "name": self.name,
            "link": self.link.as_posix()
        }


class SoftSyncContext:
    def __init__(self, root: Root, path: Path, path_must_exist: bool, options: Options = Options(),
                 cache: Optional[Dict[str, "SoftSyncContext"]] = None):
        self.__root = root
        self.__path = path
        self.__options = options
        self.__cache = cache if cache is not None else {}
        self.__manifest: Optional[Dict[str, Any]] = None
        self.__files: Dict[str, FileEntry] = {}
        self.__dirty = False
        self.__init(path_must_exist)
        self.load()

    def __init(self, path_must_exist: bool) -> None:
        self.__full_path = self.__root.path / self.__path
        if self.__root.scheme.path_exists(self.__full_path):
            if not self.__root.scheme.path_is_dir(self.__full_path):
                raise ContextException(f"path is not a directory: {self.__path}")
        else:
            if path_must_exist:
                raise ContextException(f"directory does not exist: {self.__path}")
        self.__manifest_file = self.__full_path.joinpath(self.__full_path, SOFTSYNC_MANIFEST_FILENAME)

    def load(self) -> None:
        self.__files.clear()
        if self.__root.scheme.path_exists(self.__full_path):
            for entry in self.__root.scheme.path_listdir(self.__full_path):
                if entry.is_file():
                    if entry.name == SOFTSYNC_MANIFEST_FILENAME:
                        continue
                    file_entry = FileEntry(entry.name)
                    if self.__add_file_entry(file_entry, False) is not None:
                        raise ValueError(f"FATAL filesystem conflict, in: {self.__path}, on: {entry.name}")
            if self.__root.scheme.path_exists(self.__manifest_file):
                if not self.__root.scheme.path_is_file(self.__manifest_file):
                    raise ContextException("manifest file location conflict")
                with self.__root.scheme.path_open(self.__manifest_file, mode='r') as file:
                    self.__manifest = json.load(file)
                    entries: List[Dict[str, str]] = self.__manifest.get(SOFTLINKS_KEY, None)
                    if entries is not None:
                        conflicts = []
                        for entry in entries:
                            file_entry = FileEntry(**entry)
                            if self.__add_file_entry(file_entry, False) is not None:
                                conflicts.append(file_entry)
                        if len(conflicts) > 0:
                            raise ContextCorruptException(
                                f"softlink entries conflict with files in: {self.__path}",
                                conflicts,
                                self
                            )
        self.__dirty = False

    def __add_file_entry(self, file_entry: FileEntry, strict: bool) -> Optional[FileEntry]:
        existing_entry = self.__files.get(file_entry.name)
        if existing_entry is None or (existing_entry.is_soft() and self.__options.force):
            self.__files[file_entry.name] = file_entry
            self.__dirty = True
        elif strict:
            raise ContextException(f"file already exists: {existing_entry}")
        return existing_entry

    def __remove_file_entry(self, file_entry, strict: bool) -> Optional[FileEntry]:
        existing_entry = self.__files.get(file_entry.name)
        if existing_entry is not None:
            if existing_entry.is_soft():
                del self.__files[existing_entry.name]
                self.__dirty = True
            else:
                file_path = self.__full_path / existing_entry.name
                if self.__options.force:
                    self.__root.scheme.path_unlink(file_path)
                else:
                    raise ContextException(f"not removing real file: {file_path}")
        elif strict:
            raise ContextException(f"file does not exist: {file_entry}")
        return existing_entry

    def save(self) -> None:
        self.__save()
        if self.__cache is not None:
            for context in self.__cache.values():
                context.__save()

    def __save(self) -> None:
        if not self.__dirty or self.__options.dry_run:
            return
        self.__root.scheme.path_mkdir(self.__full_path)
        with self.__root.scheme.path_open(self.__manifest_file, mode='w') as file:
            if self.__manifest is None:
                self.__manifest = {}
            entries: List[Dict[str, str]] = []
            for entry in self.__files.values():
                if entry.is_soft():
                    entries.append(entry.json)
            entries.sort(key=lambda e: e["name"])
            self.__manifest[SOFTLINKS_KEY] = entries
            json.dump(self.__manifest, file, indent=2)
        self.__dirty = False

    def relative_path_to(self, other: "SoftSyncContext") -> Path:
        if self.__root != other.__root:
            raise ValueError("contexts must have the same root")
        src_parts = self.__path.parts
        dest_parts = other.__path.parts
        index: int = 0
        while index < len(src_parts) and index < len(dest_parts):
            if src_parts[index] != dest_parts[index]:
                break
            index = index + 1
        relative_path = ([".."] * (len(dest_parts) - index))
        relative_path.extend(src_parts[index:])
        return Path(*relative_path)

    def list_files(self, file_matcher: Optional[Union[str, Pattern, Callable]] = None) -> List[FileEntry]:
        files: List[FileEntry] = list(self.__files.values())
        if file_matcher is not None:
            if isinstance(file_matcher, str):
                file_pattern = re.compile(fnmatch.translate(file_matcher))
                file_matcher = file_pattern
            if isinstance(file_matcher, Pattern):
                file_pattern = file_matcher
                file_matcher = lambda e: file_pattern.match(e.name) is not None
            if isinstance(file_matcher, Callable):
                files = list(filter(file_matcher, files))
            else:
                raise ValueError(f"invalid type for file_matcher: {type(file_matcher)}")
        return files

    def dupe_file(self, src_file: FileEntry, relative_path: Path,
                  file_mapper: Optional[Union[str, Callable]] = None) -> None:
        if file_mapper is None:
            dest_file = src_file.name
        elif isinstance(file_mapper, str):
            dest_file = file_mapper
        elif isinstance(file_mapper, Callable):
            dest_file = file_mapper(src_file.name)
        else:
            raise ValueError(f"invalid type for file_mapper: {type(file_mapper)}")
        link = relative_path.joinpath(src_file.name)
        file_entry = FileEntry(dest_file, link)
        self.__add_file_entry(file_entry, True)

    def sync_file(self, file: FileEntry, dest_ctx: "SoftSyncContext") -> None:
        if self.__root == dest_ctx.__root:
            raise ValueError("contexts must not have the same root")
        src_ctx, dest_ctx, src_file = self.__resolve(file.name, dest_ctx)
        src_file = src_ctx.__full_path.joinpath(src_file)
        dest_file = dest_ctx.__full_path.joinpath(
            src_file.name if self.__options.reconstruct else file.name
        )
        dest_ctx.__sync(src_file, dest_file)

    def rm_file(self, file: FileEntry) -> None:
        if self.__options.dry_run:
            return
        return self.__remove_file_entry(file, True)

    def __resolve(self, file_name: str, dest_ctx: "SoftSyncContext") -> ("SoftSyncContext", "SoftSyncContext", str):
        file = self.__files.get(file_name, None)
        if file is None:
            raise ContextException(f"failed to resolve file: {file_name}, not found")
        if not file.is_soft():
            return self, dest_ctx, file.name
        if self.__options.reconstruct:
            dest_ctx.__add_file_entry(file, True)
        link_path = file.link.parent
        link_name = file.link.name
        link_path = self.__path / link_path
        try:
            path = resolve_path(link_path)
        except IndexError:
            raise ContextException(f"failed to resolve file: {file_name}, path escaped root: {link_path}")
        src_ctx = self.__context_for_path(path, True)
        if self.__options.reconstruct:
            dest_ctx = dest_ctx.__context_for_path(path, False)
        return src_ctx.__resolve(link_name, dest_ctx)

    def __sync(self, src_file: Path, dest_file: Path):
        if self.__root.scheme.path_exists(dest_file):
            if self.__root.scheme.path_is_dir(dest_file):
                raise ContextException(f"destination is a directory: {dest_file}")
            if not self.__options.force:
                raise ContextException(f"destination file exists: {dest_file}")
            if not self.__options.dry_run:
                dest_file.unlink()
        if not self.__options.dry_run:
            self.__root.scheme.path_mkdir(self.__full_path)
            if self.__options.symbolic:
                self.__root.scheme.path_symlink_to(src_file, dest_file)
            else:
                self.__root.scheme.path_hardlink_to(src_file, dest_file)

    def __context_for_path(self, path: Path, path_must_exist: bool) -> "SoftSyncContext":
        if path == self.__path:
            return self
        context_for_path = self.__cache.get(path, None) if self.__cache is not None else None
        if context_for_path is None:
            context_for_path = SoftSyncContext(self.__root, path, path_must_exist, self.__options, self.__cache)
            if self.__cache is not None:
                self.__cache[path] = context_for_path
        return context_for_path
