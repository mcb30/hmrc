"""HMRC client"""

from dataclasses import dataclass, fields
import functools
from typing import ClassVar, List
from urllib.parse import urljoin
from requests import HTTPError
from uritemplate import URITemplate
from ..auth.session import HmrcSession
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
        # pylint: disable=no-member
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
class HmrcClient:
    """HMRC API client"""

    session: HmrcSession
    """Requests session"""

    scope: ClassVar[List[str]] = []
    """Authorisation scopes"""

    REQUEST_CONTENT_TYPE = 'application/json'
    RESPONSE_CONTENT_TYPE = 'application/vnd.hmrc.1.0+json'

    def __post_init__(self):
        self.session.extend_scope(self.scope)

    def request(self, uri, *, method='GET', query=None, body=None,
                scenario=None):
        """Send request"""

        # Create required headers
        headers = {
            'Content-Type': self.REQUEST_CONTENT_TYPE,
            'Accept': self.RESPONSE_CONTENT_TYPE,
        }

        # Add test scenario header, if applicable
        if scenario is not None:
            headers['Gov-Test-Scenario'] = scenario

        # Construct request
        rsp = self.session.request(method, urljoin(self.session.uri, uri),
                                   headers=headers, params=query, data=body)

        # Check for errors
        try:
            rsp.raise_for_status()
        except HTTPError as exc:

            # Add response body to exception message
            exc.args = tuple(tuple(exc.args) + (rsp.text,))

            # Try to parse error response body
            try:
                error = HmrcErrorResponse.from_json(rsp.text)
            except Exception:
                raise exc from None

            # Raise chained exception
            raise HmrcClientError(error) from exc

        return rsp.text


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

    def __call__(self, client, *args, scenario=None, **kwargs):
        """Call endpoint"""

        # Extract any path parameter arguments and construct URI
        path_kwargs = {k: kwargs.pop(k, None) for k in self.path_args}
        path_kwargs = {k: v if v is not None else getattr(client, k)
                       for k, v in path_kwargs.items()}
        path = self.path(**path_kwargs).to_hmrc()
        uri = self.template.expand(path)

        # Construct query parameters from remaining arguments
        query = self.query(**kwargs).to_hmrc()

        # Construct request body, if applicable
        if args:
            (data,) = args
            if not hasattr(data, 'to_json'):
                data = self.request(**data)
            req = data.to_json()
        else:
            req = None

        # Issue request
        rsp = client.request(uri, method=self.method, query=query, body=req,
                             scenario=scenario)

        # Construct response
        return self.response.from_json(rsp)
