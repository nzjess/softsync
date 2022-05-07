from argparse import ArgumentParser
from pathlib3x import Path

from typing import List, Optional, Callable

from softsync.common import Options, Root
from softsync.common import split_path
from softsync.context import SoftSyncContext, FileEntry
from softsync.exception import CommandException


def softsync_ls_arg_parser() -> ArgumentParser:
    parser = ArgumentParser("softsync ls")
    parser.add_argument("-R", "--root", dest="root", help="root dir", metavar="root", type=str, default=".")
    parser.add_argument("path", type=str, nargs=1)
    return parser


def softsync_ls_cli(args: List[str], parser: ArgumentParser) -> None:
    cmdline = parser.parse_args(args)
    root = Root(cmdline.root)
    path = Path(cmdline.path[0])
    options = Options()
    files = softsync_ls(
        root,
        path,
        options
    )
    for file in files:
        print(file)


def softsync_ls(root: Root, path: Path,
                options: Options = Options(),
                matcher: Optional[Callable] = None) -> List[FileEntry]:
    path_dir, path_file = split_path(root, path)
    if path_file is not None:
        if matcher is not None:
            raise CommandException("'src-path' must be a directory if matcher function is used")
    context = SoftSyncContext(root, path_dir, True, options)
    return context.list_files(matcher if matcher is not None else path_file)
