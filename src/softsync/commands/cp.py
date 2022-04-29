from argparse import ArgumentParser

from typing import List

from softsync.common import Options, Roots
from softsync.common import is_file_pattern, normalise_path, check_dirs_are_disjoint
from softsync.exception import CommandException
from softsync.context import SoftSyncContext


def command_cp_arg_parser() -> ArgumentParser:
    parser = ArgumentParser("softsync cp")
    parser.add_argument("-R", "--root", dest="roots", help="root dir(s)", metavar="src[:dest]", type=str, default=".")
    parser.add_argument("args", metavar="arg", type=str, nargs='+')
    parser.add_argument("-r", "--recursive", dest="recursive", help="recurse into sub-directories", action='store_true')
    parser.add_argument("-f", "--force", dest="force", help="copy over duplicates", action='store_true')
    parser.add_argument("--dry", dest="dry_run", help="dry run only", action='store_true')
    return parser


def command_cp_cli(args: List[str], parser: ArgumentParser) -> None:
    cmdline = parser.parse_args(args)
    roots = Roots(cmdline.roots)
    options = Options(
        recursive=cmdline.recursive,
        force=cmdline.force,
        dry_run=cmdline.dry_run,
    )
    command_cp(roots, cmdline.args, options)


def command_cp(roots: Roots, args: List[str], options: Options = Options()) -> None:
    if roots.dest is None:
        if len(args) != 2:
            raise CommandException("root has source only, expected 'src' and 'dest' path args")
        src_dir, src_file = normalise_path(roots.src.path, args[0])
        dest_dir, dest_file = normalise_path(roots.src.path, args[1])
        if not check_dirs_are_disjoint(src_dir, dest_dir):
            raise CommandException("'src' and 'dest' paths must be disjoint")
        if dest_file is not None:
            if is_file_pattern(src_file) or is_file_pattern(dest_file):
                raise CommandException("'dest' path must be a directory")
        __dupe(roots.src.path, src_dir, src_file, dest_dir, dest_file, options)
    else:
        if len(args) != 1:
            raise CommandException("root has both source and destination, expected only 'src' path arg")
        src_dir, src_file = normalise_path(roots.src.path, args[0])
        __sync(roots.src.path, roots.dest.path, src_dir, src_file, options)


def __dupe(root_dir: str, src_dir: str, src_file: str, dest_dir: str, dest_file: str, options: Options) -> None:
    src_ctx = SoftSyncContext(root_dir, src_dir, True, options)
    dest_ctx = SoftSyncContext(root_dir, dest_dir, False, options)
    relative_path = src_ctx.relative_path_to(dest_ctx)
    src_files = src_ctx.list_files(src_file)
    if len(src_files) == 0:
        return
    if dest_file is not None:
        if len(src_files) != 1:
            raise CommandException("multiple source files for single destination")
        dest_ctx.dupe_file(src_files[0], relative_path, dest_file)
    else:
        for file in src_files:
            dest_ctx.dupe_file(file, relative_path, file.name)
    if not options.dry_run:
        dest_ctx.save()


def __sync(src_root_dir: str, dest_root_dir: str, src_dir: str, src_file: str, options: Options) -> None:
    print("sync", src_root_dir, dest_root_dir, src_dir, src_file, options)
