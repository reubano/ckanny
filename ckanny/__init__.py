# -*- coding: utf-8 -*-
# vim: sw=4:ts=4:expandtab

"""
ckanny
~~~~~~

Miscellaneous CKAN utility scripts

Examples:
    literal blocks::

        python example_google.py

Attributes:
    module_level_variable1 (int): Module level variables may be documented in
"""

from __future__ import (
    absolute_import, division, print_function, with_statement,
    unicode_literals)

from manager import Manager
from . import datastorer, filestorer, package, hdx

__version__ = '0.17.2'

__title__ = 'ckanny'
__author__ = 'Reuben Cummings'
__description__ = 'Miscellaneous CKAN utility scripts'
__email__ = 'reubano@gmail.com'
__license__ = 'MIT'
__copyright__ = 'Copyright 2015 Reuben Cummings'

manager = Manager()
manager.merge(datastorer.manager, namespace='ds')
manager.merge(filestorer.manager, namespace='fs')
manager.merge(hdx.manager, namespace='hdx')
manager.merge(package.manager, namespace='pk')


@manager.command
def ver():
    """Show ckanny version"""
    print('v%s' % __version__)

if __name__ == '__main__':
    manager.main()
