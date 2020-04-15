# -*- coding: utf-8 -*-
"""
Copyright (c) 2015 Red Hat, Inc
All rights reserved.

This software may be modified and distributed under the terms
of the BSD license. See the LICENSE file for details.
"""
from __future__ import unicode_literals, absolute_import

from sys import version_info

# from python-six
PY2 = version_info[0] == 2

DOCKERFILE_FILENAME = 'Dockerfile'
COMMENT_INSTRUCTION = 'COMMENT'
