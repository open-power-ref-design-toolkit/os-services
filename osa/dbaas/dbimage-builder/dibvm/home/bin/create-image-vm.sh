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

if [ "$1" == "--help" ]; then
    echo "Usage: create-image-vm.sh -i dibvm-ipaddr -d db-name -v db-version"
    echo "          [ -D distro-db-pkg-name -V distro-db-pkg-version | -p pkg ] [ -u user ]"
    echo ""
    echo "Upon successful completion, a raw disk image file is created in $HOME/img/"
    echo ""
    echo "See the README.rst file for more information"
    exit 1
fi

if [ -e bin/$0 ]; then
    echo "This script must be invoked from $HOME"
    exit 1
fi

echo "$0 $*"

SCRIPTS_DIR=$(dirname $0)
source $SCRIPTS_DIR/process-image-args.sh

# Calculate -a arch argument to disk-image-create.  This parameter is used to populate
# the chrooted environment in which commands will be run
ARCH=$(uname -m)
case "$ARCH" in
    ppc64le)
        ARCH=ppc64el
        ;;
    x86_64)
        ARCH=amd64
        ;;
    *)
        echo "create-image-vm.sh failed, invalid platform architecture - $ARCH"
        exit 1
esac

if [ -n "$DIB_RELEASE" ]; then
    # Target image is specified via an environment variable
    case "$DIB_RELEASE" in
        trusty)
            DISTRO_NAME=ubuntu
            ;;
        xenial)
            DISTRO_NAME=ubuntu
            ;;
        *)
            echo "create-image-vm.sh failed, invalid DIB_RELEASE - $DIB_RELEASE"
            exit 1
    esac
    IMG="${DISTRO_NAME}_${DIB_RELEASE}_${DBIMAGE_DBNAME}"
    GUESTELE="${DISTRO_NAME}-${DIB_RELEASE}-guest"
    DBELE="${DISTRO_NAME}-${DIB_RELEASE}-${DBIMAGE_DBNAME}"
else
    # Image is based on the running distro
    if [ -e /etc/centos-release ] ; then
        DISTRO_REL=$(cat /etc/centos-release | awk '{print $4}')
        IMG="centos_${DISTRO_REL}_${DBIMAGE_DBNAME}_${DBIMAGE_DBVERSION}"
        DISTRO_NAME="centos7"
        GUESTELE=
        DBELE="${DBIMAGE_DBNAME}"
    elif [ -e /etc/redhat-release ] ; then
        DISTRO_REL=$(cat /etc/redhat-release | awk '{print $7}')
        IMG="rhel_${DISTRO_REL}_${DBIMAGE_DBNAME}_${DBIMAGE_DBVERSION}"
        DISTRO_NAME="rhel7"
        GUESTELE=
        DBELE="${DBIMAGE_DBNAME}"
    else
        DISTRO_NAME=$(lsb_release -i | awk '{print $3}' | awk '{print tolower($0)}')
        if [ $? != 0 ]; then
            echo "create-image-vm.sh failed, invalid Linux distributor - $DISTRO_NAME.  Ubuntu expected"
            exit 1
        fi
        DISTRO_REL=$(lsb_release -r | awk '{print $2}')
        DIB_RELEASE=$(lsb_release -c | awk '{print $2}' | awk '{print tolower($0)}')
        IMG="${DISTRO_NAME}_${DISTRO_REL}_${DBIMAGE_DBNAME}_${DBIMAGE_DBVERSION}"
        GUESTELE="${DISTRO_NAME}-${DIB_RELEASE}-guest"
        DBELE="${DISTRO_NAME}-${DIB_RELEASE}-${DBIMAGE_DBNAME}"
    fi
fi
export DISTRO_NAME
export DIB_RELEASE

# Generate output image name
IMG=$(echo $IMG | tr '.' '_' | tr '-' '_')

CMD="disk-image-create"
CMDARGS="--no-tmpfs -a $ARCH -o $HOME/img/$IMG $DISTRO_NAME vm heat-cfntools cloud-init-datasources $GUESTELE $DBELE"

# These environment variables are input parameters to trovedibrc
export SERVICE_TYPE=$DBIMAGE_DBNAME
export CONTROLLER_IP=$DBIMAGE_IPADDR
if [ -z "$DBIMAGE_PKG" ]; then
    export DATASTORE_PKG_LOCATION=""
else
    export DATASTORE_PKG_LOCATION="$HOME/pkg"
fi

# Create a file that can be manually invoked for debug purposes
cat <<EOF > $HOME/cmd.log
export DISTRO_NAME=$DISTRO_NAME
export DIB_RELEASE=$DIB_RELEASE
export SERVICE_TYPE=$SERVICE_TYPE
export CONTROLLER_IP=$CONTROLLER_IP
export DATASTORE_PKG_LOCATION=$DATASTORE_PKG_LOCATION"
source $SCRIPTS_DIR/trovedibrc
$CMD $CMDARGS"
EOF

# Caller scans stdout for this string and uses it to fetch the image
echo "OUTPUT_IMAGE: $IMG.qcow2"
echo "OUTPUT_LOG: $IMG.log"

source $SCRIPTS_DIR/trovedibrc

$CMD $CMDARGS > $HOME/log/$IMG.log 2>&1

