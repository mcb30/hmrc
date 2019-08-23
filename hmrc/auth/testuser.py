"""Test user automatic authorization"""

from dataclasses import dataclass
import re
from urllib.parse import urljoin
from requests import Session
from lxml import html

__all__ = [
    'TestUserAuth',
]


@dataclass
class TestUserAuth:
    """Test user automatic authorization

    The authorization code will be obtained automatically using the
    test user's credentials.
    """

    user_id: str
    password: str

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

    def authorize(self, uri, _state):
        """Obtain authorization code using test user ID and password"""

        # Construct temporary session
        with Session() as session:

            # Get starting page
            uri, page = self.fetch_auth_page(session, uri)

            # Click on the initial "Continue" button
            href = page.find('.//a[@class="button"]').get('href')
            uri, page = self.fetch_auth_page(session, urljoin(uri, href))

            # Submit sign in form
            form = page.find('.//form')
            form.find('.//input[@id="userId"]').set('value', self.user_id)
            form.find('.//input[@id="password"]').set('value', self.password)
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

    __call__ = authorize
