import configparser
import os.path
import sys

topdir = os.path.abspath('..')
sys.path.insert(0, topdir)

config = configparser.ConfigParser()
config.read(os.path.join(topdir, 'setup.cfg'))

project = config['metadata']['name']
author = config['metadata']['author']
copyright = config['metadata']['copyright']
version = config['metadata']['version']
release = version

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
]

source_suffix = '.rst'
master_doc = 'index'
exclude_patterns = ['_build']
pygments_style = None
html_theme = 'alabaster'
