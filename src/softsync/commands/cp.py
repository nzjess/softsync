from argparse import ArgumentParser

from typing import List

from softsync.common import Options, Roots
from softsync.common import is_file_pattern, normalise_path, check_dirs_are_disjoint
from softsync.exception import CommandException
from softsync.context import SoftSyncContext, FileEntry


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
    options = Options(
        force=cmdline.force,
        recursive=cmdline.recursive,
        symbolic=cmdline.symbolic,
        verbose=cmdline.verbose,
        dry_run=cmdline.dry_run,
    )
    files = command_cp(roots, cmdline.src_path[0], cmdline.dest_path, options)
    if options.verbose:
        for file in files:
            print(file)


def command_cp(roots: Roots, src_path: str, dest_path: str, options: Options = Options()) -> List[FileEntry]:
    if roots.dest is None:
        if dest_path is None:
            raise CommandException("root has source only, expected both 'src-path' and 'dest-path' args")
        src_dir, src_file = normalise_path(roots.src.path, src_path)
        dest_dir, dest_file = normalise_path(roots.src.path, dest_path)
        if not check_dirs_are_disjoint(src_dir, dest_dir):
            raise CommandException("'src' and 'dest' paths must be disjoint")
        if dest_file is not None:
            if is_file_pattern(src_file) or is_file_pattern(dest_file):
                raise CommandException("'dest' path must be a directory")
        return __dupe(roots.src.path, src_dir, src_file, dest_dir, dest_file, options)
    else:
        if dest_path is not None:
            raise CommandException("root has both source and destination, expected only 'src-path' arg")
        src_dir, src_file = normalise_path(roots.src.path, src_path)
        return __sync(roots.src.path, roots.dest.path, src_dir, src_file, options)


def __dupe(root_dir: str, src_dir: str, src_file: str, dest_dir: str, dest_file: str, options: Options) -> List[FileEntry]:
    if options.symbolic:
        raise CommandException("symbolic option is not valid here")
    src_ctx = SoftSyncContext(root_dir, src_dir, True, options)
    dest_ctx = SoftSyncContext(root_dir, dest_dir, False, options)
    relative_path = src_ctx.relative_path_to(dest_ctx)
    src_files = src_ctx.list_files(src_file)
    if len(src_files) > 0:
        if dest_file is not None:
            if len(src_files) != 1:
                raise CommandException("multiple source files for single destination")
            dest_ctx.dupe_file(src_files[0], relative_path, dest_file)
        else:
            for file in src_files:
                dest_ctx.dupe_file(file, relative_path, file.name)
        if not options.dry_run:
            dest_ctx.save()
    return src_files


def __sync(src_root_dir: str, dest_root_dir: str, src_dir: str, src_file: str, options: Options) -> List[FileEntry]:
    src_ctx = SoftSyncContext(src_root_dir, src_dir, True, options)
    dest_ctx = SoftSyncContext(dest_root_dir, src_dir, False, options)
    src_files = src_ctx.list_files(src_file)
    context_cache = {}
    for file in src_files:
        src_ctx.sync_file(file, dest_ctx, context_cache)
    return src_files
