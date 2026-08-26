#!/bin/bash

# Check command result
# $1: command result (usually $?)
# $2: awaited command result
checkResult() {
    if [ $1 -ne $2 ]
    then
        echo "Error occured. Please check command output."
        exit 1
    fi  
}

# install core dependencies
# we install scipy and numpy from debian repositories because it's too long (and problematic) to build these libraries on raspi
apt-get -y update
apt-get install -y python3-dev libffi-dev libssl-dev python3-scipy python3-numpy
checkResult $? 0
apt-get clean -y
apt-get autoremove -y
echo "Done"
echo ""

# install pip (or upgrade if necessary)
echo "Installing pip..."
PY_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')
wget --no-check-certificate -O /tmp/get-pip.py "https://bootstrap.pypa.io/pip/3.${PY_MINOR}/get-pip.py"
checkResult $? 0
python3 /tmp/get-pip.py --trusted-host pypi.python.org
checkResult $? 0
rm -f /tmp/get-pip.py
echo "Done"
echo ""

# install python dependencies
echo "Installing python dependencies..."
pip install --no-cache-dir --trusted-host pypi.python.org -r /etc/cleep/requirements.txt
checkResult $? 0
rm -rf /etc/cleep/requirements.txt || /bin/true
echo "Done"
echo ""

