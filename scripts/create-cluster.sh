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

if [ "$1" == "--help" ]; then
    echo "Usage: create-cluster.sh"
    echo ""
    echo "export DEPLOY_CEPH=yes|no                          Default is no"
    echo "export DEPLOY_OPSMGR=yes|no                        Default is no"
    echo "export DEPLOY_HARDENING=yes|no                     Default is no"
    echo "export DEPLOY_TEMPEST=yes|no                       Default is no"
    echo "export ADMIN_PASSWORD=                             Not applicable unless set"
    echo ""
    echo "See the README.rst file for more information"
    exit 1
fi

if [ ! -e scripts/bootstrap-cluster.sh ]; then
    echo "This script must be run in root directory of the project.  ie. /root/os-services"
    exit 1
fi
export TOP_PCLD_DIR=`pwd`

# Save command arguments as source script parses command arguments using optind
ARGS=$@
source osa/scripts/process-args.sh

echo DEPLOY_CEPH=$DEPLOY_CEPH
echo DEPLOY_OPSMGR=$DEPLOY_OPSMGR

# Validate the config
validate_config

# Check openstack-ansible configuration as user may have introduced an error when customizing
run_project_script osa check-osa.sh $ARGS
exit_on_error $? 2

if is_positive $DEPLOY_CEPH; then
    run_project_script ceph-services check-ceph.sh $ARGS
    exit_on_error $? 3
fi

if is_positive $DEPLOY_OPSMGR; then
    run_project_script opsmgr check-opsmgr.sh $ARGS
    exit_on_error $? 4
fi

# Configure ceph-ansible
if is_positive $DEPLOY_CEPH; then
    run_project_script ceph-services create-cluster-ceph.sh $ARGS
    exit_on_error $? 5
fi

run_project_script osa create-cluster-osa.sh $ARGS required
exit_on_error $? 6

# Configure opsmgr - ELK, Nagios, and Horizon extensions
if is_positive $DEPLOY_OPSMGR; then
    run_project_script opsmgr create-cluster-opsmgr.sh $ARGS
    exit_on_error $? 7
fi
