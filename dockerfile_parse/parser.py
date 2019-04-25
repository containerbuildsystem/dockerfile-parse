# -*- coding: utf-8 -*-
"""
Copyright (c) 2015, 2018, 2019 Red Hat, Inc
All rights reserved.

This software may be modified and distributed under the terms
of the BSD license. See the LICENSE file for details.
"""

from __future__ import print_function, unicode_literals

import json
import logging
import os
import re
from contextlib import contextmanager
from six import string_types

from .constants import DOCKERFILE_FILENAME
from .util import (b2u, extract_labels_or_envs, get_key_val_dictionary,
                   u2b, Context, WordSplitter)

try:
    # py3
    from shlex import quote
except ImportError:
    from pipes import quote


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
        :param fileobj: seekable file-like object containing Dockerfile content
                        as bytes (will be truncated on write)
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

        if parent_env is None:
            self.parent_env = {}
        else:
            assert isinstance(parent_env, dict)
            logger.debug("Setting inherited parent image ENV vars: %s", parent_env)
            self.parent_env = parent_env

    @contextmanager
    def _open_dockerfile(self, mode):
        if self.fileobj is not None:
            self.fileobj.seek(0)
            if 'w' in mode:
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
            with self._open_dockerfile('rb') as dockerfile:
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
            with self._open_dockerfile('wb') as dockerfile:
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
            with self._open_dockerfile('rb') as dockerfile:
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
            with self._open_dockerfile('wb') as dockerfile:
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
    def parent_images(self):
        """
        :return: list of parent images -- one image per each stage's FROM instruction
        """
        parents = []
        for instr in self.structure:
            if instr['instruction'] != 'FROM':
                continue
            image, _ = image_from(instr['value'])
            if image is not None:
                parents.append(image)
        return parents

    @parent_images.setter
    def parent_images(self, parents):
        """
        setter for images in 'FROM' instructions.
        Images are updated per build stage with the given parents in the order they appear.
        Raises RuntimeError if a different number of parents are given than there are stages
        as that is likely to be a mistake.

        :param parents: list of image strings
        """
        parents = list(parents)
        change_instrs = []
        for instr in self.structure:
            if instr['instruction'] != 'FROM':
                continue

            old_image, stage = image_from(instr['value'])
            if not old_image:
                continue  # broken FROM, fixing would just confuse things
            if not parents:
                raise RuntimeError("not enough parents to match build stages")

            image = parents.pop(0)
            if image != old_image:
                instr['value'] = '{0} AS {1}'.format(image, stage) if stage else image
                instr['content'] = 'FROM {0}\n'.format(instr['value'])
                change_instrs.append(instr)

        if parents:
            raise RuntimeError("trying to update too many parents for build stages")

        lines = self.lines
        for instr in reversed(change_instrs):
            lines[instr['startline']:instr['endline']+1] = [instr['content']]

        self.lines = lines

    @property
    def is_multistage(self):
        return len(self.parent_images) > 1

    @property
    def baseimage(self):
        """
        :return: base image, i.e. value of final stage FROM instruction
        """
        return (self.parent_images or [None])[-1]

    @baseimage.setter
    def baseimage(self, new_image):
        """
        change image of final stage FROM instruction
        """
        images = self.parent_images or [None]
        images[-1] = new_image
        self.parent_images = images

    @property
    def cmd(self):
        """
        Determine the final CMD instruction, if any, in the final build stage.
        CMDs from earlier stages are ignored.
        :return: value of final stage CMD instruction
        """
        value = None
        for insndesc in self.structure:
            if insndesc['instruction'] == 'FROM':  # new stage, reset
                value = None
            elif insndesc['instruction'] == 'CMD':
                value = insndesc['value']
        return value

    @cmd.setter
    def cmd(self, value):
        """
        setter for final 'CMD' instruction in final build stage

        """
        cmd = None
        for insndesc in self.structure:
            if insndesc['instruction'] == 'FROM':  # new stage, reset
                cmd = None
            elif insndesc['instruction'] == 'CMD':
                cmd = insndesc

        new_cmd = 'CMD ' + value
        if cmd:
            self.add_lines_at(cmd, new_cmd, replace=True)
        else:
            self.add_lines(new_cmd)

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
        envs = {}

        for instruction_desc in self.structure:
            this_instruction = instruction_desc['instruction']
            if this_instruction == 'FROM':
                instructions.clear()
                envs = self.parent_env.copy()
            elif this_instruction in (name, 'ENV'):
                logger.debug("%s value: %r", name.lower(), instruction_desc['value'])
                key_val_list = extract_labels_or_envs(env_replace=env_replace,
                                                      envs=envs,
                                                      instruction_value=instruction_desc['value'])
                for key, value in key_val_list:
                    if this_instruction == name:
                        instructions[key] = value
                        logger.debug("new %s %r=%r", name.lower(), key, value)
                    if this_instruction == 'ENV':
                        envs[key] = value

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

        # extract target instructions from the final stage only
        candidates = []
        for insn in self.structure:
            if insn['instruction'] == 'FROM':
                candidates = []
            if insn['instruction'] == instruction:
                candidates.append(insn)

        # Find where in the file to put the changes
        content = startline = endline = None
        for candidate in candidates:
            words = list(WordSplitter(candidate['value']).split(dequote=False))

            # LABEL/ENV syntax is one of two types:
            if '=' not in words[0]:  # LABEL/ENV name value
                # Remove quotes from key name and see if it's the one
                # we're looking for.
                if WordSplitter(words[0]).dequote() == instr_key:
                    if instr_value is None:
                        # Delete this line altogether
                        content = None
                    else:
                        # Adjust label/env value
                        words[1:] = [quote(instr_value)]

                        # Now reconstruct the line
                        content = " ".join([instruction] + words) + '\n'

                    startline = candidate['startline']
                    endline = candidate['endline']
                    break
            else:  # LABEL/ENV "name"="value"
                for index, token in enumerate(words):
                    key, _ = token.split("=", 1)
                    if WordSplitter(key).dequote() == instr_key:
                        if instr_value is None:
                            # Delete this label
                            del words[index]
                        else:
                            # Adjust label/env value
                            words[index] = "{0}={1}".format(key,
                                                            quote(instr_value))

                        if len(words) == 0:
                            # We removed the last label/env, delete the whole line
                            content = None
                        else:
                            # Now reconstruct the line
                            content = " ".join([instruction] + words) + '\n'

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
            if not lines[len(lines) - 1].endswith('\n'):
                new_line = '\n' + new_line
            lines += new_line
            self.lines = lines

    def add_lines(self, *lines, **kwargs):
        """
        Add lines to the beginning or end of the build.
        :param lines: one or more lines to add to the content, by default at the end.
        :param all_stages: bool for whether to add in all stages for a multistage build
                           or (by default) only the last.
        :param at_start: adds at the beginning (after FROM) of the stage(s) instead of the end.
        :param skip_scratch: skip stages which use "FROM scratch"
        """
        assert len(lines) > 0
        lines = [_endline(line) for line in lines]
        all_stages = kwargs.pop('all_stages', False)
        at_start = kwargs.pop('at_start', False)
        skip_scratch = kwargs.pop('skip_scratch', False)
        assert not kwargs, "Unknown keyword argument(s): {0}".format(kwargs.keys())

        froms = [
            instr for instr in self.structure
            if instr['instruction'] == 'FROM'
        ] or [{'endline': -1}]  # no FROM? fake one before the beginning
        if not all_stages:  # only modify the last
            froms = [froms[-1]]

        df_lines = self.lines
        # make sure last line has a newline if lines are to be appended
        if df_lines and not at_start:
            df_lines[-1] = _endline(df_lines[-1])

        # iterate through the stages in reverse order
        # so adding lines doesn't invalidate line numbers from structure dicts.
        # first add a bogus instruction to represent EOF in our iteration.
        froms.append({'startline': len(df_lines) + 1})
        for stage in range(len(froms)-2, -1, -1):  # e.g. 0 for single or 2, 1, 0 for 3 stages
            start, finish = froms[stage], froms[stage+1]
            linenum = start['endline'] + 1 if at_start else finish['startline']
            if skip_scratch and froms[stage]['value'] == 'scratch':
                continue
            df_lines[linenum:linenum] = lines

        self.lines = df_lines

    def add_lines_at(self, anchor, *lines, **kwargs):
        """
        Add lines at a specific location in the file.
        :param anchor: structure_dict|line_str|line_num a reference to where adds should occur
        :param lines: one or more lines to add to the content
        :param replace: if True -- replace the anchor
        :param after: if True -- insert after the anchor (conflicts with "replace")
        """
        assert len(lines) > 0
        replace = kwargs.pop('replace', False)
        after = kwargs.pop('after', False)
        assert not (after and replace)
        assert not kwargs, "Unknown keyword argument(s): {0}".format(kwargs.keys())

        # find the line number for the insertion
        df_lines = self.lines
        if isinstance(anchor, int):  # line number, just validate
            assert anchor in range(len(df_lines))
            if replace:
                del df_lines[anchor]
        elif isinstance(anchor, dict):  # structure
            assert anchor in self.structure, "Current structure does not match: {0}".format(anchor)
            if replace:
                df_lines[anchor['startline']:anchor['endline'] + 1] = []
            if after:
                anchor = anchor['endline']
            else:
                anchor = anchor['startline']
        elif isinstance(anchor, string_types):  # line contents
            matches = [index for index, text in enumerate(df_lines) if text == anchor]
            if not matches:
                raise RuntimeError("Cannot find line in the build file:\n" + anchor)
            anchor = matches[-1]
            if replace:
                del df_lines[anchor]
        else:
            raise RuntimeError("Unknown anchor type {0}".format(anchor))

        if after:
            # ensure there's a newline on final line
            df_lines[anchor] = _endline(df_lines[anchor])
            anchor += 1

        df_lines[anchor:anchor] = [_endline(line) for line in lines]
        self.lines = df_lines

    @property
    def context_structure(self):
        """
        :return: list of Context objects
            (Contains info about labels and environment variables for each line.)
        """
        instructions = []
        last_context = Context()
        for instr in self.structure:
            instruction_type = instr['instruction']
            if instruction_type == "FROM":  # reset per stage
                last_context = Context()

            context = Context(envs=dict(last_context.envs),
                              labels=dict(last_context.labels))

            if instruction_type in ["ENV", "LABEL"]:
                val = get_key_val_dictionary(instruction_value=instr['value'],
                                             env_replace=self.env_replace,
                                             envs=last_context.envs)
                context.set_line_value(context_type=instruction_type, value=val)

            instructions.append(context)
            last_context = context
        return instructions


def image_from(from_value):
    """
    :param from_value: string like "image:tag" or "image:tag AS name"
    :return: tuple of the image and stage name, e.g. ("image:tag", None)
    """
    regex = re.compile(r"""(?xi)     # readable, case-insensitive regex
        \s*                          # ignore leading whitespace
        (?P<image> \S+ )             # image and optional tag
        (?:                          # optional "AS name" clause for stage
            \s+ AS \s+
            (?P<name> \S+ )
        )?
        """)
    match = re.match(regex, from_value)
    return match.group('image', 'name') if match else (None, None)


def _endline(line):
    """
    Make sure the line ends with a single newline.
    Since trailing whitespace has no significance, remove it.
    """
    return line.rstrip() + '\n'
