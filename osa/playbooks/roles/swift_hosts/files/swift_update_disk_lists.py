#!/usr/bin/env python
#
# Copyright 2016 IBM Corp.
#
# All Rights Reserved.
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
import copy
import signal
import sys
import yaml


NODENAME_FIELD = 'ipv4-pxe'


class SwiftDiskPrep(object):
    """Class for performing swift disk prep genesis inventory updates."""

    def __init__(self, nodename, input_file, output_file, dl_file, dl_type):
        """Initializer.

        :param nodename: Name of a host in the genesis inventory (YAML) file.
        :param input_file: Name of a genesis inventory (YAML) file.
        :param output_file: Output modified genesis inventory (YAML) file.
        :param dl_file: Flat (non-YAML) file with a single disk per line.
        :param dl_type: <account | container | object>.
        """
        super(SwiftDiskPrep, self).__init__()
        self.nodename = nodename
        self.input_file = input_file
        self.output_file = output_file
        self.dl_file = dl_file
        self.dl_type = dl_type
        self.dl_type_string = dl_type + '-ring-disks'

        # Start with an empty disklist and input/output dict.
        self.dl = []
        self.input_dict = {}
        self.output_dict = {}

    def _load_yml(self, name):
        with open(name, 'r') as stream:
            try:
                return yaml.safe_load(stream)
            except yaml.YAMLError as ex:
                print(ex)
            sys.exit(1)

    def _write_yml(self, filename, contents):
        stream = file(filename, 'w')
        yaml.dump(contents, stream, indent=4, default_flow_style=False)

    def _read_dl_file(self):
        with open(self.dl_file, 'r') as fp:
            for line in fp.readlines():
                stripline = line.strip()
                self.dl.append(stripline)

    def _add_dl_to_inventory(self):
        self.output_dict = copy.deepcopy(self.input_dict)

        target_host = {}
        host_types = ('swift-metadata', 'swift-object')

        for host_type in host_types:
            if host_type not in self.output_dict['nodes']:
                continue

            swift_hosts = self.output_dict['nodes'][host_type]

            for host in swift_hosts:
                if self.nodename == host[NODENAME_FIELD]:
                    target_host = host
                    break

        if target_host:
            if 'domain-settings' not in target_host:
                target_host['domain-settings'] = {}
            target_host['domain-settings'][self.dl_type_string] = self.dl
        else:
            print ("Error: Host %s not found.\n" % (self.nodename))
            sys.exit(1)


def process_disklist(args):
    sdp = SwiftDiskPrep(args.nodename, args.input_file, args.output_file,
                        args.disklist_file, args.disklist_type)

    sdp.input_dict = sdp._load_yml(sdp.input_file)
    sdp._read_dl_file()
    sdp._add_dl_to_inventory()
    sdp._write_yml(sdp.output_file, sdp.output_dict)


def parse_command():
    """Parse the command arguments for generate user config."""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=('A command to add swift account, container, and '
                     'object disk lists to the Genesis inventory file.'))
    parser.add_argument('-n', '--nodename', required=True,
                        help=('Name of host in the Genesis inventory YAML'
                              'file.'))
    parser.add_argument('-i', '--input-file', required=True,
                        help=('Path to the Genesis inventory YAML file.'))
    parser.add_argument('-d', '--disklist-file', required=True,
                        help=('Path to the disk list file (flat, non-YAML).'))
    parser.add_argument('-t', '--disklist-type', required=True,
                        help=('<account | container | object>.'))
    parser.add_argument('-o', '--output-file', default='output.inventory.yml',
                        help=('Path to the updated Genesis inventory YAML'
                              'file to be generated.'))

    return parser


def signal_handler(signal, frame):
    """Signal handler to for processing, e.g. keyboard interrupt signals."""
    sys.exit(0)


def main():
    """Main function."""
    parser = parse_command()
    args = parser.parse_args()
    signal.signal(signal.SIGINT, signal_handler)

    if (len(sys.argv) < 1):
        parser.print_help()
        sys.exit(1)

    if args.disklist_type not in ('account', 'container', 'object'):
        parser.print_help()
        sys.exit(1)

    process_disklist(args)
    return 0


if __name__ == "__main__":
    main()
