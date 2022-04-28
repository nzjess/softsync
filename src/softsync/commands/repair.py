from argparse import ArgumentParser

from typing import List

from softsync.common import Options, Root
from softsync.common import normalise_path
from softsync.exception import CommandException, ContextCorruptException
from softsync.context import SoftSyncContext


def command_repair_arg_parser() -> ArgumentParser:
    parser = ArgumentParser("softsync")
    parser.add_argument("-R", "--root", dest="root", help="root dir", metavar="root", type=str, default=".")
    parser.add_argument("path", type=str, nargs=1)
    parser.add_argument("-r", "--recursive", dest="recursive", help="recurse into sub-directories", action='store_true')
    return parser


def command_repair_cli(args: List[str], parser: ArgumentParser) -> None:
    cmdline = parser.parse_args(args)
    root = Root(cmdline.root)
    path = cmdline.path[0]
    options = Options(
        recursive=cmdline.recursive,
    )
    command_repair(root, path, options)


def command_repair(root: Root, path: str, options: Options = Options()) -> None:
    path_dir, path_file = normalise_path(root.path, path)
    if path_file is not None:
        raise CommandException("path must be a directory")
    try:
        SoftSyncContext(root.path, path_dir, options)
        print("no repair needed")
    except ContextCorruptException as e:
        e.source.save()
        print(str(e))
        print("\n...repaired\n")
