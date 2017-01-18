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
USER_VARIABLES_FILE="/etc/openstack_deploy/user_variables.yml"

if [ "$1" == "--help" ]; then
    echo "Usage: create-cluster-osa.sh"
    echo ""
    echo "export DEPLOY_HARDENING=yes|no                     Default is no"
    echo "export ADMIN_PASSWORD=                             Not applicable unless set"
    exit 1
fi

if [ ! -e scripts/bootstrap-osa.sh ]; then
    echo "This script must be run from /root/os-services/osa."
    exit 1
fi
PCLD_DIR=`pwd`

SCRIPTS_DIR=$(dirname $0)
source $SCRIPTS_DIR/process-args.sh

echo "DEPLOY_AIO=$DEPLOY_AIO"
echo "DEPLOY_HARDENING=$DEPLOY_HARDENING"
echo "DEPLOY_TEMPEST=$DEPLOY_TEMPEST"
echo "InfraNodes=$infraNodes"
echo "allNodes=$allNodes"

function rebuild_container {
    failingContainer=$1
    failingNode=${1%%_*}         # Get the part of arg1 before '_'. ie aio1_galera_container-3ac6d84 --> aio1

    echo "Rebuild failing container $failingContainer on node $failingNode"

    # If there is no '_' in arg1, then the failing object is a node.  ie. aio1
    if [ "$failingNode" == "$failingContainer" ]; then
        echo "Rebuild failed on node $1!!!"
        return 1
    fi

    # Destroy the old container
    if [ "$failingNode" == "aio1" ] || [ "$failingNode" == "$HOSTNAME" ]; then
        # Stop the container.  Enable debug logging.  Log is removed on success
        lxc-stop -n $failingContainer -l DEBUG
        rc=$?
        echo "Rebuild stop container ${failingContainer} rc=$rc"

        # Destroy container with force option.  Will stop it first if necessary
        lxc-destroy -n $failingContainer -f -l DEBUG
        rc=$?
        echo "Rebuild destroy container ${failingContainer} rc=$rc"

        # Check if the container still exists
        lxc-info -n $failingContainer
        rc=$?
        if [ $rc == 1 ]; then
            # Remove root file system of failing container
            rm -rf /openstack/${failingContainer}/*
            # Remove log file of failing container
            rm -rf /openstack/log/${failingContainer}/*
        else
            echo "For more information, please see log file /openstack/log/${failingContainer}/*.log"
            return 1
        fi
    else
        # Stop the container.  Enable debug logging.  Log is removed on success
        ansible $failingNode -a "lxc-stop -n $failingContainer -l DEBUG"
        rc=$?
        echo "Rebuild stop container ${failingContainer} rc=$rc"

        # Destroy container with force option.  Will stop it first if necessary
        ansible $failingNode -a "lxc-destroy -n $failingContainer -f -l DEBUG"
        rc=$?
        echo "Rebuild destroy container ${failingContainer} on node $failingNode rc=$rc"

        # Check if the container still exists
        ansible $failingNode -a "lxc-info -n $failingContainer"
        rc=$?
        if [ $rc == 2 ]; then
            # Remove root file system of failing container
            ansible $failingNode -a "rm -rf /openstack/${failingContainer}/*"
            # Remove log file of failing container
            ansible $failingNode -a "rm -rf /openstack/log/${failingContainer}/*"
        else
            echo "For more information, please see /openstack/log/${failingContainer}/*.log on node $failingNode"
            return 1
        fi
    fi

    # Run the playbook to rebuild the container
    run_ansible setup-hosts.yml -l ${failingNode} -l ${failingContainer}
    rc=$?
    if [ $rc != 0 ]; then
        echo "Rebuild failed setup-hosts.yml -l ${failingNode} -l ${failingContainer} rc=$rc, retry once"

        run_ansible setup-hosts.yml -l ${failingNode} -l ${failingContainer}
        rc=$?
        if [ $rc != 0 ]; then
            echo "Failed setup-hosts.yml again -l ${failingNode} -l ${failingContainer} rc=$rc"
            return $rc
        fi
        rm -f ~/setup-hosts.retry
    fi

    echo "Rebuild setup-hosts.yml successful for container $failingContainer on node $failingNode"

    # Run the playbook to configure the container
    run_ansible setup-infrastructure.yml -l ${failingNode} -l ${failingContainer}
    rc=$?
    if [ $rc != 0 ]; then
        echo "Rebuild failed setup-infrastructure -l ${failingNode} -l ${failingContainer} rc=$rc, retry once"

        run_ansible setup-infrastructure.yml -l ${failingNode} -l ${failingContainer}
        rc=$?
        if [ $rc != 0 ]; then
            echo "Failed setup-infrastructure.yml again -l ${failingNode} -l ${failingContainer} rc=$rc"
            return $rc
        fi
        rm -f ~/setup-infrastructure.retry
    fi
    echo "Rebuild setup-infrastructure.yml successful for container $failingContainer on node $failingNode"
    return 0
}

function configure_variable {
    key=$1
    value=$2
    var_file=$3

    pattern=`echo '^'$key`
    if grep -q $pattern $var_file
    then
        sed -i "s/$pattern:.*/$key: $value/" $var_file
    else
        echo $key": "$value  >> $var_file
    fi
}

cd ${OSA_DIR}

# Apply host security hardening with openstack-ansible-security
# This is applied as part of setup-hosts.yml
if [[ "$DEPLOY_HARDENING" == "yes" ]]; then
    echo "Security hardening enabled"
    configure_variable apply_security_hardening true $USER_VARIABLES_FILE
else
    echo "Security hardening disabled"
    configure_variable apply_security_hardening false $USER_VARIABLES_FILE
fi

# Disable apt cache proxy until the currently existing issues are fixed
configure_variable repo_pkg_cache_enabled false $USER_VARIABLES_FILE

# Set nova_console_type to novnc sothat deployed VM's console can be
# accessed through vnc
configure_variable nova_console_type novnc $USER_VARIABLES_FILE

# Set password in file for named secret if it is not set in file and environment variable is set
set_passwd /etc/openstack_deploy/user_secrets.yml keystone_auth_admin_password $ADMIN_PASSWORD

echo "Generating passwords"

# Ensure all needed passwords and tokens are generated
./scripts/pw-token-gen.py --file /etc/openstack_deploy/user_secrets.yml

# Generate passwords needed for Trove
./scripts/pw-token-gen.py --file /etc/openstack_deploy/user_secrets_trove.yml

echo "Running OSA playbooks"

cd ${OSA_DIR}/playbooks/

# Setup the hosts and build the basic containers
run_ansible setup-hosts.yml
rc=$?
if [ $rc != 0 ]; then
    echo "Failed setup-hosts.yml"
    exit 2
fi
echo "OSA playbook setup-hosts.yml successful"

# Setup the infrastructure
i=0
prevFailingContainer=""
failingContainer=""
done="False"
while [ "$done" == "False" ] && [ $i -lt 4 ]; do
    run_ansible setup-infrastructure.yml
    rc=$?
    if [ $rc == 0 ]; then
        echo "OSA playbook setup-infrastructure.yml successful"
        done="True"
        break
    fi

    failingContainer=`cat ~/setup-infrastructure.retry`
    if [ $? != 0 ]; then
        i=$((i+1))
        continue
    fi

    if [ "$failingContainer" == "$prevFailingContainer" ]; then
        echo "Failed setup-infrastructure.yml again with the same failures rc=$rc container=$failingContainer"
        exit 3
    fi
    prevFailingContainer=$failingContainer

    echo "Failed setup-infrastructure.yml rc=$rc, rebuild failing container $failingContainer ..."

    rebuild_container $failingContainer
    rc=$?
    if [ $rc != 0 ]; then
        echo "Failed rebuild_container rc=$rc container=$failingContainer"
        exit 4
    fi

    rm -f ~/setup-infrastructure.retry

    i=$((i+1))
done
if [ "$done" == "False" ]; then
    echo "Failed setup-infrastructure.yml too many times!!!"
    exit 5
fi

# This section is duplicated from OSA/run-playbooks
# Note that switching to run-playbooks may inadvertently convert to repo build from repo clone.
# When running in an AIO, we need to drop the following iptables rule in any neutron_agent containers
# to ensure that instances can communicate with the neutron metadata service.
# This is necessary because in an AIO environment there are no physical interfaces involved in
# instance -> metadata requests, and this results in the checksums being incorrect.
if [[ "$DEPLOY_AIO" == "yes" ]]; then
    ansible neutron_agent -m command \
        -a '/sbin/iptables -t mangle -A POSTROUTING -p tcp --sport 80 -j CHECKSUM --checksum-fill'
    ansible neutron_agent -m shell \
        -a 'DEBIAN_FRONTEND=noninteractive apt-get -qq -y install iptables-persistent'
fi

# Setup openstack
i=0
prevFailingContainer=""
failingContainer=""
done="False"
while [ "$done" == "False" ] && [ $i -lt 4 ]; do

    # For DEBUG purposes all echo statements start with either "Failed" or "Rebuild"
    # To see flow in log file, grep -e "^Failed" -e "^Rebuild" -e "^ValueError" <log-file>

    echo "Rebuild run setup-openstack.yml cnt=$i"
    run_ansible setup-openstack.yml
    rc=$?
    if [ $rc == 0 ]; then
        echo "OSA playbook setup-openstack.yml successful"
        done="True"
        break
    fi

    # Check for last iteration
    if [ $i -eq 3 ]; then
        break
    fi

    failingContainer=`cat ~/setup-openstack.retry`
    if [ "$failingContainer" == "$prevFailingContainer" ]; then
        echo "Failed setup-openstack.yml again rc=$rc container=$failingContainer"
        exit 6
    fi

    echo "Failed setup-openstack.yml rc=$rc, rebuild failing container(s) $failingContainer ..."

    failedAgain=""
    for container in $failingContainer; do
        # For node errors, we run setup-openstack.yml at the top of the while loop above
        if [ "$container" == "aio1" ] || [ "$container" == "$HOSTNAME" ]; then
            echo "Rebuild skip $container on node $failingNode"
            failedAgain="$failedAgain $container"
            continue;
        fi

        # This destroys container and re-builds it
        rebuild_container $container
        rc=$?
        if [ $rc != 0 ]; then
            echo "Failed rebuild_container rc=$rc container=${container}"
            exit 7
        fi

        run_ansible setup-openstack.yml -l $failingNode -l $container
        rc=$?
        if [ $rc != 0 ]; then
            echo "Failed setup-openstack.yml -l $failingNode -l $container rc=$rc, continueing ..."
            failedAgain="$failedAgain $container"
            continue
        fi
        echo "Rebuild setup-openstack.yml successful for container $container on node $failingNode"
    done

    prevFailingContainer=$failedAgain
    rm -f ~/setup-openstack.retry

    i=$((i+1))
done
if [ "$done" == "False" ]; then
    echo "Failed setup-openstack.yml too many times!!!"
    exit 8
fi

# The post-deploy.yml playbook copies /etc/openstack_deploy to each controller node enabling
# each to assume the role of operational management.  Copying the data allows each node to
# recreate the configuration. The data pertains to inventory, user variables, and user secrets.

echo "Invoking post-deploy playbooks"
pushd $PCLD_DIR/playbooks >/dev/null 2>&1
run_ansible -i $OSA_DIR/playbooks/inventory/dynamic_inventory.py post-deploy.yml
rc=$?
if [ $rc != 0 ]; then
    echo "scripts/create-cluster-osa.sh failed, invoking post-deploy playbooks rc=$rc"
    echo "Non-fatal error, continuing..."
    echo "Manual recovery procedure:"
    echo "1) For each controller, scp -r /etc/openstack-deploy root@controller:/etc"
fi
popd >/dev/null 2>&1

if [[ "$DEPLOY_TEMPEST" == "yes" ]]; then
    run_ansible os-tempest-install.yml
    rc=$?
    if [ $rc != 0 ]; then
        echo "scripts/create-cluster-osa.sh failed, installing tempest rc=$rc"
        exit 9
    fi
fi
