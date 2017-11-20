# -*- coding: utf-8 -*-
"""
Copyright (c) 2015 Red Hat, Inc
All rights reserved.

This software may be modified and distributed under the terms
of the BSD license. See the LICENSE file for details.
"""

from __future__ import print_function, unicode_literals

import shlex
from io import StringIO

from .constants import PY2


def b2u(string):
    """ bytes to unicode """
    if (isinstance(string, bytes) or
        (PY2 and isinstance(string, str))):
        return string.decode('utf-8')
    return string


def u2b(string):
    """ unicode to bytes"""
    if ((PY2 and isinstance(string, unicode)) or
        ((not PY2) and isinstance(string, str))):
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


def split_tuple(text):
    text_split = text.split('=', 1)
    if len(text_split) == 2:
        return tuple(text_split)
    return None


def extract_labels_or_envs(env_replace, envs, instruction_value):
    shlex_splits_raw = shlex_split(instruction_value,
                                   env_replace=env_replace, envs=envs)

    key_val_list = []
    if '=' not in shlex_splits_raw[0]:  # LABEL/ENV name value
        # split it to first (name) and the rest (value)
        key_val = instruction_value.split(None, 1)
        key = strip_quotes(key_val[0])
        try:
            val = key_val[1]
        except IndexError:
            val = ''

        if env_replace:
            val = EnvSubst(val, envs).substitute()
        val = remove_nonescaped_quotes(val)

        key_val_list.append((key, val))

    else:  # LABEL/ENV "name"="value"

        for k_v in shlex_splits_raw:
            key_val_list.append(split_tuple(k_v))

    return key_val_list


def get_key_val_dictionary(instruction_value, env_replace=False, envs=None):
    envs = envs or []
    return dict(extract_labels_or_envs(instruction_value=instruction_value,
                                       env_replace=env_replace,
                                       envs=envs))


class Context(object):
    def __init__(self, envs=None, labels=None, line_envs=None, line_labels=None):
        """
        Class representing current state of environment variables and labels.

        :param envs: dict with variables valid for this line
            (all variables defined to this line)
        :param labels: dict with labels valid for this line
            (all labels defined to this line)
        :param line_envs: dict with variables defined on this line
        :param line_labels: dict with labels defined on this line
        """
        self.envs = envs or {}
        self.labels = labels or {}
        self.line_envs = line_envs or {}
        self.line_labels = line_labels or {}

    def set_line_value(self, context_type, value):
        """
        Set value defined on this line ('line_envs'/'line_labels')
        and update 'envs'/'labels'.

        :param context_type: "ENV" or "LABEL"
        :param value: new value for this line
        """
        if context_type.upper() == "ENV":
            self.line_envs = value
            self.envs.update(value)
        elif context_type.upper() == "LABEL":
            self.line_labels = value
            self.labels.update(value)

    def get_line_value(self, context_type):
        """
        Get the values defined on this line.

        :param context_type: "ENV" or "LABEL"
        :return: values of given type defined on this line
        """
        if context_type.upper() == "ENV":
            return self.line_envs
        elif context_type.upper() == "LABEL":
            return self.line_labels

    def get_values(self, context_type):
        """
        Get the values valid on this line.

        :param context_type: "ENV" or "LABEL"
        :return: values of given type valid on this line
        """
        if context_type.upper() == "ENV":
            return self.envs
        elif context_type.upper() == "LABEL":
            return self.labels
