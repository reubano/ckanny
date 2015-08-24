#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" A script to manage development tasks """

from __future__ import (
    absolute_import, division, print_function, with_statement,
    unicode_literals)

from os import path as p
from manager import Manager
from subprocess import call

manager = Manager()
_basedir = p.dirname(__file__)


@manager.command
def clean():
    """Remove Python file and build artifacts"""
    call(p.join(_basedir, 'helpers', 'clean'), shell=True)


@manager.command
def check():
    """Check staged changes for lint errors"""
    call(p.join(_basedir, 'helpers', 'check-stage'), shell=True)


@manager.command
def lint():
    """Check style with flake8"""
    call('flake8 ckanutils tests', shell=True)


@manager.command
def pipme():
    """Install requirements.txt"""
    call('pip install -r requirements.txt', shell=True)


@manager.command
def require():
    """Create requirements.txt"""
    cmd = 'pip freeze -l | grep -vxFf dev-requirements.txt > requirements.txt'
    call(cmd, shell=True)


@manager.command
def test():
    """Run nose and script tests"""
    call(p.join(_basedir, 'helpers', 'test'), shell=True)


@manager.command
def register():
    """Register package with PyPI"""
    call('python setup.py register')


@manager.command
def release():
    """Package and upload a release"""
    sdist()
    wheel()
    upload


@manager.command
def build():
    """Create a source distribution and wheel package"""
    sdist()
    wheel()


@manager.command
def upload():
    """Upload distribution files"""
    call('twine upload %s' % p.join(_basedir, 'dist', '*'), shell=True)


@manager.command
def sdist():
    """Create a source distribution package"""
    call(p.join(_basedir, 'helpers', 'sdist'), shell=True)


@manager.command
def wheel():
    """Create a wheel package"""
    call(p.join(_basedir, 'helpers', 'wheel'), shell=True)


if __name__ == '__main__':
    manager.main()
