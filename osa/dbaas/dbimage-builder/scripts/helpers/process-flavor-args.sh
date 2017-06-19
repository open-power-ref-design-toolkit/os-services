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

dbName=""
flavor=""
cpus=""
mem=""
vdisk1=""
vdisk2=""
swift=""
predefinedOnly=false

cmd=$(basename $0)

OPTIND=1
while getopts "d:f:c:m:r:s:b:p" opt; do
    case "$opt" in
        d) dbName=$OPTARG
           ;;
        f) flavor=$OPTARG
           ;;
        c) cpus=$OPTARG
           ;;
        m) mem=$OPTARG
           ;;
        r) vdisk1=$OPTARG
           ;;
        s) vdisk2=$OPTARG
           ;;
        b) swift=$OPTARG
           ;;
        p) predefinedOnly=true
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
            echo "-d <db> must be specified.  One of $dbSupported"
        else
            echo "-d $dbName is not supported.  Must be one of $dbSupported"
        fi
        exit 1
esac

if [ "$cmd" == "dbflavor-change.sh" ]; then
    if [ -z "$flavor" ]; then
        echo "-f <flavor> must be specified"
        exit 1
    fi
    if [ -z "$cpus" -a -z "$mem" -a -z "$vdisk1" -a -z "$vdisk2" -a -z "$swift" ]; then
        echo "At least one of -c <vcpus>, -m <mem>, -r <vdisk1>, -s <vdisk2>, " \
             "or -b <swift storage> must be specified"
        exit 1
    fi
fi

export DBFLAVOR_DBNAME=$dbName
export DBFLAVOR_NAME=$flavor
export DBFLAVOR_CPUS=$cpus
export DBFLAVOR_MEM=$mem
export DBFLAVOR_VDISK1=$vdisk1
export DBFLAVOR_VDISK2=$vdisk2
export DBFLAVOR_SWIFT=$swift
export DBFLAVOR_PREDEFINED_ONLY=$predefinedOnly

