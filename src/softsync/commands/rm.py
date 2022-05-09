from argparse import ArgumentParser
from pathlib3x import Path

from typing import List, Optional, Callable

from softsync.common import Options, Root
from softsync.common import split_path
from softsync.context import SoftSyncContext, FileEntry
from softsync.exception import CommandException


def softsync_rm_arg_parser() -> ArgumentParser:
    parser = ArgumentParser("softsync rm")
    parser.add_argument("-R", "--root", dest="root", help="root dir", metavar="root", type=str, default=".")
    parser.add_argument("path", type=str, nargs=1)
    parser.add_argument("-f", "--force", dest="force", help="copy over duplicates", action='store_true')
    parser.add_argument("-r", "--recursive", dest="recursive", help="recurse into sub-directories", action='store_true')
    parser.add_argument("-v", "--verbose", dest="verbose", help="verbose output", action='store_true')
    parser.add_argument("--dry", dest="dry_run", help="dry run only", action='store_true')
    return parser


def softsync_rm_cli(args: List[str], parser: ArgumentParser) -> None:
    cmdline = parser.parse_args(args)
    root = Root(cmdline.root)
    path = Path(cmdline.path[0])
    options = Options(
        force=cmdline.force,
        recursive=cmdline.recursive,
        verbose=cmdline.verbose,
        dry_run=cmdline.dry_run,
    )
    files = softsync_rm(
        root,
        path,
        options
    )
    if options.verbose:
        for file in files:
            print(file)


def softsync_rm(root: Root, path: Path,
                options: Options = Options(),
                matcher: Optional[Callable] = None) -> List[FileEntry]:
    path_dir, path_file = split_path(root, path)
    if path_file is not None:
        if matcher is not None:
            raise CommandException("'src-path' must be a directory if matcher function is used")
    context = SoftSyncContext(root, path_dir, True, options)
    files = context.list_files(matcher if matcher is not None else path_file)
    for file in files:
        context.rm_file(file)
    context.save()
    return files
