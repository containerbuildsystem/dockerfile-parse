#!/bin/bash
set -eux

# Prepare env vars
ENGINE=${ENGINE:="podman"}
OS=${OS:="centos"}
OS_VERSION=${OS_VERSION:="7"}
PYTHON_VERSION=${PYTHON_VERSION:="2"}
ACTION=${ACTION:="test"}
IMAGE="$OS:$OS_VERSION"
CONTAINER_NAME="dockerfile-parse-$OS-$OS_VERSION-py$PYTHON_VERSION"

if [[ $ACTION == "markdownlint" ]]; then
  IMAGE="ruby"
  CONTAINER_NAME="dockerfile-parse-$ACTION-$IMAGE"
fi

RUN="$ENGINE exec -ti $CONTAINER_NAME"

# Use arrays to prevent globbing and word splitting
engine_mounts=(-v "$PWD":"$PWD":z)
for dir in ${EXTRA_MOUNT:-}; do
  engine_mounts=("${engine_mounts[@]}" -v "$dir":"$dir":z)
done

# Create or resurrect container if needed
if [[ $($ENGINE ps -qa -f name="$CONTAINER_NAME" | wc -l) -eq 0 ]]; then
  $ENGINE run --name "$CONTAINER_NAME" -d "${engine_mounts[@]}" -w "$PWD" -ti "$IMAGE" sleep infinity
elif [[ $($ENGINE ps -q -f name="$CONTAINER_NAME" | wc -l) -eq 0 ]]; then
  echo found stopped existing container, restarting. volume mounts cannot be updated.
  $ENGINE container start "$CONTAINER_NAME"
fi

function setup_dfp() {
  # Pull fedora images from registry.fedoraproject.org
  if [[ $OS == "fedora" ]]; then
    IMAGE="registry.fedoraproject.org/$IMAGE"
  fi

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

  # CentOS needs to have setuptools updates to make pytest-cov work
  if [[ $OS != "fedora" ]]; then
    $RUN $PIP install -U setuptools

    # Watch out for https://github.com/pypa/setuptools/issues/937
    $RUN curl -O https://bootstrap.pypa.io/2.6/get-pip.py
    $RUN $PYTHON get-pip.py
  fi

  $RUN $PIP install -r tests/requirements.txt

  if [[ $PYTHON_VERSION -gt 2 ]]; then $RUN $PIP install -r requirements-py3.txt; fi
}

case ${ACTION} in
"test")
  setup_dfp
  TEST_CMD="py.test --cov dockerfile_parse --cov-report html -vv tests"
  ;;
"bandit")
  setup_dfp
  $RUN $PKG install -y git-core
  $RUN $PIP install bandit
  TEST_CMD="bandit-baseline -r dockerfile_parse -ll -ii"
  ;;
"markdownlint")
  $RUN gem install mdl
  TEST_CMD="mdl -g ."
  ;;
*)
  echo "Unknown action: ${ACTION}"
  exit 2
  ;;
esac

# Run tests
$RUN ${TEST_CMD} "$@"

echo "To run tests again:"
echo "$RUN ${TEST_CMD}"
