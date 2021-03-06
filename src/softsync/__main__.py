import sys
import os
from argparse import ArgumentParser

from typing import List, Optional

from softsync.commands import cp
from softsync.commands import rm
from softsync.commands import ls
from softsync.commands import repair

from softsync.exception import SoftSyncException, CommandException


def __help(problem: str, parser: ArgumentParser = None) -> None:
    print(problem)
    print()
    if parser is not None:
        parser.print_help()


CLI_COMMANDS = {
    "cp": (cp.softsync_cp_cli, cp.softsync_cp_arg_parser),
    "rm": (rm.softsync_rm_cli, rm.softsync_rm_arg_parser),
    "ls": (ls.softsync_ls_cli, ls.softsync_ls_arg_parser),
    "repair": (repair.softsync_repair_cli, repair.softsync_repair_arg_parser)
}


def cli(cli_args: Optional[List[str]] = None) -> None:
    if cli_args is None:
        cli_args = sys.argv

    cmd = None if len(cli_args) < 2 else cli_args[1]

    if cmd is None or cmd == "-h":
        commands = "\n  ".join(list(CLI_COMMANDS.keys()))
        __help(f"Usage: {os.path.basename(cli_args[0])} cmd [-h] [args...]\n\ncommands:\n  {commands}")
        return 1

    args = cli_args[2:]

    command = CLI_COMMANDS.get(cmd)
    if command is not None:
        cli_call, arg_parser = command
        arg_parser = arg_parser()
        try:
            cli_call(args, arg_parser)
        except CommandException as e:
            __help(str(e), arg_parser)
            return 1
        except SoftSyncException as e:
            print(str(e))
            return 1
    else:
        __help(f"Unknown command: {cmd}")
        return 1


if __name__ == "__main__":
    cli()
