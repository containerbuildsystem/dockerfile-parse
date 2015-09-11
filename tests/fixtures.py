# -*- coding: utf-8 -*-
"""
Copyright (c) 2015 Red Hat, Inc
All rights reserved.

This software may be modified and distributed under the terms
of the BSD license. See the LICENSE file for details.
"""

from __future__ import unicode_literals

import pytest

from dockerfile_parse import DockerfileParser


@pytest.fixture(params=[False, True])
def dfparser(tmpdir, request):
    """

    :param tmpdir: already existing fixture defined in pytest
    :param request: parameter, cache_content arg to DockerfileParser
    :return: DockerfileParser instance
    """
    tmpdir_path = str(tmpdir.realpath())
    return DockerfileParser(tmpdir_path, request.param)
