dockerfile-parse
====

[![Build Status](https://travis-ci.org/DBuildService/dockerfile-parse.svg?branch=master)](https://travis-ci.org/DBuildService/dockerfile-parse)

Python library for parsing Dockerfile files.

## Installation

### from git

Clone this git repo and install dockerfile-parse using python installer:

```shell
$ git clone https://github.com/DBuildService/dockerfile-parse.git
$ cd dockerfile-parse
$ sudo pip install .
```

## Usage

```python
from pprint import pprint
from dockerfile_parse import DockerfileParser
dfp=DockerfileParser()
dfp.content = """\
From  base
LABEL foo="bar baz"
USER  me"""
pprint(dfp.structure)
pprint(dfp.json)
pprint(dfp.labels)
```
