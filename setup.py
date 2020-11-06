#!/usr/bin/python
"""
Copyright (c) 2015 Red Hat, Inc
All rights reserved.

This software may be modified and distributed under the terms
of the BSD license. See the LICENSE file for details.
"""

import re
import sys
import io

from os import path
from setuptools import setup, find_packages

def _get_requirements(path):
    try:
        with open(path) as f:
            packages = f.read().splitlines()
    except (IOError, OSError) as ex:
        raise RuntimeError("Can't open file with requirements: %s", repr(ex))
    return [p.strip() for p in packages if not re.match(r"^\s*#", p)]

def _install_requirements():
    requirements = _get_requirements('requirements.txt')
    if sys.version_info[0] >= 3:
        requirements += _get_requirements('requirements-py3.txt')
    return requirements

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with io.open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='dockerfile-parse',
    version='1.1.0',
    description='Python library for Dockerfile manipulation',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Jiri Popelka',
    author_email='jpopelka@redhat.com',
    url='https://github.com/containerbuildsystem/dockerfile-parse',
    license="BSD",
    packages=find_packages(exclude=["tests"]),
    install_requires=_install_requirements(),
    tests_require=_get_requirements('tests/requirements.txt'),
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Other Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
)

