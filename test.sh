#!/bin/bash
set -eux

# Prepare env vars
OS=${OS:="centos"}
OS_VERSION=${OS_VERSION:="7"}
PYTHON_VERSION=${PYTHON_VERSION:="2"}
IMAGE="$OS:$OS_VERSION"
docker_mounts="-v $PWD:$PWD:z"
for dir in ${EXTRA_MOUNT:-}; do
  docker_mounts="${docker_mounts} -v $dir:$dir:z"
done

# Pull fedora images from registry.fedoraproject.org
if [[ $OS == "fedora" ]]; then
  IMAGE="registry.fedoraproject.org/$IMAGE"
fi


CONTAINER_NAME="dockerfile-parse-$OS-$OS_VERSION-py$PYTHON_VERSION"
RUN="docker exec -ti $CONTAINER_NAME"
if [[ $OS == "fedora" ]]; then
  PIP_PKG="python$PYTHON_VERSION-pip"
  PIP="pip$PYTHON_VERSION"
  PKG="dnf"
  PKG_EXTRA="dnf-plugins-core"
  BUILDDEP="dnf builddep"
  PYTHON="python$PYTHON_VERSION"
else
  PIP_PKG="python-pip"
  PIP="pip"
  PKG="yum"
  PKG_EXTRA="yum-utils epel-release"
  BUILDDEP="yum-builddep"
  PYTHON="python"
fi

# Create or resurrect container if needed
if [[ $(docker ps -qa -f name=$CONTAINER_NAME | wc -l) -eq 0 ]]; then
  docker run --name $CONTAINER_NAME -d $docker_mounts -w $PWD -ti $IMAGE sleep infinity
elif [[ $(docker ps -q -f name=$CONTAINER_NAME | wc -l) -eq 0 ]]; then
  echo found stopped existing container, restarting. volume mounts cannot be updated.
  docker container start $CONTAINER_NAME
 fi

# Install dependencies
$RUN $PKG install -y $PKG_EXTRA
$RUN $BUILDDEP -y python-dockerfile-parse.spec
if [[ $OS != "fedora" ]]; then
  # Install dependecies for test, as check is disabled for rhel
  $RUN yum install -y python-six
fi

# Install package
$RUN $PKG install -y $PIP_PKG
if [[ $PYTHON_VERSION == 3 ]]; then
  # https://fedoraproject.org/wiki/Changes/Making_sudo_pip_safe
  $RUN mkdir -p /usr/local/lib/python3.6/site-packages/
fi
$RUN $PYTHON setup.py install

$RUN $PIP install -r tests/requirements.txt

# CentOS needs to have setuptools updates to make pytest-cov work
if [[ $OS != "fedora" ]]; then
  $RUN $PIP install -U setuptools

  # Watch out for https://github.com/pypa/setuptools/issues/937
  $RUN curl -O https://bootstrap.pypa.io/2.6/get-pip.py
  $RUN $PYTHON get-pip.py
fi
if [[ $PYTHON_VERSION -gt 2 ]]; then $RUN $PIP install -r requirements-py3.txt; fi

# Run tests
$RUN py.test --cov dockerfile_parse --cov-report html -vv tests "$@"

echo "To run tests again:"
echo "$RUN py.test --cov dockerfile_parse --cov-report html -vv tests"
