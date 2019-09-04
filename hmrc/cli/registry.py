"""HMRC command line registry"""

from argparse import ArgumentParser, Action
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Dict
from pkg_resources import iter_entry_points

__all__ = [
    'HMRC_CLI_COMMAND',
    'CommandRegistry',
    'commands',
    'main',
]


HMRC_CLI_COMMAND = 'hmrc.cli.command'
"""HMRC command line entry point name"""


@dataclass
class CommandRegistry(Mapping):
    """Command registry"""

    parser: ArgumentParser
    """Argument parser for this (sub)command"""

    subcommands: Dict[str, 'CommandRegistry'] = None
    """Subcommands of this (sub)command"""

    subparsers: Action = field(default=None, repr=False)
    """Argument parser subparsers object (if subcommands exist)"""

    def __getitem__(self, key):

        # Create subcommands dictionary and subparsers object, if applicable
        if self.subcommands is None:
            self.subcommands = {}
            self.subparsers = self.parser.add_subparsers(
                dest='subcommand', title='subcommands', required=True,
            )

        # Create subcommand, if applicable
        if key not in self.subcommands:
            subparser = self.subparsers.add_parser(key)
            self.subcommands[key] = type(self)(subparser)

        return self.subcommands[key]

    def __iter__(self):
        return iter(self.subcommands)

    def __len__(self):
        return len(self.subcommands)

    def register(self, group):
        """Register command entry points"""
        for entry_point in iter_entry_points(group):
            subcommand = self
            for name in entry_point.name.split():
                subcommand = subcommand[name]
            cls = entry_point.load()
            subcommand.parser.set_defaults(cls=cls)
            cls.init_parser(subcommand.parser)

    def parse(self, args=None):
        """Parse arguments"""
        return self.parser.parse_args(args)

    def command(self, args=None):
        """Construct command"""
        args = self.parse(args)
        return args.cls(args)


commands = CommandRegistry(ArgumentParser())
"""Registry of all commands"""


def main(args=None):
    """Command line entry point"""
    command = commands.command(args)
    output = command()
    if output is not None:
        print('\n'.join(output) if isinstance(output, list) else output)


# Register all known commands
commands.register(HMRC_CLI_COMMAND)


if __name__ == '__main__':
    main()
