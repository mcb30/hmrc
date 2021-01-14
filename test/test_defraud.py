"""Test Fraud Prevention Headers API tests"""

from hmrc.api.defraud import DefraudClient
from . import TestCase, application


class DefraudTest(TestCase):
    """Test Fraud Prevention Headers API tests"""

    Client = DefraudClient

    @application
    def test_defraud(self, client):
        """Test fraud prevention headers"""
        msg = client.validate()
        self.assertFalse(msg.errors)
        self.assertFalse(msg.warnings)
        self.assertEqual(msg.code, 'VALID_HEADERS')
