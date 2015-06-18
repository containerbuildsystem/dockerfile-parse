#!/usr/bin/python
"""
Copyright (c) 2015 Red Hat, Inc
All rights reserved.

This software may be modified and distributed under the terms
of the BSD license. See the LICENSE file for details.
"""

import re

from setuptools import setup, find_packages

def _get_requirements(path):
    try:
        with open(path) as f:
            packages = f.read().splitlines()
    except (IOError, OSError) as ex:
        raise RuntimeError("Can't open file with requirements: %s", repr(ex))
    packages = (p.strip() for p in packages if not re.match("^\s*#", p))
    packages = list(filter(None, packages))
    return packages

def _install_requirements():
    requirements = _get_requirements('requirements.txt')
    return requirements

setup(
    name='dockerfile-parser',
    version='0.0.1',
    description='Python library for Dockerfile manipulation',
    author='Jiri Popelka',
    author_email='jpopelka@redhat.com',
    url='https://github.com/DBuildService/dockerfile',
    license="BSD",
    packages=find_packages(exclude=["tests"]),
    install_requires=_install_requirements(),
)

