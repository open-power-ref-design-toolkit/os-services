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

OSA_FILES_WITH_GIT_URLS="/opt/openstack-ansible/ansible-role-requirements.yml \
    /opt/openstack-ansible/playbooks/defaults/repo_packages/openstack_services.yml"

echo "DEPLOY_AIO=$DEPLOY_AIO"
echo "infraNodes=$infraNodes"
echo "allNodes=$allNodes"
echo "GIT_MIRROR=$GIT_MIRROR"

OSA_TAG=${OSA_TAG:-"14.0.6"}
OSA_DIR="/opt/openstack-ansible"
OSA_PLAYS="${OSA_DIR}/playbooks"

ANSIBLE_RUNTIME_DIR="/opt/ansible-runtime"

function generate_user_config {

    if real_genesis_inventory_present; then
        echo "Found inventory provided by cluster-genesis"
        $SCRIPTS_DIR/generate_user_config.py \
            -i $GENESIS_INVENTORY \
            -d /etc/openstack_deploy
        rc=$?
        if [ $rc -ne 0 ]; then
            echo "Error generating config files from genesis file."
            exit 1
        fi
    else
        echo "Create cluster-genesis style inventory for post-OSA playbooks"
        cp -r var/oprc /var             # Presently only AIO yml

        # Indicate that inventory is simulated to maintain reentrancy
        touch $GENESIS_SIMULATED

        if [[ $DEPLOY_AIO == "yes" ]]; then
            if [ ! -d /openstack ]; then
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
    fi
}

if [ "$1" == "--help" ]; then
    echo "Usage: bootstrap-osa.sh"
    echo ""
    echo "export DEPLOY_HARDENING=yes|no                     Default is no"
    echo "export ADMIN_PASSWORD=                             Not applicable unless set"
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
    git checkout stable/newton
    if [ $? != 0 ]; then
        exit 1
    fi
    git checkout ${OSA_TAG}
    if [ $? != 0 ]; then
        exit 1
    fi
    popd >/dev/null 2>&1
    if [ -n "$GIT_MIRROR" ]; then
        echo "Patching OSA files to include GIT_MIRROR"
        sed -i "s/git\.openstack\.org/$GIT_MIRROR/g" $OSA_FILES_WITH_GIT_URLS
    fi
    # An openstack-ansible script is invoked below to install ansible
    rm -rf /etc/ansible
    #INSTALL=True

    # Apply patches to /opt/openstack-ansible so that bootstrap-ansible.sh
    # related patches are applied before bootstrap-ansible.sh is run.
    if [ -d $PCLD_DIR/diffs ]; then

        echo "Applying patches to /opt/openstack-ansible"
        pushd / >/dev/null 2>&1

        for f in ${PCLD_DIR}/diffs/opt-openstack-ansible-*.patch; do
            patch -N -p1 < $f
            rc=$?
            if [ $rc != 0 ]; then
                echo "Applying patches to /opt/openstack-ansible failed, rc=$rc"
                echo "Patch $f could not be applied"
                echo "Manual retry procedure:"
                echo "1) fix patch $f"
                echo "2) rm -rf /opt/openstack-ansible"
                echo "3) re-run command"
                exit 1
            fi
        done

        popd >/dev/null 2>&1
    fi
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
        # Override the user's lack of input as the goal is to automate install and workaround errors
        if [ -z "$GIT_MIRROR" ]; then
            GIT_MIRROR=github.com
            echo "Setting GIT_MIRROR=$GIT_MIRROR"
            sed -i "s/git\.openstack\.org/$GIT_MIRROR/g" $OSA_FILES_WITH_GIT_URLS
        fi
        echo "Installing ansible [retry]..."
        scripts/bootstrap-ansible.sh
        rc=$?
    fi
    if [ $rc != 0 ]; then
        echo "scripts/bootstrap-ansible.sh failed, rc=$rc"
        echo "Manual retry procedure:"
        echo "1) fix root cause of error if known"
        echo "2) rm -rf /etc/ansible; rm -rf $ANSIBLE_RUNTIME_DIR"
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

# Apply patches iff ansible is installed above.  Code is intended to be reentrant
if [ "$INSTALL" == "True" ] && [ -d $PCLD_DIR/diffs ]; then
    # Copy configuration files before patches are applied, so that
    # patches may be provided for configuration files
    cp -R /opt/openstack-ansible/etc/openstack_deploy /etc

    PATCHES=`find ${PCLD_DIR}/diffs/ ! -name '*opt-openstack-ansible-*' -type f`
    echo "Applying other patches"
    pushd / >/dev/null 2>&1

    for f in $PATCHES; do
        patch -N -p1 < $f
        rc=$?
        if [ $rc != 0 ]; then
            echo "scripts/bootstrap-ansible.sh failed, rc=$rc"
            echo "Patch $f could not be applied"
            echo "Manual retry procedure:"
            echo "1) fix patch $f"
            echo "2) pip uninstall ansible"
            echo "3) rm -rf /etc/ansible; rm -rf $ANSIBLE_RUNTIME_DIR"
            echo "4) re-run command"
            exit 1
        fi
    done

    popd >/dev/null 2>&1
fi

# Validate the config now that yaml and python dependencies are installed
# and before the config/inventory is used.
validate_config

# Translate cluster-genesis inventory into OpenStack parameters
if real_genesis_inventory_present; then
    echo "Found cluster-genesis inventory"

    # Clone cluster-genesis to access the dynamic inventory module.
    if [ ! -d ${GENESIS_DIR} ]; then
        echo "Installing cluster-genesis..."
        git clone ${GIT_GENESIS_URL} ${GENESIS_DIR}
        if [ $? != 0 ]; then
            echo "Manual retry procedure:"
            echo "1) fix root cause of error if known"
            echo "2) rm -rf ${GENESIS_DIR}"
            echo "3) re-run command"
            exit 1
        fi

        pushd ${GENESIS_DIR} >/dev/null 2>&1
        git checkout ${GENESIS_TAG}
        if [ $? != 0 ]; then
            exit 1
        fi
        popd >/dev/null 2>&1
    fi

    # Call the pre-deploy playbook to do additional pre-OSA prep.
    echo "Run pre-OSA prep..."
    pushd playbooks >/dev/null 2>&1
    ansible-playbook -i ${GENESIS_DIR}/scripts/python/yggdrasil/inventory.py pre-deploy.yml
    rc=$?
    if [ $rc != 0 ]; then
        echo "playbooks/pre-deploy.yml failed, rc=$rc"
        exit 1
    fi
    popd >/dev/null 2>&1
fi

# Copy over Trove-specific files - power_trove role and container groups specification
echo "Copying over Trove files..."
pushd dbaas >/dev/null 2>&1
cp -R etc /
popd >/dev/null 2>&1

echo "Generate OpenStack user configuration"
generate_user_config

