dockerfile-parser
====

[![Build Status](https://travis-ci.org/DBuildService/dockerfile-parser.svg?branch=master)](https://travis-ci.org/DBuildService/dockerfile-parser)

Python library for parsing Dockerfile files.

## Features

 * 

## Installation

### from git

Clone this git repo and install dockerfile-parser using python installer:

```shell
$ git clone https://github.com/DBuildService/dockerfile-parser.git
$ cd dockerfile-parser
$ sudo pip install .
```

## Usage

```python
from dockerfile_parser import DockerfileParser
dfp=DockerfileParser('.')
dfp.lines = ["# comment\n",
             " From  \\\n",
             "   base\n",
             " # comment\n",
             " label  foo  \\\n",
             "    bar  \n",
             "USER  no-newline"]
print(dfp.structure)
print(dfp.get_labels())
```