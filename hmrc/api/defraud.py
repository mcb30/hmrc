"""Test Fraud Prevention Headers API"""

from dataclasses import dataclass
from typing import List
from .data import HmrcDataClass, hmrcdataclass
from .client import HmrcClient, HmrcEndpoint

__all__ = [
    'DefraudMessage',
    'DefraudClient',
]


@hmrcdataclass
class DefraudError(HmrcDataClass):
    """Test Fraud Prevention Headers error message"""
    code: str
    message: str
    headers: List[str]


@hmrcdataclass
class DefraudMessage(HmrcDataClass):
    """Test Fraud Prevention Headers message"""
    spec_version: str
    code: str
    message: str
    warnings: List[DefraudError] = None
    errors: List[DefraudError] = None


@dataclass
class DefraudClient(HmrcClient):
    """Test Fraud Prevention Headers API client"""

    validate = HmrcEndpoint('test/fraud-prevention-headers/validate',
                            response=DefraudMessage)
