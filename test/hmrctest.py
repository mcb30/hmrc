"""Test utilities"""

from configparser import ConfigParser
import functools
import os
from pathlib import Path
import shlex
import sys
from tempfile import NamedTemporaryFile
import unittest
from hmrc.api import HmrcClient
from hmrc.api.testuser import TestUserService, TestUserServices, TestUserClient
from hmrc.auth import (HmrcSession, HmrcTokenStorage, HmrcTokenFileStorage,
                       TestUserAuthClient)
from hmrc.cli.registry import commands

__all__ = [
    'TestCase',
    'anonymous',
    'application',
    'individual',
    'organisation',
]


class TestCase(unittest.TestCase):
    """HMRC API test suite"""

    CLIENT_ID = 'HMRC_CLIENT_ID'
    CLIENT_SECRET = 'HMRC_CLIENT_SECRET'
    SERVER_TOKEN = 'HMRC_SERVER_TOKEN'

    Client = HmrcClient
    Storage = HmrcTokenStorage

    @classmethod
    def setUpClass(cls):
        """Initialise test suite"""

        # Retrieve session parameters from test environment
        cls.client_id = os.environ.get(cls.CLIENT_ID, '')
        cls.client_secret = os.environ.get(cls.CLIENT_SECRET, '')
        cls.server_token = os.environ.get(cls.SERVER_TOKEN, None)

        # Construct anonymous and application-authorized clients
        cls.anonymous = cls.Client(HmrcSession(test=True))
        cls.application = cls.Client(HmrcSession(
            cls.client_id, client_secret=cls.client_secret,
            token=cls.server_token, storage=cls.Storage(), test=True,
        ))

        # Construct test user creation client
        cls.testuser = TestUserClient(HmrcSession(
            cls.client_id, client_secret=cls.client_secret,
            token=cls.server_token, storage=cls.Storage(), test=True,
        ))
        cls.individual = {}
        cls.organisation = {}

        # Construct configuration file
        cls.config = NamedTemporaryFile(mode='w+t')
        parser = ConfigParser()
        parser['DEFAULT'] = {
            'client_id': cls.client_id,
            'client_secret': cls.client_secret,
            'test': True,
        }
        if cls.server_token:
            parser['DEFAULT']['server_token'] = cls.server_token
        parser.write(cls.config)
        cls.config.flush()

        # Locate test files directory (if present)
        module = sys.modules[cls.__module__]
        cls.files = Path(module.__file__).parent / 'files'

    @classmethod
    def tearDownClass(cls):
        """Finalise test suite"""
        cls.anonymous.session.close()
        cls.application.session.close()
        cls.testuser.session.close()
        for client, _user in cls.individual.values():
            client.session.close()
        for client, _user in cls.organisation.values():
            client.session.close()
        cls.config.close()

    def skipIfNoCredentials(self):
        """Skip test unless application credentials are available"""
        if not self.application.session.client_id:
            self.skipTest("Missing %s" % self.CLIENT_ID)
        if not self.application.session.client_secret:
            self.skipTest("Missing %s" % self.CLIENT_SECRET)
        if not self.application.session.token:
            self.skipTest("Missing %s" % self.SERVER_TOKEN)

    def createUser(self, create, *services):
        """Create authorized client for a new test user"""
        service_names = [TestUserService(x) for x in services]
        user = create(TestUserServices(service_names=service_names))
        test_auth = TestUserAuthClient(client_id=self.client_id)
        session = HmrcSession(self.client_id, client=test_auth,
                              client_secret=self.client_secret,
                              storage=self.Storage(), test=True)
        client = self.Client(session)
        session.fetch_token(username=user.user_id, password=user.password)
        return client, user

    def createIndividual(self, *services):
        """Create authorized client for a new individual test user"""
        return self.createUser(self.testuser.create_individual, *services)

    def createOrganisation(self, *services):
        """Create authorized client for a new organisation test user"""
        return self.createUser(self.testuser.create_organisation, *services)

    def command(self, client, command):
        """Invoke command"""
        args = shlex.split(command)
        with NamedTemporaryFile(mode='w+t') as token:
            with HmrcTokenFileStorage(file=token) as storage:
                if client.session.storage is not None:
                    storage.save(client.session.storage.token)
                args.extend(['--config', self.config.name,
                             '--token', token.name])
                command = commands.command(args)
                return command()


def anonymous(func):
    """Decorator for a test case using no authorization"""
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        client = self.anonymous
        return func(self, client, *args, **kwargs)
    return wrapper


def application(func):
    """Decorator for a test case using application authorization"""
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        self.skipIfNoCredentials()
        client = self.application
        return func(self, client, *args, **kwargs)
    return wrapper


def individual(*services, key=None):
    """Decorator for a test case using an individual test user"""

    # Default to caching user by list of services
    if key is None:
        key = frozenset(services)

    # Construct decorator
    def decorate(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            self.skipIfNoCredentials()
            if key not in self.individual:
                self.individual[key] = self.createIndividual(*services)
            client, user = self.individual[key]
            return func(self, client, user, *args, **kwargs)
        return wrapper

    return decorate


def organisation(*services, key=None):
    """Decorator for a test case using an organisation test user"""

    # Default to caching user by list of services
    if key is None:
        key = frozenset(services)

    # Construct decorator
    def decorate(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            self.skipIfNoCredentials()
            if key not in self.organisation:
                self.organisation[key] = self.createOrganisation(*services)
            client, user = self.organisation[key]
            return func(self, client, user, *args, **kwargs)
        return wrapper

    return decorate
