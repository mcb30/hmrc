"""Test user automatic authorization"""

import re
from urllib.parse import urljoin
from oauthlib.oauth2 import WebApplicationClient
from requests import Session
from lxml import html

__all__ = [
    'TestUserAuthClient',
]

DUMMY_AUTH_CODE = True
"""Dummy authorization code

This is required to convince requests_oauthlib that an authorization
code is available, despite not being passed as a parameter to
:meth:`fetch_token`.
"""


class TestUserAuthClient(WebApplicationClient):
    """Test user OAuth2 authorization client

    This may be used as a drop-in replacement for
    :class:`oauthlib.oauth2.LegacyApplicationClient`.  It provides an
    OAuth2 client capable of obtaining an access token using a test
    user's username and password.

    Note that the HMRC API sandbox does not actually support the
    RFC6749 Resource Owner Password Credentials grant type.  Instead,
    this OAuth2 client steps through the HMRC API sandbox login pages,
    filling in the HTML forms as required.

    This OAuth2 client is usable only for test user accounts created
    using :mod:`hmrc.api.testuser`.
    """

    def __init__(self, client_id, code=DUMMY_AUTH_CODE, **kwargs):
        super().__init__(client_id, code=code, **kwargs)

    @staticmethod
    def fetch_auth_page(session, uri, *args, method='GET', **kwargs):
        """Fetch an authorization journey page"""
        rsp = session.request(method, uri, *args, **kwargs)
        rsp.raise_for_status()
        return rsp.url, html.fromstring(rsp.content)

    def fetch_auth_page_form(self, session, uri, form, *args, **kwargs):
        """Fetch an authorization journey page via a form submission"""
        inputs = form.findall('.//input')
        method = form.get('method')
        uri = urljoin(uri, form.get('action'))
        data = {x.get('name'): x.get('value') for x in inputs}
        return self.fetch_auth_page(session, uri, *args, method=method,
                                    data=data, **kwargs)

    def authorize(self, uri, username, password):
        """Obtain authorization code using test user ID and password"""

        # Construct temporary session
        with Session() as session:

            # Get starting page
            uri, page = self.fetch_auth_page(session, uri)

            # Click on the initial "Continue" button
            href = page.find('.//a[@role="button"]').get('href')
            uri, page = self.fetch_auth_page(session, urljoin(uri, href))

            # Click on the "Sign in to Government Gateway" button
            href = page.find('.//a[@role="button"]').get('href')
            uri, page = self.fetch_auth_page(session, urljoin(uri, href))

            # Submit sign in form
            form = page.find('.//form')
            form.find('.//input[@id="userId"]').set('value', username)
            form.find('.//input[@id="password"]').set('value', password)
            uri, page = self.fetch_auth_page_form(session, uri, form)

            # Submit authorisation form
            form = page.find('.//form')
            uri, page = self.fetch_auth_page_form(session, uri, form)

            # Extract code from page title
            title = page.find('head//title').text
            m = re.match(r'Success.+code=(?P<code>[0-9a-f]+)', title, re.I)
            if not m:
                raise IOError("Could not identify code from '%s'" % title)
            return m.group('code')

    def prepare_request_body(self, auth_uri, username, password, code=None,
                             **kwargs):
        """Prepare access token request body"""
        # pylint: disable=arguments-differ,bad-option-value,arguments-renamed
        if code == DUMMY_AUTH_CODE or not code:
            code = self.authorize(auth_uri, username, password)
        return super().prepare_request_body(code=code, **kwargs)
