"""HMRC API session with authorization support"""

from datetime import datetime
import getpass
import os
from pathlib import Path
import platform
import socket
from urllib.parse import urljoin, quote
import uuid
import psutil
from requests.adapters import HTTPAdapter
from requests_oauthlib import OAuth2Session
from urllib3.util.retry import Retry

__all__ = [
    'HmrcSession',
]

OAUTHLIB_INSECURE_TRANSPORT = 'OAUTHLIB_INSECURE_TRANSPORT'
"""Environment variable required for out-of-band authorization"""

UUID_NS = uuid.UUID('c9da8da2-c7e0-4873-97fc-6d783e908751')
"""Namespace for fraud prevention client identifiers"""

CLIENT_ID = 'Oo4p6xztJXMIMhpZQgLR3UccFnQN'
"""Client ID issued by HMRC"""

CLIENT_NON_SECRET = '114e4a63-6172-4348-81ec-c0282838fa12'
"""Client "secret" issued by HMRC

The client "secret" is associated with the codebase (rather than with
any individual user).  It does not itself grant access to any user
data: it merely allows the codebase to access the authentication
endpoints and to therefore direct the user through the real
authentication process.

There is zero point to this client "secret" from a security
perspective, but it is required by the HMRC API design.

Interested readers are politely requested to steal a client secret
from elsewhere, to avoid disruption to any users of this open-source
codebase.  HMRC publishes a list of authorised closed-source
applications that run locally (e.g. as VBA macros within an Excel
spreadsheet): please steal a secret from one of those instead.
"""


class HmrcSession(OAuth2Session):
    """HMRC API session"""

    BASE_URI = 'https://api.service.hmrc.gov.uk'
    BASE_TEST_URI = 'https://test-api.service.hmrc.gov.uk'

    AUTH_URI = '/oauth/authorize'
    TOKEN_URI = '/oauth/token'
    OOB_REDIRECT_URI = 'urn:ietf:wg:oauth:2.0:oob'

    def __init__(self, client_id=None, *, client_secret=None, test=False,
                 uri=None, token=None, storage=None, gdpr_consent=False,
                 **kwargs):

        # Construct base URI
        self.test = test
        if uri is None:
            self.uri = self.BASE_TEST_URI if self.test else self.BASE_URI

        # Set default out-of-band redirect URI
        kwargs.setdefault('redirect_uri', self.OOB_REDIRECT_URI)

        # Use default client credentials if none provided
        if client_id is None:
            client_id = CLIENT_ID
        if client_secret is None:
            client_secret = CLIENT_NON_SECRET
        self.client_secret = client_secret

        # Configure automatic token refresh
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

        # Use existing token's scope, if applicable
        scope = [] if token is None else token.get('scope', [])

        # Record GDPR consent status
        self.gdpr_consent = gdpr_consent or test

        # Call superclass
        super().__init__(client_id, scope=scope, token=token, **kwargs)

        # Configure automatic retries since API is unreliable
        retries = Retry(status_forcelist=[503])
        adapter = HTTPAdapter(max_retries=retries)
        self.mount('https://', adapter)
        self.mount('http://', adapter)

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

        # Force client_id to be included in request body
        kwargs.setdefault('include_client_id', True)

        # Include authorization URI to support test user flow
        kwargs.setdefault('auth_uri', self.authorization_url()[0])

        # Fetch token, allowing for use of out-of-band redirect URI
        saved = os.environ.get(OAUTHLIB_INSECURE_TRANSPORT)
        try:

            # Allow use of out-of-band redirect URI if applicable
            if self.redirect_uri == self.OOB_REDIRECT_URI:
                os.environ[OAUTHLIB_INSECURE_TRANSPORT] = '1'

            # Fetch token
            token = super().fetch_token(url, **kwargs)

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

    def request(self, method, url, params=None, data=None, headers=None,
                **kwargs):
        """Send request"""
        # pylint: disable=arguments-differ,too-many-arguments
        headers = {} if headers is None else headers.copy()
        headers.update(self.defraud())
        return super().request(method, url, params=params, data=data,
                               headers=headers, **kwargs)

    @staticmethod
    def dmifile(filename, default='Unknown'):
        """Read DMI file contents"""
        try:
            path = Path('/sys/devices/virtual/dmi/id/%s' % filename)
            return path.read_text(encoding='utf8').strip() or default
        except FileNotFoundError:
            return default

    def defraud(self):
        """Construct fraud prevention headers"""
        timestamp = datetime.utcnow().isoformat(timespec='milliseconds') + 'Z'
        headers = {
            'Gov-Client-Connection-Method': 'DESKTOP_APP_DIRECT',
            'Gov-Client-Device-ID': str(UUID_NS),
            'Gov-Client-Local-IPs': '127.0.0.1',
            'Gov-Client-Local-IPs-Timestamp': timestamp,
            'Gov-Client-MAC-Addresses': quote('52:54:00:12:34:56'),
            'Gov-Client-Multi-Factor': '',
            'Gov-Client-Screens': '&'.join([
                'width=1920',
                'height=1080',
                'scaling-factor=1',
                'colour-depth=24',
            ]),
            'Gov-Client-Timezone': 'UTC+00:00',
            'Gov-Client-User-Agent': '&'.join([
                'os-family=Linux',
                'os-version=1',
                'device-manufacturer=Intel',
                'device-model=Computer',
            ]),
            'Gov-Client-User-IDs': 'os=user',
            'Gov-Client-Window-Size': 'width=640&height=480',
            'Gov-Vendor-License-IDs': 'hmrc=497427732047504C2C20626974636821',
            'Gov-Vendor-Product-Name': quote('Python API'),
            'Gov-Vendor-Version': 'hmrc=1.1.3',
        }
        if self.gdpr_consent:
            nics = psutil.net_if_addrs()
            headers['Gov-Client-Local-IPs'] = ','.join(sorted(
                quote(addr.address) for nic in nics.values() for addr in nic
                if addr.family == socket.AF_INET
            ))
            headers['Gov-Client-MAC-Addresses'] = ','.join(sorted(
                quote(addr.address) for nic in nics.values() for addr in nic
                if addr.family == psutil.AF_LINK
            ))
            headers['Gov-Client-Device-ID'] = str(uuid.uuid5(
                UUID_NS, headers['Gov-Client-MAC-Addresses']
            ))
            tzsec = datetime.now().astimezone().utcoffset().total_seconds()
            tzmin = tzsec / 60
            if tzmin >= 0:
                (tzhour, tzmin) = divmod(tzmin, 60)
            else:
                (tzhour, tzmin) = divmod(-tzmin, 60)
                tzhour = -tzhour
            headers['Gov-Client-Timezone'] = 'UTC%+03d:%02d' % (tzhour, tzmin)
            headers['Gov-Client-User-Agent'] = '&'.join([
                'os-family=%s' % quote(platform.system()),
                'os-version=%s' % quote(platform.release()),
                'device-manufacturer=%s' % quote(self.dmifile('sys_vendor')),
                'device-model=%s' % quote(self.dmifile('product_family')),
            ])
            headers['Gov-Client-User-IDs'] = 'os=%s' % getpass.getuser()
        return headers
