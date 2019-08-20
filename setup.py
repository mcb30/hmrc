#!/usr/bin/env python3

"""Setup script"""

from setuptools import setup, find_packages

setup(
    name="hmrc",
    description="HMRC API client library",
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author="Michael Brown",
    author_email="mbrown@fensystems.co.uk",
    url="https://github.com/mcb30/hmrc",
    license="GPLv2+",
    version="0.0.1",
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
        'oauthlib',
        'requests',
        'simplejson',
        'uritemplate',
    ],
)
