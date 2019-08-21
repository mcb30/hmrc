"""HMRC API token storage"""

from dataclasses import dataclass, InitVar
import json
import os
import stat
from tempfile import TemporaryFile
from typing import TextIO

__all__ = [
    'HmrcTokenStorage',
    'HmrcTokenFileStorage',
]


@dataclass
class HmrcTokenStorage:
    """OAuth2 token storage"""

    token: dict = None
    """Token value"""

    def __post_init__(self):

        # Automatically load token if not explicitly specified
        if self.token is None:
            self.token = {}
            self.load()

    def load(self):
        """Load token from storage"""
        return self.token

    def save(self, token):
        """Save token to storage"""
        self.token = token

    def close(self):
        """Close storage medium"""


@dataclass
class HmrcTokenFileStorage(HmrcTokenStorage):
    """OAuth2 token storage in a local JSON file"""

    file: TextIO = None
    """File used to store JSON representation of OAuth2 token"""

    path: InitVar[str] = None
    """Path to file"""

    def __post_init__(self, path):
        # pylint: disable=arguments-differ

        # Open/create file if no explicit file was provided
        if self.file is None:
            if path is None:
                self.file = TemporaryFile(mode='w+t')
            else:
                fd = os.open(path, (os.O_RDWR | os.O_CREAT),
                             (stat.S_IRUSR | stat.S_IWUSR))
                self.file = open(fd, 'a+t')

        super().__post_init__()

    def load(self):
        """Load token from JSON file"""
        self.file.seek(0)
        data = self.file.read()
        self.token = json.loads(data) if data else {}
        return super().load()

    def save(self, token):
        """Save token to JSON file"""
        super().save(token)
        data = json.dumps(self.token)
        self.file.seek(0)
        self.file.truncate(0)
        self.file.write(data)
        self.file.flush()

    def close(self):
        """Close file"""
        self.file.close()
