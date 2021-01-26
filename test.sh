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
  RUN="$ENGINE exec -i $CONTAINER_NAME"
  if [[ $OS == "centos" ]]; then
    PYTHON="python"
    PIP_PKG="python-pip"
    PIP="pip"
    PKG="yum"
    PKG_EXTRA=(yum-utils epel-release)
    BUILDDEP="yum-builddep"
  else
    PYTHON="python$PYTHON_VERSION"
    PIP_PKG="$PYTHON-pip"
    PIP="pip$PYTHON_VERSION"
    PKG="dnf"
    PKG_EXTRA=(dnf-plugins-core "$PYTHON"-pylint)
    BUILDDEP=(dnf builddep)
  fi

  PIP_INST=("$PIP" install --index-url "${PYPI_INDEX:-https://pypi.org/simple}")

  # Install dependencies
  $RUN $PKG install -y "${PKG_EXTRA[@]}"
  $RUN $"${BUILDDEP[@]}" -y python-dockerfile-parse.spec
  if [[ $OS = "centos" ]]; then
    # Install dependecies for test, as check is disabled for rhel
    $RUN yum install -y python-six
  fi

  # Install pip package
  $RUN $PKG install -y $PIP_PKG
  if [[ $PYTHON_VERSION == 3 ]]; then
    # https://fedoraproject.org/wiki/Changes/Making_sudo_pip_safe
    $RUN mkdir -p /usr/local/lib/python3.6/site-packages/
  fi

  # Setuptools install dfp from source
  $RUN $PYTHON setup.py install

  # CentOS needs to have setuptools updates to make pytest-cov work
  if [[ $OS = "centos" && $OS_VERSION == 7  ]]; then
    $RUN "${PIP_INST[@]}" -U 'pip<21.0'
    $RUN "${PIP_INST[@]}" -U setuptools
  fi

  # Pip install packages for unit tests
  $RUN "${PIP_INST[@]}" -r tests/requirements.txt
}

case ${ACTION} in
"test")
  setup_dfp
  TEST_CMD="coverage run --source=dockerfile_parse -m pytest tests -ra --color=auto --html=__pytest_reports/dfp-unit-tests.html --self-contained-html"
  ;;
"pylint")
  setup_dfp
  PACKAGES='dockerfile_parse tests'
  TEST_CMD="${PYTHON} -m pylint ${PACKAGES}"
  ;;
"bandit")
  setup_dfp
  $RUN $PKG install -y git-core
  $RUN $PIP install 'bandit<1.6.3'
  TEST_CMD="bandit-baseline -r dockerfile_parse -ll -ii"
  ;;
*)
  echo "Unknown action: ${ACTION}"
  exit 2
  ;;
esac

# Run tests
# shellcheck disable=SC2086
$RUN ${TEST_CMD} "$@"

echo "To run tests again:"
echo "$RUN ${TEST_CMD}"
