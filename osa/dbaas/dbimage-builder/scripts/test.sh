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

SCRIPTS_DIR=$(dirname $0)

source $SCRIPTS_DIR/dbimagerc
source dibvm/home/bin/process-image-args.sh
source $SCRIPTS_DIR/setup-playbooks.sh

create-playbook-inventory

cd playbooks

if [[ "$DBIMAGE_ANSIBLE_ARGS" == *"-k"* ]]; then
    promptmsg=".  You will be prompted for the controller's Ubuntu password"
else
    promptmsg=""
fi

echo "Validate ssh connection to the controller$promptmsg"
validate-playbook-environment controller "apt-get -y update"
if [ $? != 0 ]; then
    exit 3
fi

echo "Validate ssh connection to the dibvm"
validate-playbook-environment dib "apt-get -y update && apt-get -y install python"
if [ $? != 0 ]; then
    exit 4
fi

echo "Run playbooks to create image$promptmsg"
ansible-playbook -i inventory -c ssh $DBIMAGE_ANSIBLE_ARGS dbimage-make.yml
if [ $? != 0 ]; then
    echo "Error: dbimage-make.yml failed"
    exit 5
fi
