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

function validate-tar {
    tarflags=$1
    pkg=$2

    if tar $tarflgs $pkg setup.sh; then
        installScript=setup.sh
    else
        echo "Error: tar file must contain a setup.sh file at root" 1>&2
        exit 1
    fi
    return $installScript
}


# Packages built from source
couchUrl=
couchTag=
cassandraUrl=git://github.com/apache/cassandra
cassandraTag=3.7

ipAddrDib=""
dbName=""
dbVersion=""
pkg=""
pkgType=""
installScript=""
cloudUser=""
branch=""
gitUrl=""
gitTag=""
communityEdition=false
dibUser=ubuntu

cmd=$(basename $0)

# These arguments apply to dbimage-make.sh and create-image-vm.sh
# which run on different hosts.  They have the same command arguments.
# Both commands source this file ensuring that there are no command
# argument errors in the backend when create-image-vm.sh is invoked.

OPTERR=0
OPTIND=1
while getopts ":i:d:v:p:u:b:c" opt; do
    case "$opt" in
        i) ipAddrDib=$OPTARG
           ;;
        d) dbName=$OPTARG
           ;;
        v) dbVersion=$OPTARG
           ;;
        p) pkg=$OPTARG
           if [ ! -e "$pkg" ]; then
               echo "Error: package file $pkg does not exist" 1>&2
               exit 1
           fi
           IFS='.' read -r pkgName pkgType <<< "$pkg"
           case "$pkgType" in
               tar)
                   installScript=validate-tar -tvf $pkg
                   ;;
               tgz)
                   installScript=validate-tar -ztvf $pkg
                   ;;
               bz2)
                   installScript=validate-tar -jtvf $pkg
                   ;;
               deb)
                   if file $pkg | grep -e Debian; then
                       installScript=apt-get
                   else
                       echo "Error: invalid Debian package specified (-p $pkg)" 1>&2
                       exit 1
                   fi
                   ;;
               *)
                   echo "Error: unsupported package type $pkgType.  Must be one of tar, tgz, bz2, deb" 1>&2
                   exit 1
           esac
           ;;
        u) cloudUser=$OPTARG
           ;;
        b) dibUser=$OPTARG
           ;;
        c) communityEdition=true
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
#   couchbase)
#       gitUrl=$couchUrl
#       gitTag=$couchTag
#       ;;
    *)
        if [ -z "$dbName" ]; then
            echo "Error: -d <db> must be specified.  One of $dbSupported" 1>&2
        else
            echo "Error: -d $dbName is not supported.  Must be one of $dbSupported" 1>&2
        fi
        exit 1
esac

if [ -n "$pkg" ] && [ -z "$dbVersion" ]; then
    echo "Error: -p <package> must be specified with -v <db-version>"
    exit 1
fi

DISTRO_CODENAME=$(lsb_release -c | awk '{print $2}' | awk '{print tolower($0)}')
if [ $? != 0 ] || [ "$DISTRO_CODENAME" != "xenial" ] && [ "$communityEdition" == "true" ]; then
    echo "Error: community provided databases (-c) are only supported on Ubuntu 16.04"
    exit 1
fi

if [ -n "$DIB_RELEASE" ]; then
    case "$DIB_RELEASE" in
        trusty)
            if [ "$communityEdition" == "true" ]; then
                echo "Error: -c cannot be specified with DIB_RELEASE=trusty"
                exit 1
            fi
            DISTRO_NAME=ubuntu
            ;;
        xenial)
            DISTRO_NAME=ubuntu
            ;;
        *)
            echo "Error: invalid DIB_RELEASE - $DIB_RELEASE.  Must be one of trusty or xenial"
            exit 1
    esac
fi

# These variables are derived from command line argument
echo "ipAddrDib=$ipAddrDib"
echo "dbName=$dbName"
echo "dbVersion=$dbVersion"
echo "pkg=$pkg"
echo "pkgType=$pkgType"
echo "installScript=$installScript"
echo "cloudUser=$cloudUser"
echo "gitUrl=$gitUrl"
echo "gitTag=$gitTag"
echo "dibUser=$dibUser"
echo "communityEdition=$communityEdition"

# These variables are derived from environment variables
echo "dibRelease=$DIB_RELEASE"
echo "distroName=$DISTRO_NAME"
echo "dibDebug=$DIB_MYDEBUG"

export DBIMAGE_IPADDR=$ipAddrDib
export DBIMAGE_DBNAME=$dbName
export DBIMAGE_DBVERSION=$dbVersion
export DBIMAGE_PKG=$pkg
export DBIMAGE_PKGTYPE=$pkgType
export DBIMAGE_INSTALLSCRIPT=$installScript
export DBIMAGE_USER=$cloudUser
export DBIMAGE_GITURL=$gitUrl
export DBIMAGE_GITTAG=$gitTag
export DBIMAGE_DIBUSER=$dibUser
export DBIMAGE_HOME=$HOME
export DBIMAGE_COMMUNITY_EDITION=$communityEdition
