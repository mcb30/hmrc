"""VAT API tests"""

from datetime import date, datetime
from decimal import Decimal
from hmrc.api import HmrcClientError
from hmrc.api.vat import VatObligationStatus, VatSubmission, VatClient
from hmrc.api.testuser import TestUserService
from . import TestCase, organisation


class VatTest(TestCase):
    """VAT API tests"""

    Client = VatClient

    @organisation(TestUserService.MTD_VAT)
    def test_monthly_obs_05_open(self, client, user):
        """Test scenario with monthly obligations: 4 fulfilled, 1 open"""
        obligations = client.obligations(
            vrn=user.vrn, from_=date(2018, 1, 1), to=date(2018, 12, 31),
            scenario='MONTHLY_OBS_05_OPEN',
        )
        self.assertEqual(len(obligations.obligations), 5)
        january = obligations.obligations[0]
        self.assertEqual(january.end, date(2018, 1, 31))
        self.assertEqual(january.status, VatObligationStatus.FULFILLED)
        fulfilled = [x for x in obligations.obligations
                     if x.status == VatObligationStatus.FULFILLED]
        self.assertEqual(len(fulfilled), 4)
        may = obligations.obligations[-1]
        self.assertEqual(may.start, date(2018, 5, 1))
        self.assertEqual(may.due, date(2018, 7, 7))
        self.assertIsNone(may.received)

    @organisation(TestUserService.MTD_VAT)
    def test_submit_retrieve(self, client, user):
        """Test submission and retrieval of a VAT return"""
        submission = VatSubmission(
            period_key='18AA',
            vat_due_sales=Decimal('100.30'),
            vat_due_acquisitions=Decimal('100.02'),
            total_vat_due=Decimal('200.32'),
            vat_reclaimed_curr_period=Decimal('100.00'),
            net_vat_due=Decimal('100.32'),
            total_value_sales_ex_vat=500,
            total_value_purchases_ex_vat=500,
            total_value_goods_supplied_ex_vat=500,
            total_acquisitions_ex_vat=500,
            finalised=True,
        )
        confirmation = client.submit(submission, vrn=user.vrn)
        self.assertIsInstance(confirmation.processing_date, datetime)
        self.assertTrue(confirmation.form_bundle_number)
        retrieved = client.retrieve(vrn=user.vrn, period_key='18AA')
        self.assertEqual(retrieved.period_key, '18AA')
        self.assertEqual(retrieved.net_vat_due, Decimal('100.32'))
        self.assertEqual(retrieved.total_value_sales_ex_vat, 500)
        with self.assertRaises(HmrcClientError) as ctx:
            client.submit(submission, vrn=user.vrn)
        exc = ctx.exception
        self.assertEqual(exc.error.code, 'BUSINESS_ERROR')
        self.assertEqual(len(exc.error.errors), 1)
        self.assertEqual(exc.error.errors[0].code, 'DUPLICATE_SUBMISSION')
        self.assertIn(exc.error.errors[0].message, str(exc))
