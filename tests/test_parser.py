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

NON_ASCII = "žluťoučký"

class TestDockerfileParser(object):

    def test_dockerfileparser_non_ascii(self, tmpdir):
        df_content = """\
FROM fedora
CMD {0}""".format(NON_ASCII)
        df_lines = ["FROM fedora\n", "CMD {0}".format(NON_ASCII)]

        tmpdir_path = str(tmpdir.realpath())
        df = DockerfileParser(tmpdir_path)

        df.content = ""
        df.content = df_content
        assert df.content == df_content
        assert df.lines == df_lines

        df.content = ""
        df.lines = df_lines
        assert df.content == df_content
        assert df.lines == df_lines

    def test_dockerfile_structure(self, tmpdir):
        df = DockerfileParser(str(tmpdir))
        df.lines = ["# comment\n",        # should be ignored
                    " From  \\\n",        # mixed-case
                    "   base\n",          # extra ws, continuation line
                    " # comment\n",
                    " label  foo  \\\n",  # extra ws
                    "    bar  \n",        # extra ws, continuation line
                    "USER  no-newline"]   # extra ws, no newline

        structure = df.structure
        assert structure == [{'instruction': 'FROM',
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
                          'content': 'USER  no-newline',
                          'value': 'no-newline'}]

    def test_get_baseimg_from_df(self, tmpdir):
        tmpdir_path = str(tmpdir.realpath())
        df = DockerfileParser(tmpdir_path)
        df.lines = ["From fedora:latest\n",
                    "LABEL a b\n"]
        base_img = df.get_baseimage()
        assert base_img.startswith('fedora')

    def test_get_labels_from_df(self, tmpdir):
        tmpdir_path = str(tmpdir.realpath())
        df = DockerfileParser(tmpdir_path)
        df.content = ""
        lines = df.lines
        lines.insert(-1, 'LABEL "label1"="value 1" "label2"=myself label3="" label4\n')
        lines.insert(-1, 'LABEL label5=5\n')
        lines.insert(-1, 'LABEL "label6"=6\n')
        lines.insert(-1, 'LABEL label7\n')
        lines.insert(-1, 'LABEL "label8"\n')
        lines.insert(-1, 'LABEL "label9"="asd \  \nqwe"\n')
        lines.insert(-1, 'LABEL "label10"="{0}"\n'.format(NON_ASCII))
        lines.insert(-1, 'LABEL "label1 1"=1\n')
        # old syntax (without =)
        lines.insert(-1, 'LABEL label101 101\n')
        lines.insert(-1, 'LABEL label102 1 02\n')
        lines.insert(-1, 'LABEL "label103" 1 03\n')
        lines.insert(-1, 'LABEL label104 "1" 04\n')
        lines.insert(-1, 'LABEL label105 1 \'05\'\n')
        lines.insert(-1, 'LABEL label106 1 \'0\'   6\n')
        df.lines = lines
        labels = df.get_labels()
        assert len(labels) == 17
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
        assert labels.get('label101') == '101'
        assert labels.get('label102') == '1 02'
        assert labels.get('label103') == '1 03'
        assert labels.get('label104') == '1 04'
        assert labels.get('label105') == '1 05'
        assert labels.get('label106') == '1 0   6'
