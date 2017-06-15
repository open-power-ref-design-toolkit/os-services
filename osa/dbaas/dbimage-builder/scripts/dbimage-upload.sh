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

export DBIMAGE_SOURCE=${DBIMAGE_SOURCE:-"-dib"}

if [ "$1" == "--help" ]; then
    echo "Usage: dbimage-upload.sh -d db-name -v db-version [ -c | -e ] -f image-name"
    echo "                       [ -k key-name ] [ -s chroot-cmd ] [ -b dib-user ]"
    echo ""
    echo "This command creates a Trove datastore from a previously created qcow2 image.  The image may optionally"
    echo "be customized with a user provided script which is run in a chroot'd environment to modify the image."
    echo ""
    echo "The -d, -v, -k, -c, -e arguments are the same as for the dbimage-make.sh command"
    echo "The -f argument identifies the previously created image that is to be updated"
    echo "The -s argument is a command that is invoked in a chroot'd environment over the mounted image"
    echo "The dib-user argument is the remote ssh user on the vm under which the image is built.  The default is ubuntu"
    echo ""
    echo "The qcow2 image must be located in the dbimage-builder/images/ directory"
    echo ""
    echo "See the README.rst file for more information"
    exit 1
fi

if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root."
    exit 1
fi

SCRIPTS_DIR=$(dirname $0)

source $SCRIPTS_DIR/dbimagerc
source $SCRIPTS_DIR/process-image-upload-args.sh
source $SCRIPTS_DIR/setup-playbooks.sh

create-playbook-inventory

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

echo "Run playbooks to create image$promptmsg"
ansible-playbook -i inventory -c ssh $CTRL_ANSIBLE_ARGS dbimage-upload.yml
if [ $? != 0 ]; then
    echo "Error: dbimage-upload.yml failed"
    exit 5
fi
