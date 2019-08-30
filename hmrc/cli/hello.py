"""Hello World API command line interface"""

from .base import Command, LoginCommand
from ..api.hello import HelloClient

__all__ = [
    'HelloCommand',
    'HelloLoginCommand',
    'HelloWorldCommand',
    'HelloApplicationCommand',
    'HelloUserCommand',
]


class HelloCommand(Command, section=True):
    """Hello World commands"""

    Client = HelloClient


class HelloLoginCommand(HelloCommand, LoginCommand):
    """Log in to Hello World API"""
    pass


class HelloWorldCommand(HelloCommand):
    """Test endpoint with no authorization"""

    @staticmethod
    def execute(client, args):
        return client.world().message


class HelloApplicationCommand(HelloCommand):
    """Test endpoint with application authorization"""

    @staticmethod
    def execute(client, args):
        return client.application().message


class HelloUserCommand(HelloCommand):
    """Test endpoint with user authorization"""

    @staticmethod
    def execute(client, args):
        return client.user().message
