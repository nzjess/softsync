from argparse import ArgumentParser
from pathlib3x import Path

from typing import List, Optional

from softsync.common import Options, Root
from softsync.common import split_path
from softsync.context import SoftSyncContext, FileEntry
from softsync.exception import CommandException, ContextCorruptException


def softsync_repair_arg_parser() -> ArgumentParser:
    parser = ArgumentParser("softsync repair")
    parser.add_argument("-R", "--root", dest="root", help="root dir", metavar="root", type=str, default=".")
    parser.add_argument("path", type=str, nargs=1)
    parser.add_argument("-r", "--recursive", dest="recursive", help="recurse into sub-directories", action='store_true')
    parser.add_argument("-v", "--verbose", dest="verbose", help="verbose output", action='store_true')
    parser.add_argument("--dry", dest="dry_run", help="dry run only", action='store_true')
    return parser


def softsync_repair_cli(args: List[str], parser: ArgumentParser) -> None:
    cmdline = parser.parse_args(args)
    root = Root(cmdline.root)
    path = Path(cmdline.path[0])
    options = Options(
        recursive=cmdline.recursive,
        verbose=cmdline.verbose,
        dry_run=cmdline.dry_run,
    )
    conflicts = softsync_repair(
        root,
        path,
        options
    )
    if conflicts is None:
        print("no repair needed")
    else:
        message = "repaired" if not cmdline.dry_run else "needs repair"
        if options.verbose:
            conflicts = "\n  ".join([str(c) for c in conflicts])
            print(f"{message}:\n  {conflicts}")
        else:
            print(message)


def softsync_repair(root: Root, path: Path,
                    options: Options = Options()) -> Optional[List[FileEntry]]:
    path_dir, path_file = split_path(root, path)
    if path_file is not None:
        raise CommandException("path must be a directory")
    try:
        SoftSyncContext(root, path_dir, True, options)
        return None
    except ContextCorruptException as e:
        e.source.save()
        return e.conflicts
