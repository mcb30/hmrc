"""CSV data formats"""

from contextlib import contextmanager
import csv
from dataclasses import dataclass
from datetime import date, datetime
from typing import ClassVar
from parsedatetime import Calendar
from .tabular import (TabularTypeParser, TabularDataClass, TabularCommand,
                      TabularVatReturn, TabularVatSubmitCommand,
                      tabulardataclass)

__all__ = [
    'CsvTypeParser',
    'CsvDataClass',
    'CsvVatReturn',
    'CsvCommand',
    'CsvVatSubmitCommand',
]


@dataclass
class CsvTypeParser(TabularTypeParser):
    """CSV type parser"""

    calendar: ClassVar[Calendar] = Calendar()
    """Calendar object used for date parsing"""

    def __post_init__(self):
        if self.parse is None:
            if issubclass(self.pytype, datetime):
                self.parse = self.parse_datetime
            elif issubclass(self.pytype, date):
                self.parse = self.parse_date
        super().__post_init__()

    @classmethod
    def parse_datetime(cls, value):
        """Parse datetime from CSV value"""
        timestamp, ret = cls.calendar.parseDT(value)
        if not ret:
            raise ValueError("Invalid date: '%s'" % value)
        return timestamp

    @classmethod
    def parse_date(cls, value):
        """Parse date from CSV value"""
        return cls.parse_datetime(value).date()


class CsvDataClass(TabularDataClass):
    """CSV data class"""

    TypeParser = CsvTypeParser


@tabulardataclass
class CsvVatReturn(CsvDataClass, TabularVatReturn):
    """VAT return from CSV data"""


class CsvCommand(TabularCommand):
    """CSV file command"""

    @classmethod
    def init_parser(cls, parser):
        super().init_parser(parser)
        parser.add_argument('filename', help="CSV file")

    @contextmanager
    def data(self):
        with open(self.args.filename, encoding='utf8') as f:
            yield csv.reader(f)


class CsvVatSubmitCommand(CsvCommand, TabularVatSubmitCommand):
    """Submit VAT return(s) from CSV file"""

    Row = CsvVatReturn
