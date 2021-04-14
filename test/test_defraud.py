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
        self.assertEqual(len(msg.warnings), 1)
        self.assertEqual(set(header.lower()
                             for warning in msg.warnings
                             for header in warning.headers),
                         {'gov-client-multi-factor'})
        self.assertEqual(set(warning.code for warning in msg.warnings),
                         {'EMPTY_HEADER'})
        self.assertEqual(msg.code, 'POTENTIALLY_INVALID_HEADERS')
