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
    echo "Usage: dbimage-make.sh -d db-name -i dibvm-ip-addr"
    echo "                     [ -v db-version ] [ -k key-name ]"
    echo "                     [ -b dib-user ] [ -c | -e ] [ -I ]"
    echo ""
    echo "The dib-ip-addr argument is the ipaddr of the virtual machine where the image is built"
    echo "The dib-user argument is the remote ssh user on the vm under which the image is built.  The default is ubuntu"
    echo "The key-name argument identifies a Nova ssh key pair.  If specified, the public key is placed in the image"
    echo "The -e argument indicates that the user wants the enterprise provided database if supported"
    echo "The -c argument indicates that the user wants the more recent community provided database if supported"
    echo "The -I argument indicates that the image only should be produced.  Don't upload and create the datastore"
    echo ""
    echo "See the README.rst file for more information"
    exit 1
fi

# pip cache is not handled correctly when in another user's home directory
if [[ $EUID -eq 0 ]] && [[ "$(pwd)" != "/root"* ]]; then
    echo "This script may be run by any user.  But if run as root, it should be from /root"
    exit 1
fi

# The file process-image-args.sh is shared between this script and the dibvm.  It
# ensures that the same command argument processing logic is applied remotely in
# the dibvm.  The playbooks invoke create-image-vm.sh in the dibvm which sources
# process-image-args.sh.  create-image-vm.sh is the back end of this script.  The
# playbooks assume that the current directory is dbimage-builder, so that it can
# place images at the top level of the tool at dbimage-builder/images.

if [ ! -e dibvm/home/bin/process-image-args.sh ]; then
    echo "This script must be run in the directory dbimage-builder (os-services/osa/dbaas/dbimage-builder)"
    exit 1
fi

SCRIPTS_DIR=$(dirname $0)

source $SCRIPTS_DIR/dbimagerc
source dibvm/home/bin/process-image-args.sh
source $SCRIPTS_DIR/helpers/setup-playbooks.sh

create-playbook-inventory

# There is a bug in diskimage-builder that corrupts the boot image so that it can't be rebooted.
# The node goes into a grub rescue state and cannot be easily recovered
ctrl=$DBIMAGE_CONTROLLER_IP
if [ "$ctrl" == "localhost" ]; then
    ip_addresses="$(hostname -I) 127.0.0.1 localhost"
    for ip_address in $ip_addresses; do
         if [ "$DBIMAGE_IPADDR" == "$ip_address" ]; then
             echo "The dibvm must be set to an external node."
             exit 1
          fi
    done
elif [ "$DBIMAGE_IPADDR" == "$ctrl" ] || [ "$DBIMAGE_IPADDR" == "localhost" ]; then
    echo "The dibvm must not be the same node as the controller or the deployer."
    exit 1
fi

if [ "$ctrl" == "localhost" ] && [ -z "$DBIMAGE_CHARM" ]; then
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

echo "Validate ssh connection to the dibvm"
validate-playbook-environment dib "apt-get -y update && apt-get -y install python"
if [ $? != 0 ]; then
    exit 4
fi

echo "Run playbooks to create image$promptmsg"
ansible-playbook -i inventory -c ssh $CTRL_ANSIBLE_ARGS dbimage-make.yml
if [ $? != 0 ]; then
    echo "Error: dbimage-make.yml failed"
    exit 5
fi
