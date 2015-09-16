# -*- coding: utf-8 -*-
"""
Copyright (c) 2015 Red Hat, Inc
All rights reserved.

This software may be modified and distributed under the terms
of the BSD license. See the LICENSE file for details.
"""

from __future__ import print_function, unicode_literals

import shlex

from .constants import PY2


def b2u(string):
    """ bytes to unicode """
    if isinstance(string, bytes):
        return string.decode('utf-8')
    return string


def u2b(string):
    """ unicode to bytes (Python 2 only) """
    if PY2 and isinstance(string, unicode):
        return string.encode('utf-8')
    return string


def shlex_split(string):
    """
    Python2's shlex doesn't like unicode, so we have to convert the string
    into bytes, run shlex.split() and convert it back to unicode.
    """
    if PY2 and isinstance(string, unicode):
        string = u2b(string)
        # this takes care of quotes
        splits = shlex.split(string)
        return map(b2u, splits)
    else:
        return shlex.split(string)


def strip_quotes(string):
    """ strip first and last (double) quotes"""
    if string.startswith('"') and string.endswith('"'):
        return string[1:-1]
    if string.startswith("'") and string.endswith("'"):
        return string[1:-1]
    return string


def remove_quotes(string):
    """ remove all (double) quotes"""
    return string.replace("'", "").replace('"', '')


def remove_nonescaped_quotes(string):
    """
    "' "   -> ' '
    '" '   -> ' '
    '\ '  -> ' '
    "\\' " -> "' "
    '\\" ' -> '" '
    """
    string = string.replace("\\'", "\\s").replace('\\"', '\\d')  # backup
    string = remove_quotes(string)
    string = string.replace('\ ', ' ')
    return string.replace("\\s", "'").replace('\\d', '"')  # restore
