"""HMRC client"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, fields
import functools
from typing import List
from urllib.parse import urljoin
from requests import Request, Session, HTTPError
from oauthlib.oauth2.rfc6749.tokens import prepare_bearer_headers
from uritemplate import URITemplate
from .data import HmrcDataClass, hmrcdataclass

__all__ = [
    'HmrcNoData',
    'HmrcErrorDetail',
    'HmrcErrorResponse',
    'HmrcClientError',
    'HmrcClient',
    'HmrcEndpoint',
]


@hmrcdataclass
class HmrcNoData(HmrcDataClass):
    """Empty HMRC data class"""
    pass


@hmrcdataclass
class HmrcErrorDetail(HmrcDataClass):
    """Error description"""
    code: str
    message: str
    path: str = None
    reactivation_timestamp: int = None


@hmrcdataclass
class HmrcErrorResponse(HmrcErrorDetail):
    """Error response

    An error response comprises a top-level error description plus an
    optional list of contributory error descriptions.
    """
    errors: List[HmrcErrorDetail] = None


class HmrcClientError(IOError):
    """HMRC API exception

    This is used only when the server returns a recognisable HMRC
    error response representation.
    """

    def __str__(self):
        error = self.error
        if error.errors is None:
            return error.message
        return '%s: %s' % (error.message,
                           '/'.join(x.message for x in error.errors))

    @property
    def error(self):
        """The HMRC error response"""
        # pylint: disable=unsubscriptable-object
        return self.args[0]


@dataclass
class HmrcClient(ABC):
    """HMRC API client"""

    token: str = None
    """Authorisation token"""

    test: bool = False
    """Test mode"""

    BASE_URI = 'https://api.service.hmrc.gov.uk'
    BASE_TEST_URI = 'https://test-api.service.hmrc.gov.uk'
    REQUEST_CONTENT_TYPE = 'application/json'
    RESPONSE_CONTENT_TYPE = 'application/vnd.hmrc.1.0+json'

    def __post_init__(self):
        self.session = Session()

    def request(self, uri, *, method='GET', query=None, body=None):
        """Construct request"""

        # Create required headers
        headers = {
            'Content-Type': self.REQUEST_CONTENT_TYPE,
            'Accept': self.RESPONSE_CONTENT_TYPE,
        }

        # Add authorisation token, if available
        if self.token is not None:
            prepare_bearer_headers(self.token, headers)

        # Construct request
        req = Request(method, urljoin(self.uri, uri), headers=headers,
                      params=query, data=body)
        return req

    def response(self, req):
        """Submit request and obtain response"""

        # Prepare and send request
        rsp = self.session.send(req.prepare())

        # Check for errors
        try:
            rsp.raise_for_status()
        except HTTPError as exc:

            # Add response body to exception message
            exc.args = tuple(tuple(exc.args) + (rsp.text,))

            # Try to parse error response body
            try:
                error = HmrcErrorResponse.from_json(rsp.text)
            except:
                raise exc from None

            # Raise chained exception
            raise HmrcClientError(error) from exc

        return rsp

    @property
    def uri(self):
        """Service base URI"""
        return self.BASE_TEST_URI if self.test else self.BASE_URI

    @property
    @abstractmethod
    def scope(self):
        """Authorisation scopes"""
        pass


@dataclass
class HmrcEndpoint:
    """A callable API endpoint"""

    uri: str
    """Endpoint URI"""

    method: str = None
    """HTTP method"""

    path: type = HmrcNoData
    """URI path parameter type"""

    query: type = HmrcNoData
    """URI query parameter type"""

    request: type = HmrcNoData
    """Request body type"""

    response: type = HmrcNoData
    """Response body type"""

    def __post_init__(self):
        if self.method is None:
            self.method = 'GET' if self.request is HmrcNoData else 'POST'
        self.template = URITemplate(self.uri)
        self.path_args = {x.name for x in fields(self.path)}

    def __str__(self):
        return self.uri

    def __get__(self, instance, owner, partial=functools.partial):
        """Allow instances to function as callable methods on the instance"""
        if instance is None:
            return self
        return partial(self.__call__, instance)

    def __call__(self, client, *args, **kwargs):
        """Call endpoint"""

        # Extract any path parameter arguments and construct URI
        path_kwargs = {k: kwargs.pop(k) if k in kwargs else getattr(client, k)
                       for k in self.path_args}
        path = self.path(**path_kwargs).to_hmrc()
        uri = self.template.expand(path)

        # Construct query parameters from remaining arguments
        query = self.query(**kwargs).to_hmrc()

        # Construct request body, if applicable
        if args:
            (data,) = args
            if not hasattr(data, 'to_json'):
                data = self.request(**data)
            body = data.to_json().encode()
        else:
            body = None

        # Issue request
        req = client.request(uri, method=self.method, query=query, body=body)
        rsp = client.response(req)

        # Construct response
        return self.response.from_json(rsp.text)
