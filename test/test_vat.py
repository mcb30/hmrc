"""VAT API tests"""

from datetime import date, datetime
from decimal import Decimal
from requests import HTTPError
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


class VatCommandTest(TestCase):
    """VAT command line tests"""

    Client = VatClient

    @organisation(TestUserService.MTD_VAT)
    def test_monthly_two_met(self, client, user):
        """Test scenario with monthly obligations: 2 fulfilled, 1 open"""
        cmd = "vat obligations --vrn %s --scenario MONTHLY_TWO_MET" % user.vrn
        output = self.command(client, cmd)
        self.assertIn('FULFILLED', output[0])
        self.assertIn('FULFILLED', output[1])
        self.assertIn('OPEN', output[2])

    @organisation(TestUserService.MTD_VAT)
    def test_obligations_options(self, client, user):
        """Test ability to construct non-erroring search criteria"""
        self.command(client, "vat obligations --vrn %s" % user.vrn)
        self.command(client, "vat obligations --vrn %s --all" % user.vrn)
        self.command(client, "vat obligations --vrn %s --open" % user.vrn)
        self.command(client, "vat obligations --vrn %s --fulfilled" % user.vrn)
        self.command(client, ("vat obligations --vrn %s --all "
                              "--from 2018-04-01" % user.vrn))
        self.command(client, ("vat obligations --vrn %s --all "
                              "--to 2018-12-01" % user.vrn))
        self.command(client, ("vat obligations --vrn %s --all "
                              "--to 2020-02-29" % user.vrn))

    @organisation(TestUserService.MTD_VAT)
    def test_submit_draft(self, client, user):
        """Test construction of a draft VAT return"""
        cmd = (
            "vat submit --vrn %s --vat-sales 3442.79 --vat-reclaimed 742.15 "
            "--total-sales 17214 --total-purchases 3711 18AF"
            % user.vrn
        )
        output = self.command(client, cmd)
        self.assertIn('DRAFT', output[0])
        self.assertIn('DRAFT', output[-1])
        with self.assertRaises(HTTPError):
            self.command(client, "vat return --vrn %s 18AF" % user.vrn)

    @organisation(TestUserService.MTD_VAT)
    def test_submit_retrieve(self, client, user):
        """Test submission and retrieval of a VAT return"""
        cmd = (
            "vat submit --vrn %s --vat-sales 3442.79 --vat-reclaimed 742.15 "
            "--total-sales 17214 --total-purchases 3711 --finalise 18AE"
            % user.vrn
        )
        output = self.command(client, cmd)
        self.assertIn('3442.79', output[0])
        self.assertIn('3442.79', output[2])
        self.assertIn('742.15', output[3])
        self.assertIn('2700.64', output[4])
        self.assertIn('17214', output[5])
        self.assertIn('3711', output[6])
        check = self.command(client, "vat return --vrn %s 18AE" % user.vrn)
        self.assertEqual(check, output)

    @organisation(TestUserService.MTD_VAT)
    def test_csv(self, client, user):
        """Test CSV submission"""
        filename = self.files / 'vat_quarterly_obs.csv'
        cmd = ("vat csv submit --vrn %s --scenario QUARTERLY_OBS_02_OPEN "
               "--finalise %s" % (user.vrn, filename))
        self.command(client, cmd)
        retrieved = client.retrieve(vrn=user.vrn, period_key='18A2')
        self.assertEqual(retrieved.net_vat_due, Decimal('3753.51'))
        self.assertEqual(retrieved.total_value_sales_ex_vat, 41408)

    @organisation(TestUserService.MTD_VAT)
    def test_excel(self, client, user):
        """Test Excel submission"""
        filename = self.files / 'vat_quarterly_obs.xls'
        cmd = ("vat excel submit --vrn %s --scenario QUARTERLY_OBS_03_OPEN "
               "--finalise %s" % (user.vrn, filename))
        self.command(client, cmd)
        retrieved = client.retrieve(vrn=user.vrn, period_key='18A3')
        self.assertEqual(retrieved.net_vat_due, Decimal('5814.61'))
        self.assertEqual(retrieved.total_value_sales_ex_vat, 36314)
