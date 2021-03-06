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

OSA_DIR="/opt/openstack-ansible"

shopt -s nullglob
set -o pipefail

ulimit -n 100000

function git-clone {
    GIT_URL=$1
    DESIRED_TAG=$2
    TARGET_DIR=$3
    echo "GIT_URL=$GIT_URL"
    echo "DESIRED_TAG=$DESIRED_TAG"
    pushd . >/dev/null 2>&1
    if [ -d $TARGET_DIR ]; then
        cd $TARGET_DIR
        TAG=`git symbolic-ref -q --short HEAD || git describe --tags --exact-match`
        if [ "$TAG" == "$DESIRED_TAG" ]; then
            git pull
            rc=$?
        else
            git checkout $DESIRED_TAG
            rc=$?
        fi
    else
        git clone $GIT_URL $TARGET_DIR
        rc=$?
        if [ $rc == 0 ]; then
            cd $TARGET_DIR
            git checkout $DESIRED_TAG
            rc=$?
        fi
    fi
    popd >/dev/null 2>&1
    if [ $rc != 0 ]; then
        echo "Failed git $TARGET_DIR, rc=$rc"
        exit 99
    fi
}

function run_project_script {
    dir=$1
    script=$2
    args=$3

    if [ ! -d "$dir" ]; then
        echo "Run ./scripts/bootstrap-cluster first!!!  $dir code is missing"
        return 1
    fi
    pushd $dir >/dev/null 2>&1
    if [ -e "scripts/$script" ]; then
        echo "Invoking scripts/$script $args"
        scripts/$script $args
        rc=$?
        if [ $rc != 0 ]; then
            echo "Failed scripts/$script, rc=$rc"
            return 2
        fi
    elif [[ "$script" != "check"* ]]; then
        echo "Failed required scripts/$script is missing!"
        return 3
    fi
    popd >/dev/null 2>&1

    return 0
}

function exit_on_error {
    rc=$1
    exitstatus=$2
    msg=$3

    if [ $rc != 0 ]; then
        if [ -n "$msg" ]; then
            echo $msg;
        fi
        exit $exitstatus
    fi
}


STAGE_FILE=${TOP_PCLD_DIR}/cluster-progress.txt
function record_success {
    stage=$1

    if stage_complete $stage ; then
        echo "Stage '$stage' already completed."
    else
        echo "$stage" >> ${STAGE_FILE}
    fi

}

function stage_complete {
    stage=$1
    if [ -e ${STAGE_FILE} ] && (grep $stage ${STAGE_FILE} >/dev/null) ; then
        return 0
    else
        return 1
    fi
}

function set_passwd {
    FILE=$1
    KEY=$2
    VALUE=$3
    if [ ! -z "$VALUE" ]; then
        PATTERN=`grep $KEY $FILE`
        if [ $? == 0 ]; then
            PASSWORD="${PATTERN##*:}"          # Delete everything before ':'
            PASSWORD="${PASSWORD// /}"         # Delete all blanks.  There is no newline
            if [ -z "$PASSWORD" ]; then
                sed -i "s/^$KEY:.*/$KEY: ${VALUE}/" $FILE
            fi
        fi
    fi
}

export ANSIBLE_PARAMETERS=${ANSIBLE_PARAMETERS:-""}
export ANSIBLE_FORCE_COLOR=${ANSIBLE_FORCE_COLOR:-"true"}
export FORKS=${FORKS:-8}
export BOOTSTRAP_OPTS=${BOOTSTRAP_OPTS:-""}

function run_ansible {
    openstack-ansible ${ANSIBLE_PARAMETERS} --forks ${FORKS} $@
}

GENESIS_INVENTORY="/var/oprc/inventory.yml"
GENESIS_SIMULATED="/var/oprc/inventory-simulated"

function real_genesis_inventory_present {

    if [ -r $GENESIS_INVENTORY ] && [ ! -e $GENESIS_SIMULATED ]; then
        return 0
    fi
    return 1
}

# Reduce list to unique items
function mkListsUnique {
    if [[ $# -eq 0 ]]; then
        uniqueList=""
    else
        node_array=($@)
        uniqueList=`echo "${node_array[@]}" | tr ' ' '\n' | sort -u | tr '\n' ' '`
    fi
}

# Finds whether the string given represents positive value like
# (y, yes, true) allowing both lower and upper case words
function is_positive {
    if [[ -n "$1" ]]; then
        VAR=`echo $1 | tr '[:upper:]' '[:lower:]'`
        case "$VAR" in
            y | yes | true)
                return 0  # true
            ;;
            *)
                return 1  # false
        esac
    else
        return 1  # false
    fi
}

function load_env_vars {
    if real_genesis_inventory_present && [ -z "$ENV_VARS_DEFINED" ]; then
        # Set any deployment variables that are present in the inventory
        while read -r line; do
            eval "export $line"
            echo "Defining variable: $line"
        done < <($TOP_PCLD_DIR/osa/scripts/get_env_vars.py -i $GENESIS_INVENTORY)
        export ENV_VARS_DEFINED=yes
    fi
}


if [[ $EUID -ne 0 ]]; then
    echo "This script must run as root."
    exit 1
fi

function validate_config {
    if real_genesis_inventory_present; then
        # Validate the config sections of the inventory.
        echo "Validate config ..."
        ${TOP_PCLD_DIR}/scripts/validate_config.py --file /var/oprc/inventory.yml
        rc=$?
        if [ $rc != 0 ]; then
            echo "${TOP_PCLD_DIR}/scripts/validate_config.py failed, rc=$rc"
            exit 1
        fi
    fi
}

# These command line parameters are not specified if the inventory is generated by Genesis (ie. manufacturing)
infraNodes=""
storageNodes=""
computeNodes=""
OPTIND=1
while getopts "i:c:s:" opt; do
    case "$opt" in
    i)  infraNodes=${OPTARG//,/ }       # {var//,/ } replaces all commas in the list with blanks
        ;;
    s)  storageNodes=${OPTARG//,/ }
        ;;
    c)  computeNodes=${OPTARG//,/ }
        ;;
    esac
done
shift $((OPTIND-1))                    # Now reference remaining arguments with $@, $1, $2, ...

mkListsUnique $infraNodes $storageNodes $computeNodes
allNodes=$uniqueList

if real_genesis_inventory_present; then
    # End user is not invoking commands.  Genesis process sets policy
    if [ -z "$DEPLOY_CEPH" ]; then
        DEPLOY_CEPH=yes
    fi
    if [ -z "$DEPLOY_OPSMGR" ]; then
        DEPLOY_OPSMGR=yes
    fi
    DEPLOY_AIO=no
elif [ "$infraNodes" == "" ]; then
    DEPLOY_AIO=yes
else
    infraArray=( $infraNodes )
    cnt=${#infraArray[@]}
    if [ $cnt -gt 1 ]; then
        DEPLOY_AIO=no
    else
        DEPLOY_AIO=yes
    fi
fi
