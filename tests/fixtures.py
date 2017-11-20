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


@pytest.fixture(params=[(use_fileobj, cache_content) for use_fileobj in [True, False] for cache_content in [True, False]])
def dfparser(tmpdir, request):
    """

    :param tmpdir: already existing fixture defined in pytest
    :param request: parameter, cache_content arg to DockerfileParser
    :return: DockerfileParser instance
    """

    use_fileobj, cache_content = request.param
    if use_fileobj:
        file = six.BytesIO()
        return DockerfileParser(fileobj=file, cache_content=cache_content)
    else:
        tmpdir_path = str(tmpdir.realpath())
        return DockerfileParser(path=tmpdir_path, cache_content=cache_content)


@pytest.fixture(params=['LABEL', 'ENV'])
def instruction(request):
    """
    Parametrized fixture which enables to run a test once for each instruction in params
    """
    return request.param
