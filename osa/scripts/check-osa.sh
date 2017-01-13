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
    echo "Usage: check-osa.sh"
    exit 1
fi

if [ ! -e scripts/check-osa.sh ]; then
    echo "This script must be run from /root/os-services/osa."
    exit 1
fi
PCLD_DIR=`pwd`

SCRIPTS_DIR=$(dirname $0)
source $SCRIPTS_DIR/process-args.sh

echo "Checking for syntax errors in OSA playbooks"
pushd $OSA_DIR/playbooks >/dev/null 2>&1
run_ansible --syntax-check setup-hosts.yml
rc=$?
if [ $rc != 0 ]; then
    echo "Failed syntax check, rc=$rc"
    echo "Did you edit a configuration file?"
    exit $rc
fi
popd >/dev/null 2>&1
