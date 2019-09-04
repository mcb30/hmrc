"""Hello World API command line interface"""

from . import Command, LoginCommand
from ..api.hello import HelloClient

__all__ = [
    'HelloCommand',
    'HelloLoginCommand',
    'HelloWorldCommand',
    'HelloApplicationCommand',
    'HelloUserCommand',
]


class HelloCommand(Command):
    """Hello World commands"""

    section = 'hello'

    Client = HelloClient


class HelloLoginCommand(HelloCommand, LoginCommand):
    """Log in to Hello World API"""
    pass


class HelloWorldCommand(HelloCommand):
    """Test endpoint with no authorization"""

    @staticmethod
    def execute(client):
        return client.world().message


class HelloApplicationCommand(HelloCommand):
    """Test endpoint with application authorization"""

    @staticmethod
    def execute(client):
        return client.application().message


class HelloUserCommand(HelloCommand):
    """Test endpoint with user authorization"""

    @staticmethod
    def execute(client):
        return client.user().message
