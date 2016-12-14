# -*- coding: utf-8 -*-
"""
Copyright (c) 2015 Red Hat, Inc
All rights reserved.

This software may be modified and distributed under the terms
of the BSD license. See the LICENSE file for details.
"""

from __future__ import unicode_literals

import pytest
import six

from dockerfile_parse import DockerfileParser


@pytest.fixture(params=[(dockerfile, cache_content) for dockerfile in ['fileobj', 'path'] for cache_content in [True, False]])
def dfparser(tmpdir, request):
    """

    :param tmpdir: already existing fixture defined in pytest
    :param request: parameter, cache_content arg to DockerfileParser
    :return: DockerfileParser instance
    """

    if request.param[1] == 'path':
        tmpdir_path = str(tmpdir.realpath())
        return DockerfileParser(path=tmpdir_path, cache_content=request.param[0])
    else:
        file = six.StringIO()
        return DockerfileParser(fileobj=file, cache_content=request.param[0])


@pytest.fixture(params=['LABEL', 'ENV'])
def instruction(request):
    """
    Parametrized fixture which enables to run a test once for each instruction in params
    """
    return request.param
