"""Hello World API tests"""

from hmrc.api import HmrcClientError
from hmrc.api.hello import HelloClient
from . import TestCase, anonymous, application, individual, organisation


class HelloTest(TestCase):
    """Hello World API tests"""

    Client = HelloClient

    @anonymous
    def test_world(self, client):
        """Test open access endpoint"""
        msg = client.world()
        self.assertEqual(msg.message, "Hello World")
        with self.assertRaises(HmrcClientError):
            client.application()
        with self.assertRaises(HmrcClientError):
            client.user()

    @application
    def test_application(self, client):
        """Test application-restricted endpoint"""
        msg = client.world()
        self.assertEqual(msg.message, "Hello World")
        msg = client.application()
        self.assertEqual(msg.message, "Hello Application")
        with self.assertRaises(HmrcClientError):
            client.user()

    @individual()
    def test_individual(self, client, _user):
        """Test user-restricted endpoint with individual test user"""
        msg = client.world()
        self.assertEqual(msg.message, "Hello World")
        msg = client.application()
        self.assertEqual(msg.message, "Hello Application")
        msg = client.user()
        self.assertEqual(msg.message, "Hello User")

    @organisation()
    def test_organisation(self, client, _user):
        """Test user-restricted endpoint with organisation test user"""
        msg = client.world()
        self.assertEqual(msg.message, "Hello World")
        msg = client.application()
        self.assertEqual(msg.message, "Hello Application")
        msg = client.user()
        self.assertEqual(msg.message, "Hello User")


class HelloCommandTest(TestCase):
    """Hello World command line tests"""

    Client = HelloClient

    @anonymous
    def test_world(self, client):
        """Test open access endpoint"""
        output = self.command(client, "hello world")
        self.assertEqual(output, "Hello World")

    @application
    def test_application(self, client):
        """Test application-restricted endpoint"""
        output = self.command(client, "hello application")
        self.assertEqual(output, "Hello Application")

    @individual()
    def test_user(self, client, _user):
        """Test user-restricted endpoint"""
        output = self.command(client, "hello user")
        self.assertEqual(output, "Hello User")
