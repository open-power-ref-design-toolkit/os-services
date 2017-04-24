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
        echo "Tar file must contain a setup.sh file at root" 1>&2
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
distroPkgName=""
distroPkgVersion=""
dibUser="ubuntu"
dataStoreSuffix=""

cmd=$(basename $0)

# These arguments apply to dbimage-make.sh and create-image-vm.sh
# but not necessarily equally.  User arguments are passed from the
# front end to the back end, but the former dbimage internally
# calculates a few extra parms which are passed to the backend
# such as the distro provided package name and version [-D and -V]

OPTERR=0
OPTIND=1
while getopts ":i:d:v:p:u:D:V:b:" opt; do
    case "$opt" in
        i) ipAddrDib=$OPTARG
           ;;
        d) dbName=$OPTARG
           ;;
        D) distroPkgName=$OPTARG
           ;;
        v) dbVersion=$OPTARG
           ;;
        V) distroPkgVersion=$OPTARG
           ;;
        p) pkg=$OPTARG
           if [ ! -e "$pkg" ]; then
               echo "Package file $pkg does not exist" 1>&2
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
                       echo "Invalid Debian package specified (-p $pkg)" 1>&2
                       exit 1
                   fi
                   ;;
               *)
                   echo "Unsupported package type $pkgType.  Must be one of tar, tgz, bz2, deb" 1>&2
                   exit 1
           esac
           ;;
        u) cloudUser=$OPTARG
           ;;
        b) dibUser=$OPTARG
           ;;
        :) echo "Invalid argument: -$OPTARG requires an argument." >&2
           exit 1
           ;;
       \?) echo "Invalid option: $OPTARG" 1>&2
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
            echo "-d <db> must be specified.  One of $dbSupported" 1>&2
        else
            echo "-d $dbName is not supported.  Must be one of $dbSupported" 1>&2
        fi
        exit 1
esac

if [ -n "$pkg" ] && [ -z "$dbVersion" ]; then
    echo "-p <package> must be specified with -v <db-version>"
    exit 1
fi

# These variables are derived from command line argument
echo "ipAddrDib=$ipAddrDib"
echo "dbName=$dbName"
echo "dbVersion=$dbVersion"
echo "distroPkgName=$distroPkgName"
echo "distroPkgVersion=$distroPkgVersion"
echo "pkg=$pkg"
echo "pkgType=$pkgType"
echo "installScript=$installScript"
echo "cloudUser=$cloudUser"
echo "gitUrl=$gitUrl"
echo "gitTag=$gitTag"
echo "dibUser=$dibUser"

# These variables are derived from environment variables
echo "dibRelease=$DIB_RELEASE"
echo "distroName=$DISTRO_NAME"
echo "dataStoreSuffix=$DBIMAGE_DATASTORE_SUFFIX"

export DBIMAGE_IPADDR=$ipAddrDib
export DBIMAGE_DBNAME=$dbName
export DBIMAGE_DBVERSION=$dbVersion
export DBIMAGE_DISTRODBNAME=$distroPkgName
export DBIMAGE_DISTRODBVERSION=$distroPkgVersion
export DBIMAGE_PKG=$pkg
export DBIMAGE_PKGTYPE=$pkgType
export DBIMAGE_INSTALLSCRIPT=$installScript
export DBIMAGE_USER=$cloudUser
export DBIMAGE_GITURL=$gitUrl
export DBIMAGE_GITTAG=$gitTag
export DBIMAGE_DIBUSER=$dibUser
export DBIMAGE_HOME=$HOME
