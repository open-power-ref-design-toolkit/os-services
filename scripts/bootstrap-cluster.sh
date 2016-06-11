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
shopt -s nullglob

# User can override the git urls
GIT_OPSMGR_URL=${GIT_OPSMGR_URL:-"https://github.com/ibmsoe/ibm-openstack-opsmgr"}
GIT_CEPH_URL=${GIT_CEPH_URL:-"https://github.com/ibmsoe/ibm-openstack-ceph"}

# Get the current branch or tag for this repository, ie. os-services
MASTER_TAG=`git symbolic-ref -q --short HEAD || git describe --tags --exact-match`

# User can override the git tag or branch that is used to clone the repository
CEPH_TAG=${CEPH_TAG:-MASTER_TAG}
OPSMGR_TAG=${OPSMGR_TAG:-MASTER_TAG}

export ANSIBLE_PARAMETERS=${ANSIBLE_PARAMETERS:-""}
export ANSIBLE_FORCE_COLOR=${ANSIBLE_FORCE_COLOR:-"true"}
export BOOTSTRAP_OPTS=${BOOTSTRAP_OPTS:-""}

if [ "$1" == "--help" ]; then
    echo "Usage: bootstrap-cluster.sh [ -i <controllernode1,...> -s <storagenode1,...> -c <computenode1,...> ]"
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
    echo "This script must be run in the root directory of the project.  ie. /root/os-services"
    exit 1
fi
PCLD_DIR=`pwd`

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
apt-get -qq update
apt-get -qq -y install build-essential libssl-dev libffi-dev python-dev python3-dev \
           bridge-utils debootstrap ifenslave ifenslave-2.6 lsof lvm2 ntp ntpdate tcpdump vlan

CODENAME=`lsb_release -c | awk '{print $2}'`
if [ $? != 0 ] && [ "$CODENAME" != "trusty" ]; then
    echo "Unsupported Linux distribution.  Must be Ubuntu 14.04"
else
    # XXX Does this need to be done on each controller node?
    # Sequentially invoke build/install/wget scripts to replace non-openstack related pkgs
    pushd pkgs >/dev/null 2>&1
    for script in *.sh
    do
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
scripts/bootstrap-osa.sh $@ ${PCLD_DIR}/etc
rc=$?
if [ $rc != 0 ]; then
    echo "Failed scripts/bootstrap-osa.sh, rc=$rc"
    exit 2
fi

popd >/dev/null 2>&1

# Installs ceph-ansible
if [[ "${DEPLOY_CEPH}" == "yes" ]]; then
    pushd . >/dev/null 2>&1
    if [ -d $PCLD_DIR/ceph ]; then
        cd $PCLD_DIR/ceph
        TAG=`git symbolic-ref -q --short HEAD || git describe --tags --exact-match`
        if [ "$TAG" == "$CEPH_TAG" ]; then
            git pull
            rc=$?
        else
            git checkout $CEPH_TAG
            rc=$?
        fi
    else
        # TODO: Update with external github.com
        git clone $GIT_CEPH_URL
        cd $PCLD_DIR/ceph
        git checkout $CEPH_TAG
        rc=$?
    fi
    if [ $rc != 0 ]; then
        echo "Failed git ceph, rc=$rc"
        exit 3
    fi
    scripts/bootstrap-ceph.sh $@ ${PCLD_DIR}/etc
    rc=$?
    if [ $rc != 0 ]; then
        echo "Failed scripts/bootstrap-ceph.sh, rc=$rc"
        echo "You may want to continue manually.  cd ceph; ./scripts/bootstrap-ceph.sh"
        exit 4
    fi
    popd >/dev/null 2>&1
fi

# Installs opsmgr
if [[ "${DEPLOY_OPSMGR}" == "yes" ]]; then
    pushd . >/dev/null 2>&1
    if [ -d $PLCD_DIR/opsmgr ]; then
        cd $PCLD_DIR/opsmgr
        TAG=`git symbolic-ref -q --short HEAD || git describe --tags --exact-match`
        if [ "$TAG" == "$OPSMGR_TAG" ]; then
            git pull
            rc=$?
        else
            git checkout $OPSMGR_TAG
            rc=$?
        fi
    else
        # TODO: Update with external github.com
        git clone $GIT_OPSMGR_URL opsmgr
        cd $PCLD_DIR/opsmgr
        git checkout $OPSMGR_TAG
        rc=$?
    fi
    if [ $rc != 0 ]; then
        echo "Failed git opsmgr, rc=$rc"
        echo "You may want to continue manually.  cd opsmgr; ./scripts/bootstrap-opsmgr.sh"
        exit 5
    fi
    scripts/bootstrap-opsmgr.sh $@ ${PCLD_DIR}/etc
    rc=$?
    if [ $rc != 0 ]; then
        echo "Failed scripts/bootstrap-opsmgr.sh, rc=$rc"
        exit 6
    fi
    popd >/dev/null 2>&1
fi

#   /etc/ansible/roles/galera_client/tasks/galera_client_install_apt.yml
#       Set retries: 25 and delay: 10
#       Reason: circumvent poor network performance
#
#   /etc/ansible/roles/pip_install/tasks/main.yml
#       Set retries: 25 and delay: 10 in both "Get Modern PIP" and "Get Modern PIP using fallback URL"
#       Reason: circumvent poor network performance

echo ""
echo ""
echo "Depending on your network bandwidth, some manual setup may be required to avoid download failures."
echo "One option is to use local apt servers to avoid this issue."
echo ""
echo "vi /etc/ansible/roles/galera_client/tasks/galera_client_install_apt.yml"
echo "Set retries: 25 and delay: 10"
echo ""
echo "vi /etc/ansible/roles/pip_install/tasks/main.yml"
echo "Set retries: 25 and delay: 10 in both \"Get Modern PIP\" and \"Get Modern PIP using fallback URL\""
echo ""
echo "Run ./scripts/create-cluster.sh"
