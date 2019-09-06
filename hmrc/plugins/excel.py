"""Excel data formats"""

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from xlrd import open_workbook, xldate_as_datetime, XL_CELL_DATE
from .tabular import (TabularTypeParser, TabularDataClass, TabularCommand,
                      TabularVatReturn, TabularVatSubmitCommand,
                      tabulardataclass)

PENCE = Decimal('0.01')


@dataclass
class ExcelTypeParser(TabularTypeParser):
    """Excel type parser"""

    def __post_init__(self):
        if self.parse is None:
            if issubclass(self.pytype, datetime):
                self.parse = lambda x: x
            elif issubclass(self.pytype, date):
                self.parse = lambda x: x.date()
            elif issubclass(self.pytype, Decimal):
                self.parse = lambda x: Decimal.from_float(x).quantize(PENCE)
        super().__post_init__()


class ExcelDataClass(TabularDataClass):
    """Excel data class"""

    TypeParser = ExcelTypeParser


@tabulardataclass
class ExcelVatReturn(ExcelDataClass, TabularVatReturn):
    """VAT return from Excel data"""


class ExcelCommand(TabularCommand):
    """Excel file command"""

    @classmethod
    def init_parser(cls, parser):
        super().init_parser(parser)
        parser.add_argument('filename', help="Excel file")
        parser.add_argument('--sheet', help="Worksheet name", default='VAT')

    @contextmanager
    def data(self):
        with open_workbook(self.args.filename) as workbook:

            # Get selected worksheet
            sheet = workbook.sheet_by_name(self.args.sheet)

            # Get date mode for this workbook
            datemode = workbook.datemode

            def excel_value(cell, datemode=datemode):
                """Parse raw cell value"""
                if cell.ctype == XL_CELL_DATE:
                    return xldate_as_datetime(cell.value, datemode=datemode)
                return cell.value

            yield ([excel_value(x) for x in row] for row in sheet.get_rows())


class ExcelVatSubmitCommand(ExcelCommand, TabularVatSubmitCommand):
    """Submit VAT return(s) from Excel file"""

    Row = ExcelVatReturn
