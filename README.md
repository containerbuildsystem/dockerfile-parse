dockerfile-parse
====

[![Build Status](https://travis-ci.org/DBuildService/dockerfile-parse.svg?branch=master)](https://travis-ci.org/DBuildService/dockerfile-parse)

Python library for parsing Dockerfile files.

## Features

 * 

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
from dockerfile_parse import DockerfileParser
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