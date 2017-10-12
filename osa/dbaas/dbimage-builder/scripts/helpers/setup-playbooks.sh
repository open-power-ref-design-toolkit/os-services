#!/usr/bin/env bash
#
# Copyright 2017 IBM Corp.
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

shopt -s nullglob
set -o pipefail

export DBIMAGE_CONTROLLER_IP=${DBIMAGE_CONTROLLER_IP:-localhost}
export DBIMAGE_DIR=`pwd`

export TOP_PCLD_DIR=../../../..

GENESIS_INVENTORY="$DBIMAGE_DIR/etc/inventory.yml"
GENESIS_SIMULATED="$DBIMAGE_DIR/etc/inventory-simulated"

function create-playbook-inventory {

    type pip >/dev/null 2>&1 || sudo apt-get install -qq -y libssl-dev libffi-dev python-pip
    type ansible-playbook >/dev/null 2>&1 || sudo pip install ansible==2.3.2
    sudo apt-get install -qq -y sshpass

    ctrl=$DBIMAGE_CONTROLLER_IP

    hostFile=playbooks/inventory

    # short and long hostnames
    shorthost=$(hostname -s 2>/dev/null)
    longhost=$(hostname -f 2>/dev/null)
    if [ "$longhost" == "localhost" ]; then
        longhost=$shorthost
    fi

    IFS='.' read -r shorthost string <<< "$longhost"

    if [ -z "$ipAddrDib" ] || [ "$ipAddrDib"  == "localhost" ] ||
       [ "$ipAddrDib" == "$shorthost" ] || [ "$ipAddrDib" == "$longhost" ]; then

        # DBIMAGE_IPADDR is set to localhost to facilitate comparisons in playbooks
        export DBIMAGE_IPADDR=localhost

        # Need to use the actual hostname for ssh connections
        dibvm="$longhost ansible_connection=ssh ansible_user=$DBIMAGE_DIBUSER"
    else
        dibvm="$ipAddrDib ansible_connection=ssh ansible_user=$DBIMAGE_DIBUSER"
        if [ -n "$DBIMAGE_DIB_PRIVATE_SSH_KEY" ]; then
            dibvm+=" ansible_ssh_private_key_file=$DBIMAGE_DIB_PRIVATE_SSH_KEY"
        elif [ -n "$DBIMAGE_DIB_PASSWD" ]; then
            dibvm+=" ansible_ssh_pass=$DBIMAGE_DIB_PASSWD"
        fi
    fi

    if [ "$ctrl" == "localhost" ] ||
       [ "$ctrl" == "$shorthost" ] || [ "$ctrl" == "$longhost" ]; then
        ctrl="$ctrl ansible_connection=local"
    else
        ctrl="$ctrl ansible_connection=ssh ansible_user=ubuntu"
        if [ -n "$DBIMAGE_CTRL_PRIVATE_SSH_KEY" ]; then
            ctrl+=" ansible_ssh_private_key_file=$DBIMAGE_CTRL_PRIVATE_SSH_KEY"
        elif [ -n "$DBIMAGE_CTRL_PASSWD" ]; then
            ctrl+=" ansible_ssh_pass=$DBIMAGE_CTRL_PASSWD"
        fi
    fi

    echo -e "[deployer]\nlocalhost ansible_connection=local\n\n[dib]\n$dibvm\n\n[controller]\n$ctrl\n\n" > $hostFile

    echo "dibvm=$dibvm"
}

function real_genesis_inventory_present {

    if [ -r $GENESIS_INVENTORY ] && [ ! -e $GENESIS_SIMULATED ]; then
        return 0
    fi
    return 1
}

function load_env_vars {

    if real_genesis_inventory_present && [ -z "$ENV_VARS_DEFINED" ]; then

        if [ ! -e $TOP_PCLD_DIR/osa/scripts/get_env_vars.py ]; then
            echo "Error: $TOP_PCLD_DIR/osa/scripts/get_env_vars.py not found"
            echo "The os-services project appears to be corrupted.  Please git clone os-services again"
            return 1
        fi

        # Set any deployment variables that are present in the inventory
        while read -r line; do
            eval "export $line"
            echo "Defining variable: $line"
        done < <($TOP_PCLD_DIR/osa/scripts/get_env_vars.py -i $GENESIS_INVENTORY)

        export ENV_VARS_DEFINED=yes
    fi

    return 0
}

function validate-playbook-environment {
    target=$1
    cmd="$2"

    if [ "$target" == "controller" ]; then
        ansible_args="$CTRL_ANSIBLE_ARGS"
    else
        ansible_args="$DIBVM_ANSIBLE_ARGS"
    fi

    # Validate dib only to minimize ssh prompting.  Invoke non-privileged cmd to test the connection
    if [ "$target" == "dib" ]; then
        ansible $target -i inventory $ansible_args -m raw -a ls >/dev/null
    else
        file1="src=/var/oprc/inventory-simulated dest=$DBIMAGE_DIR/etc/ flat=yes"
        file2="src=/var/oprc/inventory.yml dest=$DBIMAGE_DIR/etc/ flat=yes"
        ansible $target -i inventory $ansible_args --become -m fetch -a "$file1" >/dev/null
        ansible $target -i inventory $ansible_args --become -m fetch -a "$file2" >/dev/null
    fi
    if [ $? != 0 ]; then
        echo "Error: validate-playbook-environment failed.  Could not connect to $target"
        if [ "$target" == "dib" ]; then
            echo "Did you set one of the following in the file $SCRIPTS_DIR/dbimagerc?"
            echo "export DBIMAGE_DIB_PASSWD=<x>"
            echo "export DBIMAGE_DIB_PRIVATE_SSH_KEY=~/.ssh/<y>"
            echo "Else test the connection manually by invoking 'ssh ubuntu@<ip-addr-dibvm>'"
            return 1
        else
            echo "Did you specify the wrong IP address or hostname?"
        fi
    fi
    if [ "$target" == "controller" ]; then
        load_env_vars
        if [ $? != 0 ]; then
            return 1
        fi
    fi

    # Validate ssh connection to local and remote nodes with a privileged command.
    # This is typically apt-get update which is the most common failure of the playbooks
    # so it done here upfront to avoid downstream errors in the playbooks.
    i=0
    done="False"
    while [ "$done" == "False" ] && [ $i -lt 2 ]; do
        ansible $target -b -i inventory $ansible_args -m raw -a "$cmd"
        if [ $? == 0 ]; then
            done="True"
            break
        else
            sleep 20
            i=$((i+1))
            echo "Retrying $i..2"
        fi
    done

    if [ "$done" == "False" ]; then
        echo "Error: dbimage-make.yml failed to run command '$cmd' on the $target"
        if [ "$target" == "controller" ]; then
            echo "Did you set one of the following in the file $SCRIPTS_DIR/dbimagerc?"
            echo "export DBIMAGE_CTRL_SSH_PROMPT=yes"
            echo "export DBIMAGE_CTRL_PASSWD=<p>"
            echo "export DBIMAGE_CTRL_PRIVATE_SSH_KEY=~/.ssh/<q>"
        else
            echo "This appears to be either an intermittent network error or a command error in the dibvm"
        fi
        return 1
    fi
    return 0
}

CTRL_ANSIBLE_ARGS=""
DIBVM_ANSIBLE_ARGS=""

if [ "$DBIMAGE_CTRL_SSH_PROMPT" == 'yes' ] || [ "$DBIMAGE_CTRL_SSH_PROMPT" == 'y' ]; then
    CTRL_ANSIBLE_ARGS+="-k "
fi
if [ "$DBIMAGE_ANSIBLE_DEBUG" == 'yes' ] || [ "$DBIMAGE_ANSIBLE_DEBUG" == 'y' ]; then
    CTRL_ANSIBLE_ARGS+="-vvv"
    DIBVM_ANSIBLE_ARGS+="-vvv"
fi
