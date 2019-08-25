"""Token refresh tests"""

from hmrc.api.hello import HelloClient
from . import TestCase, individual


class TokenRefreshTest(TestCase):
    """Token refresh tests"""

    Client = HelloClient

    @individual()
    def test_refresh(self, client, _user):
        """Test ability to refresh an expired token"""

        # Get existing token
        storage = client.session.storage
        old = client.session.token
        self.assertEqual(old, storage.token)

        # Expire existing token
        del old['expires_at']
        old['expires_in'] = 0
        client.session.token = old

        # Issue API call to trigger token refresh
        msg = client.user()
        self.assertEqual(msg.message, "Hello User")

        # Check that token has been refreshed
        new = client.session.token
        self.assertNotEqual(new['access_token'], old['access_token'])
        self.assertEqual(new, storage.token)
