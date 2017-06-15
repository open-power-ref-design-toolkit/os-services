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

ipAddrDib=""
dbName=""
dbVersion=""
pkg=""
pkgType=""
chrootCmd=""
cloudKey=""
communityEdition=false
enterpriseEdition=false
dibUser=ubuntu
imageName=""

cmd=$(basename $0)

# These arguments apply to dbimage-make.sh and create-image-vm.sh
# which run on different hosts.  They have the same command arguments.
# Both commands source this file ensuring that there are no command
# argument errors in the backend when create-image-vm.sh is invoked.

OPTERR=0
OPTIND=1
while getopts ":d:v:f:k:ces:" opt; do
    case "$opt" in
        d) dbName=$OPTARG
           ;;
        v) dbVersion=$OPTARG
           ;;
        k) cloudKey=$OPTARG
           ;;
        c) communityEdition=true
           ;;
        e) enterpriseEdition=true
           ;;
        f) imageName=$OPTARG
           ;;
        s) chrootCmd=$OPTARG
           ;;
        :) echo "Error: -$OPTARG requires an argument." >&2
           exit 1
           ;;
       \?) echo "Error: invalid option $OPTARG" 1>&2
           exit 1
           ;;
    esac
done
shift $((OPTIND-1))                    # Now reference remaining arguments with $@, $1, $2, ...

dbSupported="mariadb, mongodb, mysql, postgresql, or redis"

case "$dbName" in
    mariadb|mongodb|mysql|postgresql|redis)
        ;;
    *)
        if [ -z "$dbName" ]; then
            echo "Error: -d <db> must be specified.  One of $dbSupported" 1>&2
        else
            echo "Error: -d $dbName is not supported.  Must be one of $dbSupported" 1>&2
        fi
        exit 1
esac

if [ -z "$dbVersion" ]; then
    echo "Error: -v <db-version> must be specified"
    exit 1
fi

if [ -z "$imageName" ]; then
    echo "Error: -f <path-to-image> must be specified"
    exit 1
fi

if [ ! -r "./images/$imageName" ]; then
    echo "Error: file images/$imageName does not exist or is not readable"
    exit 1
fi

# These variables are derived from command line argument
echo "ipAddrDib=$ipAddrDib"
echo "dbName=$dbName"
echo "dbVersion=$dbVersion"
echo "pkg=$pkg"
echo "pkgType=$pkgType"
echo "chrootCmd=$chrootCmd"
echo "cloudKey=$cloudKey"
echo "dibUser=$dibUser"
echo "communityEdition=$communityEdition"
echo "enterpriseEdition=$enterpriseEdition"
echo "imageName=$imageName"

# These variables are derived from environment variables
echo "dibRelease=$DIB_RELEASE"
echo "distroName=$DISTRO_NAME"
echo "dibDebug=$DIB_MYDEBUG"

export DBIMAGE_CMD=upload
export DBIMAGE_IPADDR=$ipAddrDib
export DBIMAGE_DBNAME=$dbName
export DBIMAGE_DBVERSION=$dbVersion
export DBIMAGE_PKG=$pkg
export DBIMAGE_PKGTYPE=$pkgType
export DBIMAGE_CHROOT_CMD=$chrootCmd
export DBIMAGE_CLOUD_KEY=$cloudKey
export DBIMAGE_DIBUSER=$dibUser
export DBIMAGE_HOME=$HOME
export DBIMAGE_COMMUNITY_EDITION=$communityEdition
export DBIMAGE_ENTERPRISE_EDITION=$enterpriseEdition
export DBIMAGE_IMAGE_NAME=$imageName
