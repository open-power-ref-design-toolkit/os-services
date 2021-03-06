#!/usr/bin/env python
#
# Copyright 2016, 2017 IBM US, Inc.
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
import netaddr

OSA_USER_CFG_FILE = 'openstack_user_config.yml'
OSA_USER_VAR_HAPROXY = 'user_var_haproxy.yml'
OSA_USER_VAR_RABBITMQ = 'user_var_rabbitmq.yml'
OSA_USER_VAR_CEILOMETER = 'user_var_ceilometer.yml'
OSA_USER_VAR_CEPH = 'user_var_ceph.yml'

# deployment_environment_variables go into user_var_deploy_env.yml.
# OpenStack-Ansible applies these environment variables during deployment
# phase only. These environment variables are not available in hosts
# and containers once the deployment is completed.
OSA_USER_VAR_DEPLOY_ENV = 'user_var_deploy_env.yml'

SWIFT_MINIMUM_HARDWARE = 'swift-minimum-hardware'
SWIFT = 'swift'
PRIVATE_COMPUTE_CLOUD = 'private-compute-cloud'
DBAAS_REF_CLOUD = 'dbaas'

ARCHITECTURE = 'architecture'
X86_64 = 'x86_64'
PPC64 = 'ppc64'
PPC64LE = 'ppc64le'

REPO_INFRA_HOSTS = 'repo-infra_hosts'
OS_INFRA_HOSTS = 'os-infra_hosts'
SHARED_INFRA_HOSTS = 'shared-infra_hosts'
IDENTITY_HOSTS = 'identity_hosts'
COMPUTE_HOSTS = 'compute_hosts'
SWIFT_PROXY_HOSTS = 'swift-proxy_hosts'
SWIFT_HOSTS = 'swift_hosts'


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

        swift_repl_network = networks.get('swift-replication', None)
        if swift_repl_network:
            cidr['swift_repl'] = swift_repl_network.get('addr', 'N/A')

        self.user_config['cidr_networks'] = cidr

    def is_host_type_of_role(self, role, node_template):
        """ Check if the given node_template has the given role"""
        roles = node_template.get('roles', [])
        if role in roles:
            return True

        return False

    def _get_nodes_through_roles(self, role):
        """ Go through all node-templates and get all the host types which
            have the given role. This method looks at roles only. It
            doesn't look for sections like "controllers", "computes", etc
            under nodes unless "controllers" or "compute" node-template has
            controller/compute role defined.
        """
        hosts = []  # hosts of given role

        # Find the node-templates section.
        node_templates = self.gen_dict.get('node-templates', None)
        nodes = self.gen_dict.get('nodes', None)
        if not node_templates or not nodes:
            return hosts

        # Go through all the node-templates and look for the given role
        for host_type, template in node_templates.iteritems():
            if self.is_host_type_of_role(role, template):
                # Add nodes of this host type to hosts list
                hosts.extend(nodes.get(host_type, []))

        return hosts

    def _get_nodes_for_role(self, role):
        nodes = self.gen_dict.get('nodes', {})
        nodes_for_role = []
        nodes_for_role.extend(nodes.get(role, []))
        by_role = self._get_nodes_through_roles(role)
        for node in by_role:
            if node not in nodes_for_role:
                nodes_for_role.append(node)
        return nodes_for_role

    def _get_controllers(self):
        nodes = self.gen_dict.get('nodes', None)
        if not nodes:
            return None

        controllers_list1 = nodes.get('controllers', [])
        controllers_list2 = self._get_nodes_through_roles('controller')

        for node in controllers_list1:
            if node not in controllers_list2:
                controllers_list2.append(node)
        return controllers_list2

    def _configure_infra_hosts(self):
        """Configure the infra hosts."""

        controllers = self._get_controllers()
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

        # Set all the common services across all the controllers which
        # provides the minimal control plane.
        self.user_config[SHARED_INFRA_HOSTS] = hosts
        self.user_config[REPO_INFRA_HOSTS] = copy.deepcopy(hosts)
        self.user_config[IDENTITY_HOSTS] = copy.deepcopy(hosts)
        self.user_config['dashboard_hosts'] = copy.deepcopy(hosts)
        self.user_config['haproxy_hosts'] = copy.deepcopy(hosts)
        self.user_config['log_hosts'] = copy.deepcopy(hosts)

        if PRIVATE_COMPUTE_CLOUD in self.get_ref_arch():
            # Private compute cloud adds additional services to the
            # control plane.
            self.user_config['storage-infra_hosts'] = copy.deepcopy(hosts)
            self.user_config['network_hosts'] = copy.deepcopy(hosts)
            self.user_config['image_hosts'] = copy.deepcopy(hosts)
            self.user_config['compute-infra_hosts'] = copy.deepcopy(hosts)
            self.user_config['orchestration_hosts'] = copy.deepcopy(hosts)

        if DBAAS_REF_CLOUD in self.get_ref_arch():
            self.user_config['trove-infra_hosts'] = copy.deepcopy(hosts)

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

        ref_arch_list = self.get_ref_arch()
        if PRIVATE_COMPUTE_CLOUD in ref_arch_list:
            net_tunnel = networks.get('openstack-tenant-vxlan', None)

        net_vlan = networks.get('openstack-tenant-vlan', None)
        if net_vlan:
            br_vlan = net_vlan.get('bridge', 'N/A')

        controllers = self._get_controllers()
        e_addr = self._get_external_vip_value()
        if len(controllers) > 1:
            i_addr = self.gen_dict.get('internal-floating-ipaddr', 'N/A')
        else:
            # This is only 1 controller, don't use the external vip, use
            # the controllers ip addresses for haproxy instead
            i_addr = controllers[0].get('openstack-mgmt-addr', 'N/A')
            e_net, e_net_details = self.find_external_network(e_addr,
                                                              networks)
            # Now substitute the controllers address
            e_addr = controllers[0].get(e_net + '-addr', 'N/A')

        self.user_config['global_overrides'] = {
            # Set the load balancing addresses
            # They are in the form 1.2.3.4/22, we only need the address here
            'internal_lb_vip_address': self._get_address(i_addr),
            'external_lb_vip_address': self._get_address(e_addr),
            'management_bridge': br_mgmt,
        }

        if net_tunnel:
            br_tunnel = net_tunnel.get('bridge', 'N/A')
            self.user_config['global_overrides']['tunnel_bridge'] = br_tunnel

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
        if 'mtu' in net_mgmt:
            mgmt_network['container_mtu'] = net_mgmt.get('mtu')
        if DBAAS_REF_CLOUD in ref_arch_list:
            mgmt_network['type'] = 'flat'
            mgmt_network['host_bind_override'] = net_mgmt.get('bridge-port')
            mgmt_network['net_name'] = 'infra'

        networks.append({'network': mgmt_network})
        if net_stg:
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
            if 'mtu' in net_stg:
                storage_network['container_mtu'] = net_stg.get('mtu')
            networks.append({'network': storage_network})

        if PRIVATE_COMPUTE_CLOUD in ref_arch_list:
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
            if 'mtu' in net_tunnel:
                vxlan_network['container_mtu'] = net_tunnel.get('mtu')

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
            if 'mtu' in net_vlan:
                vlan_vlan_network['container_mtu'] = net_vlan.get('mtu')

            host_vlan_intf = net_vlan.get('bridge-port', 'eth12')
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
            if 'mtu' in net_vlan:
                vlan_flat_network['container_mtu'] = net_vlan.get('mtu')
            networks.append({'network': vxlan_network})
            networks.append({'network': vlan_vlan_network})
            networks.append({'network': vlan_flat_network})

        self.user_config['global_overrides']['provider_networks'] = networks

    def _get_compute_hosts(self):
        if PRIVATE_COMPUTE_CLOUD not in self.get_ref_arch():
            return None

        nodes = self.gen_dict.get('nodes', None)
        if not nodes:
            return None
        compute_list = self._get_nodes_for_role('compute')
        return compute_list

    def _configure_compute_hosts(self):
        """Configure the compute hosts."""

        hosts = self._get_compute_hosts()
        if not hosts:
            return

        # Compute Hosts
        compute_hosts = {}
        for compute in hosts:
            hostname = compute.get('hostname', None)
            if hostname:
                compute_hosts[hostname] = {
                    'ip': compute.get('openstack-mgmt-addr', 'N/A')
                }

        self.user_config[COMPUTE_HOSTS] = compute_hosts

    def _configure_storage_hosts(self):
        """Configure the storage hosts."""
        if PRIVATE_COMPUTE_CLOUD not in self.get_ref_arch():
            return

        nodes = self.gen_dict.get('nodes', None)
        if not nodes:
            return

        controllers = self._get_controllers()
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

    def _configure_swift_general(self):
        """Configure general user variables for swift."""

        # Find the storage network bridge name.
        networks = self.gen_dict.get('networks', None)
        if not networks:
            return

        stg_network = networks.get('openstack-stg', None)
        if not stg_network:
            return

        bridge_name = stg_network.get('bridge', None)
        if not bridge_name:
            return

        swift_rep_network = networks.get('swift-replication', None)
        br_swift_repl = None
        if swift_rep_network:
            br_swift_repl = swift_rep_network.get('bridge', None)

        # General swift vars
        swift = {}
        swift['storage_network'] = bridge_name
        swift['part_power'] = 8
        swift['mount_point'] = '/srv/node'
        if br_swift_repl:
            swift['repl_network'] = br_swift_repl

        if 'global_overrides' not in self.user_config:
            self.user_config['global_overrides'] = {}

        self.user_config['global_overrides']['swift'] = swift

        return

    def _configure_swift_policies(self):
        """Configure storage_policies for swift."""

        storage_policies = []
        policy = {
            'name': 'default',
            'index': 0,
            'default': 'True',
        }
        storage_policies.append({'policy': policy})

        self.user_config['global_overrides']['swift']['storage_policies'] = (
            storage_policies)

        return

    def _get_swift_proxy_hosts(self):
        nodes = self.gen_dict.get('nodes', None)
        if not nodes:
            return None

        proxies = []

        ref_arch_list = self.get_ref_arch()

        if SWIFT in ref_arch_list:
            proxies = self._get_nodes_for_role('swift-proxy')
            # for backward compatibility we fall back to the controller
            # nodes if we haven't found proxies yet and SWIFT_MINIMUM_HARDWARE
            # is specified.
            if not proxies and (SWIFT_MINIMUM_HARDWARE in ref_arch_list):
                proxies = self._get_controllers()

        return proxies

    def _configure_swift_proxy_hosts(self):
        """Configure list of swift proxy hosts."""

        swift_proxy_hosts = self._get_swift_proxy_hosts()
        if swift_proxy_hosts is None:
            return

        proxy_hosts = {}

        # Swift Proxy Hosts.
        for proxy in swift_proxy_hosts:
            hostname = proxy.get('hostname', None)
            if hostname:
                proxy_hosts[hostname] = {
                    'ip': proxy.get('openstack-mgmt-addr', 'N/A')
                }

        self.user_config[SWIFT_PROXY_HOSTS] = proxy_hosts
        return

    def _configure_swift_template(self, host, template_vars):
        """Grab values from the node-template for the given host_type."""

        # Find the node-templates section.
        node_templates = self.gen_dict.get('node-templates', None)
        if not node_templates:
            return

        # The host_type is either swift-metadata or swift-object.
        template = node_templates.get(host['template'], None)
        if not template:
            return

        # Find the domain-settings section.
        domain_settings = template.get('domain-settings', None)
        if not domain_settings:
            return

        # Override the default zone_count if necessary.
        zcount = domain_settings.get('zone-count', None)
        if zcount:
            template_vars['zone_count'] = zcount

        # Override the default mount_point if necessary.
        mpoint = domain_settings.get('mount-point', None)
        if mpoint:
            template_vars['mount_point'] = mpoint

        return

    def _configure_swift_host(self, host, zone, mount_point, swift_vars):
        """Configure a single swift_host.

        This typically includes a list of drives specific to this host.
        """

        domain_settings = host.get('domain-settings', None)
        if not domain_settings:
            return

        # There are three different disk lists we need to check.
        drive_types = (
            'account-ring-disks',
            'container-ring-disks',
            'object-ring-disks')

        name_to_drive = {}
        for drive_type in drive_types:

            ring_disks = domain_settings.get(drive_type, None)
            if not ring_disks:
                continue

            for disk in ring_disks:
                drive = name_to_drive.get(disk)
                if not drive:
                    drive = {
                        'name': disk,
                        'groups': [],
                    }
                    name_to_drive[disk] = drive

                if drive_type == 'object-ring-disks':
                    drive['groups'].append('default')
                elif drive_type == 'account-ring-disks':
                    drive['groups'].append('account')
                elif drive_type == 'container-ring-disks':
                    drive['groups'].append('container')
        # This list of drives for this host will be inserted into swift_vars.
        drives = []
        for drive in sorted(name_to_drive.keys()):
            drives.append(name_to_drive[drive])

        swift_vars['zone'] = zone
        swift_vars['drives'] = drives

        # If the mount_point value was specified in the node-template,
        # use it here.  Otherwise, don't specify a node specific mount_point
        # here.  That way we default to the mount point generated by
        # _configure_swift_general.
        if mount_point:
            swift_vars['mount_point'] = mount_point

        return

    def _get_swift_ring_hosts(self):
        nodes = self.gen_dict.get('nodes', None)
        if not nodes:
            return None
        object_nodes = self._get_nodes_for_role('swift-object')
        md_nodes = self._get_nodes_for_role('swift-metadata')
        for node in md_nodes:
            if node not in object_nodes:
                object_nodes.append(node)
        return object_nodes

    def _configure_swift_hosts(self):
        """Configure list of swift_hosts.

        This typically includes a list of drives specific to this host.
        """

        nodes = self.gen_dict.get('nodes', None)
        if not nodes:
            return

        def is_converged_metadata_object(meta, object):
            meta_copy = list(meta)
            object_copy = list(object)
            try:
                for node in meta_copy:
                    object_copy.remove(node)
            except ValueError:
                return False
            return not object_copy

        object_nodes = self._get_nodes_for_role('swift-object')
        md_nodes = self._get_nodes_for_role('swift-metadata')
        # Here we simply see if the two node lists have the same elements.
        # Better checking of ring device settings, etc is done in the
        # validate config step which is called earlier.
        converged = is_converged_metadata_object(md_nodes, object_nodes)
        if converged:
            swift_hosts = self._build_swift_hosts_section(object_nodes)
        else:
            # Separate metadata and object nodes.
            # We build the swift host sections for each and merge them
            # and add the merged dict to the config.
            swift_hosts = self._build_swift_hosts_section(object_nodes)
            mh = self._build_swift_hosts_section(md_nodes)
            swift_hosts.update(mh)

        # Avoid adding an empty value for the key 'swift_hosts' in the
        # case where no swift metadata or swift object nodes exist
        # in the inventory.
        if swift_hosts:
            self.user_config[SWIFT_HOSTS] = swift_hosts

    def _build_swift_hosts_section(self, nodes):
        # We automatically set the zone index for each host.  This
        # assumes the default 3x swift replication, so the zone
        # values cycle between 0-2.
        swift_hosts = {}
        zone = 0
        for host in nodes:

            hostname = host.get('hostname', None)
            if hostname:

                # See if there are values for zone_count and mount_point
                # specified in the node-templates.
                template_vars = {}
                self._configure_swift_template(host, template_vars)
                zone_count = template_vars.get('zone_count', 3)
                mount_point = template_vars.get('mount_point', None)
                # Fill out the dictionary of swift_vars for
                # this host (including the zone and drives list).
                swift_vars = {}
                self._configure_swift_host(host, zone, mount_point,
                                           swift_vars)

                swift_hosts[hostname] = {
                    'ip': host.get('openstack-mgmt-addr', 'N/A'),
                    'container_vars': {'swift_vars': swift_vars},
                }

                zone += 1
                if zone % zone_count == 0:
                    zone = 0
        return swift_hosts

    def _configure_swift(self):
        """Configure user variables for swift."""
        ref_arch_list = self.get_ref_arch()

        if SWIFT not in ref_arch_list:
            return

        self._configure_swift_general()
        self._configure_swift_policies()
        self._configure_swift_proxy_hosts()
        self._configure_swift_hosts()

    def get_ref_arch(self):
        return self.gen_dict.get('reference-architecture', [])

    def _do_configure_repo_hosts(self, hosts, hosts_type,
                                 repo_hosts_archs_set):
        """Configure repo hosts of any other architecture if the
           hosts of given host type are of different architecture
           compared to the controller nodes.
        """
        if not hosts:
            return

        for host in hosts:
            hostname = host.get('hostname', None)
            if hostname:
                arch = host.get(ARCHITECTURE, X86_64)
                if arch.lower().startswith(PPC64):
                    arch = PPC64LE
                if arch not in repo_hosts_archs_set:
                    self.user_config[REPO_INFRA_HOSTS][hostname] = \
                        copy.deepcopy(self.user_config[hosts_type][hostname])
                    repo_hosts_archs_set.add(arch)

    def _get_repo_hosts_archs_set(self):
        controllers = self._get_controllers()
        if not controllers:
            return None
        repo_hosts_archs = set()
        for controller in controllers:
            hostname = controller.get('hostname', None)
            if hostname:
                arch = controller.get(ARCHITECTURE, X86_64)
                if arch.lower().startswith(PPC64):
                    arch = PPC64LE
                repo_hosts_archs.add(arch)
        return repo_hosts_archs

    def _configure_extra_repo_hosts(self):
        """Configure repo hosts of any other architecture if the
           hosts (compute nodes, storage nodes, etc) are of different
           architecture compared to the controller nodes.
        """

        # repo_hosts_archs is the set of architectures for which
        # repo container will be created and repo will be built.
        repo_hosts_archs = self._get_repo_hosts_archs_set()
        if not repo_hosts_archs:
            return

        hosts = self._get_compute_hosts()
        self._do_configure_repo_hosts(hosts, COMPUTE_HOSTS, repo_hosts_archs)
        hosts = self._get_swift_proxy_hosts()
        self._do_configure_repo_hosts(hosts, SWIFT_PROXY_HOSTS,
                                      repo_hosts_archs)
        hosts = self._get_swift_ring_hosts()
        self._do_configure_repo_hosts(hosts, SWIFT_HOSTS, repo_hosts_archs)

    def create_user_config(self):
        """Process the inventory input and generate the OSA user config."""
        self._load_yml()
        self._configure_cidr_networks()
        self._configure_infra_hosts()
        self._configure_global_overrides()
        self._configure_compute_hosts()
        self._configure_storage_hosts()
        self._configure_swift()
        self._configure_extra_repo_hosts()

        self._dump_yml(self.user_config, OSA_USER_CFG_FILE)

    def get_network_interface(self, net_details):
        """Find network interface from the given network details."""

        port_keys = ['bond', 'eth-port']
        ext_intf = None
        for port_key in port_keys:
            intf = net_details.get(port_key, None)
            if intf:
                ext_intf = intf
                break

        return ext_intf

    def find_external_network(self, ext_floating_ip, networks):
        """Find external network based on the network address that matches
           external-floating-ipaddr.
           If not found, return the management network interface.

           Returns: network name, network details
        """
        if ext_floating_ip == 'N/A':
            return None

        for net, net_details in networks.iteritems():
            if 'addr' in net_details:
                # Check if matching
                if (netaddr.IPAddress(ext_floating_ip) in
                   netaddr.IPSet([net_details['addr']])):
                    return net, net_details

        return 'openstack-mgmt', networks.get('openstack-mgmt', None)

    def find_external_interface(self, ext_floating_ip, networks):
        """Find external interface based on the network address that matches
           external-floating-ipaddr.
           If not found, return the management network interface.
        """
        if ext_floating_ip == 'N/A':
            return None

        net, net_details = self.find_external_network(ext_floating_ip,
                                                      networks)
        if net_details:
            ext_intf = self.get_network_interface(net_details)
        else:
            mgmt_network = networks.get('openstack-mgmt', None)
            ext_intf = mgmt_network.get('eth-port', None)

        return ext_intf

    def _get_external_vip_value(self):
        external_vip = self.gen_dict.get('external-floating-ipaddr', 'N/A')
        if external_vip != 'N/A' and '/' in external_vip:
            # remove cidr prefix, if exists
            external_vip = external_vip.split('/')[0]
        return external_vip

    def generate_haproxy(self):
        """Generate user variable file for HAProxy."""
        external_vip = self._get_external_vip_value()
        internal_vip = self.gen_dict.get('internal-floating-ipaddr', 'N/A')
        networks = self.gen_dict.get('networks', None)
        mgmt_network = networks.get('openstack-mgmt', None)
        bridge = mgmt_network.get('bridge', None)
        ext_intf = self.find_external_interface(external_vip, networks)
        settings = {
            'haproxy_keepalived_external_vip_cidr': external_vip,
            'haproxy_keepalived_internal_vip_cidr': internal_vip,
            'haproxy_keepalived_external_interface': ext_intf,
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

    def generate_rabbitmq(self):
        """Generate user variable file for rabbitmq."""
        settings = {
            # Disable rabbitmq management plugin by default
            'rabbitmq_plugins': [{
                'name': 'rabbitmq_management', 'state': 'disabled'
            }]
        }
        self._dump_yml(settings, OSA_USER_VAR_RABBITMQ)

    def generate_ceph(self):
        """Generate user variable file for ceph."""
        if PRIVATE_COMPUTE_CLOUD not in self.get_ref_arch():
            return

        nodes = self.gen_dict.get('nodes', None)
        if not nodes:
            return

        mons = self._get_ceph_monitors()
        if not mons:
            return

        monitors = []
        for c in mons:
            monitors.append(c.get('openstack-stg-addr', 'N/A'))

        settings = {
            'ceph_pkg_source': 'uca',
            'glance_default_store': 'rbd',
            'glance_rbd_store_pool': 'images',
            'nova_libvirt_images_rbd_pool': 'vms',
            'ceph_mons': monitors,
        }

        self._dump_yml(settings, OSA_USER_VAR_CEPH)

    def _get_ceph_monitors(self):
        # Get ceph monitors by template name
        nodes = self.gen_dict.get('nodes', {})
        mons = []
        mons.extend(nodes.get('ceph-monitor', []))

        # Get ceph monitors by role
        role_mons = self._get_nodes_through_roles('ceph-monitor')
        for mon in role_mons:
            if mon not in mons:
                mons.append(mon)
        if mons:
            return mons

        # If no nodes were found using the ceph-monitor role, we
        # return the controller nodes for backward compatibility with
        # configurations that assumed the ceph monitors were controllers.
        # The implication here is that if node templates are using the
        # ceph-monitor role then the 'controllers' node template will not be
        # automatically added as a monitor node.
        return self._get_controllers()

    def define_no_proxy(self, env_vars_dict):
        """ Define the variable 'no_proxy' if not already defined and
            append the required addresses to it if missing. """
        internal_lb_addr = self.user_config['global_overrides'][
            'internal_lb_vip_address']
        external_lb_addr = self.user_config['global_overrides'][
            'external_lb_vip_address']
        required_addresses = ["localhost", "127.0.0.1",
                              internal_lb_addr, external_lb_addr]
        no_proxy_value = env_vars_dict.get('no_proxy')
        if not no_proxy_value:
            env_vars_dict['no_proxy'] = ",".join(required_addresses)
        else:
            addresses = no_proxy_value.split(",")
            changed = False
            for addr in required_addresses:
                if addr not in addresses:
                    addresses.append(addr)
                    changed = True
            if changed:
                env_vars_dict['no_proxy'] = ','.join(addresses)

    def generate_deployment_env_vars(self):
        """Generate user variable file for deployment environment variables."""
        env_vars_dict = self.gen_dict.get('deployment-environment')
        if env_vars_dict:
            if 'http_proxy' in env_vars_dict or 'https_proxy' in env_vars_dict:
                # Make sure no_proxy is defined and has the required
                # addresses
                self.define_no_proxy(env_vars_dict)
            settings = {
                'deployment_environment_variables': env_vars_dict
            }
            self._dump_yml(settings, OSA_USER_VAR_DEPLOY_ENV)


def process_inventory(inv_name, output_dir):
    """Process the input inventory file.

    :param inv_name: The path name of the input genesis inventory.
    :param output_dir: The name of path for the generated files.
    """
    generator = OSAFileGenerator(inv_name, output_dir)
    generator._load_yml()
    if 'reference-architecture' not in generator.gen_dict:
        print "The inventory file is missing the reference-architecture."
        sys.exit(1)

    generator.create_user_config()
    generator.generate_haproxy()
    generator.generate_ceilometer()
    generator.generate_ceph()
    generator.generate_deployment_env_vars()


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
