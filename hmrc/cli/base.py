"""HMRC API command line"""

from argparse import Namespace
from configparser import ConfigParser, DEFAULTSECT, NoOptionError
from dataclasses import dataclass
import logging
import os.path
from typing import ClassVar, Set
import webbrowser
import parsedatetime
from ..auth import HmrcSession, HmrcTokenFileStorage
from ..api import HmrcClient

__all__ = [
    'datestring',
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
class Command:
    """Command line command"""

    args: Namespace
    """Parsed arguments"""

    section: ClassVar[str] = DEFAULTSECT
    """Configuration file section"""

    Client: ClassVar[type] = HmrcClient
    """API client class"""

    @classmethod
    def init_parser(cls, parser):
        """Initialise argument parser"""

        # Use class documentation as subcommand description
        parser.description = cls.__doc__

        # Add common argument definitions
        parser.add_argument('--scenario', help="Use named test scenario")
        parser.add_argument('-d', '--debug', action='store_true',
                            help="Enable debug logging")
        parser.add_argument('-c', '--config', help="Configuration file")
        parser.add_argument('--token', help="Authentication token file")
        parser.add_argument('--gdpr-consent', action='store_true',
                            help="Consent to sending fraud prevention headers")

    def __call__(self):

        # Extract configuration file parameters
        config = self.config
        section = self.section
        if section not in config:
            section = config.default_section

        # Extract session parameters
        try:
            client_id = config.get(section, 'client_id', fallback=None)
            client_secret = config.get(section, 'client_secret', fallback=None)
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

        # Consent to GDPR data collection, if applicable
        gdpr_consent = self.args.gdpr_consent

        # Execute command
        with self.storage as storage:
            token = None if 'access_token' in storage.token else server_token
            with HmrcSession(client_id, client_secret=client_secret,
                             storage=storage, token=token, test=test,
                             gdpr_consent=gdpr_consent) as session:
                client = self.Client(session, **params)
                return self.execute(client)

    def execute(self, client):
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
        return HmrcTokenFileStorage(path=self.args.token)


class LoginCommand(Command):
    """Log in to HMRC APIs"""

    Clients: ClassVar[Set[type]] = {HmrcClient}
    """Set of all known client classes"""

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.Clients.add(cls.Client)

    @classmethod
    def init_parser(cls, parser):
        super().init_parser(parser)
        parser.add_argument('--scope', action='append',
                            help="Authorization scope")
        parser.add_argument('--code', help="Authorization code")

    def execute(self, client):

        # Determine scope
        scope = (self.args.scope or client.scope or
                 [x for Client in self.Clients for x in Client.scope])

        # Apply scope to session
        session = client.session
        session.extend_scope(scope)

        # Obtain authorization code via browser, if applicable
        code = self.args.code
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
    def execute(client):
        client.session.storage.delete()
