# -*- coding: utf-8 -*-
"""
Copyright (c) 2015 Red Hat, Inc
All rights reserved.

This software may be modified and distributed under the terms
of the BSD license. See the LICENSE file for details.
"""

from __future__ import print_function, unicode_literals

import json
import logging
import os
import re
import shlex
from .constants import DOCKERFILE_FILENAME, PY2

logger = logging.getLogger(__name__)

class DockerfileParser(object):
    def __init__(self, path=None):
        """
        Initialize path to Dockerfile
        :param path: path to (directory with) Dockerfile
        """
        path = path or '.'
        if path.endswith(DOCKERFILE_FILENAME):
            self.dockerfile_path = path
        else:
            self.dockerfile_path = os.path.join(path, DOCKERFILE_FILENAME)

    @staticmethod
    def b2u(string):
        """ bytes to unicode """
        if isinstance(string, bytes):
            return string.decode('utf-8')
        return string

    @staticmethod
    def u2b(string):
        """ unicode to bytes (Python 2 only) """
        if PY2 and isinstance(string, unicode):
            return string.encode('utf-8')
        return string

    @property
    def lines(self):
        """
        :return: list containing lines (unicode) from Dockerfile
        """
        try:
            with open(self.dockerfile_path, 'r') as dockerfile:
                return [self.b2u(l) for l in dockerfile.readlines()]
        except (IOError, OSError) as ex:
            logger.error("Couldn't retrieve lines from dockerfile: %s" % repr(ex))
            raise

    @lines.setter
    def lines(self, lines):
        """
        Fill Dockerfile content with specified lines
        :param lines: list of lines to be written to Dockerfile
        """
        try:
            with open(self.dockerfile_path, 'w') as dockerfile:
                dockerfile.writelines([self.u2b(l) for l in lines])
        except (IOError, OSError) as ex:
            logger.error("Couldn't write lines to dockerfile: %s" % repr(ex))
            raise

    @property
    def content(self):
        """
        :return: string (unicode) with Dockerfile content
        """
        try:
            with open(self.dockerfile_path, 'r') as dockerfile:
                return self.b2u(dockerfile.read())
        except (IOError, OSError) as ex:
            logger.error("Couldn't retrieve content of dockerfile: %s" % repr(ex))
            raise

    @content.setter
    def content(self, content):
        """
        Overwrite Dockerfile with specified content
        :param content: string to be written to Dockerfile
        """
        try:
            with open(self.dockerfile_path, 'w') as dockerfile:
                dockerfile.write(self.u2b(content))
        except (IOError, OSError) as ex:
            logger.error("Couldn't write content to dockerfile: %s" % repr(ex))
            raise

    @property
    def structure(self):
        """
        Returns a list of dicts describing the commands:
        [
            {"instruction": "FROM",       # always upper-case
             "startline": 0,              # 0-based
             "endline": 0,                # 0-based
             "content": "From fedora\n",
             "value": "fedora"},

            {"instruction": "CMD",
             "startline": 1,
             "endline": 2,
             "content": "CMD yum -y update && \\\n    yum clean all\n",
             "value": "yum -y update && yum clean all"}
        ]

        Comments are ignored.
        """
        def _rstrip_backslash(l):
            l = l.rstrip()
            if l.endswith('\\'):
                return l[:-1]
            return l

        instructions = []
        lineno = -1
        insnre = re.compile(r'^\s*(\w+)\s+(.*)$')  # matched group is insn
        contre = re.compile(r'^.*\\\s*$')          # line continues?
        in_continuation = False
        current_instruction = None
        for line in self.lines:
            lineno += 1
            if not in_continuation:
                m = insnre.match(line)
                if not m:
                    continue

                current_instruction = {'instruction': m.groups()[0].upper(),
                                       'startline': lineno,
                                       'endline': lineno,
                                       'content': line,
                                       'value': _rstrip_backslash(m.groups()[1])}
            else:
                current_instruction['content'] += line
                current_instruction['endline'] = lineno
                if current_instruction['value']:
                    current_instruction['value'] += _rstrip_backslash(line)
                else:
                    current_instruction['value'] = _rstrip_backslash(line.lstrip())

            in_continuation = contre.match(line)
            if not in_continuation and current_instruction is not None:
                instructions.append(current_instruction)

        return instructions

    @property
    def json(self):
        """
        :return: JSON formatted string with instructions & values from Dockerfile
        """
        insndescs = [{insndesc['instruction']: insndesc['value']} for insndesc in self.structure]
        return json.dumps(insndescs)

    @property
    def baseimage(self):
        """
        :return: base image, i.e. value of FROM instruction
        """
        for insndesc in self.structure:
            if insndesc['instruction'] == 'FROM':
                return insndesc['value']

    def _shlex_split(self, string):
        """
        Python2's shlex doesn't like unicode, so we have to convert the string
        into bytes, run shlex.split() and convert it back to unicode.
        """
        if PY2 and isinstance(string, unicode):
            string = self.u2b(string)
            # this takes care of quotes
            splits = shlex.split(string)
            return map(self.b2u, splits)
        else:
            return shlex.split(string)

    @property
    def labels(self):
        """
        LABELs from Dockerfile
        :return: dictionary of label:value (value might be '')
        """
        labels = {}
        for insndesc in self.structure:
            if insndesc['instruction'] == 'LABEL':
                shlex_splits = self._shlex_split(insndesc['value'])
                if '=' not in shlex_splits[0]:  # LABEL name value
                    # remove (double-)quotes
                    value = insndesc['value'].replace("'", "").replace('"', '')
                    # split it to first and the rest
                    key_val = value.split(None, 1)
                    labels[key_val[0]] = key_val[1] if len(key_val) > 1 else ''
                    logger.debug("new label %s=%s", repr(key_val[0]), repr(labels[key_val[0]]))
                else:  # LABEL "name"="value"
                    for token in shlex_splits:
                        key_val = token.split("=", 1)
                        labels[key_val[0]] = key_val[1] if len(key_val) > 1 else ''
                        logger.debug("new label %s=%s", repr(key_val[0]), repr(labels[key_val[0]]))
        return labels
