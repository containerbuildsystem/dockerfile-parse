# -*- coding: utf-8 -*-
"""
Copyright (c) 2015 Red Hat, Inc
All rights reserved.

This software may be modified and distributed under the terms
of the BSD license. See the LICENSE file for details.
"""

from __future__ import unicode_literals

import json
import pytest

from dockerfile_parse import DockerfileParser

NON_ASCII = "žluťoučký"


class TestDockerfileParser(object):

    @pytest.mark.parametrize('cache_content', [
        False,
        True
    ])
    def test_dockerfileparser(self, tmpdir, cache_content):
        df_content = """\
FROM fedora
CMD {0}""".format(NON_ASCII)
        df_lines = ["FROM fedora\n", "CMD {0}".format(NON_ASCII)]

        tmpdir_path = str(tmpdir.realpath())
        df = DockerfileParser(tmpdir_path, cache_content)

        df.content = ""
        df.content = df_content
        assert df.content == df_content
        assert df.lines == df_lines

        df.content = ""
        df.lines = df_lines
        assert df.content == df_content
        assert df.lines == df_lines

    def test_constructor_cache(self, tmpdir):
        tmpdir_path = str(tmpdir.realpath())
        df1 = DockerfileParser(tmpdir_path)
        df1.lines = ["From fedora:latest\n", "LABEL a b\n"]

        df2 = DockerfileParser(tmpdir_path, True)
        assert df2.cached_content

    @pytest.mark.parametrize('cache_content', [
        False,
        True
    ])
    def test_dockerfile_structure(self, tmpdir, cache_content):
        df = DockerfileParser(str(tmpdir), cache_content)
        df.lines = ["# comment\n",        # should be ignored
                    " From  \\\n",        # mixed-case
                    "   base\n",          # extra ws, continuation line
                    " # comment\n",
                    " label  foo  \\\n",  # extra ws
                    "    bar  \n",        # extra ws, continuation line
                    "USER  {0}".format(NON_ASCII)]   # extra ws, no newline

        assert df.structure == [{'instruction': 'FROM',
                                 'startline': 1,  # 0-based
                                 'endline': 2,
                                 'content': ' From  \\\n   base\n',
                                 'value': 'base'},
                                {'instruction': 'LABEL',
                                 'startline': 4,
                                 'endline': 5,
                                 'content': ' label  foo  \\\n    bar  \n',
                                 'value': 'foo      bar'},
                                {'instruction': 'USER',
                                 'startline': 6,
                                 'endline': 6,
                                 'content': 'USER  {0}'.format(NON_ASCII),
                                 'value': '{0}'.format(NON_ASCII)}]

    @pytest.mark.parametrize('cache_content', [
        False,
        True
    ])
    def test_dockerfile_json(self, tmpdir, cache_content):
        df = DockerfileParser(str(tmpdir), cache_content)
        df.content = """\
# comment
From  base
LABEL foo="bar baz"
USER  {0}""".format(NON_ASCII)
        expected = json.dumps([{"FROM": "base"},
                               {"LABEL": "foo=\"bar baz\""},
                               {"USER": "{0}".format(NON_ASCII)}])
        assert df.json == expected

    @pytest.mark.parametrize('cache_content', [
        False,
        True
    ])
    def test_get_baseimg_from_df(self, tmpdir, cache_content):
        tmpdir_path = str(tmpdir.realpath())
        df = DockerfileParser(tmpdir_path, cache_content)
        df.lines = ["From fedora:latest\n",
                    "LABEL a b\n"]
        base_img = df.baseimage
        assert base_img.startswith('fedora')

    @pytest.mark.parametrize('cache_content', [
        False,
        True
    ])
    def test_get_labels_from_df(self, tmpdir, cache_content):
        tmpdir_path = str(tmpdir.realpath())
        df = DockerfileParser(tmpdir_path, cache_content)
        df.content = ""
        lines = []
        lines.insert(-1, 'LABEL "label1"=\'value 1\' "label2"=myself label3="" label4\n')
        lines.insert(-1, 'LABEL label5=5\n')
        lines.insert(-1, 'LABEL "label6"=6\n')
        lines.insert(-1, 'LABEL label7\n')
        lines.insert(-1, 'LABEL "label8"\n')
        lines.insert(-1, 'LABEL "label9"="asd \  \nqwe"\n')
        lines.insert(-1, 'LABEL "label10"="{0}"\n'.format(NON_ASCII))
        lines.insert(-1, 'LABEL "label1 1"=1\n')
        lines.insert(-1, 'LABEL "label12"=12 \ \n   "label13"=13\n')
        # old syntax (without =)
        lines.insert(-1, 'LABEL label101 101\n')
        lines.insert(-1, 'LABEL label102 1 02\n')
        lines.insert(-1, 'LABEL "label103" 1 03\n')
        lines.insert(-1, 'LABEL label104 "1"  04\n')
        lines.insert(-1, 'LABEL label105 1 \'05\'\n')
        lines.insert(-1, 'LABEL label106 1 \'0\'   6\n')
        df.lines = lines
        labels = df.labels
        assert len(labels) == 19
        assert labels.get('label1') == 'value 1'
        assert labels.get('label2') == 'myself'
        assert labels.get('label3') == ''
        assert labels.get('label4') == ''
        assert labels.get('label5') == '5'
        assert labels.get('label6') == '6'
        assert labels.get('label7') == ''
        assert labels.get('label8') == ''
        assert labels.get('label9') == 'asd qwe'
        assert labels.get('label10') == '{0}'.format(NON_ASCII)
        assert labels.get('label1 1') == '1'
        assert labels.get('label12') == '12'
        assert labels.get('label13') == '13'
        assert labels.get('label101') == '101'
        assert labels.get('label102') == '1 02'
        assert labels.get('label103') == '1 03'
        assert labels.get('label104') == '1  04'
        assert labels.get('label105') == '1 05'
        assert labels.get('label106') == '1 0   6'

    def test_modify_instruction(self, tmpdir):
        FROM = ('ubuntu', 'fedora:latest')
        CMD = ('old cmd', 'new command')
        df_content = """\
FROM {0}
CMD {1}""".format(FROM[0], CMD[0])

        tmpdir_path = str(tmpdir.realpath())
        dfp = DockerfileParser(tmpdir_path)
        dfp.content = df_content

        assert dfp.baseimage == FROM[0]
        dfp.baseimage = FROM[1]
        assert dfp.baseimage == FROM[1]

        assert dfp.cmd == CMD[0]
        dfp.cmd = CMD[1]
        assert dfp.cmd == CMD[1]

    @pytest.mark.parametrize(('old_labels', 'key', 'new_value', 'expected'), [
        # Simple case, no '=' or quotes
        ('Release 1', 'Release', '2', 'Release 2'),
        # No '=' but quotes
        ('"Release" "2"', 'Release', '3', 'Release 3'),
        # Deal with another label
        ('Release 3\nLABEL Name foo', 'Release', '4', 'Release 4'),
        # Simple case, '=' but no quotes
        ('Release=1', 'Release', '6', 'Release=6'),
        # '=' and quotes
        ('"Name"=\'alpha alpha\' Version=1', 'Name', 'beta delta', 'Name=\'beta delta\' Version=1'),
        # '=', multiple labels, no quotes
        ('Name=foo Release=3', 'Release', '4', 'Name=foo Release=4'),
        # '=', multiple labels and quotes
        ('Name=\'foo bar\' "Release"="4"', 'Release', '5', 'Name=\'foo bar\' Release=5'),
        # Release that's not entirely numeric
        ('Version=1.1', 'Version', '2.1', 'Version=2.1'),
    ])
    def test_change_labels(self, tmpdir, key, old_labels, new_value, expected):
        df_content = """\
FROM xyz
LABEL a b
LABEL {0}
LABEL x=\"y z\"
""".format(old_labels)

        tmpdir_path = str(tmpdir.realpath())
        dfp = DockerfileParser(tmpdir_path)
        dfp.content = df_content

        dfp.change_labels({key: new_value})
        assert dfp.labels[key] == new_value
        assert dfp.lines[2] == 'LABEL {0}\n'.format(expected)

    def test_add_del_instruction(self, tmpdir):
        df_content = """\
CMD xyz
LABEL a=b c=d
LABEL x=\"y z\"
"""
        tmpdir_path = str(tmpdir.realpath())
        dfp = DockerfileParser(tmpdir_path)
        dfp.content = df_content

        dfp._add_instruction('FROM', 'fedora')
        assert dfp.baseimage == 'fedora'
        dfp._delete_instructions('FROM')
        assert dfp.baseimage is None

        dfp._add_instruction('FROM', 'fedora')
        assert dfp.baseimage == 'fedora'
        dfp._delete_instructions('FROM', 'fedora')
        assert dfp.baseimage is None

        dfp._add_instruction('LABEL', ('Name', 'self'))
        assert len(dfp.labels) == 4
        assert dfp.labels.get('Name') == 'self'
        dfp._delete_instructions('LABEL')
        assert dfp.labels == {}

        assert dfp.cmd == 'xyz'

    @pytest.mark.parametrize(('existing',
                              'delete_key',
                              'expected',
    ), [
        # Delete non-existing label
        (['LABEL a b\n',
          'LABEL x="y z"\n'],
         'name',
         KeyError()),

        # Simple remove
        (['LABEL a b\n',
          'LABEL x="y z"\n'],
         'a',
         ['LABEL x="y z"\n']),

        # Simple remove
        (['LABEL a b\n',
          'LABEL x="y z"\n'],
         'x',
         ['LABEL a b\n']),

        #  Remove first of two labels on the same line
        (['LABEL a b\n',
          'LABEL x="y z"\n',
          'LABEL "first"="first" "second"="second"\n'],
         'first',
         ['LABEL a b\n',
          'LABEL x="y z"\n',
          'LABEL second=second\n']),

        #  Remove second of two labels on the same line
        (['LABEL a b\n',
          'LABEL x="y z"\n',
          'LABEL "first"="first" "second"="second"\n'],
         'second',
         ['LABEL a b\n',
          'LABEL x="y z"\n',
          'LABEL first=first\n']),
    ])
    def test_delete_label(self, tmpdir, existing, delete_key, expected):
        tmpdir_path = str(tmpdir.realpath())
        dfp = DockerfileParser(tmpdir_path)
        dfp.lines = ["FROM xyz\n"] + existing

        if isinstance(expected, KeyError):
            with pytest.raises(KeyError):
                dfp._delete_instructions('LABEL', delete_key)
        else:
            dfp._delete_instructions('LABEL', delete_key)
            assert set(dfp.lines[1:]) == set(expected)

    @pytest.mark.parametrize(('existing',
                              'labels',
                              'expected',
    ), [
        # Simple test: set a label
        (['LABEL a b\n',
          'LABEL x="y z"\n'],
         {'Name': 'New shiny project'},
         ['LABEL Name=\'New shiny project\'\n']),

        # Set two labels
        (['LABEL a b\n',
          'LABEL x="y z"\n'],
         {'something': 'nothing', 'mine': 'yours'},
         ['LABEL something=nothing\n', 'LABEL mine=yours\n']),

        # Set labels to what they already were: should be no difference
        (['LABEL a b\n',
          'LABEL x="y z"\n',
          'LABEL "first"="first" second=\'second value\'\n'],
         {'a': 'b', 'x': 'y z', 'first': 'first', 'second': 'second value'},
         ['LABEL a b\n',
          'LABEL x="y z"\n',
          'LABEL "first"="first" second=\'second value\'\n']),

        # Adjust one label of a multi-value LABEL statement
        (['LABEL a b\n',
          'LABEL first=\'first value\' "second"=second\n',
          'LABEL x="y z"\n'],
         {'first': 'changed', 'second': 'second'},
         ['LABEL first=changed second=second\n']),

        # Delete one label of a multi-value LABEL statement
        (['LABEL a b\n',
          'LABEL x="y z"\n',
          'LABEL first=first second=second\n'],
         {'second': 'second'},
         ['LABEL second=second\n']),

        # Nested quotes
        (['LABEL "ownership"="Alice\'s label" other=value\n'],
         {'ownership': "Alice's label"},
         # quote() will always use single quotes when it can
         ["LABEL ownership='Alice\'\"\'\"\'s label'\n"]),

        # Modify a single value that needs quoting
        (['LABEL foo bar\n'],
         {'foo': 'extra bar'},
         ["LABEL foo 'extra bar'\n"]),
    ])
    def test_labels_setter(self, tmpdir, existing, labels, expected):
        tmpdir_path = str(tmpdir.realpath())
        dfp = DockerfileParser(tmpdir_path)
        dfp.lines = ["FROM xyz\n"] + existing

        dfp.labels = labels
        assert dfp.labels == labels
        assert set(dfp.lines[1:]) == set(expected)

    @pytest.mark.parametrize('label', [
        "LABEL mylabel=foo\n",
        "LABEL mylabel foo\n",
    ])
    def test_labels_setter_direct(self, tmpdir, label):
        tmpdir_path = str(tmpdir.realpath())
        dfp = DockerfileParser(tmpdir_path)
        dfp.lines = ["FROM xyz\n",
                     label]

        dfp.labels['mylabel'] = 'bar'
        assert dfp.labels['mylabel'] == 'bar'

        dfp.labels['newlabel'] = 'new'
        assert dfp.labels == {'mylabel': 'bar', 'newlabel': 'new'}

        del dfp.labels['newlabel']
        assert dfp.labels == {'mylabel': 'bar'}
