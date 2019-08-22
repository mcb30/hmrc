"""Test user authentication"""

import re
from urllib.parse import urljoin
from requests import Session
from lxml import html
from .session import HmrcSession

__all__ = [
    'TestUserSession',
]


class TestUserSession(HmrcSession):
    """HMRC API session with test user credentials"""

    def __init__(self, client_id=None, *, user=None, **kwargs):
        super().__init__(client_id, test=True, **kwargs)
        self.user = user

    def fetch_token(self, url=None, *, code=None, **kwargs):
        """Fetch an access token

        The authorization code will be obtained automatically using
        the test user's credentials.
        """
        # pylint: disable=arguments-differ
        if code is None:
            code = self.authorize_test_user(self.user.user_id,
                                            self.user.password)
        return super().fetch_token(url, code=code, **kwargs)

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

    def authorize_test_user(self, user_id, password):
        """Obtain authorization code using test user ID and password"""

        # Construct temporary session
        with Session() as session:

            # Get starting page
            uri, _state = self.authorization_url()
            uri, page = self.fetch_auth_page(session, uri)

            # Click on the initial "Continue" button
            href = page.find('.//a[@class="button"]').get('href')
            uri, page = self.fetch_auth_page(session, urljoin(uri, href))

            # Submit sign in form
            form = page.find('.//form')
            form.find('.//input[@id="userId"]').set('value', user_id)
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
