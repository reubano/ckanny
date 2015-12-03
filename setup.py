#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import ckanny
import pkutils

from os import path as p

try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup, find_packages

sys.dont_write_bytecode = True
requirements = list(pkutils.parse_requirements('requirements.txt'))
dependencies = list(pkutils.parse_requirements('requirements.txt', dep=True))
dev_requirements = list(pkutils.parse_requirements('dev-requirements.txt'))
readme = pkutils.read('README.md')
changes = pkutils.read('CHANGES.rst').replace('.. :changelog:', '')
license = ckanny.__license__
version = ckanny.__version__
title = ckanny.__title__
gh = 'https://github.com/reubano'

setup(
    name=title,
    version=version,
    description=ckanny.__description__,
    long_description=readme + '\n\n' + changes,
    author=ckanny.__author__,
    author_email=ckanny.__email__,
    url='%s/%s' % (gh, title),
    download_url='%s/%s/downloads/%s*.tgz' % (gh, title, title),
    packages=find_packages(exclude=['docs', 'tests']),
    include_package_data=True,
    install_requires=requirements,
    dependency_links=dependencies,
    tests_require=dev_requirements,
    license=license,
    zip_safe=False,
    keywords=[title],
    package_data={},
    classifiers=[
        pkutils.LICENSES[license],
        'Development Status :: 4 - Beta',
        'Natural Language :: English',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'Operating System :: POSIX',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX :: Linux',
    ],
    platforms=['MacOS X', 'Windows', 'Linux'],
    scripts=[p.join('bin', 'ckanny')],
)
