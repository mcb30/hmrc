#!/bin/sh

set -e
set -x

coverage3 erase
coverage3 run --branch --source hmrc setup.py test
coverage3 report --show-missing
