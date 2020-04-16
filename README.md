# dockerfile-parse

[![build status]][build status link]
[![coverage status]][coverage status link]

Python library for parsing Dockerfile files.

## Installation

### From PyPI

```shell
pip install dockerfile-parse
```

### From git

Clone this git repo and install using the python installer

```shell
git clone https://github.com/containerbuildsystem/dockerfile-parse.git
cd dockerfile-parse
sudo pip install .
```

## Usage

```python
from pprint import pprint
from dockerfile_parse import DockerfileParser

dfp = DockerfileParser()
dfp.content = """\
From  base
LABEL foo="bar baz"
USER  me"""

# Print the parsed structure:
pprint(dfp.structure)
pprint(dfp.json)
pprint(dfp.labels)

# Set a new base:
dfp.baseimage = 'centos:7'

# Print the new Dockerfile with an updated FROM line:
print(dfp.content)
```

[build status]: https://travis-ci.org/containerbuildsystem/dockerfile-parse.svg?branch=master
[build status link]: https://travis-ci.org/containerbuildsystem/dockerfile-parse
[coverage status]: https://coveralls.io/repos/containerbuildsystem/dockerfile-parse/badge.svg?branch=master&service=github
[coverage status link]: https://coveralls.io/github/containerbuildsystem/dockerfile-parse?branch=master