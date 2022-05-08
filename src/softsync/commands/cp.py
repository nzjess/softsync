from argparse import ArgumentParser
from pathlib3x import Path

from typing import List, Callable, Optional

from softsync.common import Root, Options
from softsync.common import parse_roots, is_glob_pattern, split_path, check_paths_are_disjoint
from softsync.context import SoftSyncContext, FileEntry
from softsync.exception import CommandException


def softsync_cp_arg_parser() -> ArgumentParser:
    parser = ArgumentParser("softsync cp")
    parser.add_argument("-R", "--root", dest="roots", help="root dir(s)", metavar="src[:dest]", type=str, default=".")
    parser.add_argument("src_path", metavar="src-path", type=str, nargs=1)
    parser.add_argument("dest_path", metavar="dest-path", type=str, nargs='?', default=None)
    parser.add_argument("-f", "--force", dest="force", help="copy over duplicates", action='store_true')
    parser.add_argument("-r", "--recursive", dest="recursive", help="recurse into sub-directories", action='store_true')
    parser.add_argument("-c", "--reconstruct", dest="reconstruct", help="reconstruct file hierarchy", action='store_true')
    parser.add_argument("-s", "--symbolic", dest="symbolic", help="produce symlink", action='store_true')
    parser.add_argument("-v", "--verbose", dest="verbose", help="verbose output", action='store_true')
    parser.add_argument("--dry", dest="dry_run", help="dry run only", action='store_true')
    return parser


def softsync_cp_cli(args: List[str], parser: ArgumentParser) -> None:
    cmdline = parser.parse_args(args)
    src_root, dest_root = parse_roots(cmdline.roots)
    src_path = Path(cmdline.src_path[0])
    dest_path = Path(cmdline.dest_path) if cmdline.dest_path is not None else None
    options = Options(
        force=cmdline.force,
        recursive=cmdline.recursive,
        reconstruct=cmdline.reconstruct,
        symbolic=cmdline.symbolic,
        verbose=cmdline.verbose,
        dry_run=cmdline.dry_run,
    )
    files = softsync_cp(
        src_root,
        src_path,
        dest_root,
        dest_path,
        options
    )
    if options.verbose:
        for file in files:
            print(file)


def softsync_cp(src_root: Root, src_path: Path,
                dest_root: Optional[Root] = None, dest_path: Optional[Path] = None,
                options: Options = Options(),
                matcher: Optional[Callable] = None,
                mapper: Optional[Callable] = None) -> List[FileEntry]:
    if dest_root is None:
        if options.symbolic:
            raise CommandException("symbolic option is not valid here")
        if options.reconstruct:
            raise CommandException("reconstruct option is not valid here")
        if dest_path is None:
            raise CommandException("source root only present, expected both 'src-path' and 'dest-path' args")
        src_dir, src_file = split_path(src_root, src_path)
        dest_dir, dest_file = split_path(src_root, dest_path)
        if not check_paths_are_disjoint(src_dir, dest_dir):
            raise CommandException("'src' and 'dest' paths must be disjoint")
        if src_file is not None:
            if matcher is not None:
                raise CommandException("'src-path' must be a directory if matcher function is used")
        if dest_file is not None:
            if is_glob_pattern(dest_file):
                raise CommandException("'dest-path' cannot be a glob pattern")
            if mapper is not None:
                raise CommandException("'dest-path' must be a directory if mapper function is used")
        return __dupe(src_root, src_dir, src_file, dest_dir, dest_file, options, matcher, mapper)
    else:
        if dest_root.scheme.name != "file":
            raise CommandException("'dest' root must have 'file://' scheme")
        if src_root.scheme == dest_root.scheme:
            if not check_paths_are_disjoint(src_root.path, dest_root.path):
                raise CommandException("'src' and 'dest' roots must be disjoint")
        if dest_path is not None:
            raise CommandException("source and destination roots present, expected only 'src-path' arg")
        if mapper is not None:
            raise CommandException("source and destination roots present, cannot use mapper function")
        src_dir, src_file = split_path(src_root, src_path)
        if src_file is not None:
            if matcher is not None:
                raise CommandException("'src-path' must be a directory if matcher function is used")
        return __sync(src_root, dest_root, src_dir, src_file, options, matcher)


def __dupe(root: Root, src_dir: Path, src_file: str, dest_dir: Path, dest_file: str, options: Options,
           matcher: Optional[Callable] = None, mapper: Optional[Callable] = None) -> List[FileEntry]:
    src_ctx = SoftSyncContext(root, src_dir, True, options)
    dest_ctx = SoftSyncContext(root, dest_dir, False, options)
    relative_path = src_ctx.relative_path_to(dest_ctx)
    src_files = src_ctx.list_files(matcher if matcher is not None else src_file)
    for file in src_files:
        dest_ctx.dupe_file(file, relative_path, mapper if mapper is not None else dest_file)
    dest_ctx.save()
    return src_files


def __sync(src_root: Root, dest_root: Root, src_dir: Path, src_file: Path, options: Options,
           matcher: Optional[Callable] = None) -> List[FileEntry]:
    src_ctx = SoftSyncContext(src_root, src_dir, True, options)
    dest_ctx = SoftSyncContext(dest_root, src_dir, False, options)
    src_files = src_ctx.list_files(matcher if matcher is not None else src_file)
    for file in src_files:
        src_ctx.sync_file(file, dest_ctx)
    dest_ctx.save()
    return src_files
