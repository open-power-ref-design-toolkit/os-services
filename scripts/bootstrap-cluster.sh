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

# User can override the git urls
GIT_OPSMGR_URL=${GIT_OPSMGR_URL:-"git://github.com/ibmsoe/ibm-openstack-opsmgr"}
GIT_CEPH_URL=${GIT_CEPH_URL:-"git://github.com/ibmsoe/ibm-openstack-ceph"}

# Get the current branch or tag for this repository, ie. os-services
MASTER_TAG=`git symbolic-ref -q --short HEAD || git describe --tags --exact-match`

# User can override the git tag or branch that is used to clone the repository
CEPH_TAG=${CEPH_TAG:-${MASTER_TAG}}
OPSMGR_TAG=${OPSMGR_TAG:-${MASTER_TAG}}

# Note help text assumes the end user is invoking this script as Genesis is fully automated
# Default value (yes) is reversed for Genesis

if [ "$1" == "--help" ]; then
    echo "Usage: bootstrap-cluster.sh [-i <controllernode1,...>] [-s <storagenode1,...>] [-c <computenode1,...>]"
    echo ""
    echo "export DEPLOY_CEPH=yes|no                          Default is no"
    echo "export DEPLOY_OPSMGR=yes|no                        Default is no"
    echo "export DEPLOY_HARDENING=yes|no                     Default is no"
    echo "export ADMIN_PASSWORD=                             Not applicable unless set"
    echo ""
    exit 1
fi

if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root."
    exit 1
fi

if [ ! -e scripts/bootstrap-cluster.sh ]; then
    echo "This script must be run in the root directory of the project.  ie. /root/os-services"
    exit 1
fi

# Install some prerequisite packages
DISTO=`lsb_release -r | awk '{print $2}'`
if [ $? != 0 ]; then
    echo "Unsupported Linux distribution.  Must be Ubuntu 14.04"
    exit 1
fi

type apt-get >/dev/null 2>&1
if [ $? != 0 ]; then
    echo "Unsupported Linux distribution.  Must be Ubuntu 14.04"
    exit 1
fi
PCLD_DIR=`pwd`

# Save command arguments as source script parses command arguments using optind
ARGS=$@
source osa/scripts/process-args.sh

echo DEPLOY_CEPH=$DEPLOY_CEPH
echo DEPLOY_OPSMGR=$DEPLOY_OPSMGR
echo MASTER_TAG=$MASTER_TAG

apt-get -qq update
apt-get -qq -y install build-essential libssl-dev libffi-dev python-dev \
    python3-dev bridge-utils debootstrap ifenslave ifenslave-2.6 lsof lvm2 \
    ntp ntpdate tcpdump vlan

CODENAME=`lsb_release -c | awk '{print $2}'`
if [ $? != 0 ] || [ "$CODENAME" != "trusty" ]; then
    echo "Unsupported Linux distribution.  Must be Ubuntu 14.04"
else
    # XXX Does this need to be done on each controller node?
    # Sequentially invoke build/install/wget scripts to replace
    # non-openstack related pkgs
    pushd pkgs >/dev/null 2>&1
    for script in *.sh; do
        command ./$script
        rc=$?
        if [ $rc != 0 ]; then
            echo "Failed ./pkgs/$script failed, rc=$rc"
            if [[ $rc > 1 ]]; then
                exit $rc;
            fi
        fi
    done
    popd >/dev/null 2>&1
fi

# Installs ansible and openstack-ansible
pushd osa >/dev/null 2>&1
echo "Invoking scripts/bootstrap-osa.sh"
scripts/bootstrap-osa.sh $ARGS ${PCLD_DIR}/etc
rc=$?
if [ $rc != 0 ]; then
    echo "Failed scripts/bootstrap-osa.sh, rc=$rc"
    exit 2
fi
popd >/dev/null 2>&1

# Installs ceph and ceph-ansible
if [[ "$DEPLOY_CEPH" == "yes" ]]; then
    if [ ! -d $PCLD_DIR/ceph ]; then
        git-clone $GIT_CEPH_URL $CEPH_TAG $PCLD_DIR/ceph
    fi
    pushd ceph >/dev/null 2>&1
    echo "Invoking scripts/bootstrap-ceph.sh"
    scripts/bootstrap-ceph.sh $ARGS $PCLD_DIR/etc
    rc=$?
    if [ $rc != 0 ]; then
        echo "Failed scripts/bootstrap-ceph.sh, rc=$rc"
        echo "You may want to continue manually.  cd ceph; ./scripts/bootstrap-ceph.sh"
        exit 4
    fi
    popd >/dev/null 2>&1
fi

# Installs opsmgr
if [[ "$DEPLOY_OPSMGR" == "yes" ]]; then
    if [ ! -d $PCLD_DIR/opsmgr ]; then
        git-clone $GIT_OPSMGR_URL $OPSMGR_TAG $PCLD_DIR/opsmgr
    fi
    pushd opsmgr >/dev/null 2>&1
    echo "Invoking scripts/bootstrap-opsmgr.sh"
    scripts/bootstrap-opsmgr.sh $ARGS $PCLD_DIR/etc
    rc=$?
    if [ $rc != 0 ]; then
        echo "Failed scripts/bootstrap-opsmgr.sh, rc=$rc"
        echo "You may want to continue manually.  cd opsmgr; ./scripts/bootstrap-opsmgr.sh"
        exit 5
    fi
    popd >/dev/null 2>&1
fi

# Depending on your network bandwidth, some manual setup may be required to avoid download failures
# Edit the following files and increase the delay and retry counts
#
#   /etc/ansible/roles/galera_client/tasks/galera_client_install_apt.yml
#       Set retries: 25 and delay: 10
#       Reason: circumvent poor network performance
#
#   /etc/ansible/roles/pip_install/tasks/main.yml
#       Set retries: 25 and delay: 10 in both "Get Modern PIP" and "Get Modern PIP using fallback URL"
#       Reason: circumvent poor network performance

echo ""
echo "At this point, it may be desirable to customize some settings before"
echo "starting the cluster.  For example, keystone_auth_admin_password in"
echo "/etc/openstack_deploy/user_secrets.yml.  The setting of this user account"
echo "may also be scripted using the environment variable ADMIN_PASSWORD."
echo "Otherwise passwords will be dynamically generated."
echo ""
echo "Passwords may be edited by utilizing the following command:"
echo ""
echo "vi /etc/openstack_deploy/user_secrets.yml"
echo ""
echo "Additional parameters may be found in $PCLD_DIR/etc/*.  For example,"
echo ""
echo "vi $PCLD_DIR/etc/openstack_deploy/*.yml"
echo "vi $PCLD_DIR/etc/ceph_inventory/*.yml"
echo ""
echo "Note there is no requirement to modify any parameter."
echo ""
echo "When you are ready, invoke the following command to create the cluster"
echo "with the parameters given above."
echo ""
echo "./scripts/create-cluster.sh"
