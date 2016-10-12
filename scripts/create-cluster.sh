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

# Note help text assumes the end user is invoking this script as Genesis is fully automated
# Default value (yes) is reversed for Genesis

if [ "$1" == "--help" ]; then
    echo "Usage: create-cluster.sh"
    echo ""
    echo "export DEPLOY_CEPH=yes|no                          Default is no"
    echo "export DEPLOY_OPSMGR=yes|no                        Default is no"
    echo "export DEPLOY_HARDENING=yes|no                     Default is no"
    echo "export DEPLOY_TEMPEST=yes|no                       Default is no"
    echo "export ADMIN_PASSWORD=                             Not applicable unless set"
    exit 1
fi

if [ ! -e scripts/bootstrap-cluster.sh ]; then
    echo "This script must be run in root directory of the project.  ie. /root/os-services"
    exit 1
fi
PCLD_DIR=`pwd`

# Save command arguments as source script parses command arguments using optind
ARGS=$@
source osa/scripts/process-args.sh

echo DEPLOY_CEPH=$DEPLOY_CEPH
echo DEPLOY_OPSMGR=$DEPLOY_OPSMGR

# Configure ceph-ansible.  Inventory is created during the bootstrap-ceph phase, so user can customize
if [ "$DEPLOY_CEPH" == "yes" ]; then
    if [ ! -d ceph ]; then
        echo "Run ./scripts/bootstrap-cluster first!!!  Ceph code is missing"
        exit 2
    fi
    pushd ceph >/dev/null 2>&1
    echo "Invoking scripts/create-cluster-ceph.sh"
    scripts/create-cluster-ceph.sh $ARGS
    rc=$?
    if [ $rc != 0 ]; then
        echo "Failed scripts/create-cluster-ceph.sh, rc=$rc"
        exit 3
    fi
    popd >/dev/null 2>&1
fi

# Configure openstack-ansible
pushd osa >/dev/null 2>&1
echo "Invoking scripts/create-cluster-osa.sh"
scripts/create-cluster-osa.sh $ARGS
rc=$?
if [ $rc != 0 ]; then
    echo "Failed scripts/create-cluster-osa.sh, rc=$rc"
    exit 4
fi
popd >/dev/null 2>&1

# Configure opsmgr - ELK, Nagios, and Horizon extensions
if [ "$DEPLOY_OPSMGR" == "yes" ]; then
    if [ ! -d opsmgr ]; then
        echo "Run ./scripts/bootstrap-cluster first!!!  Opsmgr code is missing"
        exit 5
    fi
    pushd opsmgr >/dev/null 2>&1
    echo "Invoking scripts/create-cluster-opsmgr.sh"
    scripts/create-cluster-opsmgr.sh $ARGS
    rc=$?
    if [ $rc != 0 ]; then
        echo "Failed scripts/create-cluster-opsmgr.sh, rc=$rc"
        exit 6
    fi
    popd >/dev/null 2>&1
fi
