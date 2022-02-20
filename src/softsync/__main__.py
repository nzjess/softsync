import sys
import os
from argparse import ArgumentParser

from softsync.commands import cp

from softsync.exception import CommandException, ContextException


def __help(problem: str, parser: ArgumentParser = None) -> None:
    print(problem)
    print()
    if parser is not None:
        parser.print_help()


CLI_COMMANDS = {
    "cp": (cp.command_cp_cli, cp.command_cp_arg_parser)
}


def main():
    if len(sys.argv) < 2:
        commands = "\n  ".join(list(CLI_COMMANDS.keys()))
        __help(f"Usage: {os.path.basename(sys.argv[0])} cmd [args...]\n\ncommands:\n  {commands}")
        return 1

    cmd = sys.argv[1]
    args = sys.argv[2:]

    command = CLI_COMMANDS.get(cmd)
    if command is not None:
        cli, arg_parser = command
        arg_parser = arg_parser()
        try:
            cli(args, arg_parser)
        except ContextException as e:
            print(str(e))
            return 1
        except CommandException as e:
            __help(str(e), arg_parser)
            return 1
    else:
        __help(f"Unknown command: {cmd}")
        return 1


if __name__ == "__main__":
    main()
