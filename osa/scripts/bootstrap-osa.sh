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

echo "DEPLOY_AIO=$DEPLOY_AIO"
echo "infraNodes=$infraNodes"
echo "allNodes=$allNodes"

OSA_TAG="13.1.0"
OSA_DIR="/opt/openstack-ansible"
OSA_PLAYS="${OSA_DIR}/playbooks"

EXPECTED_ANSIBLE_VERSION="v1.9.4-1"

function generate_inventory {

    if [ -r $GENESIS_INVENTORY ]; then
        echo "Inventory provided by genesis"
        $SCRIPTS_DIR/generate_user_config.py \
            -i $GENESIS_INVENTORY \
            -d etc/openstack_deploy
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
    cd ${OSA_DIR}
    git checkout stable/mitaka
    if [ $? != 0 ]; then
        exit 1
    fi
    git checkout ${OSA_TAG}
    if [ $? != 0 ]; then
        exit 1
    fi
fi

# Install ansible
if [ ! -d /etc/ansible ]; then
    echo "Installing ansible..."
    cd ${OSA_DIR}
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
fi

# Load the python requirements
pip install -r $SCRIPTS_DIR/../../requirements.txt >/dev/null
rc=$?
if [ $rc != 0 ]; then
    echo "pip install requirements.txt failed, rc=$rc"
    exit 1
fi

echo "Bootstrap inventory"

generate_inventory

echo "Applying patches"

# TODO(luke): Need to apply patches to all controller nodes for opsmgr resiliency

cd /
ANSIBLE_PATCH=False
for f in ${PCLD_DIR}/diffs/*.patch; do
    patch -N -p1 < $f
    rc=$?
    if [[ "$f" == *"/opt-ansible"* ]] && [ $rc == 0 ]; then
        ANSIBLE_PATCH=True
    fi
done

if [ "$ANSIBLE_PATCH" == "True" ]; then
    echo "pip uninstall ansible"
    pip uninstall -y ansible
    echo "pip install patched ansible"
    pip install -q /opt/ansible_*
fi

# Override nova, neutron roles' git projects versions because OSA_TAG could be a later version than the branch
VAR_FILE=${OSA_PLAYS}/defaults/repo_packages/openstack_services.yml
PVAR_FILE=${OSA_PLAYS}/vars/pkvm/pkvm.yml
KEYS=$(grep -e "^neutron_.*:" -e "^nova_.*:" $VAR_FILE | awk '{print $1}')

for k in $KEYS
do
  # Remove any existing lines with this key
  sed -i "/^$k.*$/d" $PVAR_FILE
  # Put in new lines
  grep -e "^$k" $VAR_FILE >>$PVAR_FILE
done

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
