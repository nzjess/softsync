from argparse import ArgumentParser

from typing import List, Callable, Optional, Union

from softsync.common import Root, Roots, Options
from softsync.common import is_glob_pattern, split_path, check_dirs_are_disjoint
from softsync.context import SoftSyncContext, FileEntry
from softsync.exception import CommandException


def command_cp_arg_parser() -> ArgumentParser:
    parser = ArgumentParser("softsync cp")
    parser.add_argument("-R", "--root", dest="roots", help="root dir(s)", metavar="src[:dest]", type=str, default=".")
    parser.add_argument("src_path", metavar="src-path", type=str, nargs=1)
    parser.add_argument("dest_path", metavar="dest-path", type=str, nargs='?', default=None)
    parser.add_argument("-f", "--force", dest="force", help="copy over duplicates", action='store_true')
    parser.add_argument("-r", "--recursive", dest="recursive", help="recurse into sub-directories", action='store_true')
    parser.add_argument("-s", "--symbolic", dest="symbolic", help="produce symlink", action='store_true')
    parser.add_argument("-v", "--verbose", dest="verbose", help="verbose output", action='store_true')
    parser.add_argument("--dry", dest="dry_run", help="dry run only", action='store_true')
    return parser


def command_cp_cli(args: List[str], parser: ArgumentParser) -> None:
    cmdline = parser.parse_args(args)
    roots = Roots(cmdline.roots)
    src_path = cmdline.src_path[0]
    dest_path = cmdline.dest_path
    options = Options(
        force=cmdline.force,
        recursive=cmdline.recursive,
        symbolic=cmdline.symbolic,
        verbose=cmdline.verbose,
        dry_run=cmdline.dry_run,
    )
    files = command_cp(
        roots,
        src_path,
        dest_path,
        options
    )
    if options.verbose:
        for file in files:
            print(file)


def command_cp(root: Union[Root, Roots], src_path: str, dest_path: Optional[str] = None, options: Options = Options(),
               matcher: Optional[Callable] = None, mapper: Optional[Callable] = None) -> List[FileEntry]:
    if isinstance(root, Roots):
        src_root = root.src
        dest_root = root.dest
    elif isinstance(root, Root):
        src_root = root
        dest_root = None
    else:
        raise ValueError(f"invalid type for root: {type(root)}")
    if dest_root is None:
        if dest_path is None:
            raise CommandException("source root only present, expected both 'src-path' and 'dest-path' args")
        src_dir, src_file = split_path(src_root.path, src_path)
        dest_dir, dest_file = split_path(src_root.path, dest_path)
        if not check_dirs_are_disjoint(src_dir, dest_dir):
            raise CommandException("'src' and 'dest' paths must be disjoint")
        if src_file is not None:
            if matcher is not None:
                raise CommandException("'src-path' must be a directory if matcher function is used")
        if dest_file is not None:
            if is_glob_pattern(dest_file):
                raise CommandException("'dest-path' cannot be a glob pattern")
            if mapper is not None:
                raise CommandException("'dest-path' must be a directory if mapper function is used")
        return __dupe(src_root.path, src_dir, src_file, dest_dir, dest_file, options, matcher, mapper)
    else:
        if dest_path is not None:
            raise CommandException("source and destination roots present, expected only 'src-path' arg")
        if mapper is not None:
            raise CommandException("source and destination roots present, cannot use mapper function")
        src_dir, src_file = split_path(src_root.path, src_path)
        if src_file is not None:
            if matcher is not None:
                raise CommandException("'src-path' must be a directory if matcher function is used")
        return __sync(src_root.path, dest_root.path, src_dir, src_file, options, matcher)


def __dupe(root_dir: str, src_dir: str, src_file: str, dest_dir: str, dest_file: str, options: Options,
           matcher: Optional[Callable] = None, mapper: Optional[Callable] = None) -> List[FileEntry]:
    if options.symbolic:
        raise CommandException("symbolic option is not valid here")
    src_ctx = SoftSyncContext(root_dir, src_dir, True, options)
    dest_ctx = SoftSyncContext(root_dir, dest_dir, False, options)
    relative_path = src_ctx.relative_path_to(dest_ctx)
    src_files = src_ctx.list_files(matcher if matcher is not None else src_file)
    for file in src_files:
        dest_ctx.dupe_file(file, relative_path, mapper if mapper is not None else dest_file)
    if not options.dry_run:
        dest_ctx.save()
    return src_files


def __sync(src_root_dir: str, dest_root_dir: str, src_dir: str, src_file: str, options: Options,
           matcher: Optional[Callable] = None) -> List[FileEntry]:
    src_ctx = SoftSyncContext(src_root_dir, src_dir, True, options)
    dest_ctx = SoftSyncContext(dest_root_dir, src_dir, False, options)
    src_files = src_ctx.list_files(matcher if matcher is not None else src_file)
    context_cache = {}
    for file in src_files:
        src_ctx.sync_file(file, dest_ctx, context_cache)
    return src_files
