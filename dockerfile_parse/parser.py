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
try:
    # py3
    from shlex import quote
except ImportError:
    from pipes import quote

from .constants import DOCKERFILE_FILENAME
from .util import b2u, u2b, shlex_split, strip_quotes, remove_quotes, remove_nonescaped_quotes, EnvSubst
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class Labels(dict):
    """
    A class for allowing direct write access to Dockerfile labels, e.g.:

    parser.labels['label'] = 'value'
    """

    def __init__(self, labels, parser):
        super(Labels, self).__init__(labels)
        self.parser = parser

    def __delitem__(self, key):
        super(Labels, self).__delitem__(key)
        self.parser.labels = dict(self)

    def __setitem__(self, key, value):
        super(Labels, self).__setitem__(key, value)
        self.parser.labels = dict(self)


class Envs(dict):
    """
    A class for allowing direct write access to Dockerfile env. vars., e.g.:

    parser.envs['variable_name'] = 'value'
    """

    def __init__(self, envs, parser):
        super(Envs, self).__init__(envs)
        self.parser = parser

    def __delitem__(self, key):
        super(Envs, self).__delitem__(key)
        self.parser.envs = dict(self)

    def __setitem__(self, key, value):
        super(Envs, self).__setitem__(key, value)
        self.parser.envs = dict(self)


class DockerfileParser(object):
    def __init__(self, path=None,
                 cache_content=False,
                 env_replace=True,
                 parent_env=None,
                 fileobj=None):
        """
        Initialize source of Dockerfile
        :param path: path to (directory with) Dockerfile
        :param cache_content: cache Dockerfile content inside DockerfileParser
        :param parent_env: python dict of inherited env vars from parent image
        :param fileobj: seekable file-like object containing Dockerfile content (will be truncated on write)
        """

        self.fileobj = fileobj

        if self.fileobj is not None:
            if path is not None:
                raise ValueError("Parameters path and fileobj cannot be used together.")
            else:
                self.fileobj.seek(0)
        else:
            path = path or '.'
            if path.endswith(DOCKERFILE_FILENAME):
                self.dockerfile_path = path
            else:
                self.dockerfile_path = os.path.join(path, DOCKERFILE_FILENAME)

        self.cache_content = cache_content
        self.cached_content = ''  # unicode string

        if cache_content:
            try:
                # this will cache the Dockerfile content
                self.content
            except (IOError, OSError):
                # the Dockerfile doesn't exist yet
                pass

        self.env_replace = env_replace

        if isinstance(parent_env, dict):
            logger.debug("Setting inherited parent image ENV vars: %s", parent_env)
            self.parent_env = parent_env
        elif parent_env is not None:
            assert isinstance(parent_env, dict)
        else:
            self.parent_env = {}

    @contextmanager
    def _open_dockerfile(self, mode):
        if self.fileobj is not None:
            self.fileobj.seek(0)
            if mode == 'w':
                self.fileobj.truncate()
            yield self.fileobj
            self.fileobj.seek(0)
        else:
            with open(self.dockerfile_path, mode) as dockerfile:
                yield dockerfile

    @property
    def lines(self):
        """
        :return: list containing lines (unicode) from Dockerfile
        """
        if self.cache_content and self.cached_content:
            return self.cached_content.splitlines(True)

        try:
            with self._open_dockerfile('r') as dockerfile:
                lines = [b2u(l) for l in dockerfile.readlines()]
                if self.cache_content:
                    self.cached_content = ''.join(lines)
                return lines
        except (IOError, OSError) as ex:
            logger.error("Couldn't retrieve lines from dockerfile: %r", ex)
            raise

    @lines.setter
    def lines(self, lines):
        """
        Fill Dockerfile content with specified lines
        :param lines: list of lines to be written to Dockerfile
        """
        if self.cache_content:
            self.cached_content = ''.join([b2u(l) for l in lines])

        try:
            with self._open_dockerfile('w') as dockerfile:
                dockerfile.writelines([u2b(l) for l in lines])
        except (IOError, OSError) as ex:
            logger.error("Couldn't write lines to dockerfile: %r", ex)
            raise

    @property
    def content(self):
        """
        :return: string (unicode) with Dockerfile content
        """
        if self.cache_content and self.cached_content:
            return self.cached_content

        try:
            with self._open_dockerfile('r') as dockerfile:
                content = b2u(dockerfile.read())
                if self.cache_content:
                    self.cached_content = content
                return content
        except (IOError, OSError) as ex:
            logger.error("Couldn't retrieve content of dockerfile: %r", ex)
            raise

    @content.setter
    def content(self, content):
        """
        Overwrite Dockerfile with specified content
        :param content: string to be written to Dockerfile
        """
        if self.cache_content:
            self.cached_content = b2u(content)

        try:
            with self._open_dockerfile('w') as dockerfile:
                dockerfile.write(u2b(content))
        except (IOError, OSError) as ex:
            logger.error("Couldn't write content to dockerfile: %r", ex)
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
        commentre = re.compile(r'^\s*#')           # line is a comment?
        in_continuation = False
        current_instruction = None
        for line in self.lines:
            lineno += 1
            if commentre.match(line):
                continue
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
        return None

    @baseimage.setter
    def baseimage(self, value):
        """
        setter for 'FROM' instruction

        """
        self._modify_instruction('FROM', value)

    @property
    def cmd(self):
        """
        There can only be one CMD instruction in a Dockerfile.
        If there's more than one CMD then only the last CMD takes effect.
        :return: value of last CMD instruction
        """
        value = None
        for insndesc in self.structure:
            if insndesc['instruction'] == 'CMD':
                value = insndesc['value']
        return value

    @cmd.setter
    def cmd(self, value):
        """
        setter for 'CMD' instruction

        """
        self._modify_instruction('CMD', value)

    @property
    def labels(self):
        """
        LABELs from Dockerfile
        :return: dictionary of label:value (value might be '')
        """
        return self._instruction_getter('LABEL', env_replace=self.env_replace)

    @property
    def envs(self):
        """
        ENVs from Dockerfile
        :return: dictionary of env_var_name:value (value might be '')
        """
        return self._instruction_getter('ENV', env_replace=self.env_replace)

    def _instruction_getter(self, name, env_replace):
        """
        Get LABEL or ENV instructions with environment replacement

        :param name: e.g. 'LABEL' or 'ENV'
        :param env_replace: bool, whether to perform ENV substitution
        :return: Labels instance or Envs instance
        """
        if name != 'LABEL' and name != 'ENV':
            raise ValueError("Unsupported instruction '%s'", name)
        instructions = {}
        envs = self.parent_env.copy()
        for insndesc in self.structure:
            this_insn = insndesc['instruction']
            if this_insn in (name, 'ENV'):
                logger.debug("%s value: %r", name.lower(), insndesc['value'])
                shlex_splits = shlex_split(insndesc['value'],
                                           env_replace=env_replace, envs=envs)
                if '=' not in shlex_splits[0]:  # LABEL/ENV name value
                    # split it to first (name) and the rest (value)
                    key_val = insndesc['value'].split(None, 1)
                    key = strip_quotes(key_val[0])
                    try:
                        val = key_val[1]
                    except IndexError:
                        val = ''

                    if env_replace:
                        val = EnvSubst(val, envs).substitute()

                    val = remove_nonescaped_quotes(val)
                    if this_insn == name:
                        instructions[key] = val
                        logger.debug("new %s %r=%r", name.lower(), key, val)
                    if env_replace and this_insn == 'ENV':
                        envs[key] = val
                else:  # LABEL/ENV "name"="value"
                    for token in shlex_splits:
                        key_val = token.split("=", 1)
                        key = key_val[0]
                        val = key_val[1] if len(key_val) > 1 else ''
                        if this_insn == name:
                            instructions[key] = val
                            logger.debug("new %s %r=%r", name.lower(), key, val)
                        if this_insn == 'ENV':
                            envs[key] = val

        logger.debug("instructions: %r", instructions)
        return Labels(instructions, self) if name == 'LABEL' else Envs(instructions, self)

    @labels.setter
    def labels(self, labels):
        """
        Setter for LABEL instruction, i.e. sets LABELs per input param.
        :param labels: dictionary of label name & value to be set
        """
        self._instructions_setter('LABEL', labels)

    @envs.setter
    def envs(self, envs):
        """
        Setter for ENV instruction, i.e. sets ENVs per input param.
        :param envs: dictionary of env. var. name & value to be set
        """
        self._instructions_setter('ENV', envs)

    def _instructions_setter(self, name, instructions):
        if not isinstance(instructions, dict):
            raise TypeError('instructions needs to be a dictionary {name: value}')

        if name == 'LABEL':
            existing = self.labels
        elif name == 'ENV':
            existing = self.envs

        logger.debug("setting %s instructions: %r", name, instructions)

        to_delete = [k for k in existing if k not in instructions]
        for key in to_delete:
            logger.debug("delete %r", key)
            self._modify_instruction_label_env(name, key, None)

        to_add = dict((k, v) for (k, v) in instructions.items() if k not in existing)
        for k, v in to_add.items():
            logger.debug("add %r", k)
            self._add_instruction(name, (k, v))

        to_change = dict((k, v) for (k, v) in instructions.items()
                         if (k in existing and v != existing[k]))
        for k, v in to_change.items():
            logger.debug("modify %r", k)
            self._modify_instruction_label_env(name, k, v)

    def _modify_instruction_label(self, label_key, instr_value):
        self._modify_instruction_label_env('LABEL', label_key, instr_value)

    def _modify_instruction_env(self, env_var_key, env_var_value):
        self._modify_instruction_label_env('ENV', env_var_key, env_var_value)

    def _modify_instruction_label_env(self, instruction, instr_key, instr_value):
        """
        set <INSTRUCTION> instr_key to instr_value

        :param instr_key: str, label key
        :param instr_value: str or None, new label/env value or None to remove
        """
        if instruction == 'LABEL':
            instructions = self.labels
        elif instruction == 'ENV':
            instructions = self.envs
        else:
            raise ValueError("Unknown instruction '%s'" % instruction)

        if instr_key not in instructions:
            raise KeyError('%s not in %ss' % (instr_key, instruction))

        # Find where in the file to put the next release
        content = startline = endline = None
        for candidate in [insn for insn in self.structure
                          if insn['instruction'] == instruction]:
            splits = shlex_split(candidate['value'])

            # LABEL/ENV syntax is one of two types:
            if '=' not in splits[0]:  # LABEL/ENV name value
                # remove (double-)quotes
                value = remove_quotes(candidate['value'])
                words = value.split(None, 1)
                if words[0] == instr_key:
                    if instr_value is None:
                        # Delete this line altogether
                        content = None
                    else:
                        # Adjust label/env value
                        words[1] = quote(instr_value)

                        # Now reconstruct the line
                        content = " ".join([instruction] + words) + '\n'

                    startline = candidate['startline']
                    endline = candidate['endline']
                    break
            else:  # LABEL/ENV "name"="value"
                for index, token in enumerate(splits):
                    words = token.split("=", 1)
                    if words[0] == instr_key:
                        if instr_value is None:
                            # Delete this label
                            del splits[index]
                        else:
                            # Adjust label/env value
                            words[1] = instr_value
                            splits[index] = "=".join(words)

                        if len(splits) == 0:
                            # We removed the last label/env, delete the whole line
                            content = None
                        else:
                            instrs = [x.split('=', 1) for x in splits]
                            quoted_instrs = ['='.join(map(quote, x))
                                             for x in instrs]
                            # Now reconstruct the line
                            content = " ".join([instruction] + quoted_instrs) + '\n'

                        startline = candidate['startline']
                        endline = candidate['endline']
                        break

        # We know the label/env we're looking for is there
        assert startline and endline

        # Re-write the Dockerfile
        lines = self.lines
        del lines[startline:endline + 1]
        if content:
            lines.insert(startline, content)
        self.lines = lines

    def _modify_instruction(self, instruction, new_value):
        """
        :param instruction: like 'FROM' or 'CMD'
        :param new_value: new value of instruction
        """
        if instruction == 'LABEL':
            raise ValueError('Please use labels.setter')
        if instruction == 'ENV':
            raise ValueError('Please use envs.setter')
        for insn in self.structure:
            if insn['instruction'] == instruction:
                new_line = '{0} {1}\n'.format(instruction, new_value)
                lines = self.lines
                del lines[insn['startline']:insn['endline'] + 1]
                lines.insert(insn['startline'], new_line)
                self.lines = lines

    def _delete_instructions(self, instruction, value=None):
        """
        :param instruction: name of instruction to be deleted
        :param value: if specified, delete instruction only when it has this value
                      if instruction is LABEL then value is label name
        """
        if instruction == 'LABEL' and value:
            self._modify_instruction_label(value, None)
            return
        if instruction == 'ENV' and value:
            self._modify_instruction_env(value, None)
            return

        lines = self.lines
        deleted = False
        for insn in reversed(self.structure):
            if insn['instruction'] == instruction:
                if value and insn['value'] != value:
                    continue
                deleted = True
                del lines[insn['startline']:insn['endline'] + 1]
        if deleted:
            self.lines = lines

    def _add_instruction(self, instruction, value):
        """
        :param instruction: instruction name to be added
        :param value: instruction value
        """
        if (instruction == 'LABEL' or instruction == 'ENV') and len(value) == 2:
            new_line = instruction + ' ' + '='.join(map(quote, value)) + '\n'
        else:
            new_line = '{0} {1}\n'.format(instruction, value)
        if new_line:
            lines = self.lines
            lines += new_line
            self.lines = lines
