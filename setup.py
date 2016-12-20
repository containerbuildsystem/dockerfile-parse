#!/usr/bin/python
"""
Copyright (c) 2015 Red Hat, Inc
All rights reserved.

This software may be modified and distributed under the terms
of the BSD license. See the LICENSE file for details.
"""

import re

from setuptools import setup, find_packages

setup(
    name='dockerfile-parse',
    version='0.0.6',
    description='Python library for Dockerfile manipulation',
    author='Jiri Popelka',
    author_email='jpopelka@redhat.com',
    url='https://github.com/DBuildService/dockerfile-parse',
    license="BSD",
    packages=find_packages(exclude=["tests"]),
)

