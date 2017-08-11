#!/usr/bin/env bash
#
# Copyright 2017 IBM Corp.
#
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

if [ "$1" == "--help" ]; then
    echo "Usage: dbflavor-upload.sh -d db-name"
    echo ""
    echo "See the README.rst file for more information"
    exit 1
fi

# pip cache is not handled correctly when in another user's home directory
if [[ $EUID -eq 0 ]] && [[ "$(pwd)" != "/root"* ]]; then
    echo "This script may be run by any user.  But if run as root, it should be from /root"

    exit 1
fi

if [ ! -e scripts/dbflavor-upload.sh ]; then
    echo "This script must be run from the directory dbimage-builder (os-services/dbimage-builder)"
    exit 1
fi

SCRIPTS_DIR=$(dirname $0)

source $SCRIPTS_DIR/dbimagerc
source $SCRIPTS_DIR/helpers/process-flavor-args.sh
source $SCRIPTS_DIR/helpers/setup-playbooks.sh

ctrl=$DBIMAGE_CONTROLLER_IP
if [ "$ctrl" == "localhost" ]; then
    type lxc-ls >/dev/null 2>&1
    if [ $? != 0 ] || [ -z "$(lxc-ls --filter=trove)" ]; then
        echo "The current host does not appear to be running Trove.  Did you forget the following?"
        echo "Did you forget to set the following in the file $SCRIPTS_DIR/dbimagerc?"
        echo "export DBIMAGE_CONTROLLER_IP=<ipaddr>"
        exit 1
    fi
fi

cd playbooks

if [[ "$ANSIBLE_ARGS" == *"-k"* ]]; then
    promptmsg=".  You will be prompted for the controller's Ubuntu password"
else
    promptmsg=""
fi

# Run 'apt-get -y update' upfront via an adhoc command as it fails too often in playbooks

echo "Validate ssh connection to the controller$promptmsg"
validate-playbook-environment controller "apt-get -y update"
if [ $? != 0 ]; then
    exit 3
fi

echo "Run playbooks to upload flavors$promptmsg"
ansible-playbook -i inventory -c ssh $CTRL_ANSIBLE_ARGS dbflavor-upload.yml
if [ $? != 0 ]; then
    echo "Error: dbflavor-upload.yml failed"
    exit 5
fi
