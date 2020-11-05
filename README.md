# dockerfile-parse

[![unittests status badge]][unittests status link]
[![coveralls status badge]][coveralls status link]
[![lgtm python badge]][lgtm python link]
[![lgtm alerts badge]][lgtm alerts link]
[![linters status badge]][linters status link]

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

[coveralls status badge]: https://coveralls.io/repos/containerbuildsystem/dockerfile-parse/badge.svg?branch=master
[coveralls status link]: https://coveralls.io/r/containerbuildsystem/dockerfile-parse?branch=master
[lgtm python badge]: https://img.shields.io/lgtm/grade/python/g/containerbuildsystem/dockerfile-parse.svg?logo=lgtm&logoWidth=18
[lgtm python link]: https://lgtm.com/projects/g/containerbuildsystem/dockerfile-parse/context:python
[lgtm alerts badge]: https://img.shields.io/lgtm/alerts/g/containerbuildsystem/dockerfile-parse.svg?logo=lgtm&logoWidth=18
[lgtm alerts link]: https://lgtm.com/projects/g/containerbuildsystem/dockerfile-parse/alerts
[linters status badge]: https://github.com/containerbuildsystem/dockerfile-parse/workflows/Linters/badge.svg?branch=master&event=push
[linters status link]: https://github.com/containerbuildsystem/dockerfile-parse/actions?query=event%3Apush+branch%3Amaster+workflow%3A%22Linters%22
[unittests status badge]: https://github.com/containerbuildsystem/dockerfile-parse/workflows/Unittests/badge.svg?branch=master&event=push
[unittests status link]: https://github.com/containerbuildsystem/dockerfile-parse/actions?query=event%3Apush+branch%3Amaster+workflow%3A%22Unittests%22
