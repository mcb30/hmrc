"""HMRC API command line"""

from argparse import ArgumentParser, Action
from collections.abc import Mapping
from configparser import ConfigParser, DEFAULTSECT, NoOptionError
from dataclasses import dataclass, field
import logging
import os.path
import re
from typing import ClassVar, Dict, Set
import webbrowser
import parsedatetime
from ..auth import HmrcSession, HmrcTokenFileStorage
from ..api import HmrcClient

__all__ = [
    'datestring',
    'CommandTree',
    'Command',
    'LoginCommand',
    'LogoutCommand',
]

calendar = parsedatetime.Calendar()


def datestring(string):
    """Parse date from string"""
    timestamp, ret = calendar.parseDT(string)
    if not ret:
        raise ValueError("Invalid date: '%s'" % string)
    return timestamp.date()


@dataclass
class CommandTree(Mapping):
    """Command tree"""

    parser: ArgumentParser
    """Argument parser for this (sub)command"""

    subcommands: Dict[str, 'CommandTree'] = None
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


class Command:
    """Command line command"""

    parser: ClassVar[ArgumentParser] = ArgumentParser()
    """Argument parser"""

    subcommands: ClassVar[CommandTree] = CommandTree(parser)
    """Root of command tree"""

    section: ClassVar[str] = DEFAULTSECT
    """Configuration file section"""

    Client: ClassVar[type] = HmrcClient
    """API client class"""

    all_clients: ClassVar[Set[type]] = {Client}
    """Set of all known client classes"""

    # Add arguments to root argument parser

    def __init_subclass__(cls, section=False, **kwargs):
        """Register subcommand"""
        super().__init_subclass__(**kwargs)

        # Construct command name
        names = [x.lower() for x in
                 re.findall(r'[A-Z][a-z]+', cls.__name__)[:-1]]

        # Create subcommand in command tree
        subcommand = cls.subcommands
        for name in names:
            subcommand = subcommand[name]

        # Record subcommand's class
        subcommand.parser.set_defaults(cls=cls)

        # Add to list of known client classes
        cls.all_clients.add(cls.Client)

        # Use class documentation as subcommand description
        subcommand.parser.description = cls.__doc__

        # Set configuration file section name, if applicable
        if section:
            cls.section = names[-1]

        # Add any subcommand-specific arguments, if applicable
        if not section:
            cls.add_arguments(subcommand.parser)

    def __init__(self, args=None):
        self.args = self.parser.parse_args(args)

    def __call__(self):

        # Extract configuration file parameters
        config = self.config
        section = self.args.cls.section
        if section not in config:
            section = config.default_section

        # Extract session parameters
        try:
            client_id = config.get(section, 'client_id')
            client_secret = config.get(section, 'client_secret')
            server_token = config.get(section, 'server_token', fallback=None)
            test = config.getboolean(section, 'test', fallback=False)
        except NoOptionError as exc:
            raise SystemExit(
                "Missing configuration file option '%s'" % exc.option
            ) from exc

        # Construct client parameters
        params = {k: v for k, v in config[section].items() if k not in
                  {'client_id', 'client_secret', 'server_token', 'test'}}

        # Enable debug logging, if applicable
        if self.args.debug:
            logging.basicConfig(level=logging.DEBUG)

        # Execute command
        with self.storage as storage:
            token = None if 'access_token' in storage.token else server_token
            session = HmrcSession(client_id, client_secret=client_secret,
                                  storage=storage, token=token, test=test)
            client = self.args.cls.Client(session, **params)
            return self.args.cls.execute(client, self.args)

    @staticmethod
    def add_arguments(parser):
        """Add argument definitions"""
        parser.add_argument('--scenario', help="Use named test scenario")
        parser.add_argument('-d', '--debug', action='store_true',
                            help="Enable debug logging")
        parser.add_argument('-c', '--config', help="Configuration file")
        parser.add_argument('--token', help="Authentication token file")

    @staticmethod
    def execute(client, args):
        """Execute command"""
        pass

    @property
    def config(self):
        """Configuration"""
        config = ConfigParser()
        config.read([self.args.config] if self.args.config else
                    ['hmrc.ini', os.path.expanduser('~/.hmrc.ini')])
        return config

    @property
    def storage(self):
        """Token storage"""
        return HmrcTokenFileStorage(self.args.token)


class LoginCommand(Command):
    """Log in to HMRC APIs"""

    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)
        parser.add_argument('--scope', action='append',
                            help="Authorization scope")
        parser.add_argument('--code', help="Authorization code")

    @classmethod
    def execute(cls, client, args):

        # Determine scope
        scope = (args.scope or client.scope or
                 [x for client in cls.all_clients for x in client.scope])

        # Apply scope to session
        session = client.session
        session.extend_scope(scope)

        # Obtain authorization code via browser, if applicable
        code = args.code
        if not code:
            uri, _state = session.authorization_url()
            webbrowser.open(uri)
            try:
                code = input("Enter authorization code from browser: ")
            except KeyboardInterrupt as exc:
                raise SystemExit("Aborted") from exc

        # Obtain token
        session.fetch_token(code=code)


class LogoutCommand(Command):
    """Log out from HMRC APIs"""

    @staticmethod
    def execute(client, args):
        client.session.storage.delete()
