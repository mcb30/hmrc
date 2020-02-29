"""VAT API command line interface"""

from datetime import date
from decimal import Decimal
from enum import Enum
from dateutil.relativedelta import relativedelta
from . import Command, LoginCommand, datestring
from ..api.vat import VatClient, VatObligationStatus, VatSubmission

__all__ = [
    'VatBox',
    'format_vat_return',
    'VatCommand',
    'VatLoginCommand',
    'VatObligationsCommand',
    'VatSubmitCommand',
    'VatReturnCommand',
]

MAX_RANGE = relativedelta(years=1, days=-1)

ZERO = Decimal('0.00')

PENCE = Decimal('0.01')


class VatBox(Enum):
    """VAT form box descriptions"""

    BOX1 = "VAT due on sales"
    BOX2 = "VAT due on acquisitions"
    BOX3 = "Total VAT due"
    BOX4 = "VAT reclaimed"
    BOX5 = "Net VAT due"
    BOX6 = "Total sales (ex VAT)"
    BOX7 = "Total purchases (ex VAT)"
    BOX8 = "Total supplies (ex VAT)"
    BOX9 = "Total acquisitions (ex VAT)"


def format_vat_return(ret, draft=False):
    """Format a VAT return (or submission) for human consumption"""
    output = ['%-28s %17s' % (k.value + ':', v.quantize(PENCE)) for k, v in (
        (VatBox.BOX1, ret.vat_due_sales),
        (VatBox.BOX2, ret.vat_due_acquisitions),
        (VatBox.BOX3, ret.total_vat_due),
        (VatBox.BOX4, ret.vat_reclaimed_curr_period),
        (VatBox.BOX5, ret.net_vat_due),
    )] + ['%-28s %14d' % (k.value + ':', v) for k, v in (
        (VatBox.BOX6, ret.total_value_sales_ex_vat),
        (VatBox.BOX7, ret.total_value_purchases_ex_vat),
        (VatBox.BOX8, ret.total_value_goods_supplied_ex_vat),
        (VatBox.BOX9, ret.total_acquisitions_ex_vat),
    )]
    if draft:
        banner = '%33s' % "--- DRAFT RETURN ---"
        output.insert(0, banner)
        output.append(banner)
    return output


class VatCommand(Command):
    """VAT commands"""

    section = 'vat'

    Client = VatClient

    @classmethod
    def init_parser(cls, parser):
        super().init_parser(parser)
        parser.add_argument('--vrn', help="VAT registration number")


class VatLoginCommand(VatCommand, LoginCommand):
    """Log in to VAT API"""


class VatObligationsCommand(VatCommand):
    """Retrieve VAT obligations"""

    @classmethod
    def init_parser(cls, parser):
        super().init_parser(parser)
        parser.add_argument('--from', dest='from_', metavar='FROM',
                            type=datestring, help="Start date")
        parser.add_argument('--to', type=datestring, help="End date")
        group = parser.add_mutually_exclusive_group()
        group.add_argument('--all', dest='status', action='store_const',
                           const=None, help="Find all obligations")
        group.add_argument('--open', dest='status', action='store_const',
                           const=VatObligationStatus.OPEN,
                           help="Find only open obligations (default)")
        group.add_argument('--fulfilled', dest='status', action='store_const',
                           const=VatObligationStatus.FULFILLED,
                           help="Find only fulfilled obligations")
        parser.set_defaults(status=VatObligationStatus.OPEN)

    def execute(self, client):

        # Construct a date range acceptable to the API
        if not self.args.to:
            self.args.to = (
                self.args.from_ + MAX_RANGE if self.args.from_ else
                None if self.args.status == VatObligationStatus.OPEN else
                date.today()
            )
        if self.args.to and not self.args.from_:
            self.args.from_ = self.args.to - MAX_RANGE

        # Retrieve obligations
        obligations = client.obligations(
            scenario=self.args.scenario, vrn=self.args.vrn, to=self.args.to,
            from_=self.args.from_, status=self.args.status,
        )

        # Display obligations
        return ["%s: [%s, %s] due %s %s" % (
            obligation.period_key, obligation.start, obligation.end,
            obligation.due, obligation.status.name
        ) for obligation in obligations.obligations]


class VatSubmitCommand(VatCommand):
    """Submit VAT return"""

    @classmethod
    def init_parser(cls, parser):
        super().init_parser(parser)
        parser.add_argument('key', help="Period key")
        parser.add_argument('--vat-sales', type=Decimal, default=ZERO,
                            help=VatBox.BOX1.value)
        parser.add_argument('--vat-acquisitions', type=Decimal, default=ZERO,
                            help=VatBox.BOX2.value)
        parser.add_argument('--vat-reclaimed', type=Decimal, default=ZERO,
                            help=VatBox.BOX4.value)
        parser.add_argument('--total-sales', type=int, default=0,
                            help=VatBox.BOX6.value)
        parser.add_argument('--total-purchases', type=int, default=0,
                            help=VatBox.BOX7.value)
        parser.add_argument('--total-supplies', type=int, default=0,
                            help=VatBox.BOX8.value)
        parser.add_argument('--total-acquisitions', type=int, default=0,
                            help=VatBox.BOX9.value)
        parser.add_argument('--finalise', action='store_true',
                            help="Finalise return")

    def execute(self, client):
        total_vat_due = self.args.vat_sales + self.args.vat_acquisitions
        net_vat_due = abs(total_vat_due - self.args.vat_reclaimed)
        submission = VatSubmission(
            period_key=self.args.key,
            vat_due_sales=self.args.vat_sales,
            vat_due_acquisitions=self.args.vat_acquisitions,
            total_vat_due=total_vat_due,
            vat_reclaimed_curr_period=self.args.vat_reclaimed,
            net_vat_due=net_vat_due,
            total_value_sales_ex_vat=self.args.total_sales,
            total_value_purchases_ex_vat=self.args.total_purchases,
            total_value_goods_supplied_ex_vat=self.args.total_supplies,
            total_acquisitions_ex_vat=self.args.total_acquisitions,
            finalised=self.args.finalise,
        )
        output = format_vat_return(submission, draft=not self.args.finalise)
        if self.args.finalise:
            client.submit(submission, scenario=self.args.scenario,
                          vrn=self.args.vrn)
        return output


class VatReturnCommand(VatCommand):
    """Retrieve VAT return"""

    @classmethod
    def init_parser(cls, parser):
        super().init_parser(parser)
        parser.add_argument('key', help="Period key")

    def execute(self, client):
        ret = client.retrieve(scenario=self.args.scenario, vrn=self.args.vrn,
                              period_key=self.args.key)
        return format_vat_return(ret)
