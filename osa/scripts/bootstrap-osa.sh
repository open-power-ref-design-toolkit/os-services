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

# This code delivers patches to openstack-ansible, ansible, ceph, and other components.
#
# Patches are located in <project root>/diffs directory.
#
# Patch Assumptions:
# - Patches must be generated using absolute paths from root (/).
# - Patches are applied using the command "cd /; patch -N -p1 < patch-file".
#
# Patch filename conventions:
# - if patch file name includes "ppc64le", it is applied to all nodes but only if a power server is present
# - if patch file name includes "ansible", it modifies code cloned from https://github.com/ansible/ansible/
# - if patch file name includes "osa", it modifies icode cloned from https://github.com/openatck/openstack-ansible
#
# Examples:
# osa_ppc64le_compute_galera_client.patch  <<-- The name includes both "osa" and "ppc64le"
#                                          <<-- It's power specific openstack-ansible patch
#                                          <<-- It's only applied if a power node is present in configuration
# ceph_python_libs.patch                   <<-- Always applied, may contain ppc64le support. Does not regress x86-64
# ansible_python_select.patch              <<-- Always applied, modifies ansible
#

OSA_TAG="13.1.0"
OSA_DIR="/opt/openstack-ansible"
OSA_PLAYS="${OSA_DIR}/playbooks"

shopt -s nullglob

if [ "$1" == "--help" ]; then
    echo "Usage: bootstrap-osa.sh [ -i <controllernode1,...> -s <storagenode1,...> -c <computenode1,...> ]"
    echo ""
    echo "export DEPLOY_CEPH=yes|no"
    echo "export DEPLOY_OPSMGR=yes|no"
    echo "export DEPLOY_HARDENING=yes|no"
    exit 1
fi

echo "Invoking scripts/bootstrap-osa.sh"

if [[ $EUID -ne 0 ]]; then
    echo "This script must run as root."
    exit 1
fi

if [ ! -e scripts/bootstrap-osa.sh ]; then
    echo "This script must be run from /root/os-services/osa"
    exit 1
fi
PCLD_DIR=`pwd`

# These command line parameters are not specified if the inventory is generated by Genesis (ie. manufacturing)
infraNodes=""
storageNodes=""
computeNodes=""
OPTIND=1
while getopts "i:c:s:" opt; do
    case "$opt" in
    i)  infraNodes=${OPTARG//,/ }       # {var///, } replaces all commas in the list with blanks
        ;;
    s)  storageNodes=${OPTARG//,/ }
        ;;
    c)  computeNodes=${OPTARG//,/ }
        ;;
    esac
done
shift $((OPTIND-1))                    # Now reference remaining arguments with $@, $1, $2, ...

echo "InfraNodes=$infraNodes"
echo "storageNodes=$storageNodes"
echo "computeNodes=$computeNodes"

echo "Command args=$@"

GENESIS_INVENTORY="/var/inventory"

# 1) ppc64le patches are conditionally applied at bottom
# 2) Validate ssh connections for nodes specified via command arguments if they are specified
DEPLOY_AIO="no"
POWER_NODES="False"
if [ -r $GENESIS_INVENTORY ]; then
    echo "Inventory provided by genesis"
    POWER_NODES="True"
elif [ ! -z "$infraNodes" ] || [ ! -z "$storageNodes" ] || [ ! -z "$computeNodes" ]; then
    cnt=0
    # TODO(luke): ensure nodes in for loop list below are unique.
    for node in $infraNodes $storageNodes $computeNodes
    do
        ARCH=`ssh -i ~/.ssh/id_rsa root@$node uname -m`
        rc=$rc
        if [ $rc != 0 ]; then
            echo "Node $node failed ssh test"
            exit 1
        fi
        if [ "$ARCH" == "ppc64le" ]; then
            POWER_NODES="True"
        fi
        cnt=$((cnt+1))
    done
    if [ $cnt -gt 1 ]; then
        DEPLOY_AIO="yes"
    fi
else
    echo "Assuming AIO configuration"
    DEPLOY_AIO="yes"
fi

TARGET_OSA_DEPLOY="${1:-/etc}"         # Caller defines target osa deploy directory if arg1 is specified

echo "TARGET_OSA_DEPLOY=$TARGET_OSA_DEPLOY"

# Checkout the openstack-ansible repository
if [ ! -d /opt/openstack-ansible ]; then
    echo "Installing openstack-ansible..."
    git clone https://github.com/openstack/openstack-ansible ${OSA_DIR}
    cd ${OSA_DIR}
    git checkout ${OSA_TAG}
fi

# Install ansible
if [ ! -d /etc/ansible ]; then
    echo "Installing ansible..."
    cd ${OSA_DIR}
    BOOTSTRAP_OPTS="${BOOTSTRAP_OPTS} bootstrap_host_ubuntu_repo=http://us.archive.ubuntu.com/ubuntu/"
    BOOTSTRAP_OPTS="${BOOTSTRAP_OPTS} bootstrap_host_ubuntu_security_repo=http://security.ubuntu.com/ubuntu/"
    scripts/bootstrap-ansible.sh
fi

# Update the file /opt/openstack-ansible/playbooks/ansible.cfg
grep -q callback_plugins ${OSA_PLAYS}/ansible.cfg || sed -i '/\[defaults\]/a callback_plugins = plugins/callbacks' ${OSA_PLAYS}/ansible.cfg

# Initial default files for updates below: user_variables.yml, user_secrets.yml, openstack_user_config.yml.example
cp -R /opt/openstack-ansible/etc/openstack_deploy /etc

# These are user config files for openstack-ansible.  Any unique file name may be used.  We choose our sub-project name
OSA_SECRETS="${PCLD_DIR}/etc/openstack_deploy/user_secrets_osa.yml"
OSA_VARS="${PCLD_DIR}/etc/openstack_deploy/user_variables_osa.yml"

# Initialize passwords in ${OSA_SECRETS}
# cd ${OSA_DIR}
# ./scripts/pw-token-gen.py --file ${OSA_SECRETS}

echo "Copying user variables and secrets to ${TARGET_OSA_DEPLOY}/openstack_deploy"
cp -R ${PCLD_DIR}/etc/openstack_deploy ${TARGET_OSA_DEPLOY}

if [[ "${DEPLOY_TEMPEST}" == "yes" ]]; then
    cd ${OSA_PLAYS}
    run_ansible os-tempest-install.yml
fi

# TODO(luke): Need to write ansible playbooks to apply patches to all nodes

echo "Applying patches"

cd /
PATCHED="False"
ANSIBLE_PATCH="False"
for f in ${PCLD_DIR}/diffs/*.patch; do
    if [[ $f =~ "ppc64le" ]]; then                          # If string contains substring --> =~
        if [ "$POWER_NODES" == "True" ]; then
            patch -N -p1 < $f
            PATCHED="True"
        fi
    else
        patch -N -p1 < $f
        PATCHED="True"
    fi
    if [[ $f =~ "ansible_" ]]; then
        ANSIBLE_PATCH="True"
    fi
done

if [ "$PATCHED" == "True" ] && [ "$ANSIBLE_PATCH" == "True" ]; then
    pip uninstall -y ansible
    pip install -q /opt/ansible_*
fi

echo "Leaving scripts/bootstrap-osa.sh"