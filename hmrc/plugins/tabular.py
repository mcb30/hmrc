"""Tabular data formats"""

from contextlib import contextmanager
from dataclasses import dataclass, field, fields
from datetime import date
from decimal import Decimal
from operator import itemgetter
from typing import Callable, ClassVar, Iterable, List, Mapping
from ..api.vat import VatObligationStatus, VatSubmission
from ..cli import Command
from ..cli.vat import VatBox, VatCommand, format_vat_return

__all__ = [
    'TabularTypeParser',
    'TabularDataClass',
    'tabulardataclass',
    'TabularNoData',
    'TabularRowReader',
    'TabularReader',
    'TabularColumn',
    'TabularCommand',
    'TabularVatReturn',
    'TabularVatSubmitCommand',
]

ZERO = Decimal('0.00')


@dataclass
class TabularTypeParser:
    """Tabular data type parser"""

    pytype: type
    """Target Python type"""

    parse: Callable = None
    """Value parser for this target Python type"""

    def __post_init__(self):
        if self.parse is None:
            self.parse = self.pytype


class TabularDataClass:
    """Tabular data class"""

    TypeParser = TabularTypeParser
    """Type parser class"""

    __parsers: ClassVar[Mapping[str, Callable]]
    """Type parsers for each dataclass field"""

    @classmethod
    def build_parsers(cls):
        """Construct type parsers for each dataclass field"""
        cls.__parsers = {
            f.name: cls.TypeParser(f.type).parse
            for f in fields(cls)
        }

    @classmethod
    def from_tabular(cls, **kwargs):
        """Construct Python object from tabular data"""
        parse = cls.__parsers
        return cls(**{k: parse[k](v) for k, v in kwargs.items()})


def tabulardataclass(cls):
    """Tabular data class decorator"""
    cls = dataclass(cls)
    cls.build_parsers()
    return cls


@tabulardataclass
class TabularNoData(TabularDataClass):
    """Empty tabular data"""


@dataclass
class TabularRowReader:
    """Tabular data row reader"""

    Row: type
    """Row data class"""

    headings: List[str]
    """Input column headings"""

    mapping: Mapping[str, str] = field(default_factory=dict)
    """Mapping from row data class field names to input column headings"""

    getters: Mapping[str, Callable] = field(default_factory=dict)
    """Item getters for each row data class field present in input columns"""

    def __post_init__(self):
        for f in fields(self.Row):
            heading = self.mapping.get(f.name, f.name)
            if heading in self.headings:
                # pylint: disable=unsupported-assignment-operation
                self.getters[f.name] = itemgetter(self.headings.index(heading))

    def __call__(self, row):
        """Construct row data class instance from input row data"""
        # pylint: disable=no-member
        return self.Row.from_tabular(**{
            k: v(row) for k, v in self.getters.items()
        })


@dataclass
class TabularReader:
    """Tabular data reader"""

    data: Iterable
    """Input data"""

    Row: type
    """Row class"""

    headings: List[str] = None
    """Input column headings"""

    mapping: Mapping[str, str] = field(default_factory=dict)
    """Mapping from output row field names to input column headings"""

    RowReader: ClassVar[type] = TabularRowReader
    """Data row reader class"""

    def __iter__(self):
        it = iter(self.data)
        headings = (
            self.headings if self.headings is not None else
            [str(x) for x in next(it)]
        )
        reader = self.RowReader(self.Row, headings, mapping=self.mapping)
        return (reader(row) for row in it)


@dataclass
class TabularColumn:
    """Tabular data column"""

    name: str
    """Column name"""

    description: str = None
    """Column description"""

    dest: str = None
    """Argument parser destination"""

    def __post_init__(self):
        if self.dest is None:
            self.dest = '%s_column' % self.name


class TabularCommand(Command):
    """Tabular data processing command"""

    Reader: ClassVar[type] = TabularReader
    """Data reader class"""

    Row: ClassVar[type] = TabularNoData
    """Row data class"""

    columns: ClassVar[List[TabularColumn]] = []
    """List of column definitions"""

    @classmethod
    def init_parser(cls, parser):
        super().init_parser(parser)
        for column in cls.columns:
            option = '--%s' % column.dest.replace('_', '-')
            description = column.description or column.name
            parser.add_argument(option, dest=column.dest, default=column.name,
                                help="Column heading for %s" % description)

    @contextmanager
    def data(self):
        """Read input data"""
        yield [()]

    @contextmanager
    def reader(self):
        """Construct data reader"""
        mapping = {x.name: getattr(self.args, x.dest) for x in self.columns}
        with self.data() as data:
            yield self.Reader(data, self.Row, mapping=mapping)


@tabulardataclass
class TabularVatReturn(TabularDataClass):
    """VAT return from tabular data"""

    end: date
    vat_sales: Decimal = ZERO
    vat_acquisitions: Decimal = ZERO
    vat_reclaimed: Decimal = ZERO
    total_sales: Decimal = ZERO
    total_purchases: Decimal = ZERO
    total_supplies: Decimal = ZERO
    total_acquisitions: Decimal = ZERO

    def submission(self, period_key, finalise=False):
        """Construct VAT submission"""
        total_vat_due = self.vat_sales + self.vat_acquisitions
        net_vat_due = abs(total_vat_due - self.vat_reclaimed)
        return VatSubmission(
            period_key=period_key,
            vat_due_sales=self.vat_sales,
            vat_due_acquisitions=self.vat_acquisitions,
            total_vat_due=total_vat_due,
            vat_reclaimed_curr_period=self.vat_reclaimed,
            net_vat_due=net_vat_due,
            total_value_sales_ex_vat=int(self.total_sales),
            total_value_purchases_ex_vat=int(self.total_purchases),
            total_value_goods_supplied_ex_vat=int(self.total_supplies),
            total_acquisitions_ex_vat=int(self.total_acquisitions),
            finalised=finalise,
        )


class TabularVatSubmitCommand(TabularCommand, VatCommand):
    """Submit VAT return(s) from tabular data"""

    Row = TabularVatReturn

    columns = [
        TabularColumn('end', "end date"),
        TabularColumn('vat_sales', VatBox.BOX1.value),
        TabularColumn('vat_acquisitions', VatBox.BOX2.value),
        TabularColumn('vat_reclaimed', VatBox.BOX4.value),
        TabularColumn('total_sales', VatBox.BOX6.value),
        TabularColumn('total_purchases', VatBox.BOX7.value),
        TabularColumn('total_supplies', VatBox.BOX8.value),
        TabularColumn('total_acquisitions', VatBox.BOX9.value),
    ]

    @classmethod
    def init_parser(cls, parser):
        super().init_parser(parser)
        parser.add_argument('--finalise', action='store_true',
                            help="Finalise return")

    def execute(self, client):

        # Get outstanding obligations, indexed by end date
        obligations = {
            x.end: x for x in client.obligations(
                vrn=self.args.vrn, scenario=self.args.scenario,
                status=VatObligationStatus.OPEN
            ).obligations
            # The sandbox API will stupidly ignore all search filters
            # (such as the stated obligation status) when using a
            # named test scenario, so filter the results.
            if x.status == VatObligationStatus.OPEN
        }

        # Construct submissions for which an open obligation exists
        with self.reader() as reader:
            submissions = [
                x.submission(obligations[x.end].period_key,
                             finalise=self.args.finalise)
                for x in reader
                if x.end in obligations
            ]

        # Construct command output
        output = [
            line for submission in submissions for line in
            format_vat_return(submission, draft=not submission.finalised)
        ]

        # Submit if applicable
        if self.args.finalise:
            for submission in submissions:
                client.submit(submission, vrn=self.args.vrn)

        return output
