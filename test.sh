#!/bin/sh

set -e
set -x

# Run test suite with coverage checks
#
python3 -m coverage erase
python3 -m coverage run --branch --source hmrc setup.py test
python3 -m coverage report --show-missing

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
if python3 -m pylint .pylint-check.py >/dev/null 2>/dev/null ; then
    python3 -m pylint hmrc test
else
    echo Skipping pylint check
fi

# Run mypy
#
python3 -m mypy hmrc test

# Run pycodestyle
#
python3 -m pycodestyle hmrc test
