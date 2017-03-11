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
    echo "Usage: dbimage-make.sh -d db-name [ -v db-version ] [ -i dib-ip-addr ] [ -b dib-user ] [ -u cloud-user ] [ -p pkg ]"
    echo ""
    echo "The dib-ip-addr argument is the ipaddr of the virtual machine where the image is built"
    echo "The dib-user is the remote ssh user on the vm under which the image is built.  The default is ubuntu."
    echo "The public key of the cloud-user is placed in the image.  This would be the DBA or Developer that administers the image"
    echo ""
    echo "See the README.rst file for more information"
    exit 1
fi

if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root."
    exit 1
fi

# The file process-image-args.sh is shared between this script and the dibvm.  It
# ensures that the same command argument processing logic is applied remotely in
# the dibvm.  The playbooks invoke create-image-vm.sh in the dibvm which sources
# process-image-args.sh.  create-image-vm.sh is the back end of this script.  The
# playbooks assume that the current directory is dbimage-builder, so that it can
# place images at the top level of the tool at dbimage-builder/images.

if [ ! -e dibvm/home/bin/process-image-args.sh ]; then
    echo "This script must be run in the directory dbimage-builder (/root/os-services/osa/dbaas/dbimage-builder)"
    exit 1
fi

SCRIPTS_DIR=$(dirname $0)

source $SCRIPTS_DIR/dbimagerc
source dibvm/home/bin/process-image-args.sh
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

# This is set to localhost by create-playbook-inventory above if dibvm is the deployer's host

if [ "$DBIMAGE_IPADDR" != "localhost" ]; then
    echo "Validate ssh connection to the dibvm"
    validate-playbook-environment dib "apt-get -y update && apt-get -y install python"
    if [ $? != 0 ]; then
        exit 4
    fi
fi

echo "Run playbooks to create image$promptmsg"
ansible-playbook -i inventory -c ssh $CTRL_ANSIBLE_ARGS dbimage-make.yml
if [ $? != 0 ]; then
    echo "Error: dbimage-make.yml failed"
    exit 5
fi
