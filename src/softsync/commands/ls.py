from argparse import ArgumentParser

from typing import List

from softsync.common import Options, Root
from softsync.common import normalise_path
from softsync.context import SoftSyncContext, FileEntry


def command_ls_arg_parser() -> ArgumentParser:
    parser = ArgumentParser("softsync ls")
    parser.add_argument("-R", "--root", dest="root", help="root dir", metavar="root", type=str, default=".")
    parser.add_argument("path", type=str, nargs=1)
    return parser


def command_ls_cli(args: List[str], parser: ArgumentParser) -> None:
    cmdline = parser.parse_args(args)
    root = Root(cmdline.root)
    path = cmdline.path[0]
    options = Options()
    files = command_ls(root, path, options)
    for file in files:
        print(file)


def command_ls(root: Root, path: str, options: Options = Options()) -> List[FileEntry]:
    path_dir, path_file = normalise_path(root.path, path)
    context = SoftSyncContext(root.path, path_dir, True, options)
    return context.list_files(path_file)
