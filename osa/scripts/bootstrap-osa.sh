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
SCRIPTS_DIR=$(dirname $0)
# Get the full path to the scripts directory
SCRIPTS_DIR=$(readlink -ne $SCRIPTS_DIR)
source $SCRIPTS_DIR/process-args.sh

FILES_WITH_GIT_URLS="/opt/openstack-ansible/ansible-role-requirements.yml \
    /opt/openstack-ansible/playbooks/defaults/repo_packages/openstack_services.yml \
    /opt/openstack-ansible/playbooks/defaults/repo_packages/openstack_other.yml \
    /opt/openstack-ansible/playbooks/vars/pkvm/pkvm.yml"

echo "DEPLOY_AIO=$DEPLOY_AIO"
echo "infraNodes=$infraNodes"
echo "allNodes=$allNodes"
echo "GIT_MIRROR=$GIT_MIRROR"

OSA_TAG=${OSA_TAG:-"13.1.0"}
OSA_DIR="/opt/openstack-ansible"
OSA_PLAYS="${OSA_DIR}/playbooks"

EXPECTED_ANSIBLE_VERSION="v1.9.4-1"

function generate_inventory {

    if [ -r $GENESIS_INVENTORY ]; then
        echo "Inventory provided by genesis"
        $SCRIPTS_DIR/generate_user_config.py \
            -i $GENESIS_INVENTORY \
            -d /etc/openstack_deploy
        rc=$?
        if [ $rc -ne 0 ]; then
            echo "Error generating config files from genesis file."
            exit 1
        fi
    else
        if [ ! -z "$allNodes" ]; then
            # Validate ssh connectivity
            for node in $allNodes; do
                ARCH=`ssh -i ~/.ssh/id_rsa root@$node uname -m`
                rc=$?
                if [ $rc != 0 ]; then
                    echo "Node $node failed ssh test"
                    exit 1
                fi
            done
        fi
        if [ $DEPLOY_AIO == "no" ]; then
            echo "Inventory generated from command arguments"
            # TODO(luke): Generate openstack_user_config.xml from command line args
        elif [ ! -d /openstack ]; then
            # bootstrap-aio creates /openstack, the mount point for containers
            pushd $OSA_DIR >/dev/null 2>&1
            ./scripts/bootstrap-aio.sh
            rc=$?
            if [ $rc != 0 ]; then
                echo "bootstrap-aio.sh failed, rc=$rc"
                rm -rf /openstack
                exit 1
            fi
            popd >/dev/null 2>&1
        fi
    fi
}

if [ "$1" == "--help" ]; then
    echo "Usage: bootstrap-osa.sh [-i <controllernode1,...>] [-s <storagenode1,...>] [-c <computenode1,...>]"
    echo ""
    echo "export DEPLOY_HARDENING=yes|no                     Default is no"
    echo "export ADMIN_PASSWORD=                             Not applicable unless set"
    echo ""
    echo "Default is no"
    exit 1
fi

if [ ! -e scripts/bootstrap-osa.sh ]; then
    echo "This script must be run from /root/os-services/osa"
    exit 1
fi
PCLD_DIR=`pwd`

# Checkout the openstack-ansible repository
INSTALL=False
if [ ! -d /opt/openstack-ansible ]; then
    echo "Installing openstack-ansible..."
    git clone https://github.com/openstack/openstack-ansible ${OSA_DIR}
    if [ $? != 0 ]; then
        echo "Manual retry procedure:"
        echo "1) fix root cause of error if known"
        echo "2) rm -rf /opt/openstack-ansible"
        echo "3) re-run command"
        exit 1
    fi
    pushd ${OSA_DIR} >/dev/null 2>&1
    git checkout stable/mitaka
    if [ $? != 0 ]; then
        exit 1
    fi
    git checkout ${OSA_TAG}
    if [ $? != 0 ]; then
        exit 1
    fi
    popd >/dev/null 2>&1
    # An openstack-ansible script is invoked below to install ansible
    rm -rf /etc/ansible
    INSTALL=True
fi

# Install ansible
if [ ! -d /etc/ansible ]; then
    echo "Installing ansible..."
    pushd ${OSA_DIR} >/dev/null 2>&1
    BOOTSTRAP_OPTS="${BOOTSTRAP_OPTS} bootstrap_host_ubuntu_repo=http://us.archive.ubuntu.com/ubuntu/"
    BOOTSTRAP_OPTS="${BOOTSTRAP_OPTS} bootstrap_host_ubuntu_security_repo=http://security.ubuntu.com/ubuntu/"
    scripts/bootstrap-ansible.sh
    rc=$?
    if [ $rc != 0 ]; then
        echo "scripts/bootstrap-ansible.sh failed, rc=$rc"
        echo "Manual retry procedure:"
        echo "1) fix root cause of error if known"
        echo "2) rm -rf /etc/ansible; rm -rf /opt/ansible_$EXPECTED_ANSIBLE_VERSION"
        echo "3) re-run command"
        exit 1
    fi
    popd >/dev/null 2>&1
    INSTALL=True
fi

# Load the python requirements
pip install -r $SCRIPTS_DIR/../../requirements.txt >/dev/null
rc=$?
if [ $rc != 0 ]; then
    echo "pip install requirements.txt failed, rc=$rc"
    exit 1
fi

# Apply patches iff osa is installed above.  Code is intended to be reentrant
if [ "$INSTALL" == "True" ] && [ -d $PCLD_DIR/diffs ]; then
    # Copy configuration files before patches are applied, so that patches may be provided for configuration files
    cp -R /opt/openstack-ansible/etc/openstack_deploy /etc

    # TODO(luke): Need to apply patches to all controller nodes for opsmgr resiliency
    echo "Applying patches"
    cd /
    ANSIBLE_PATCH=False
    for f in ${PCLD_DIR}/diffs/*.patch; do
        patch -N -p1 < $f
        rc=$?
        if [ $rc != 0 ]; then
            echo "scripts/bootstrap-ansible.sh failed, rc=$rc"
            echo "Patch $f could not be applied"
            echo "Manual retry procedure:"
            echo "1) fix patch $f"
            echo "2) rm -rf /etc/ansible; rm -rf /opt/ansible_$EXPECTED_ANSIBLE_VERSION"
            echo "3) re-run command"
            exit 1
        elif [[ "$f" == *"/opt-ansible"* ]]; then
            ANSIBLE_PATCH=True
        fi
    done

    if [ "$ANSIBLE_PATCH" == "True" ]; then
        echo "pip uninstall ansible"
        pip uninstall -y ansible
        echo "pip install patched ansible"
        pip install -q /opt/ansible_*
    fi
fi

# Patch ansible if a git mirror is specified.  At least one of the target files is created by patch above
if [ ! -z $GIT_MIRROR ]; then
    # TODO: Replacing string can be taken as an input
    sed -i "s/git\.openstack\.org/$GIT_MIRROR/g" $FILES_WITH_GIT_URLS
fi

# Override nova, neutron roles' git projects versions because OSA_TAG could be a later version than the branch
VAR_FILE=${OSA_PLAYS}/defaults/repo_packages/openstack_services.yml
PVAR_FILE=${OSA_PLAYS}/vars/pkvm/pkvm.yml
KEYS=$(grep -e "^neutron_.*:" -e "^nova_.*:" $VAR_FILE | awk '{print $1}')

for k in $KEYS; do
    # Remove any existing lines with this key
    sed -i "/^$k.*$/d" $PVAR_FILE
    # Put in new lines
    grep -e "^$k" $VAR_FILE >>$PVAR_FILE
done

# Update the file /opt/openstack-ansible/playbooks/ansible.cfg
grep -q callback_plugins ${OSA_PLAYS}/ansible.cfg || sed -i '/\[defaults\]/a callback_plugins = plugins/callbacks' ${OSA_PLAYS}/ansible.cfg

echo "Bootstrap inventory"
generate_inventory

