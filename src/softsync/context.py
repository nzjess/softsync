import json
import os
import re
import fnmatch
import shutil
from pathlib import Path

from typing import List, Dict, Union, Optional, Callable, Pattern

from softsync.common import Options
from softsync.exception import ContextException, ContextCorruptException


class FileEntry:
    def __init__(self, name: str, link: Optional[str] = None):
        self.__name = name
        self.__link = link

    @property
    def name(self):
        return self.__name

    @property
    def link(self):
        return self.__link

    def is_soft(self) -> bool:
        return self.link is not None

    def __repr__(self):
        if self.is_soft():
            return f"{self.name} -> {self.link}"
        else:
            return f"{self.name}"

    @property
    def json(self):
        return {
            "name": self.name,
            "link": self.link
        }


class SoftSyncContext:
    def __init__(self, root_dir: str, path: str, path_must_exist: bool, options: Options = Options()):
        self.__root_dir = root_dir
        self.__path = "" if path == "." else path
        self.__options = options
        self.__init_full_path(path_must_exist)
        self.__init_files()

    def __init_full_path(self, path_must_exist: bool) -> None:
        self.__full_path = os.path.join(self.__root_dir, self.__path)
        if os.path.exists(self.__full_path):
            if not os.path.isdir(self.__full_path):
                raise ContextException(f"path is not a directory: {self.__path}")
        else:
            if path_must_exist:
                raise ContextException(f"directory does not exist: {self.__path}")

    def __init_files(self) -> None:
        self.__files: Dict[str, FileEntry] = {}
        self.__manifest_dir = os.path.join(self.__full_path, ".softsync")
        self.__softlinks_file = os.path.join(self.__manifest_dir, "softlinks.json")
        if os.path.exists(self.__full_path):
            for entry in os.scandir(self.__full_path):
                if entry.is_file():
                    file_entry = FileEntry(entry.name)
                    if self.__add_file_entry(file_entry, False) is not None:
                        raise ValueError(f"FATAL filesystem conflict, in: {self.__path}, on: {entry.name}")
            if os.path.exists(self.__softlinks_file):
                if not os.path.isfile(self.__softlinks_file):
                    raise ContextException("manifest file location conflict")
                with open(self.__softlinks_file, 'r') as file:
                    conflicts = []
                    for entry in json.load(file):
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
        os.makedirs(self.__manifest_dir, exist_ok=True)
        with open(self.__softlinks_file, 'w') as file:
            entries = []
            for entry in self.__files.values():
                if entry.is_soft():
                    entries.append(entry.json)
            entries.sort(key=lambda e: e["name"])
            json.dump(entries, file, indent=2)

    def relative_path_to(self, other: "SoftSyncContext") -> str:
        if self.__root_dir != other.__root_dir:
            raise ValueError("contexts must have the same root dir")
        src_dir = self.__path.split(os.sep)
        dest_dir = other.__path.split(os.sep)
        index: int = 0
        while index < len(src_dir) and index < len(dest_dir):
            if src_dir[index] != dest_dir[index]:
                break
            index = index + 1
        relative_path: str = os.path.join(
            ((".." + os.sep) * (len(dest_dir) - index))[:-1],
            os.sep.join(src_dir[index:])
        )
        return relative_path

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

    def dupe_file(self, src_file: FileEntry, relative_path: str, dest_file: str) -> None:
        link = os.path.join(relative_path, src_file.name)
        file_entry = FileEntry(dest_file, link)
        self.__add_file_entry(file_entry, True)

    def sync_file(self, file: FileEntry, dest_ctx: "SoftSyncContext"):
        if self.__root_dir == dest_ctx.__root_dir:
            raise ValueError("contexts must not have the same root dir")
        context, src_file = self.__resolve(file.name)
        src_file = os.path.join(context.__full_path, src_file)
        dest_ctx.__sync(src_file, file.name)

    def __resolve(self, file_name: str) -> ("SoftSyncContext", str):
        file = self.__files.get(file_name, None)
        if file is None:
            raise ContextException(f"failed to resolve file: {file_name}")
        if not file.is_soft():
            return self
        link_file_path = os.path.join(self.__root_dir, file.link)
        root_dir = os.path.dirname(str(Path(link_file_path).resolve()))
        context = SoftSyncContext(root_dir, ".", True, self.__options)
        link_name = os.path.basename(file.link)
        return context.__resolve(link_name), link_name

    def __sync(self, src_file: str, dest_file: str):
        dest_file_path = os.path.join(self.__full_path, dest_file)
        if os.path.exists(dest_file_path):
            if os.path.isdir(dest_file_path):
                raise ContextException(f"destination exists as a directory: {dest_file}")
            if not self.__options.force:
                raise ContextException(f"destination file exists: {dest_file_path}")
            os.remove(dest_file_path)
        os.makedirs(self.__full_path, exist_ok=True)
        if not self.__options.dry_run:
            if self.__options.symbolic:
                os.symlink(src_file, dest_file_path)
            else:
                shutil.copyfile(src_file, dest_file_path)
