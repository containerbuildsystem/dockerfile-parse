# -*- coding: utf-8 -*-
"""
Copyright (c) 2015 Red Hat, Inc
All rights reserved.

This software may be modified and distributed under the terms
of the BSD license. See the LICENSE file for details.
"""

from __future__ import print_function, unicode_literals

from io import StringIO
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


class EnvSubst(object):
    """
    Substitute environment variables when quoting allows
    """

    SQUOTE = "'"
    DQUOTE = '"'

    def __init__(self, s, envs):
        """
        :param s: str, string to perform substitution on
        :param envs: dict, environment variables to use
        """
        self.stream = StringIO(s)
        self.envs = envs

        # Initial state
        self.quotes = None  # the quoting character in force, or None
        self.escaped = False

    def substitute(self):
        """
        :return: str, string resulting from substitution
        """
        return "".join(self.replace_parts())

    def update_quoting_state(self, ch):
        """
        Update self.quotes and self.escaped

        :param ch: str, next character
        """

        # Set whether the next character is escaped
        self.escaped = ch == '\\' and self.quotes != self.SQUOTE
        if self.escaped:
            return

        if self.quotes is None:
            if ch in (self.SQUOTE, self.DQUOTE):
                self.quotes = ch

        elif self.quotes == ch:
            self.quotes = None

    def replace_parts(self):
        """
        Generator for substituted parts of the string to be reassembled.
        """
        while True:
            ch = self.stream.read(1)
            if not ch:
                # EOF
                raise StopIteration

            if self.escaped:
                # This character was escaped
                yield ch

                # Reset back to not being escaped
                self.escaped = False
                continue

            if ch == '$' and self.quotes != self.SQUOTE:
                # Substitute environment variable
                braced = False
                varname = ''
                while True:
                    ch = self.stream.read(1)
                    if varname == '' and ch == '{':
                        braced = True
                        continue

                    if not ch:
                        # EOF
                        break

                    if braced and ch == '}':
                        break

                    if not ch.isalnum() and ch != '_':
                        break

                    varname += ch

                try:
                    yield self.envs[varname]
                except KeyError:
                    pass

                if braced and ch == '}':
                    continue

                # ch now holds the next character

            # This character is not special, yield it
            yield ch

            self.update_quoting_state(ch)


def shlex_split(string, env_replace=True, envs=None):
    """
    Split the string, applying environment variable substitutions

    Python2's shlex doesn't like unicode, so we have to convert the string
    into bytes, run shlex.split() and convert it back to unicode.

    This applies environment variable substitutions on the string when
    quoting allows, and splits it into tokens at whitespace
    delimiters.

    Environment variable substitution is applied to the entire string,
    even the part before any '=', which is not technically correct but
    will only fail for invalid Dockerfile content.

    :param string: str, string to split
    :param env_replace: bool, whether to perform substitution
    :param envs: dict, environment variables for substitution

    """
    if env_replace:
        string = EnvSubst(string, envs or {}).substitute()

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
