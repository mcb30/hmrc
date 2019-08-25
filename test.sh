#!/bin/sh

set -e
set -x

# Run test suite with coverage checks
#
coverage3 erase
coverage3 run --branch --source hmrc setup.py test
coverage3 report --show-missing

# Run pylint
#
# Note that pylint is currently broken on Python 3.8 beta, so run only
# if sanity check passes.  This check should be removable once Python
# 3.8 is released.
#
cat > .pylint-check.py <<EOF
"""Pylint sanity check"""
from typing import Type
check = Type
EOF
if pylint .pylint-check.py >/dev/null 2>/dev/null ; then
    pylint hmrc
else
    echo Skipping pylint check
fi

# Run mypy
#
mypy hmrc

# Run pycodestyle
#
python3 -m pycodestyle hmrc
