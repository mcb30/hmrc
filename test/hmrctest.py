"""Test utilities"""

import functools
import os
import unittest
from hmrc.api import HmrcClient
from hmrc.api.testuser import TestUserService, TestUserServices, TestUserClient
from hmrc.auth import HmrcSession, TestUserSession

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

    @classmethod
    def setUpClass(cls):
        """Initialise test suite"""

        # Retrieve session parameters from test environment
        cls.client_id = os.environ.get(cls.CLIENT_ID)
        cls.client_secret = os.environ.get(cls.CLIENT_SECRET)
        cls.server_token = os.environ.get(cls.SERVER_TOKEN)

        # Construct anonymous and application-authorized clients
        cls.anonymous = cls.Client(HmrcSession(test=True))
        cls.application = cls.Client(HmrcSession(
            cls.client_id, client_secret=cls.client_secret,
            token=cls.server_token, test=True,
        ))

        # Construct test user creation client
        cls.testuser = TestUserClient(HmrcSession(
            cls.client_id, client_secret=cls.client_secret,
            token=cls.server_token, test=True,
        ))
        cls.individual = {}
        cls.organisation = {}

    @classmethod
    def tearDownClass(cls):
        """Finalise test suite"""
        cls.anonymous.session.close()
        cls.application.session.close()
        cls.testuser.session.close()
        for client in cls.individual.values():
            client.session.close()
        for client in cls.organisation.values():
            client.session.close()

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
        client = self.Client(TestUserSession(
            self.client_id, client_secret=self.client_secret, user=user,
        ))
        client.session.fetch_token()
        return client

    def createIndividual(self, *services):
        """Create authorized client for a new individual test user"""
        return self.createUser(self.testuser.create_individual, *services)

    def createOrganisation(self, *services):
        """Create authorized client for a new organisation test user"""
        return self.createUser(self.testuser.create_organisation, *services)


def anonymous(func):
    """Decorator for a test case using no authorization"""
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        return func(self, self.anonymous, *args, **kwargs)
    return wrapper

def application(func):
    """Decorator for a test case using application authorization"""
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        self.skipIfNoCredentials()
        return func(self, self.application, *args, **kwargs)
    return wrapper

def individual(*services, key=None):
    """Decorator for a test case using an individual test user"""
    if key is None:
        key = frozenset(services)
    def decorate(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            self.skipIfNoCredentials()
            if key not in self.individual:
                self.individual[key] = self.createIndividual(*services)
            return func(self, self.individual[key], *args, **kwargs)
        return wrapper
    return decorate

def organisation(*services, key=None):
    """Decorator for a test case using an organisation test user"""
    if key is None:
        key = frozenset(services)
    def decorate(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            self.skipIfNoCredentials()
            if key not in self.organisation:
                self.organisation[key] = self.createOrganisation(*services)
            return func(self, self.organisation[key], *args, **kwargs)
        return wrapper
    return decorate
