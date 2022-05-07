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
    def __init__(self, root: Root, path: Path, path_must_exist: bool, options: Options = Options()):
        self.__root = root
        self.__path = path
        self.__options = options
        self.__manifest: Optional[Dict[str, Any]] = None
        self.__init_full_path(path_must_exist)
        self.__init_files()

    def __init_full_path(self, path_must_exist: bool) -> None:
        self.__full_path = self.__root.path / self.__path
        if self.__root.scheme.path_exists(self.__full_path):
            if not self.__root.scheme.path_is_dir(self.__full_path):
                raise ContextException(f"path is not a directory: {self.__path}")
        else:
            if path_must_exist:
                raise ContextException(f"directory does not exist: {self.__path}")

    def __init_files(self) -> None:
        self.__files: Dict[str, FileEntry] = {}
        self.__manifest_file = self.__full_path.joinpath(self.__full_path, SOFTSYNC_MANIFEST_FILENAME)
        if self.__root.scheme.path_exists(self.__full_path):
            for entry in self.__root.scheme.path_listdir(self.__full_path):
                if entry.is_file():
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

    def __add_file_entry(self, file_entry: FileEntry, strict: bool) -> Optional[FileEntry]:
        existing_entry = self.__files.get(file_entry.name)
        if existing_entry is None or (existing_entry.is_soft() and self.__options.force):
            self.__files[file_entry.name] = file_entry
        elif strict:
            raise ContextException(f"file already exists: {existing_entry}")
        return existing_entry

    def save(self) -> None:
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

    def list_files(self,
                   file_matcher: Optional[Union[str, Pattern, Callable]] = None) -> List[FileEntry]:
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

    def sync_file(self, file: FileEntry, dest_ctx: "SoftSyncContext",
                  context_cache: Optional[Dict[str, "SoftSyncContext"]] = None):
        if self.__root.path == dest_ctx.__root.path:
            raise ValueError("contexts must not have the same root dir")
        context, src_file = self.__resolve(file.name, context_cache)
        src_file = context.__full_path.joinpath(src_file)
        dest_ctx.__sync(src_file, file.name)

    def __resolve(self, file_name: str,
                  context_cache: Optional[Dict[str, "SoftSyncContext"]] = None) -> ("SoftSyncContext", str):
        file = self.__files.get(file_name, None)
        if file is None:
            raise ContextException(f"failed to resolve file: {file_name}, not found")
        if not file.is_soft():
            return self, file.name
        link_path = file.link.parent
        link_name = file.link.name
        if len(link_path.parts) > 0:
            link_path = self.__path / link_path
            try:
                path = resolve_path(link_path)
            except IndexError:
                raise ContextException(f"failed to resolve file: {file_name}, path escaped root: {link_path}")
            context = context_cache.get(path, None) if context_cache is not None else None
            if context is None:
                context = SoftSyncContext(self.__root, path, True, self.__options)
                if context_cache is not None:
                    context_cache[path] = context
        else:
            context = self
        return context.__resolve(link_name, context_cache)

    def __sync(self, src_file: Path, dest_file: str):
        dest_file_path = self.__full_path.joinpath(dest_file)
        if self.__root.scheme.path_exists(dest_file_path):
            if self.__root.scheme.path_is_dir(dest_file_path):
                raise ContextException(f"destination exists as a directory: {dest_file}")
            if not self.__options.force:
                raise ContextException(f"destination file exists: {dest_file_path}")
            dest_file_path.unlink()
        self.__root.scheme.path_mkdir(self.__full_path)
        if not self.__options.dry_run:
            if self.__options.symbolic:
                self.__root.scheme.path_symlink_to(src_file, dest_file_path)
            else:
                self.__root.scheme.path_hardlink_to(src_file, dest_file_path)
