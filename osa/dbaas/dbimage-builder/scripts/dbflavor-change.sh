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
    echo "Usage: dbflavor-change.sh -d db-name -f flavor"
    echo "         { [ -c vcpus ] | [ -m mem-in-megabytes ] | [ -r root-vdisk1-in-gigabytes ] }"
    echo ""
    echo "At least one of -c, -m, or -r must be specified"
    echo ""
    echo "See the README.rst file for more information"
    exit 1
fi

if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root."
    exit 1
fi

if [ ! -e scripts/dbflavor-change.sh ]; then
    echo "This script must be run from the directory dbimage-builder (/root/os-services/dbimage-builder)"
    exit 1
fi

if [ ! -e playbooks/vars/predefined-flavors.yml ]; then
    echo "Error: playbooks/var/predefined-flavors.yml not found!"
    exit 1
fi

ARGS=$*

SCRIPTS_DIR=$(dirname $0)

source $SCRIPTS_DIR/helpers/process-flavor-args.sh

python scripts/helpers/flavor.py change -P playbooks/vars/predefined-flavors.yml -C playbooks/vars/customized-flavors.yml $ARGS
