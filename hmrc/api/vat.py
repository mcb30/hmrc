"""VAT API"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import List
from .data import HmrcFieldMap, HmrcDataClass, hmrcdataclass
from .client import HmrcClient, HmrcEndpoint

__all__ = [
    'VatObligationStatus',
    'VatPaymentIndicator',
    'VatVrnParams',
    'VatVrnPeriodParams',
    'VatObligationsParams',
    'VatObligation',
    'VatObligations',
    'VatReturn',
    'VatSubmission',
    'VatConfirmation',
    'VatClient',
]


class VatFieldMap(HmrcFieldMap):
    """VAT field mapping customisation"""

    def default_hmrc_name(self):
        """Construct default HMRC API field name from Python field name

        The VAT API fields ending with "ExVAT" do not follow the usual
        camelCase convention for HMRC API field names.
        """
        return super().default_hmrc_name().replace('ExVat', 'ExVAT')


class VatDataClass(HmrcDataClass):
    """VAT data class"""

    FieldMap = VatFieldMap


class VatObligationStatus(Enum):
    """Obligation status"""
    OPEN = 'O'
    FULFILLED = 'F'


class VatPaymentIndicator(Enum):
    """Payment method"""
    DIRECT_DEBIT = 'DD'
    DIRECT_CREDIT = 'BANK'


@hmrcdataclass
class VatVrnParams(VatDataClass):
    """Parameter list: VAT registration number only"""
    vrn: str


@hmrcdataclass
class VatVrnPeriodParams(VatVrnParams):
    """Parameter list: VAT registration number and period key"""
    period_key: str


@hmrcdataclass
class VatObligationsParams(VatDataClass):
    """Parameter list: VAT obligations search criteria"""
    from_: date = None
    to: date = None
    status: VatObligationStatus = None


@hmrcdataclass
class VatObligation(VatDataClass):
    """VAT obligation"""
    start: date
    end: date
    due: date
    status: VatObligationStatus
    period_key: str
    received: date = None


@hmrcdataclass
class VatObligations(VatDataClass):
    """List of VAT obligations"""
    obligations: List[VatObligation]


@hmrcdataclass
class VatReturn(VatDataClass):
    """VAT return"""
    period_key: str
    vat_due_sales: Decimal
    vat_due_acquisitions: Decimal
    total_vat_due: Decimal
    vat_reclaimed_curr_period: Decimal
    net_vat_due: Decimal
    total_value_sales_ex_vat: int
    total_value_purchases_ex_vat: int
    total_value_goods_supplied_ex_vat: int
    total_acquisitions_ex_vat: int


@hmrcdataclass
class VatSubmission(VatReturn):
    """VAT return submission"""
    finalised: bool


@hmrcdataclass
class VatConfirmation(VatDataClass):
    """VAT return submission confirmation"""
    processing_date: datetime
    payment_indicator: VatPaymentIndicator
    form_bundle_number: str = None
    charge_ref_number: str = None


@dataclass
class VatClient(HmrcClient):
    """VAT API client"""

    scope = ['read:vat', 'write:vat']

    obligations = HmrcEndpoint(
        '/organisations/vat/{vrn}/obligations',
        path=VatVrnParams, query=VatObligationsParams, response=VatObligations,
    )

    submit = HmrcEndpoint(
        '/organisations/vat/{vrn}/returns',
        path=VatVrnParams, request=VatSubmission, response=VatConfirmation,
    )

    retrieve = HmrcEndpoint(
        '/organisations/vat/{vrn}/returns/{periodKey}',
        path=VatVrnPeriodParams, response=VatReturn,
    )

    def __init__(self, vrn, *, token=None, test=False):
        super().__init__(token=token, test=test)
        self.vrn = vrn
