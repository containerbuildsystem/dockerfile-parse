# -*- coding: utf-8 -*-
"""
Copyright (c) 2015, 2019 Red Hat, Inc
All rights reserved.

This software may be modified and distributed under the terms
of the BSD license. See the LICENSE file for details.
"""

from __future__ import unicode_literals

import inspect
import json
import os
import pytest
import re
import six
import sys
from textwrap import dedent

from dockerfile_parse import DockerfileParser
from dockerfile_parse.parser import image_from
from tests.fixtures import dfparser, instruction

NON_ASCII = "žluťoučký"
# flake8 does not understand fixtures:
dfparser = dfparser
instruction = instruction


class TestDockerfileParser(object):
    def test_all_versions_match(self):
        def read_version(fp, regex):
            with open(fp, "r") as fd:
                content = fd.read()
                found = re.findall(regex, content)
                if len(found) == 1:
                    return found[0]
                else:
                    raise Exception("Version not found!")

        import dockerfile_parse
        from dockerfile_parse import __version__ as module_version
        fp = inspect.getfile(dockerfile_parse)
        project_dir = os.path.dirname(os.path.dirname(fp))
        specfile = os.path.join(project_dir, "python-dockerfile-parse.spec")
        setup_py = os.path.join(project_dir, "setup.py")
        spec_version = read_version(specfile, r"\nVersion:\s*(.+?)\s*\n")
        setup_py_version = read_version(setup_py, r"version=['\"](.+)['\"]")
        assert spec_version == module_version
        assert setup_py_version == module_version

    def test_dockerfileparser(self, dfparser, tmpdir):
        df_content = dedent("""\
            FROM fedora
            LABEL label={0}""".format(NON_ASCII))
        df_lines = ["FROM fedora\n", "LABEL label={0}".format(NON_ASCII)]

        dfparser.content = ""
        dfparser.content = df_content
        assert dfparser.content == df_content
        assert dfparser.lines == df_lines
        assert [isinstance(line, six.text_type) for line in dfparser.lines]

        dfparser.content = ""
        dfparser.lines = df_lines
        assert dfparser.content == df_content
        assert dfparser.lines == df_lines
        assert [isinstance(line, six.text_type) for line in dfparser.lines]

        with open(os.path.join(str(tmpdir), 'Dockerfile'), 'wb') as fp:
            fp.write(df_content.encode('utf-8'))
        dfparser = DockerfileParser(str(tmpdir))
        assert dfparser.content == df_content
        assert dfparser.lines == df_lines
        assert [isinstance(line, six.text_type) for line in dfparser.lines]

    def test_constructor_cache(self, tmpdir):
        tmpdir_path = str(tmpdir.realpath())
        df1 = DockerfileParser(tmpdir_path)
        df1.lines = ["From fedora:latest\n", "LABEL a b\n"]

        df2 = DockerfileParser(tmpdir_path, True)
        assert df2.cached_content

    def test_dockerfile_structure(self, dfparser):
        dfparser.lines = ["# comment\n",        # should be ignored
                          " From  \\\n",        # mixed-case
                          "   base\n",          # extra ws, continuation line
                          " # comment\n",
                          " label  foo  \\\n",  # extra ws
                          "    # comment\n",    # should be ignored
                          "    bar  \n",        # extra ws, continuation line
                          "USER  {0}\n".format(NON_ASCII),
                          "# comment \\\n",     # extra ws
                          "# comment \\ \n",    # extra ws with a space
                          "# comment \\\\ \n",  # two backslashes
                          "RUN command1\n",
                          "RUN command2 && \\\n",
                          "    # comment\n",
                          "    command3\n"]

        assert dfparser.structure == [{'instruction': 'FROM',
                                       'startline': 1,  # 0-based
                                       'endline': 2,
                                       'content': ' From  \\\n   base\n',
                                       'value': 'base'},
                                      {'instruction': 'LABEL',
                                       'startline': 4,
                                       'endline': 6,
                                       'content': ' label  foo  \\\n    bar  \n',
                                       'value': 'foo      bar'},
                                      {'instruction': 'USER',
                                       'startline': 7,
                                       'endline': 7,
                                       'content': 'USER  {0}\n'.format(NON_ASCII),
                                       'value': '{0}'.format(NON_ASCII)},
                                      {'instruction': 'RUN',
                                       'startline': 11,
                                       'endline': 11,
                                       'content': 'RUN command1\n',
                                       'value': 'command1'},
                                      {'instruction': 'RUN',
                                       'startline': 12,
                                       'endline': 14,
                                       'content': 'RUN command2 && \\\n    command3\n',
                                       'value': 'command2 &&     command3'}]

    def test_dockerfile_json(self, dfparser):
        dfparser.content = dedent("""\
            # comment
            From  base
            LABEL foo="bar baz"
            USER  {0}""").format(NON_ASCII)
        expected = json.dumps([{"FROM": "base"},
                               {"LABEL": "foo=\"bar baz\""},
                               {"USER": "{0}".format(NON_ASCII)}])
        assert dfparser.json == expected

    def test_multistage_dockerfile(self, dfparser):
        dfparser.content = dedent("""\
            From builder:image AS builder
            RUN compile to /spam/eggs

            FROM base
            COPY --from=builder /spam/eggs /usr/bin/eggs
            """)
        expected = [
            {
                'instruction': 'FROM',
                'value': 'builder:image AS builder',
                'startline': 0,  # 0-based
                'endline': 0,
                'content': 'From builder:image AS builder\n',
            }, {
                'instruction': 'RUN',
                'value': 'compile to /spam/eggs',
                'startline': 1,
                'endline': 1,
                'content': 'RUN compile to /spam/eggs\n',
            }, {
                'instruction': 'FROM',
                'value': 'base',
                'startline': 3,
                'endline': 3,
                'content': 'FROM base\n',
            }, {
                'instruction': 'COPY',
                'value': '--from=builder /spam/eggs /usr/bin/eggs',
                'startline': 4,
                'endline': 4,
                'content': 'COPY --from=builder /spam/eggs /usr/bin/eggs\n',
            },
        ]
        assert dfparser.structure == expected
        assert dfparser.baseimage == 'base'
        assert dfparser.is_multistage

    def test_multistage_dockerfile_labels(self, dfparser):
        dfparser.content = dedent("""\
            From builder:image AS builder
            LABEL "spam=baked beans"

            FROM base
            LABEL "eggs=bacon"
            """)
        # only labels from final stage should count
        assert dfparser.labels == {'eggs': 'bacon'}

    def test_get_baseimg_from_df(self, dfparser):
        dfparser.lines = ["From fedora:latest\n",
                          "LABEL a b\n"]
        base_img = dfparser.baseimage
        assert base_img.startswith('fedora')

    def test_get_parent_env(self, tmpdir):
        tmpdir_path = str(tmpdir.realpath())
        p_env = {"bar": "baz"}
        df1 = DockerfileParser(tmpdir_path, env_replace=True, parent_env=p_env)
        df1.lines = [
            "FROM parent\n",
            "ENV foo=\"$bar\"\n",
            "LABEL label=\"$foo $bar\"\n"
        ]

        # Even though we inherit an ENV, this .envs count should only be for the
        # ENVs defined in *this* Dockerfile as we're parsing the Dockerfile and
        # the parent_env is only to satisfy use of inherited ENVs.
        assert len(df1.envs) == 1
        assert df1.envs.get('foo') == 'baz'
        assert len(df1.labels) == 1
        assert df1.labels.get('label') == 'baz baz'

    def test_get_parent_env_from_scratch(self, tmpdir):
        tmpdir_path = str(tmpdir.realpath())
        p_env = {"bar": "baz"}
        df1 = DockerfileParser(tmpdir_path, env_replace=True, parent_env=p_env)
        df1.lines = [
            "FROM scratch\n",
        ]

        assert not df1.envs

    @pytest.mark.parametrize(('instr_value', 'expected'), [
        ('"name1"=\'value 1\' "name2"=myself name3=""',
         {'name1': 'value 1',
          'name2': 'myself',
          'name3': ''}),
        ('name5=5', {'name5': '5'}),
        ('"name6"=6', {'name6': '6'}),
        ('name7', {'name7': ''}),
        ('"name8"', {'name8': ''}),
        ('"name9"="asd \\  \\n qwe"', {'name9': 'asd \\  \\n qwe'}),
        ('"name10"="{0}"'.format(NON_ASCII), {'name10': NON_ASCII}),
        ('"name1 1"=1', {'name1 1': '1'}),
        ('"name12"=12 \ \n   "name13"=13', {'name12': '12', 'name13': '13'}),
        ('name14=1\ 4', {'name14': '1 4'}),
        ('name15="with = in value"', {'name15': 'with = in value'}),
        # old syntax (without =)
        ('name101 101', {'name101': '101'}),
        ('name102 1 02', {'name102': '1 02'}),
        ('"name103" 1 03', {'name103': '1 03'}),
        ('name104 "1"  04', {'name104': '1  04'}),
        ('name105 1 \'05\'', {'name105': '1 05'}),
        ('name106 1 \'0\'   6', {'name106': '1 0   6'}),
        ('name107 1 0\ 7', {'name107': '1 0 7'}),
        ('name108 "with = in value"', {'name108': 'with = in value'}),
        ('name109 "\\"quoted\\""', {'name109': '"quoted"'}),
    ])
    def test_get_instructions_from_df(self, dfparser, instruction, instr_value,
                                      expected):
        dfparser.content = "{0} {1}\n".format(instruction, instr_value)
        if instruction == 'LABEL':
            instructions = dfparser.labels
        elif instruction == 'ENV':
            instructions = dfparser.envs

        assert instructions == expected

    @pytest.mark.parametrize(('from_value', 'expect'), [
        (
            "    ",
            (None, None),
        ), (
            "   foo",
            ('foo', None),
        ), (
            "foo:bar as baz   ",
            ('foo:bar', 'baz'),
        ), (
            "foo as baz",
            ('foo', 'baz'),
        ), (
            "foo and some other junk",  # we won't judge
            ('foo', None),
        ), (
            "registry.example.com:5000/foo/bar:baz",
            ('registry.example.com:5000/foo/bar:baz', None),
        )
    ])
    def test_image_from(self, from_value, expect):
        result = image_from(from_value)
        assert result == expect

    def test_parent_images(self, dfparser):
        FROM = ('my-builder:latest', 'rhel7:7.5')
        template = dedent("""\
            FROM {0} AS builder
            CMD do some stuff

            FROM {1}
            COPY --from=builder some stuff
            """)
        dfparser.content = template.format(*FROM)

        parents = dfparser.parent_images
        assert parents == list(FROM)

        NEW_FROM = ('my-builder@sha256:1234abcd...', 'rhel7@sha256:1234abcd...')
        dfparser.parent_images = NEW_FROM
        assert dfparser.content == template.format(*NEW_FROM)

        with pytest.raises(RuntimeError):
            dfparser.parent_images = [1]
        with pytest.raises(RuntimeError):
            dfparser.parent_images = [1, 2, "many"]

    def test_parent_images_missing_from(self, dfparser):
        dfparser.content = dedent("""\
            # even though this would be really broken
            FROM
            FROM first AS foo
            FROM
            FROM second
            """)
        assert dfparser.parent_images == ['first', 'second']
        assert dfparser.baseimage == 'second'
        dfparser.parent_images = ['spam', 'eggs']
        assert dfparser.parent_images == ['spam', 'eggs']
        # remains just as broken
        assert dfparser.content.count('FROM') == 4

    def test_modify_instruction(self, dfparser):
        FROM = ('ubuntu', 'fedora:latest')
        CMD = ('old cmd', 'new command')
        df_content = dedent("""\
            FROM {0}
            CMD {1}""").format(FROM[0], CMD[0])

        dfparser.content = df_content

        assert dfparser.baseimage == FROM[0]
        dfparser.baseimage = FROM[1]
        assert dfparser.baseimage == FROM[1]

        assert dfparser.cmd == CMD[0]
        dfparser.cmd = CMD[1]
        assert dfparser.cmd == CMD[1]

    def test_modify_from_multistage(self, dfparser):
        BASE_FROM = 'base:${CODE_VERSION}'
        BUILDER_FROM = 'builder:${CODE_VERSION}'
        UPDATED_BASE_FROM = 'bass:${CODE_VERSION}'

        BASE_CMD = None
        BUILDER_CMD = '/code/run-extras'
        UPDATED_BASE_CMD = '/code/run-main-actors'

        df_content = dedent("""\
            ARG  CODE_VERSION=latest
            FROM {0}
            CMD {1}

            FROM {2}
            """).format(BUILDER_FROM, BUILDER_CMD, BASE_FROM)

        INDEX_FIRST_FROM = 1
        INDEX_SECOND_FROM = 4

        INDEX_FIRST_CMD = 2
        INDEX_SECOND_CMD = 5

        dfparser.content = df_content

        assert dfparser.baseimage == BASE_FROM
        assert dfparser.lines[INDEX_FIRST_FROM].strip() == 'FROM {0}'.format(BUILDER_FROM)
        assert dfparser.lines[INDEX_SECOND_FROM].strip() == 'FROM {0}'.format(BASE_FROM)

        dfparser.baseimage = UPDATED_BASE_FROM  # should update only last FROM
        assert dfparser.baseimage == UPDATED_BASE_FROM
        assert dfparser.lines[INDEX_FIRST_FROM].strip() == 'FROM {0}'.format(BUILDER_FROM)
        assert dfparser.lines[INDEX_SECOND_FROM].strip() == 'FROM {0}'.format(UPDATED_BASE_FROM)

        assert dfparser.cmd == BASE_CMD  # Last stage command is the base command; None, initially
        assert dfparser.lines[INDEX_FIRST_CMD].strip() == 'CMD {0}'.format(BUILDER_CMD)
        assert len(dfparser.lines) == INDEX_SECOND_CMD

        # Like FROM, updates to CMD should update only the CMD in the final stage.
        dfparser.cmd = UPDATED_BASE_CMD
        assert dfparser.cmd == UPDATED_BASE_CMD
        assert dfparser.lines[INDEX_FIRST_CMD].strip() == 'CMD {0}'.format(BUILDER_CMD)
        assert dfparser.lines[INDEX_SECOND_CMD].strip() == 'CMD {0}'.format(UPDATED_BASE_CMD)

    def test_add_del_instruction(self, dfparser):
        df_content = dedent("""\
            CMD xyz
            LABEL a=b c=d
            LABEL x=\"y z\"
            ENV h i
            ENV j='k' l=m
            """)
        dfparser.content = df_content

        dfparser._add_instruction('FROM', 'fedora')
        assert dfparser.baseimage == 'fedora'
        dfparser._delete_instructions('FROM')
        assert dfparser.baseimage is None

        dfparser._add_instruction('FROM', 'fedora')
        assert dfparser.baseimage == 'fedora'
        dfparser._delete_instructions('FROM', 'fedora')
        assert dfparser.baseimage is None

        dfparser._add_instruction('LABEL', ('Name', 'self'))
        assert len(dfparser.labels) == 4
        assert dfparser.labels.get('Name') == 'self'
        dfparser._delete_instructions('LABEL')
        assert dfparser.labels == {}

        dfparser._add_instruction('ENV', ('Name', 'self'))
        assert len(dfparser.envs) == 4
        assert dfparser.envs.get('Name') == 'self'
        dfparser._delete_instructions('ENV')
        assert dfparser.envs == {}

        assert dfparser.cmd == 'xyz'

    @pytest.mark.parametrize(('existing',
                              'delete_key',
                              'expected'), [
        # Delete non-existing key
        (['a b\n',
          'x="y z"\n'],
         'name',
         KeyError()),

        # Simple remove
        (['a b\n',
          'x="y z"\n'],
         'a',
         ['x="y z"\n']),

        # Simple remove
        (['a b\n',
          'x="y z"\n'],
         'x',
         ['a b\n']),

        #  Remove first of two instructions on the same line
        (['a b\n',
          'x="y z"\n',
          '"first"="first" "second"="second"\n'],
         'first',
         ['a b\n',
          'x="y z"\n',
          '"second"="second"\n']),

        #  Remove second of two instructions on the same line
        (['a b\n',
          'x="y z"\n',
          '"first"="first" "second"="second"\n'],
         'second',
         ['a b\n',
          'x="y z"\n',
          '"first"="first"\n']),
    ])
    def test_delete_instruction(self, dfparser, instruction, existing, delete_key, expected):
        existing = [instruction + ' ' + i for i in existing]
        if isinstance(expected, list):
            expected = [instruction + ' ' + i for i in expected]
        dfparser.lines = ["FROM xyz\n"] + existing

        if isinstance(expected, KeyError):
            with pytest.raises(KeyError):
                dfparser._delete_instructions(instruction, delete_key)
        else:
            dfparser._delete_instructions(instruction, delete_key)
            assert set(dfparser.lines[1:]) == set(expected)

    @pytest.mark.parametrize(('existing',
                              'new',
                              'expected'), [
        # Simple test: set an instruction
        (['a b\n',
          'x="y z"\n'],
         {'Name': 'New shiny project'},
         ['Name=\'New shiny project\'\n']),

        # Set two instructions
        (['a b\n',
          'x="y z"\n'],
         {'something': 'nothing', 'mine': 'yours'},
         ['something=nothing\n', 'mine=yours\n']),

        # Set instructions to what they already were: should be no difference
        (['a b\n',
          'x="y z"\n',
          '"first"="first" second=\'second value\'\n'],
         {'a': 'b', 'x': 'y z', 'first': 'first', 'second': 'second value'},
         ['a b\n',
          'x="y z"\n',
          '"first"="first" second=\'second value\'\n']),

        # Adjust one label of a multi-value LABEL/ENV statement
        (['a b\n',
          'first=\'first value\' "second"=second\n',
          'x="y z"\n'],
         {'first': 'changed', 'second': 'second'},
         ['first=changed "second"=second\n']),

        # Delete one label of a multi-value LABEL/ENV statement
        (['a b\n',
          'x="y z"\n',
          'first=first second=second\n'],
         {'second': 'second'},
         ['second=second\n']),

        # Nested quotes
        (['"ownership"="Alice\'s label" other=value\n'],
         {'ownership': "Alice's label"},
         # Keeps existing key quoting style
         ['"ownership"="Alice\'s label"\n']),

        # Modify a single value that needs quoting
        (['foo bar\n'],
         {'foo': 'extra bar'},
         ["foo 'extra bar'\n"]),
    ])
    def test_setter(self, dfparser, instruction, existing, new, expected):
        existing = [instruction + ' ' + i for i in existing]
        if isinstance(expected, list):
            expected = [instruction + ' ' + i for i in expected]
        dfparser.lines = ["FROM xyz\n"] + existing

        if instruction == 'LABEL':
            dfparser.labels = new
            assert dfparser.labels == new
        elif instruction == 'ENV':
            dfparser.envs = new
            assert dfparser.envs == new
        assert set(dfparser.lines[1:]) == set(expected)

    @pytest.mark.parametrize(('old_instructions', 'key', 'new_value', 'expected'), [
        # Simple case, no '=' or quotes
        ('Release 1', 'Release', '2', 'Release 2'),
        # No '=' but quotes (which are kept)
        ('"Release" "2"', 'Release', '3', '"Release" 3'),
        # Simple case, '=' but no quotes
        ('Release=1', 'Release', '6', 'Release=6'),
        # '=' and quotes, with space in the value
        ('"Name"=\'alpha alpha\' Version=1', 'Name', 'beta delta', '"Name"=\'beta delta\' Version=1'),
        ('Name=foo', 'Name', 'new value', "Name='new value'"),
        # ' ' and quotes
        ('"Name" alpha alpha', 'Name', 'beta delta', "\"Name\" 'beta delta'"),
        # '=', multiple labels, no quotes
        ('Name=foo Release=3', 'Release', '4', 'Name=foo Release=4'),
        # '=', multiple labels and quotes
        ('Name=\'foo bar\' "Release"="4"', 'Release', '5', 'Name=\'foo bar\' "Release"=5'),
        # Release that's not entirely numeric
        ('Version=1.1', 'Version', '2.1', 'Version=2.1'),
    ])
    def test_setter_direct(self, dfparser, instruction, old_instructions, key, new_value, expected):
        df_content = dedent("""\
            FROM xyz
            LABEL a b
            LABEL x=\"y z\"
            ENV c d
            ENV e=\"f g\"
            {0} {1}
            """).format(instruction, old_instructions)

        dfparser.content = df_content
        if instruction == 'LABEL':
            dfparser.labels[key] = new_value
            assert dfparser.labels[key] == new_value
            assert dfparser.lines[-1] == '{0} {1}\n'.format(instruction, expected)
            del dfparser.labels[key]
            assert not dfparser.labels.get(key)
        elif instruction == 'ENV':
            dfparser.envs[key] = new_value
            assert dfparser.envs[key] == new_value
            assert dfparser.lines[-1] == '{0} {1}\n'.format(instruction, expected)
            del dfparser.envs[key]
            assert not dfparser.labels.get(key)

    @pytest.mark.parametrize('separator', [' ', '='])
    @pytest.mark.parametrize(('label', 'expected'), [
        # Expected substitutions
        ('$V', 'v'),
        ('"$V"', 'v'),
        ('$V-foo', 'v-foo'),
        ('"$V-foo"', 'v-foo'),
        ('"$V"-foo', 'v-foo'),
        ('${V}', 'v'),
        ('${V}-foo', 'v-foo'),
        ('$V-{foo}', 'v-{foo}'),
        ('$VS', 'spam maps'),

        # These should not be substituted, only dequoted
        ("'$V'", "$V"),
        ("\\$V", "$V"),

        # Try to trip up the parser
        ('\\"$V', '"v'),
        ("\\'$V", "'v"),
        ('$V}', 'v}'),
        ('${}', ''),
        ("'\\'$V'\\'", "\\v\\"),
    ])
    def test_env_replace(self, dfparser, label, expected, separator):
        dfparser.lines = ["FROM fedora\n",
                          "ENV V=v\n",
                          "ENV VS='spam maps'\n",
                          "LABEL TEST{0}{1}\n".format(separator, label)]
        assert dfparser.labels['TEST'] == expected

    @pytest.mark.parametrize('separator', [' ', '='])
    @pytest.mark.parametrize(('label', 'expected'), [
        # These would have been substituted with env_replace=True
        ('$V', '$V'),
        ('"$V"', '$V'),
        ('$V-foo', '$V-foo'),
        ('"$V-foo"', '$V-foo'),
        ('"$V"-foo', '$V-foo'),
    ])
    def test_env_noreplace(self, dfparser, label, expected, separator):
        """
        Make sure environment replacement can be disabled.
        """
        dfparser.env_replace = False
        dfparser.lines = ["FROM fedora\n",
                          "ENV V=v\n",
                          "LABEL TEST{0}{1}\n".format(separator, label)]
        assert dfparser.labels['TEST'] == expected

    @pytest.mark.parametrize('label', [
        '${V',
        '"${V"',
        '${{{{V}',
    ])
    def test_env_invalid(self, dfparser, label):
        """
        These tests are invalid, but the parser should at least terminate
        even if it raises an exception.
        """
        dfparser.lines = ["FROM fedora\n",
                          "ENV v=v\n",
                          "LABEL TEST={0}\n".format(label)]
        try:
            dfparser.labels['TEST']
        except:
            pass

    def test_env_multistage(self, dfparser):
        dfparser.content = dedent("""\
            FROM stuff
            ENV a=keep b=keep

            FROM base
            ENV a=delete
            RUN something
            """)

        dfparser.envs['a'] = "changed"
        del dfparser.envs['a']
        dfparser.envs['b'] = "new"

        lines = dfparser.lines
        assert "ENV" in lines[1]
        assert "a=keep" in lines[1]
        assert "b=new" not in lines[1]
        assert "a=delete" not in dfparser.content
        assert "b=new" in lines[-1]

    @pytest.mark.xfail
    @pytest.mark.parametrize(('label', 'expected'), [
        ('${V:-foo}', 'foo'),
        ('${V:+foo}', 'v'),
        ('${UNDEF:+foo}', 'foo'),
        ('${UNDEF:+${V}}', 'v'),
    ])
    def test_env_replace_notimplemented(self, dfparser, label, expected):
        """
        Test for syntax we don't support yet but should.
        """
        dfparser.lines = ["FROM fedora\n",
                          "ENV V=v\n",
                          "LABEL TEST={0}\n".format(label)]
        assert dfparser.labels['TEST'] == expected

    def test_path_and_fileobj_together(self):
        with pytest.raises(ValueError):
            DockerfileParser(path='.', fileobj=six.StringIO())

    def test_nonseekable_fileobj(self):
        with pytest.raises(AttributeError):
            DockerfileParser(fileobj=sys.stdin)

    def test_context_structure_per_line(self, dfparser, instruction):
        dfparser.content = dedent("""\
            FROM fedora:25

            {0} multi.label1="value1" \\
                  multi.label2="value2" \\
                  other="value3"

            {0} 2multi.label1="othervalue1" 2multi.label2="othervalue2" other="othervalue3"

            {0} "com.example.vendor"="ACME Incorporated"
            {0} com.example.label-with-value="foo"
            {0} version="1.0"
            {0} description="This text illustrates \\
            that label-values can span multiple lines."
            {0} key="with = in the value"
            """).format(instruction)

        c = dfparser.context_structure

        assert c[1].get_line_value(context_type=instruction) == {
            "multi.label1": "value1",
            "multi.label2": "value2",
            "other": "value3"
        }

        assert c[2].get_line_value(context_type=instruction) == {
            "2multi.label1": "othervalue1",
            "2multi.label2": "othervalue2",
            "other": "othervalue3"
        }

        assert c[3].get_line_value(context_type=instruction) == {
            "com.example.vendor": "ACME Incorporated"
        }

        assert c[4].get_line_value(context_type=instruction) == {
            "com.example.label-with-value": "foo"
        }

        assert c[5].get_line_value(context_type=instruction) == {
            "version": "1.0"
        }

        assert c[6].get_line_value(context_type=instruction) == {
            "description": "This text illustrates that label-values can span multiple lines."
        }

        assert c[7].get_line_value(context_type=instruction) == {
            "key": "with = in the value"
        }

    def test_context_structure(self, dfparser, instruction):
        dfparser.content = dedent("""\
            FROM fedora:25

            {0} multi.label1="value1" \\
                  multi.label2="value2" \\
                  other="value3"

            {0} 2multi.label1="othervalue1" 2multi.label2="othervalue2" other="othervalue3"

            {0} "com.example.vendor"="ACME Incorporated"
            {0} com.example.label-with-value="foo"
            {0} version="1.0"
            {0} description="This text illustrates \\
            that label-values can span multiple lines."
            """).format(instruction)

        c = dfparser.context_structure

        assert c[1].get_values(context_type=instruction) == {
            "multi.label1": "value1",
            "multi.label2": "value2",
            "other": "value3"
        }

        assert c[2].get_values(context_type=instruction) == {
            "multi.label1": "value1",
            "multi.label2": "value2",
            "other": "othervalue3",
            "2multi.label1": "othervalue1",
            "2multi.label2": "othervalue2"
        }

        assert c[3].get_values(context_type=instruction) == {
            "multi.label1": "value1",
            "multi.label2": "value2",
            "other": "othervalue3",
            "2multi.label1": "othervalue1",
            "2multi.label2": "othervalue2",
            "com.example.vendor": "ACME Incorporated"
        }

        assert c[4].get_values(context_type=instruction) == {
            "multi.label1": "value1",
            "multi.label2": "value2",
            "other": "othervalue3",
            "2multi.label1": "othervalue1",
            "2multi.label2": "othervalue2",
            "com.example.vendor": "ACME Incorporated",
            "com.example.label-with-value": "foo"
        }

        assert c[5].get_values(context_type=instruction) == {
            "multi.label1": "value1",
            "multi.label2": "value2",
            "other": "othervalue3",
            "2multi.label1": "othervalue1",
            "2multi.label2": "othervalue2",
            "com.example.vendor": "ACME Incorporated",
            "com.example.label-with-value": "foo",
            "version": "1.0"
        }

        assert c[6].get_values(context_type=instruction) == {"multi.label1": "value1",
                                                             "multi.label2": "value2",
                                                             "other": "othervalue3",
                                                             "2multi.label1": "othervalue1",
                                                             "2multi.label2": "othervalue2",
                                                             "com.example.vendor": "ACME Incorporated",
                                                             "com.example.label-with-value": "foo",
                                                             "version": "1.0",
                                                             "description": "This text illustrates that label-values can span multiple lines."
                                                             }

    def test_context_structure_mixed(self, dfparser, instruction):
        dfparser.content = dedent("""\
            FROM fedora:25

            {0} key=value
            RUN touch /tmp/a
            {0} key2=value2""").format(instruction)

        c = dfparser.context_structure
        assert c[0].get_values(context_type=instruction) == {}
        assert c[1].get_values(context_type=instruction) == {"key": "value"}
        assert c[2].get_values(context_type=instruction) == {"key": "value"}
        assert c[3].get_values(context_type=instruction) == {"key": "value",
                                                             "key2": "value2"}

    def test_context_structure_mixed_env_label(self, dfparser):
        dfparser.content = dedent("""\
            FROM fedora:25

            ENV key=value
            RUN touch /tmp/a
            LABEL key2=value2""")
        c = dfparser.context_structure

        assert c[0].get_values(context_type="ENV") == {}
        assert c[0].get_values(context_type="LABEL") == {}

        assert c[1].get_values(context_type="ENV") == {"key": "value"}
        assert c[1].get_values(context_type="LABEL") == {}

        assert c[2].get_values(context_type="ENV") == {"key": "value"}
        assert c[2].get_values(context_type="LABEL") == {}

        assert c[3].get_values(context_type="ENV") == {"key": "value"}
        assert c[3].get_values(context_type="LABEL") == {"key2": "value2"}

    def test_expand_concatenated_variables(self, dfparser):
        dfparser.content = dedent("""\
            FROM scratch
            ENV NAME=name VER=1
            LABEL component="$NAME$VER"
        """)
        assert dfparser.labels['component'] == 'name1'

    def test_label_env_key(self, dfparser):
        """
        Verify keys may be substituted with values containing space.

        Surprisingly, Docker allows environment variable substitution even
        in the keys of labels, and not only that but it allows them to
        contain spaces.
        """
        dfparser.content = dedent("""\
            FROM scratch
            ENV FOOBAR="foo bar"
            LABEL "$FOOBAR"="baz"
        """)
        assert dfparser.labels['foo bar'] == 'baz'

    @pytest.mark.parametrize('value', [
        'a=b c',
    ])
    def test_label_invalid(self, dfparser, value):
        dfparser.content = '\n'.join([
            "FROM scratch",
            "LABEL {0}".format(value),
        ])
        with pytest.raises(Exception):
            dfparser.labels

    def test_add_lines_stages(self, dfparser):
        dfparser.content = dedent("""\
            From builder
            CMD xyz
            From base
            LABEL a=b c=d
            ENV h i
            """)
        dfparser.add_lines("something new", all_stages=True)
        assert "something new" in dfparser.lines[2]
        assert "something new" in dfparser.lines[-1]
        assert len([line for line in dfparser.lines if "something new" in line]) == 2
        assert len(dfparser.lines) == 7

    @pytest.mark.parametrize('at_start', [True, False])
    def test_add_lines_stages_skip_scratch(self, dfparser, at_start):
        dfparser.content = dedent("""\
            From builder
            CMD xyz
            From scratch
            LABEL type=scratch
            From base
            LABEL a=b c=d
            ENV h i
            From scratch
            LABEL type=scratch2
            """)
        dfparser.add_lines("something new", all_stages=True, skip_scratch=True, at_start=at_start)

        if at_start:
            assert "something new" in dfparser.lines[1]
            assert "something new" in dfparser.lines[6]
        else:
            assert "something new" in dfparser.lines[2]
            assert "something new" in dfparser.lines[8]
        assert len([line for line in dfparser.lines if "something new" in line]) == 2
        assert len(dfparser.lines) == 11

    def test_add_lines_stage_edge(self, dfparser):
        dfparser.content = "# no from or newline"
        dfparser.add_lines("begin with new", at_start=True)
        dfparser.add_lines("end with new")
        assert "begin with new" in dfparser.lines[0]
        assert "end with new" in dfparser.lines[2]

    @pytest.mark.parametrize(('anchor', 'raises'), [
        (
            3, None
        ),
        (
            'CMD xyz\n', None
        ),
        (
            dict(
                content='CMD xyz\n',
                startline=3,
                endline=3,
                instruction='CMD',
                value='xyz'
            ),
            None
        ),
        (
            -2, AssertionError
        ),
        (
            20, AssertionError
        ),
        (
            2.0, RuntimeError
        ),
        (
            'not there', RuntimeError
        ),
        (
            dict(), AssertionError
        ),
    ])
    def test_add_lines_at(self, dfparser, anchor, raises):
        dfparser.content = dedent("""\
            From builder
            CMD xyz
            LABEL a=b c=d
            CMD xyz
            """)

        if raises:
            with pytest.raises(raises):
                dfparser.add_lines_at(anchor, "# something new")
            return

        dfparser.add_lines_at(anchor, "# something new")
        assert "something new" in dfparser.content
        assert "something new" not in dfparser.lines[1]
        assert "something new" in dfparser.lines[3]
        assert "CMD" in dfparser.lines[4]

    @pytest.mark.parametrize('anchor', [
        1,
        'CMD xyz\n',
        dict(
            content='CMD xyz\n',
            startline=1,
            endline=1,
            instruction='CMD',
            value='xyz'
        ),
    ])
    def test_replace_lines_at(self, dfparser, anchor):
        dfparser.content = dedent("""\
            From builder
            CMD xyz
            LABEL a=b c=d
            """)

        dfparser.add_lines_at(anchor, "# something new", replace=True)
        assert "something new" in dfparser.lines[1]
        assert "CMD" not in dfparser.content

    @pytest.mark.parametrize('anchor', [
        1,
        'CMD xyz\n',
        dict(
            content='CMD xyz\n',
            startline=1,
            endline=1,
            instruction='CMD',
            value='xyz'
        ),
    ])
    def test_add_lines_after(self, dfparser, anchor):
        dfparser.content = dedent("""\
            From builder
            CMD xyz
            LABEL a=b c=d
            """)

        dfparser.add_lines_at(anchor, "# something new", after=True)
        assert "something new" in dfparser.lines[2]
        assert "CMD" in dfparser.lines[1]
        assert "LABEL" in dfparser.lines[3]

    def test_add_lines_at_edge(self, dfparser):
        dfparser.content = dedent("""\
            From builder
            CMD xyz
            LABEL a=b c=d""")  # no newline
        dfparser.add_lines_at(2, "# something new", after=True)
        assert "d#" not in dfparser.content
        assert 4 == len(dfparser.lines)
        assert "something new" in dfparser.lines[3]

    def test_add_lines_after_continuation(self, dfparser):
        dfparser.content = dedent("""\
            FROM builder
            RUN touch foo; \\
                touch bar
            """)

        fromline = dfparser.structure[1]
        assert fromline['instruction'] == 'RUN'
        dfparser.add_lines_at(fromline, "# something new", after=True)
        assert dfparser.lines == [
            "FROM builder\n",
            "RUN touch foo; \\\n",
            "    touch bar\n",
            "# something new\n",
        ]

    def test_replace_lines_continuation(self, dfparser):
        dfparser.content = dedent("""\
            FROM builder
            RUN touch foo; \\
                touch bar
            """)

        fromline = dfparser.structure[1]
        assert fromline['instruction'] == 'RUN'
        dfparser.add_lines_at(fromline, "# something new", replace=True)
        assert dfparser.lines == [
            "FROM builder\n",
            "# something new\n",
        ]

    def test_remove_whitespace(self, tmpdir):
        """
        Verify keys are parsed correctly even if there is no final newline.

        """
        with open(os.path.join(str(tmpdir), 'Dockerfile'), 'w') as fp:
            fp.write('FROM scratch')
        tmpdir_path = str(tmpdir.realpath())
        df1 = DockerfileParser(tmpdir_path)
        df1.labels['foo'] = 'bar'

        df2 = DockerfileParser(tmpdir_path, True)
        assert df2.baseimage == 'scratch'
        assert df2.labels['foo'] == 'bar'
