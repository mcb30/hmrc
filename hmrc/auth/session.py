"""HMRC API session with authorization support"""

from urllib.parse import urljoin
from requests_oauthlib import OAuth2Session

__all__ = [
    'HmrcSession',
]


class HmrcSession(OAuth2Session):
    """HMRC API session"""

    BASE_URI = 'https://api.service.hmrc.gov.uk'
    BASE_TEST_URI = 'https://test-api.service.hmrc.gov.uk'

    AUTH_URI = '/oauth/authorize'
    TOKEN_URI = '/oauth/token'

    def __init__(self, client_id=None, *, client_secret=None, test=False,
                 uri=None, **kwargs):

        # Construct base URI
        self.test = test
        if uri is None:
            self.uri = self.BASE_TEST_URI if self.test else self.BASE_URI

        # Configure automatic token refresh if client secret is provided
        self.client_secret = client_secret
        if self.client_secret is not None:
            kwargs.setdefault('auto_refresh_url',
                              urljoin(self.uri, self.TOKEN_URI))
            kwargs.setdefault('auto_refresh_kwargs', {
                'client_id': client_id,
                'client_secret': client_secret,
            })

        super().__init__(client_id, scope=[], **kwargs)

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
        if url is None:
            url = urljoin(self.uri, self.TOKEN_URI)
        kwargs.setdefault('client_secret', self.client_secret)
        return super().fetch_token(url, **kwargs)
