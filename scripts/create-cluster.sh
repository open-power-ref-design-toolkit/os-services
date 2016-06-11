#!/usr/bin/env bash
#
# Copyright 2016 IBM Corp.
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


set -e
set -o pipefail

if [ "$1" == "--help" ]; then
    echo "Usage: create-cluster.sh [ -i <controllernode1,...> -s <storagenode1,...> -c <computenode1,...> ]"
    echo ""
    echo "export DEPLOY_CEPH=yes|no"
    echo "export DEPLOY_OPSMGR=yes|no"
    echo "export DEPLOY_HARDENING=yes|no"
    exit 1
fi

if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root."
    exit 1
fi

if [ ! -e scripts/bootstrap-cluster.sh ]; then
    echo "This script must be run in root directory of the project.  ie. /root/os-services"
    exit 1
fi
PCLD_DIR=`pwd`

ulimit -n 100000

# Configure ceph-ansible.  Inventory is created during the bootstrap-ceph phase, so user can customize
if [ "$DEPLOY_CEPH" == "yes" ]; then
    if [ ! -d ceph ]; then
        echo "Run ./scripts/bootstrap-cluster first!!!  Ceph code is missing"
        exit 2
    fi
    pushd ceph
    scripts/create-cluster-ceph.sh
    rc=$?
    if [ $rc != 0 ]; then
        echo "Failed scripts/create-cluster-ceph.sh, rc=$rc"
        exit 3
    fi
    popd
fi

# Apply user configuration files created by bootstrap-cluster.sh
cp -r ${PCLD_DIR}/etc/openstack_deploy /etc

# Configure openstack-ansible
pushd osa
scripts/create-cluster-osa.sh $@
rc=$?
if [ $rc != 0 ]; then
    echo "Failed scripts/create-cluster-osa.sh, rc=$rc"
    exit 4
fi
popd

# Configure opsmgr - ELK, Nagios, and Horizon extensions
if [ "$DEPLOY_OPSMGR" == "yes" ]; then
    if [ ! -d opsmgr ]; then
        echo "Run ./scripts/bootstrap-cluster first!!!  Opsmgr code is missing"
        exit 5
    fi
    pushd opsmgr
    scripts/create-cluster-opsmgr.sh $@
    rc=$?
    if [ $rc != 0 ]; then
        echo "Failed scripts/create-cluster-opsmgr.sh, rc=$rc"
        exit 6
    fi
    popd
fi
