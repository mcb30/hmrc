"""HMRC API session with authorization support"""

import os
from urllib.parse import urljoin
from requests_oauthlib import OAuth2Session

__all__ = [
    'HmrcSession',
]

OAUTHLIB_INSECURE_TRANSPORT = 'OAUTHLIB_INSECURE_TRANSPORT'
"""Environment variable required for out-of-band authorization"""


class HmrcSession(OAuth2Session):
    """HMRC API session"""

    BASE_URI = 'https://api.service.hmrc.gov.uk'
    BASE_TEST_URI = 'https://test-api.service.hmrc.gov.uk'

    AUTH_URI = '/oauth/authorize'
    TOKEN_URI = '/oauth/token'
    OOB_REDIRECT_URI = 'urn:ietf:wg:oauth:2.0:oob'

    def __init__(self, client_id=None, *, client_secret=None, test=False,
                 uri=None, token=None, storage=None, **kwargs):

        # Construct base URI
        self.test = test
        if uri is None:
            self.uri = self.BASE_TEST_URI if self.test else self.BASE_URI

        # Set default out-of-band redirect URI
        kwargs.setdefault('redirect_uri', self.OOB_REDIRECT_URI)

        # Configure automatic token refresh if client secret is provided
        self.client_secret = client_secret
        if self.client_secret is not None:
            kwargs.setdefault('auto_refresh_url',
                              urljoin(self.uri, self.TOKEN_URI))
            kwargs.setdefault('auto_refresh_kwargs', {
                'client_id': client_id,
                'client_secret': client_secret,
            })

        # Allow server token to be passed as a plain string
        if isinstance(token, str):
            token = {'access_token': token, 'token_type': 'bearer'}

        # Use token storage if provided
        self.storage = storage
        if self.storage is not None:
            if token is None:
                token = self.storage.token
            kwargs.setdefault('token_updater', self.storage.save)

        super().__init__(client_id, scope=[], token=token, **kwargs)

    def __repr__(self):
        return '%s(%r, uri=%r, scope=%r)' % (
            self.__class__.__name__, self.client_id, self.uri, self.scope
        )

    def extend_scope(self, scope):
        """Extend OAuth2 scope"""
        current = set(self.scope)
        self.scope = self.scope + [x for x in scope if x not in current]

    def authorization_url(self, url=None, **kwargs):
        """Form an authorization URL"""
        # pylint: disable=arguments-differ
        if url is None:
            url = urljoin(self.uri, self.AUTH_URI)
        return super().authorization_url(url, **kwargs)

    def fetch_token(self, url=None, **kwargs):
        """Fetch an access token"""
        # pylint: disable=arguments-differ

        # Use default token URI if none provided
        if url is None:
            url = urljoin(self.uri, self.TOKEN_URI)

        # Use stored client secret if available
        kwargs.setdefault('client_secret', self.client_secret)

        # Fetch token, allowing for use of out-of-band redirect URI
        try:

            # Allow use of out-of-band redirect URI if applicable
            saved = os.environ.get(OAUTHLIB_INSECURE_TRANSPORT)
            if self.redirect_uri == self.OOB_REDIRECT_URI:
                os.environ[OAUTHLIB_INSECURE_TRANSPORT] = '1'

            # Fetch token
            token = super().fetch_token(url, include_client_id=True, **kwargs)

        finally:

            # Restore environment
            if saved is None:
                del os.environ[OAUTHLIB_INSECURE_TRANSPORT]
            else:
                os.environ[OAUTHLIB_INSECURE_TRANSPORT] = saved

        # Store token if storage is available
        if self.storage:
            self.storage.save(token)

        return token
