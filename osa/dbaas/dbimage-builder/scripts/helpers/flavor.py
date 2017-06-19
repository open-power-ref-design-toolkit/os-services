#!/usr/bin/env python
#
# Copyright 2017 IBM US, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import sys
import yaml
from copy import deepcopy


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('func',
                        help=('The function to be performed: show or change'))
    parser.add_argument('-P', '--predefined-path', required=True,
                        help=('Path to predefined database YAML file - '
                              'playbooks/vars/predefined-flavors.yml'))
    parser.add_argument('-C', '--customized-path',
                        help=('Path to the customized database YAML file - '
                              'playbooks/vars/customized-flavors.yml'))
    parser.add_argument('-d', '--dbname',
                        help='The database to show or change')
    parser.add_argument('-f', '--flavor',
                        help='The database flavor')
    parser.add_argument('-c', '--vcpus',
                        help='The number of virtual cpus')
    parser.add_argument('-m', '--mem',
                        help='The amount of memory in gigabytes')
    parser.add_argument('-r', '--vdisk1',
                        help='The quantity in megabytes of vdisk1')
    parser.add_argument('-s', '--vdisk2',
                        help='The quantity in megabytes of vdisk2')
    parser.add_argument('-b', '--swift',
                        help='The quantity in megabytes of swift storage')
    parser.add_argument('-p', '--defaults-only', action="store_true",
                        help='Use default values only')
    return parser.parse_args()


def get_flavors(file):

    try:
        stream = open(file, 'r')
        flavors = yaml.safe_load(stream)
        stream.close()
    except IOError:
        flavors = {}
        flavors['flavors'] = []
    except Exception as e:
        assert(False), str(e)

    out = []
    try:
        for flavor in flavors['flavors']:
            out.append(flavor)
    except Exception as e:
        assert(False), str(e)

    return out


def put_flavors(data, file):

    flavors = {}
    flavors['flavors'] = data
    with open(file, 'w') as stream:
        try:
            flavors = yaml.dump(flavors, stream, explicit_start=True,
                                default_flow_style=False)
            stream.close()
        except yaml.YAMLError:
            raise


def merge_flavors(predefines, customized):

    result = deepcopy(customized)
    for predefine in predefines:
        found = False
        for item in customized:
            if predefine['name'] == item['name'] and \
               predefine['config'] == item['config']:
                found = True
                break
        if not found:
            result.append(predefine)

    return sorted(result, key=lambda k: (k['name'], k['vdisk2']))


def print_flavors(flavors, dbname):

    print("NAME        FLAVOR    DBSIZE(GBs)  VCPUS  MEM(MBs)  "
          "BACKUP STORAGE(GBs)")
    print("----        ------    -----------  -----  --------  "
          "-------------------")
    try:
        for flavor in flavors:
            if dbname and not flavor['name'].startswith(dbname):
                continue
            print("%-10s  %-9s    %-6d      %-3d    %-6d        %-8d" %
                  (flavor['name'], flavor['config'], flavor['vdisk2'],
                   flavor['vcpus'], flavor['mem'], flavor['swift']))
    except:
        print "Error: malformed flavor: %s" % str(flavor)


def change_flavors(predefines, customized, args):

    if not args.dbname:
        print("Error: -d dbname must be specified")
        sys.exit(1)

    if not args.flavor:
        print("Error: -f flavor must be specified")
        sys.exit(1)

    if args.vcpus and args.vcpus != '-1' and (int(args.vcpus) < 1 or
       int(args.vcpus) > 128):
        print("Error: range 0 < vcpus <= 128")
        sys.exit(1)

    if args.mem and args.mem != '-1' and (int(args.mem) < 1024 or
       int(args.mem) > 524288):
        print("Error: range 1G <= mem <= 512G")
        sys.exit(1)

    if args.vdisk1 and args.vdisk1 != '-1' and (int(args.vdisk1) < 1 or
       int(args.vdisk1) > 128):
        print("Error: range 1G <= vdisk1 <= 128G, vdisk1 is root volume")
        sys.exit(1)

    if args.vdisk2 and args.vdisk2 != '-1' and (int(args.vdisk2) < 1 or
       int(args.vdisk2) > 512):
        print("Error: range 1G <= vdisk2 <= 512G, vdisk2 is db volume")
        sys.exit(1)

    if args.swift and args.swift != '-1' and (int(args.swift) < 1 or
       int(args.swift) > 512):
        print("Error: range 1G <= swift <= 512G, swift is backup storage")
        sys.exit(1)

    # Find the database and flavor in predefines
    found = False
    for predefine in predefines:
        if args.dbname != predefine['name']:
            continue
        if args.flavor != predefine['config']:
            continue
        found = True
        break

    if not found:
        print("Error: invalid database or flavor")
        sys.exit(1)

    # It may also be in customized if previously modified
    found = False
    for item in customized:
        if args.dbname == item['name'] and args.flavor == item['config']:
            found = True
            break

    # Make a copy for comparison purposes to avoid unnecessary writes
    # Changes are made to item below
    if found:
        orig = deepcopy(item)
        allocateItem = False
    else:
        orig = deepcopy(predefine)
        item = deepcopy(predefine)
        allocateItem = True

    # Restore default values
    if args.vcpus == '-1':
        item['vcpus'] = predefine['vcpus']
    if args.mem == '-1':
        item['mem'] = predefine['mem']
    if args.vdisk1 == '-1':
        item['vdisk1'] = predefine['vdisk1']
    if args.vdisk2 == '-1':
        item['vdisk2'] = predefine['vdisk2']
    if args.swift == '-1':
        item['swift'] = predefine['swift']

    # Apply new values
    if args.vcpus is not None and args.vcpus != '-1':
        item['vcpus'] = int(args.vcpus)
    if args.mem is not None and args.mem != '-1':
        item['mem'] = int(args.mem)
    if args.vdisk1 is not None and args.vdisk1 != '-1':
        item['vdisk1'] = int(args.vdisk1)
    if args.vdisk2 is not None and args.vdisk2 != '-1':
        item['vdisk2'] = int(args.vdisk2)
    if args.swift is not None and args.swift != '-1':
        item['swift'] = int(args.swift)

    # Return if there is no state change --- same value was reassigned
    if orig['vcpus'] == item['vcpus'] and \
       orig['mem'] == item['mem'] and \
       orig['vdisk1'] == item['vdisk1'] and \
       orig['vdisk2'] == item['vdisk2'] and \
       orig['swift'] == item['swift']:
        return 0

    # Check if values are being changed back to defaults
    if predefine['vcpus'] == item['vcpus'] and \
       predefine['mem'] == item['mem'] and \
       predefine['vdisk1'] == item['vdisk1'] and \
       predefine['vdisk2'] == item['vdisk2'] and \
       predefine['swift'] == item['swift']:
        if not allocateItem:
            customized.remove(item)
    else:
        customized.append(item)

    return 1


if __name__ == '__main__':
    args = parse_args()

    if args.func not in 'show change dump':
        print("Error: invalid command %s" % args.func)
        sys.exit(1)

    predefines = get_flavors(args.predefined_path)
    if not predefines:
        print("Error: playbooks/vars/predefined-flavors.yml is "
              "missing, malformed, or empty")
        sys.exit(1)

    if args.defaults_only:
        customized = []
    else:
        customized = get_flavors(args.customized_path)

    if args.func == 'change':
        changed = change_flavors(predefines, customized, args)
        if changed:
            put_flavors(customized, args.customized_path)

    merged = merge_flavors(predefines, customized)

    if args.func == 'dump':
        print(yaml.dump(merged, explicit_start=True, default_flow_style=False))
    else:
        print_flavors(merged, args.dbname)
