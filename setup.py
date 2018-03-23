#!/usr/bin/python
"""
Copyright (c) 2015 Red Hat, Inc
All rights reserved.

This software may be modified and distributed under the terms
of the BSD license. See the LICENSE file for details.
"""

import re
import sys

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

setup(
    name='dockerfile-parse',
    version='0.0.10',
    description='Python library for Dockerfile manipulation',
    author='Jiri Popelka',
    author_email='jpopelka@redhat.com',
    url='https://github.com/DBuildService/dockerfile-parse',
    license="BSD",
    packages=find_packages(exclude=["tests"]),
    install_requires=_install_requirements(),
    tests_require=_get_requirements('tests/requirements.txt'),
)

