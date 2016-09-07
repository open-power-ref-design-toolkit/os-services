#!/usr/bin/env python
#
# Copyright 2016, IBM US, Inc.
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
import os
import signal
import sys
import yaml

OSA_USER_CFG_FILE = 'openstack_user_config.yml'
OSA_USER_VAR_HAPROXY = 'user_var_haproxy.yml'
OSA_USER_VAR_CEILOMETER = 'user_var_ceilometer.yml'
OSA_USER_VAR_CEPH = 'user_var_ceph.yml'


class OSAFileGenerator(object):
    """Class for generating various OSA configuration files."""

    def __init__(self, inventory_name, output_dir):
        """Initializer.

        :param inventory_name: Name of a genesis inventory file.
        :param output_dir: Directory to which files will be generated.
        """
        super(OSAFileGenerator, self).__init__()
        self.inventory_name = inventory_name
        self.output_dir = output_dir
        self.gen_dict = {}
        self.user_config = {}

    def _load_yml(self):
        with open(self.inventory_name, 'r') as stream:
            try:
                self.gen_dict = yaml.safe_load(stream)
            except yaml.YAMLError:
                raise

    def _dump_yml(self, data, fname):
        fname = os.path.join(self.output_dir, fname)
        with open(fname, 'w') as stream:
            try:
                yaml.dump(data, stream, explicit_start=True,
                          default_flow_style=False)
            except yaml.YAMLError:
                raise

    def _configure_cidr_networks(self):
        """Configure the CIDR networks."""
        networks = self.gen_dict.get('networks', None)
        if not networks:
            return

        cidr = {}
        mgmt_network = networks.get('openstack-mgmt', None)
        if mgmt_network:
            cidr['container'] = mgmt_network.get('addr', 'N/A')

        stg_network = networks.get('openstack-stg', None)
        if stg_network:
            cidr['storage'] = stg_network.get('addr', 'N/A')

        tenant_network = networks.get('openstack-tenant-vxlan', None)
        if tenant_network:
            cidr['tunnel'] = tenant_network.get('addr', 'N/A')

        self.user_config['cidr_networks'] = cidr

    def _configure_infra_hosts(self):
        """Configure the infra hosts."""
        nodes = self.gen_dict.get('nodes', None)
        if not nodes:
            return

        controllers = nodes.get('controllers', None)
        if not controllers:
            return

        # Build a list of all of the controllers / ips
        hosts = {}
        for controller in controllers:
            hostname = controller.get('hostname', None)
            if hostname:
                hosts[hostname] = {
                    'ip': controller.get('openstack-mgmt-addr', 'N/A')
                }

        # Set all the common services across all the controllers
        self.user_config['shared-infra_hosts'] = hosts
        self.user_config['os-infra_hosts'] = copy.deepcopy(hosts)
        self.user_config['repo-infra_hosts'] = copy.deepcopy(hosts)
        self.user_config['identity_hosts'] = copy.deepcopy(hosts)
        self.user_config['storage-infra_hosts'] = copy.deepcopy(hosts)
        self.user_config['network_hosts'] = copy.deepcopy(hosts)
        self.user_config['haproxy_hosts'] = copy.deepcopy(hosts)

        return

    @staticmethod
    def _get_address(addr_cidr):
        # Given 'N/A' or '1.2.3.4/22' return the address only part
        if addr_cidr == 'N/A':
            return addr_cidr
        else:
            return addr_cidr.split('/')[0]

    def _configure_global_overrides(self):
        """Configure the global overrides section."""
        nodes = self.gen_dict.get('nodes', None)
        if not nodes:
            return

        controllers = nodes.get('controllers', None)
        if not controllers:
            return

        net_mgmt = net_stg = net_tunnel = net_vlan = None
        br_mgmt = br_tunnel = br_stg = br_vlan = None

        networks = self.gen_dict.get('networks', None)
        if not networks:
            return

        net_mgmt = networks.get('openstack-mgmt', None)
        if net_mgmt:
            br_mgmt = net_mgmt.get('bridge', 'N/A')

        net_stg = networks.get('openstack-stg', None)
        if net_stg:
            br_stg = net_stg.get('bridge', 'N/A')

        net_tunnel = networks.get('openstack-tenant-vxlan', None)
        if net_tunnel:
            br_tunnel = net_tunnel.get('bridge', 'N/A')

        net_vlan = networks.get('openstack-tenant-vlan', None)
        if net_vlan:
            br_vlan = net_vlan.get('bridge', 'N/A')

        self.user_config['global_overrides'] = {
            # Set the load balancing addresses
            # They are in the form 1.2.3.4/22, we only need the address here
            'internal_lb_vip_address':
                self._get_address(self.gen_dict.get('internal-floating-ipaddr',
                                                    'N/A')),
            'external_lb_vip_address':
                self._get_address(self.gen_dict.get('external-floating-ipaddr',
                                                    'N/A')),
            'tunnel_bridge': br_tunnel,
            'management_bridge': br_mgmt,
        }

        # provider networks
        networks = []
        mgmt_network = {
            'container_bridge': br_mgmt,
            'container_type': 'veth',
            'container_interface': 'eth1',
            'ip_from_q': 'container',
            'type': 'raw',
            'group_binds': [
                'all_containers',
                'hosts'
            ],
            'is_container_address': True,
            'is_ssh_address': True
        }

        storage_network = {
            'container_bridge': br_stg,
            'container_type': 'veth',
            'container_interface': 'eth2',
            'ip_from_q': 'storage',
            'type': 'raw',
            'group_binds': [
                'glance_api',
                'cinder_api',
                'cinder_volume',
                'nova_compute',
                'swift_proxy',
            ],
        }

        vxlan_network = {
            'container_bridge': br_tunnel,
            'container_type': 'veth',
            'container_interface': 'eth10',
            'ip_from_q': 'tunnel',
            'type': 'vxlan',
            'range': '1:1000',
            'net_name': 'vxlan',
            'group_binds': [
                'neutron_linuxbridge_agent',
            ]
        }

        # Genesis doesn't create the veth pair yet, but we still need it.
        # Hardcode veth12 for now which will make our manual setup easier.
        host_vlan_intf = 'veth12'
        vlan_vlan_network = {
            'container_bridge': br_vlan,
            'container_type': 'veth',
            'container_interface': 'eth11',
            'type': 'vlan',
            'range': '1:4094',
            'net_name': 'vlan',
            'group_binds': [
                'neutron_linuxbridge_agent',
            ],
        }

        vlan_flat_network = {
            'container_bridge': br_vlan,
            'container_type': 'veth',
            'container_interface': 'eth12',
            'host_bind_override': host_vlan_intf,
            'type': 'flat',
            'net_name': 'external',
            'group_binds': [
                'neutron_linuxbridge_agent',
            ],
        }

        networks.append({'network': mgmt_network})
        networks.append({'network': storage_network})
        networks.append({'network': vxlan_network})
        networks.append({'network': vlan_vlan_network})
        networks.append({'network': vlan_flat_network})

        self.user_config['global_overrides']['provider_networks'] = networks

    def _configure_compute_hosts(self):
        """Configure the compute hosts."""
        nodes = self.gen_dict.get('nodes', None)
        if not nodes:
            return

        hosts = nodes.get('compute', None)
        if not hosts:
            return

        # Compute Hosts
        compute_hosts = {}
        for controller in hosts:
            hostname = controller.get('hostname', None)
            if hostname:
                compute_hosts[hostname] = {
                    'ip': controller.get('openstack-mgmt-addr', 'N/A')
                }

        self.user_config['compute_hosts'] = compute_hosts

    def _configure_storage_hosts(self):
        """Configure the storage hosts."""
        nodes = self.gen_dict.get('nodes', None)
        if not nodes:
            return

        controllers = nodes.get('controllers', None)
        if not controllers:
            return

        # Storage Hosts (assuming ceph as cinder backend)
        default_volume_hdd = {
            'volume_driver': 'cinder.volume.drivers.rbd.RBDDriver',
            'rbd_pool': 'volumes',
            'rbd_ceph_conf': '/etc/ceph/ceph.conf',
            'rbd_flatten_volume_from_snapshot': False,
            'rbd_max_clone_depth': 5,
            'rbd_store_chunk_size': 4,
            'rados_connect_timeout': -1,
            'volume_backend_name': 'ceph',
            'rbd_user': '{{ cinder_ceph_client }}',
            'rbd_secret_uuid': '{{ cinder_ceph_client_uuid }}',
        }

        # Storage Hosts
        storage_hosts = {}
        for controller in controllers:
            hostname = controller.get('hostname', None)
            if hostname:
                ceph_data = {
                    'ip': controller.get('openstack-mgmt-addr', 'N/A'),
                    'container_vars': {
                        'cinder_backends': {
                            'limit_container_types': 'cinder_volume',
                            'ceph': copy.deepcopy(default_volume_hdd),
                        }
                    }
                }
                storage_hosts[hostname] = ceph_data

        self.user_config['storage_hosts'] = storage_hosts

        return

    def create_user_config(self):
        """Process the inventory input and generate the OSA user config."""
        self._load_yml()
        self._configure_cidr_networks()
        self._configure_infra_hosts()
        self._configure_global_overrides()
        self._configure_compute_hosts()
        self._configure_storage_hosts()

        self._dump_yml(self.user_config, OSA_USER_CFG_FILE)

    def generate_haproxy(self):
        """Generate user variable file for HAProxy."""
        external_vip = self.gen_dict.get('external-floating-ipaddr', 'N/A')
        internal_vip = self.gen_dict.get('internal-floating-ipaddr', 'N/A')
        networks = self.gen_dict.get('networks', None)
        mgmt_network = networks.get('openstack-mgmt', None)
        bridge = mgmt_network.get('bridge', None)
        eth_intf = mgmt_network.get('eth-port', None)
        settings = {
            'haproxy_keepalived_external_vip_cidr': external_vip,
            'haproxy_keepalived_internal_vip_cidr': internal_vip,
            'haproxy_keepalived_external_interface': eth_intf,
            'haproxy_keepalived_internal_interface': bridge,
        }
        self._dump_yml(settings, OSA_USER_VAR_HAPROXY)

    def generate_ceilometer(self):
        """Generate user variable file for ceilometer."""
        settings = {
            'swift_ceilometer_enabled': False,
            'nova_ceilometer_enabled': False,
        }
        self._dump_yml(settings, OSA_USER_VAR_CEILOMETER)

    def generate_ceph(self):
        """Generate user variable file for ceph."""
        nodes = self.gen_dict.get('nodes', None)
        if not nodes:
            return

        controllers = nodes.get('controllers', None)
        if not controllers:
            return

        monitors = []
        for c in controllers:
            monitors.append(c.get('openstack-stg-addr', 'N/A'))

        settings = {
            'ceph_pkg_source': 'uca',
            'glance_default_store': 'rbd',
            'glance_rbd_store_pool': 'images',
            'nova_libvirt_images_rbd_pool': 'vms',
            'ceph_mons': monitors,
        }

        self._dump_yml(settings, OSA_USER_VAR_CEPH)


def process_inventory(inv_name, output_dir):
    """Process the input inventory file.

    :param inv_name: The path name of the input genesis inventory.
    :param output_dir: The name of path for the generated files.
    """
    generator = OSAFileGenerator(inv_name, output_dir)

    generator.create_user_config()
    generator.generate_haproxy()
    generator.generate_ceilometer()
    generator.generate_ceph()


def parse_command():
    """Parse the command arguments for generate user config."""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=('A command to generate the ansible user configuration'
                     ' based on the Genesis inventory YAML file.'))
    parser.add_argument('-i', '--input-file', required=True,
                        help=('Path to the Genesis inventory YAML file'))
    parser.add_argument('-d', '--output-dir', default='.',
                        help=('Path to the OpenStack user config file to '
                              'be generated'))

    parser.set_defaults(func=process_inventory)
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

    args.func(args.input_file, args.output_dir)
    return 0


if __name__ == "__main__":
    main()
