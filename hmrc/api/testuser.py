"""Create Test User API"""

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import List
from .data import HmrcDataClass, hmrcdataclass
from .client import HmrcClient, HmrcEndpoint

__all__ = [
    'TestUserService',
    'TestUserServices',
    'TestUserAddress',
    'TestUserIndividualDetails',
    'TestUserOrganisationDetails',
    'TestUser',
    'TestUserClient',
]


class TestUserService(Enum):
    """Service names for enrollment"""

    CORPORATION_TAX = 'corporation-tax'
    CUSTOMS_SERVICES = 'customs-services'
    LISA = 'lisa'
    MTD_INCOME_TAX = 'mtd-income-tax'
    MTD_VAT = 'mtd-vat'
    NATIONAL_INSURANCE = 'national-insurance'
    PAYE_FOR_EMPLOYERS = 'paye-for-employers'
    RELIEF_AT_SOURCE = 'relief-at-source'
    SECURE_ELECTRONIC_TRANSFER = 'secure-electronic-transfer'
    SELF_ASSESSMENT = 'self-assessment'
    SUBMIT_VAT_RETURNS = 'submit-vat-returns'


@hmrcdataclass
class TestUserServices(HmrcDataClass):
    """Services for which the test user should be enrolled"""
    service_names: List[TestUserService]


@hmrcdataclass
class TestUserAddress(HmrcDataClass):
    """Test user address"""
    line1: str
    line2: str
    postcode: str


@hmrcdataclass
class TestUserIndividualDetails(HmrcDataClass):
    """Individual test user details"""
    first_name: str
    last_name: str
    date_of_birth: date
    address: TestUserAddress


@hmrcdataclass
class TestUserOrganisationDetails(HmrcDataClass):
    """Organisation test user details"""
    name: str
    address: TestUserAddress


@hmrcdataclass
class TestUser(HmrcDataClass):
    """Organisation test user"""
    user_id: str
    password: str
    user_full_name: str
    email_address: str
    individual_details: TestUserIndividualDetails = None
    organisation_details: TestUserOrganisationDetails = None
    sa_utr: str = None
    nino: str = None
    mtd_it_id: str = None
    emp_ref: str = None
    ct_utr: str = None
    vrn: str = None
    vat_registration_date: date = None
    lisa_manager_reference_number: str = None
    secure_electronic_transfer_reference_number: str = None
    pension_scheme_administrator_identifier: str = None
    eori_number: str = None
    group_identifier: str = None


@dataclass
class TestUserClient(HmrcClient):
    """Create Test User API client"""

    test: bool = True

    scope = []

    create_individual = HmrcEndpoint('/create-test-user/individuals',
                                     request=TestUserServices,
                                     response=TestUser)

    create_organisation = HmrcEndpoint('/create-test-user/organisations',
                                       request=TestUserServices,
                                       response=TestUser)
