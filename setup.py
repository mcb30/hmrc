#!/usr/bin/env python3

"""Setup script"""

from setuptools import setup, find_packages

setup(
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Environment :: Console",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: "
        "GNU General Public License v2 or later (GPLv2+)",
        "Programming Language :: Python :: 3",
        "Topic :: Office/Business :: Financial",
        "Topic :: Software Development :: Libraries",
    ],
    packages=find_packages(),
    install_requires=[
        'iso8601',
        'lxml',
        'parsedatetime',
        'psutil',
        'python-dateutil',
        'requests',
        'requests_oauthlib',
        'setuptools',
        'simplejson',
        'uritemplate',
        'urllib3',
        'xlrd',
    ],
    entry_points={
        'console_scripts': [
            'hmrc=hmrc.cli.registry:main',
        ],
        'hmrc.cli.command': [
            'login = hmrc.cli.base:LoginCommand',
            'hello = hmrc.cli.hello:HelloCommand',
            'hello application = hmrc.cli.hello:HelloApplicationCommand',
            'hello login = hmrc.cli.hello:HelloLoginCommand',
            'hello user = hmrc.cli.hello:HelloUserCommand',
            'hello world = hmrc.cli.hello:HelloWorldCommand',
            'vat = hmrc.cli.vat:VatCommand',
            'vat login = hmrc.cli.vat:VatLoginCommand',
            'vat obligations = hmrc.cli.vat:VatObligationsCommand',
            'vat return = hmrc.cli.vat:VatReturnCommand',
            'vat submit = hmrc.cli.vat:VatSubmitCommand',
            'vat csv submit = hmrc.plugins.csv:CsvVatSubmitCommand',
            'vat excel submit = hmrc.plugins.excel:ExcelVatSubmitCommand',
        ],
    },
)
