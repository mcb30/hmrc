"""Hello World API"""

from dataclasses import dataclass
from .data import HmrcDataClass, hmrcdataclass
from .client import HmrcClient, HmrcEndpoint

__all__ = [
    'HelloMessage',
    'HelloClient',
]


@hmrcdataclass
class HelloMessage(HmrcDataClass):
    """Hello World message"""
    message: str


@dataclass
class HelloClient(HmrcClient):
    """Hello World API client"""

    scope = ['hello']

    world = HmrcEndpoint('/hello/world', response=HelloMessage)

    user = HmrcEndpoint('/hello/user', response=HelloMessage)

    application = HmrcEndpoint('/hello/application', response=HelloMessage)
