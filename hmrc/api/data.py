"""HMRC API data representation

Data structures used within API messages are represented in Python
using `dataclasses`, with the mapping between the Python
representation and the HMRC API wire protocol representation handled
automatically via introspection of the Python type annotations.

>>> from decimal import Decimal
>>> @hmrcdataclass
... class TaxPeriodSummary(HmrcDataClass):
...     tax_id: str
...     start: date
...     end: date
...     total_income: Decimal
...     tax_due: Decimal

>>> t1 = TaxPeriodSummary.from_json('''
...     {
...         "taxId": "82719NH23A",
...         "start": "2018-04-06",
...         "end": "2019-04-05",
...         "totalIncome": 38600.00,
...         "taxDue": 2412.50
...     }
... ''')

>>> t1.tax_id
'82719NH23A'

>>> t1.start.year
2018

>>> t1.total_income
Decimal('38600.00')

>>> t1.to_hmrc() # doctest: +NORMALIZE_WHITESPACE
{'taxId': '82719NH23A', 'start': '2018-04-06', 'end': '2019-04-05',
 'totalIncome': Decimal('38600.00'), 'taxDue': Decimal('2412.50')}

>>> t1.tax_due -= Decimal('100.00')

>>> t1.to_hmrc() # doctest: +NORMALIZE_WHITESPACE
{'taxId': '82719NH23A', 'start': '2018-04-06', 'end': '2019-04-05',
 'totalIncome': Decimal('38600.00'), 'taxDue': Decimal('2312.50')}

>>> t2 = TaxPeriodSummary(
...    tax_id = '543242WD69B',
...    start = date(2015, 6, 24),
...    end = date(2016, 6, 23),
...    total_income = Decimal('14000.00'),
...    tax_due = Decimal('0.00'),
... )

>>> t2.to_hmrc() # doctest: +NORMALIZE_WHITESPACE
{'taxId': '543242WD69B', 'start': '2015-06-24', 'end': '2016-06-23',
 'totalIncome': Decimal('14000.00'), 'taxDue': Decimal('0.00')}

>>> t2.to_json() # doctest: +NORMALIZE_WHITESPACE
'{"taxId": "543242WD69B", "start": "2015-06-24", "end": "2016-06-23",
  "totalIncome": 14000.00, "taxDue": 0.00}'
"""

from dataclasses import dataclass, fields
from datetime import date, datetime
from enum import Enum
import re
from typing import Callable
import iso8601
import simplejson

__all__ = [
    'HmrcUnknownFieldError',
    'HmrcFieldMap',
    'HmrcTypeMap',
    'HmrcDataClass',
    'hmrcdataclass',
]


class HmrcUnknownFieldError(KeyError):
    """Unexpected HMRC API field"""

    def __str__(self):
        return 'Unknown field "%s" in %r' % self.args


@dataclass
class HmrcFieldMap:
    """A mapping between a Python dataclass field and an HMRC API field"""

    name: str
    """Python field name"""

    from_hmrc: Callable
    """Construct Python value from HMRC API value"""

    to_hmrc: Callable
    """Convert Python value to HMRC API value"""

    hmrc_name: str = None
    """HMRC field name"""

    def __post_init__(self):
        if self.hmrc_name is None:
            self.hmrc_name = self.default_hmrc_name()

    def default_hmrc_name(self):
        """Construct default HMRC API field name from Python field name

        The Python field name is converted from snake_case to camelCase.
        """
        return re.sub(r'_(\w?)', lambda m: m.group(1).upper(), self.name)


class HmrcTypeMap:
    """Mapper between Python field values and HMRC API field values"""

    @classmethod
    def from_hmrc(cls, pytype):
        """Construct Python value from HMRC API value"""

        # Recurse into list types
        if ((isinstance(pytype, type) and issubclass(pytype, list)) or
                (getattr(pytype, '__origin__', None) is list)):
            subtype = pytype.__args__[0]
            subtype_from_hmrc = cls.from_hmrc(subtype)
            return lambda l: [subtype_from_hmrc(x) for x in l]

        # Recurse into embedded HmrcDataClass instances
        if hasattr(pytype, 'from_hmrc'):
            return pytype.from_hmrc

        # Parse ISO8601 format datetimes.  Note that the "Z" suffix
        # cannot be handled by datetime.fromisoformat()
        if issubclass(pytype, datetime):
            return iso8601.parse_date

        # Parse ISO8601 format dates
        if issubclass(pytype, date):
            return pytype.fromisoformat

        # Otherwise, assume constructor can handle the HMRC value
        return pytype

    @classmethod
    def to_hmrc(cls, pytype):
        """Convert Python value to HMRC API value"""

        # Recurse into list types
        if ((isinstance(pytype, type) and issubclass(pytype, list)) or
                (getattr(pytype, '__origin__', None) is list)):
            subtype = pytype.__args__[0]
            subtype_to_hmrc = cls.to_hmrc(subtype)
            return lambda l: [subtype_to_hmrc(x) for x in l]

        # Recurse into embedded HmrcDataClass instances
        if hasattr(pytype, 'to_hmrc'):
            return pytype.to_hmrc

        # Format dates and datetimes as ISO8601
        if issubclass(pytype, date):
            return lambda x: x.isoformat()

        # Format enumerations using the enum value
        if issubclass(pytype, Enum):
            return lambda x: x.value

        # Otherwise, assume constructor produces a valid HMRC value
        return pytype


class HmrcDataClass:
    """HMRC data class"""

    FieldMap = HmrcFieldMap
    """Field mapping class"""

    TypeMap = HmrcTypeMap
    """Type mapping class"""

    __mapping_by_name = {}
    __mapping_by_hmrc_name = {}
    __known_hmrc_names = set()

    @classmethod
    def build_hmrc_mappings(cls):
        """Construct mappings between Python fields and HMRC API fields"""
        mappings = [cls.FieldMap(
            name=f.name,
            hmrc_name=f.metadata.get('name'),
            from_hmrc=cls.TypeMap.from_hmrc(f.type),
            to_hmrc=cls.TypeMap.to_hmrc(f.type),
        ) for f in fields(cls)]
        cls.__mapping_by_name = {m.name: m for m in mappings}
        cls.__mapping_by_hmrc_name = {m.hmrc_name: m for m in mappings}
        cls.__known_hmrc_names = set(cls.__mapping_by_hmrc_name)

    @classmethod
    def from_hmrc(cls, hmrc):
        """Construct Python object from HMRC API representation"""
        mapping = cls.__mapping_by_hmrc_name
        missing = set(hmrc) - cls.__known_hmrc_names
        if missing:
            raise HmrcUnknownFieldError(missing.pop(), hmrc) from None
        vals = {
            mapping[k].name: mapping[k].from_hmrc(v)
            for k, v in hmrc.items()
        }
        return cls(**vals)

    def to_hmrc(self):
        """Convert Python object to HMRC API representation"""
        mapping = self.__mapping_by_name
        hmrc = {
            v.hmrc_name: v.to_hmrc(getattr(self, k))
            for k, v in mapping.items()
            if getattr(self, k) is not None
        }
        return hmrc

    @classmethod
    def from_json(cls, json, *, loads=simplejson.loads):
        """Construct Python object from JSON representation"""
        return cls.from_hmrc(loads(json, use_decimal=True))

    def to_json(self, *, dumps=simplejson.dumps):
        """Convert Python object to JSON representation"""
        return dumps(self.to_hmrc(), use_decimal=True)


def hmrcdataclass(cls):
    """HMRC data class decorator"""
    cls = dataclass(cls)
    cls.build_hmrc_mappings()
    return cls
