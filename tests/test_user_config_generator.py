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

import os
from os import path
import sys

import mock
import unittest
import yaml

TOP_DIR = path.join(os.getcwd(), path.dirname(__file__), '..')
SCRIPT_DIR = 'osa/scripts'
sys.path.append(path.join(TOP_DIR, SCRIPT_DIR))

import generate_user_config as guc

# Shared sequence of host service keys
COMMON_HOST_SERVICES = (
    'shared-infra_hosts',
    'os-infra_hosts',
    'repo-infra_hosts',
    'identity_hosts',
    'storage-infra_hosts',
    'network_hosts',
    'haproxy_hosts',
    'log_hosts'
)


class TestOFGBasics(unittest.TestCase):

    def test_init(self):
        ofg = guc.OSAFileGenerator('input-file', 'output-dir')
        self.assertEqual('input-file', ofg.inventory_name)
        self.assertEqual('output-dir', ofg.output_dir)
        self.assertEqual({}, ofg.gen_dict)
        self.assertEqual({}, ofg.user_config)

    def test__load_yml(self):
        ofg = guc.OSAFileGenerator('input-file', 'output-dir')
        open_name = 'generate_user_config.open'
        m = mock.mock_open(read_data='nodes:\n  host1:\n    key: value')
        with mock.patch(open_name, m, create=True) as mock_open:
            ofg._load_yml()

        mock_open.assert_called_once_with('input-file', 'r')
        self.assertEqual({'nodes': {'host1': {'key': 'value'}}}, ofg.gen_dict)

    def test__load_yml_invalid(self):
        ofg = guc.OSAFileGenerator('input-file', 'output-dir')
        open_name = 'generate_user_config.open'
        m = mock.mock_open(read_data='nodes: host1: key: value')
        with mock.patch(open_name, m, create=True) as mock_open:
            self.assertRaises(yaml.YAMLError, ofg._load_yml)

        mock_open.assert_called_once_with('input-file', 'r')

    @mock.patch.object(yaml, 'dump')
    def test__dump_yml(self, mock_dump):
        ofg = guc.OSAFileGenerator('input-file', 'output-dir')
        open_name = 'generate_user_config.open'
        m = mock.mock_open()
        data = mock.Mock()
        with mock.patch(open_name, m, create=True) as mock_open:
            ofg._dump_yml(data, 'filename')

        mock_open.assert_called_once_with('output-dir/filename', 'w')
        mock_dump.assert_called_once_with(data, m(), default_flow_style=False,
                                          explicit_start=True)

    @mock.patch.object(yaml, 'dump')
    def test__dump_yml_with_exception(self, mock_dump):
        ofg = guc.OSAFileGenerator('input-file', 'output-dir')
        mock_dump.side_effect = yaml.YAMLError
        open_name = 'generate_user_config.open'
        m = mock.mock_open()
        data = mock.Mock()
        with mock.patch(open_name, m, create=True) as mock_open:
            self.assertRaises(yaml.YAMLError,
                              ofg._dump_yml, data, 'filename')

        mock_open.assert_called_once_with('output-dir/filename', 'w')


class TestCIDRNetworks(unittest.TestCase):
    def setUp(self):
        super(TestCIDRNetworks, self).setUp()
        self.ofg = guc.OSAFileGenerator('input-file', 'output-dir')

    def test_get_normal(self):
        self.ofg.gen_dict = {
            'networks': {
                'openstack-mgmt': {
                    'addr': '1.2.3.4/20'
                },
                'openstack-stg': {
                    'addr': '2.3.4.5/20'
                },
                'openstack-tenant-vxlan': {
                    'addr': '3.4.5.6/20'
                }
            }
        }

        self.ofg._configure_cidr_networks()
        result = self.ofg.user_config

        self.assertIn('cidr_networks', result)
        networks = result['cidr_networks']
        self.assertIn('container', networks)
        self.assertIn('storage', networks)
        self.assertIn('tunnel', networks)
        self.assertEqual('1.2.3.4/20', networks['container'])
        self.assertEqual('2.3.4.5/20', networks['storage'])
        self.assertEqual('3.4.5.6/20', networks['tunnel'])

    def test_get_missing_networks(self):
        self.ofg.gen_dict = {
            'nteworks': {  # should be 'networks'
                'openstack-mgmt': {
                    'addr': '1.2.3.4/20'
                },
                'openstack-stg': {
                    'addr': '2.3.4.5/20'
                },
                'openstack-tenant-vxlan': {
                    'addr': '3.4.5.6/20'
                }
            }
        }

        self.ofg._configure_cidr_networks()
        self.assertNotIn('cidr_networks', self.ofg.user_config)

    def test_get_missing_mgmt_network(self):
        self.ofg.gen_dict = {
            'networks': {
                'openstack-mgmt-net': {  # should be 'openstack-mgmt'
                    'addr': '1.2.3.4/20'
                },
                'openstack-stg': {
                    'addr': '2.3.4.5/20'
                },
                'openstack-tenant-vxlan': {
                    'addr': '3.4.5.6/20'
                }
            }
        }

        self.ofg._configure_cidr_networks()
        result = self.ofg.user_config

        self.assertIn('cidr_networks', result)
        networks = result['cidr_networks']
        self.assertNotIn('container', networks)
        self.assertIn('storage', networks)
        self.assertIn('tunnel', networks)

    def test_get_missing_storage_network(self):
        self.ofg.gen_dict = {
            'networks': {
                'openstack-mgmt': {
                    'addr': '1.2.3.4/20'
                },
                'openstack-storage': {  # should be 'openstack-stg'
                    'addr': '2.3.4.5/20'
                },
                'openstack-tenant-vxlan': {
                    'addr': '3.4.5.6/20'
                }
            }
        }

        self.ofg._configure_cidr_networks()
        result = self.ofg.user_config

        self.assertIn('cidr_networks', result)
        networks = result['cidr_networks']
        self.assertIn('container', networks)
        self.assertNotIn('storage', networks)
        self.assertIn('tunnel', networks)

    def test_get_missing_tunnel_network(self):
        self.ofg.gen_dict = {
            'networks': {
                'openstack-mgmt': {
                    'addr': '1.2.3.4/20'
                },
                'openstack-stg': {
                    'addr': '2.3.4.5/20'
                },
                'openstack-tenant-vxLAN': {  # should be 'open....-vxlan'
                    'addr': '3.4.5.6/20'
                }
            }
        }

        self.ofg._configure_cidr_networks()
        result = self.ofg.user_config

        self.assertIn('cidr_networks', result)
        networks = result['cidr_networks']
        self.assertIn('container', networks)
        self.assertIn('storage', networks)
        self.assertNotIn('tunnel', networks)

    def test_get_not_valid_network(self):
        self.ofg.gen_dict = {
            'networks': {}
        }

        self.ofg._configure_cidr_networks()
        self.assertNotIn('cidr_networks', self.ofg.user_config)


class TestConfigureInfraHosts(unittest.TestCase):
    def setUp(self):
        super(TestConfigureInfraHosts, self).setUp()
        self.ofg = guc.OSAFileGenerator('input-file', 'output-dir')

    def test_normal(self):
        self.ofg.gen_dict = {
            'nodes': {
                'controllers': [
                    {
                        'hostname': 'host1',
                        'openstack-mgmt-addr': '11.22.33.44',
                    },
                    {
                        'hostname': 'host2',
                        'openstack-mgmt-addr': '55.66.77.88',
                    }
                ]
            }
        }

        self.ofg._configure_infra_hosts()
        result = self.ofg.user_config

        expected = {
            'host1': {
                'ip': '11.22.33.44',
            },
            'host2': {
                'ip': '55.66.77.88',
            }
        }

        for svc in COMMON_HOST_SERVICES:
            self.assertIn(svc, result)
            self.assertEqual(expected, result[svc])

    def test_nodes_not_found(self):
        self.ofg.gen_dict = {
            'hosts': {  # mistakenly used 'hosts'
                'controllers': [
                    {
                        'hostname': 'host1',
                        'openstack-mgmt-addr': '11.22.33.44',
                    },
                    {
                        'hostname': 'host2',
                        'openstack-mgmt-addr': '55.66.77.88',
                    }
                ]
            }
        }

        self.ofg._configure_infra_hosts()
        self.assertEqual({}, self.ofg.user_config)

    def test_controllers_not_found(self):
        self.ofg.gen_dict = {
            'nodes': {
                'hosts': [  # mistakenly used 'hosts'
                    {
                        'hostname': 'host1',
                        'openstack-mgmt-addr': '11.22.33.44',
                    },
                    {
                        'hostname': 'host2',
                        'openstack-mgmt-addr': '55.66.77.88',
                    }
                ]
            }
        }

        self.ofg._configure_infra_hosts()

        self.assertEqual({}, self.ofg.user_config)

    def test_hostname_not_found(self):
        self.ofg.gen_dict = {
            'nodes': {
                'controllers': [
                    {
                        'host_name': 'host1',  # incorrect key, ignored
                        'openstack-mgmt-addr': '11.22.33.44',
                    },
                    {
                        'hostname': 'host2',
                        'openstack-mgmt-addr': '55.66.77.88',
                    }
                ]
            }
        }

        self.ofg._configure_infra_hosts()
        result = self.ofg.user_config

        expected = {
            'host2': {
                'ip': '55.66.77.88',
            }
        }
        for svc in COMMON_HOST_SERVICES:
            self.assertIn(svc, result)
            self.assertEqual(expected, result[svc])

    def test_mgmt_addr_not_found(self):
        self.ofg.gen_dict = {
            'nodes': {
                'controllers': [
                    {
                        'hostname': 'host1',
                        'openstack-mgmt': '11.22.33.44',  # incorrect key
                    },
                    {
                        'hostname': 'host2',
                        'openstack-mgmt-addr': '55.66.77.88',
                    }
                ]
            }
        }

        self.ofg._configure_infra_hosts()
        result = self.ofg.user_config

        expected = {
            'host1': {
                'ip': 'N/A',
            },
            'host2': {
                'ip': '55.66.77.88',
            }
        }

        for svc in COMMON_HOST_SERVICES:
            self.assertIn(svc, result)
            self.assertEqual(expected, result[svc])


class TestConfigureGlobalOverrides(unittest.TestCase):
    def setUp(self):
        super(TestConfigureGlobalOverrides, self).setUp()
        self.ofg = guc.OSAFileGenerator('input-file', 'output-dir')

    def test_normal(self):
        self.ofg.gen_dict = {
            'internal-floating-ipaddr': '11.22.33.44/22',
            'external-floating-ipaddr': '22.33.44.55/22',
            'networks': {
                'openstack-mgmt': {
                    'bridge': 'br-mgmt',
                    'eth-port': 'eth0',
                },
                'openstack-stg': {
                    'bridge': 'br-stg',
                    'eth-port': 'eth1',
                },
                'openstack-tenant-vxlan': {
                    'bridge': 'br-vxlan',
                    'eth-port': 'eth10',
                },
                'openstack-tenant-vlan': {
                    'bridge': 'br-vlan',
                    'eth-port': 'eth11',
                }
            },
            'nodes': {
                'controllers': [
                    {
                        'hostname': 'host1',
                        'openstack-mgmt-addr': '11.22.33.44',
                        'external1-addr': '55.66.77.88',
                    },
                    {
                        'hostname': 'ignored',
                        'openstack-mgmt-addr': 'ignored',
                    }
                ]
            }
        }

        self.ofg._configure_global_overrides()
        result = self.ofg.user_config

        overrides = result['global_overrides']
        self.assertEqual('11.22.33.44', overrides['internal_lb_vip_address'])
        self.assertEqual('22.33.44.55', overrides['external_lb_vip_address'])
        self.assertEqual('br-vxlan', overrides['tunnel_bridge'])
        self.assertEqual('br-mgmt', overrides['management_bridge'])

        provider_networks = overrides['provider_networks']

        # verify management network
        mgmt_network = {
            'network': {
                'container_bridge': 'br-mgmt',
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
        }
        self.assertEqual(mgmt_network, provider_networks[0])

        # verify storage network
        storage_network = {
            'network': {
                'container_bridge': 'br-stg',
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
        }
        self.assertEqual(storage_network, provider_networks[1])

        # verify tunnel (vxlan) network
        vxlan_network = {
            'network': {
                'container_bridge': 'br-vxlan',
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
        }
        self.assertEqual(vxlan_network, provider_networks[2])

        # verify vlan network
        vlan_network = {
            'network': {
                'container_bridge': 'br-vlan',
                'container_type': 'veth',
                'container_interface': 'eth11',
                'type': 'vlan',
                'range': '1:1',
                'net_name': 'vlan',
                'group_binds': [
                    'neutron_linuxbridge_agent',
                ],
            }
        }
        self.assertEqual(vlan_network, provider_networks[3])

        # verify vlan flat network
        vlan_flat_network = {
            'network': {
                'container_bridge': 'br-vlan',
                'container_type': 'veth',
                'container_interface': 'eth12',
                'host_bind_override': 'veth12',
                'type': 'flat',
                'net_name': 'external',
                'group_binds': [
                    'neutron_linuxbridge_agent',
                ],
            }
        }
        self.assertEqual(vlan_flat_network, provider_networks[4])

    def test_nodes_not_found(self):
        self.ofg.gen_dict = {
            'hosts': {  # mistakenly used 'hosts'
                'controllers': [
                    {
                        'hostname': 'host1',
                        'openstack-mgmt-addr': '11.22.33.44',
                    },
                    {
                        'hostname': 'host2',
                        'openstack-mgmt-addr': '55.66.77.88',
                    }
                ]
            }
        }

        self.ofg._configure_global_overrides()
        self.assertEqual({}, self.ofg.user_config)

    def test_controllers_not_found(self):
        self.ofg.gen_dict = {
            'nodes': {
                'hosts': [  # should be 'controllers'
                    {
                        'hostname': 'host1',
                        'openstack-mgmt-addr': '11.22.33.44',
                    },
                    {
                        'hostname': 'host2',
                        'openstack-mgmt-addr': '55.66.77.88',
                    }
                ]
            }
        }

        self.ofg._configure_global_overrides()
        self.assertEqual({}, self.ofg.user_config)

    def test_networks_not_found(self):
        self.ofg.gen_dict = {
            'network': {  # should be 'networks'
                'openstack-mgmt': {
                    'foo': 'bar'
                }
            },
            'nodes': {
                'controllers': [
                    {
                        'hostname': 'host1',
                        'openstack-mgmt-addr': '11.22.33.44',
                    },
                    {
                        'hostname': 'host2',
                        'openstack-mgmt-addr': '55.66.77.88',
                    }
                ]
            }
        }

        self.ofg._configure_global_overrides()
        self.assertEqual({}, self.ofg.user_config)

    def test_interfaces_not_specified(self):
        self.ofg.gen_dict = {
            'internal-floating-ipaddr': '11.22.33.44/22',
            'networks': {
                'openstack-mgmt': {
                    'bridge': 'br-mgmt',
                },
                'openstack-stg': {
                    'bridge': 'br-stg',
                },
                'openstack-tenant-vxlan': {
                    'bridge': 'br-tunnel',
                },
                'openstack-tenant-vlan': {
                    'bridge': 'br-vlan',
                }
            },
            'nodes': {
                'controllers': [
                    {
                        'hostname': 'host1',
                        'openstack-mgmt-addr': '11.22.33.44',
                    },
                    {
                        'hostname': 'not used',
                        'openstack-mgmt-addr': 'ignored',
                    }
                ]
            }
        }

        self.ofg._configure_global_overrides()
        result = self.ofg.user_config

        overrides = result['global_overrides']
        self.assertEqual('11.22.33.44', overrides['internal_lb_vip_address'])
        self.assertEqual('N/A', overrides['external_lb_vip_address'])
        self.assertEqual('br-tunnel', overrides['tunnel_bridge'])
        self.assertEqual('br-mgmt', overrides['management_bridge'])

        provider_networks = overrides['provider_networks']

        # verify management network
        mgmt_network = {
            'network': {
                'container_bridge': 'br-mgmt',
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
        }
        self.assertEqual(mgmt_network, provider_networks[0])

        # verify storage network
        storage_network = {
            'network': {
                'container_bridge': 'br-stg',
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
        }
        self.assertEqual(storage_network, provider_networks[1])

        # verify tunnel (vxlan) network
        vxlan_network = {
            'network': {
                'container_bridge': 'br-tunnel',
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
        }
        self.assertEqual(vxlan_network, provider_networks[2])

        # verify vlan network
        vlan_network = {
            'network': {
                'container_bridge': 'br-vlan',
                'container_type': 'veth',
                'container_interface': 'eth11',
                'type': 'vlan',
                'range': '1:1',
                'net_name': 'vlan',
                'group_binds': [
                    'neutron_linuxbridge_agent',
                ],
            }
        }
        self.assertEqual(vlan_network, provider_networks[3])

        # verify vlan flat network
        vlan_flat_network = {
            'network': {
                'container_bridge': 'br-vlan',
                'container_type': 'veth',
                'container_interface': 'eth12',
                'host_bind_override': 'veth12',
                'type': 'flat',
                'net_name': 'external',
                'group_binds': [
                    'neutron_linuxbridge_agent',
                ],
            }
        }
        self.assertEqual(vlan_flat_network, provider_networks[4])

    def test_bridges_not_specified(self):
        self.ofg.gen_dict = {
            'internal-floating-ipaddr': '11.22.33.44/22',
            'networks': {
                'openstack-mgmt': {
                    'eth-port': 'eth0',
                },
                'openstack-stg': {
                    'eth-port': 'eth1',
                },
                'openstack-tenant-vxlan': {
                    'eth-port': 'eth10',
                },
                'openstack-tenant-vlan': {
                    'eth-port': 'eth11',
                }
            },
            'nodes': {
                'controllers': [
                    {
                        'hostname': 'host1',
                        'openstack-mgmt-addr': '11.22.33.44',
                    },
                    {
                        'hostname': 'not used',
                        'openstack-mgmt-addr': 'ignored',
                    }
                ]
            }
        }

        self.ofg._configure_global_overrides()
        result = self.ofg.user_config

        overrides = result['global_overrides']
        self.assertEqual('11.22.33.44', overrides['internal_lb_vip_address'])
        self.assertEqual('N/A', overrides['external_lb_vip_address'])
        self.assertEqual('N/A', overrides['tunnel_bridge'])
        self.assertEqual('N/A', overrides['management_bridge'])

        provider_networks = overrides['provider_networks']

        # verify management network
        mgmt_network = {
            'network': {
                'container_bridge': 'N/A',
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
        }
        self.assertEqual(mgmt_network, provider_networks[0])

        # verify storage network
        storage_network = {
            'network': {
                'container_bridge': 'N/A',
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
        }
        self.assertEqual(storage_network, provider_networks[1])

        # verify tunnel (vxlan) network
        vxlan_network = {
            'network': {
                'container_bridge': 'N/A',
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
        }
        self.assertEqual(vxlan_network, provider_networks[2])

        # verify vlan network
        vlan_network = {
            'network': {
                'container_bridge': 'N/A',
                'container_type': 'veth',
                'container_interface': 'eth11',
                'type': 'vlan',
                'range': '1:1',
                'net_name': 'vlan',
                'group_binds': [
                    'neutron_linuxbridge_agent',
                ],
            }
        }
        self.assertEqual(vlan_network, provider_networks[3])

        # verify vlan flat network
        vlan_flat_network = {
            'network': {
                'container_bridge': 'N/A',
                'container_type': 'veth',
                'container_interface': 'eth12',
                'host_bind_override': 'veth12',
                'type': 'flat',
                'net_name': 'external',
                'group_binds': [
                    'neutron_linuxbridge_agent',
                ],
            }
        }
        self.assertEqual(vlan_flat_network, provider_networks[4])

    def test_lb_address_not_specified(self):
        self.ofg.gen_dict = {
            'networks': {
                'openstack-mgmt': {},
                'openstack-stg': {},
                'openstack-tenant-vxlan': {},
                'openstack-tenant-vlan': {}
            },
            'nodes': {
                'controllers': [
                    {
                        'hostname': 'host1',
                        'mgmt-addr': '11.22.33.44',
                    }
                ]
            }
        }

        self.ofg._configure_global_overrides()
        result = self.ofg.user_config

        # only verify lb values here, others are covered in different tests
        overrides = result['global_overrides']
        self.assertEqual('N/A', overrides['internal_lb_vip_address'])
        self.assertEqual('N/A', overrides['external_lb_vip_address'])


class TestConfigureComputeHosts(unittest.TestCase):
    def setUp(self):
        super(TestConfigureComputeHosts, self).setUp()
        self.ofg = guc.OSAFileGenerator('input-file', 'output-dir')

    def test_normal(self):
        self.ofg.gen_dict = {
            'nodes': {
                'compute': [
                    {
                        'hostname': 'host1',
                        'openstack-mgmt-addr': '11.22.33.44',
                    },
                    {
                        'hostname': 'host2',
                        'openstack-mgmt-addr': '55.66.77.88',
                    }
                ]
            }
        }

        self.ofg._configure_compute_hosts()
        result = self.ofg.user_config

        self.assertIn('compute_hosts', result)
        compute_hosts = result['compute_hosts']
        self.assertIn('host1', compute_hosts)
        self.assertEqual({'ip': '11.22.33.44'}, compute_hosts['host1'])
        self.assertIn('host2', compute_hosts)
        self.assertEqual({'ip': '55.66.77.88'}, compute_hosts['host2'])

    def test_nodes_not_found(self):
        self.ofg.gen_dict = {
            'hosts': {  # mistakenly used 'hosts'
                'compute': [
                    {
                        'hostname': 'host1',
                        'openstack-mgmt-addr': '11.22.33.44',
                    },
                    {
                        'hostname': 'host2',
                        'openstack-mgmt-addr': '55.66.77.88',
                    }
                ]
            }
        }

        self.ofg._configure_compute_hosts()
        self.assertEqual({}, self.ofg.user_config)

    def test_compute_not_found(self):
        self.ofg.gen_dict = {
            'nodes': {
                'hosts': [  # mistakenly used 'hosts'
                    {
                        'hostname': 'host1',
                        'openstack-mgmt-addr': '11.22.33.44',
                    },
                    {
                        'hostname': 'host2',
                        'openstack-mgmt-addr': '55.66.77.88',
                    }
                ]
            }
        }

        self.ofg._configure_compute_hosts()
        self.assertEqual({}, self.ofg.user_config)

    def test_hostname_not_specified(self):
        self.ofg.gen_dict = {
            'nodes': {
                'compute': [
                    {
                        'host': 'host1',  # will be ignored
                        'openstack-mgmt-addr': '11.22.33.44',
                    },
                    {
                        'hostname': 'host2',
                        'openstack-mgmt-addr': '55.66.77.88',
                    }
                ]
            }
        }

        self.ofg._configure_compute_hosts()

        self.assertIn('compute_hosts', self.ofg.user_config)
        compute_hosts = self.ofg.user_config['compute_hosts']
        expected = {
            'host2': {
                'ip': '55.66.77.88',
            }
        }
        self.assertEqual(expected, compute_hosts)


class TestConfigureStorageHosts(unittest.TestCase):
    def setUp(self):
        super(TestConfigureStorageHosts, self).setUp()
        self.ofg = guc.OSAFileGenerator('input-file', 'output-dir')

    def test_normal(self):
        self.ofg.gen_dict = {
            'nodes': {
                'controllers': [
                    {
                        'hostname': 'host1',
                        'openstack-mgmt-addr': '11.22.33.44',
                    },
                    {
                        'hostname': 'host2',
                        'openstack-mgmt-addr': '55.66.77.88',
                    }
                ]
            }
        }

        self.ofg._configure_storage_hosts()
        result = self.ofg.user_config

        self.assertIn('storage_hosts', result)
        host1 = result['storage_hosts']['host1']
        host2 = result['storage_hosts']['host2']

        hdd_config = {
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

        self.assertEqual('11.22.33.44', host1['ip'])
        cinder_backend1 = host1['container_vars']['cinder_backends']
        self.assertEqual('cinder_volume',
                         cinder_backend1['limit_container_types'])
        self.assertEqual(hdd_config, cinder_backend1['ceph'])

        self.assertEqual('55.66.77.88', host2['ip'])
        cinder_backend2 = host2['container_vars']['cinder_backends']
        self.assertEqual('cinder_volume',
                         cinder_backend2['limit_container_types'])
        self.assertEqual(hdd_config, cinder_backend2['ceph'])

    def test_nodes_not_found(self):
        self.ofg.gen_dict = {
            'hosts': {  # mistakenly used 'hosts'
                'compute': [
                    {
                        'hostname': 'host1',
                        'openstack-stg-addr': '11.22.33.44',
                    },
                    {
                        'hostname': 'host2',
                        'openstack-stg-addr': '55.66.77.88',
                    }
                ]
            }
        }

        self.ofg._configure_storage_hosts()
        self.assertEqual({}, self.ofg.user_config)

    def test_compute_not_found(self):
        self.ofg.gen_dict = {
            'nodes': {
                'hosts': [  # mistakenly used 'hosts'
                    {
                        'hostname': 'host1',
                        'openstack-stg-addr': '11.22.33.44',
                    },
                    {
                        'hostname': 'host2',
                        'openstack-stg-addr': '55.66.77.88',
                    }
                ]
            }
        }

        self.ofg._configure_storage_hosts()
        self.assertEqual({}, self.ofg.user_config)

    def test_storage_addr_not_specified(self):
        self.ofg.gen_dict = {
            'nodes': {
                'controllers': [
                    {
                        'hostname': 'host1',
                        'openstack-stg': '11.22.33.44',  # ignored key
                    },
                    {
                        'hostname': 'host2',
                        'openstack-stg': '55.66.77.88',  # ignored key
                    }
                ]
            }
        }

        self.ofg._configure_storage_hosts()
        result = self.ofg.user_config

        self.assertIn('storage_hosts', result)
        self.assertEqual('N/A', result['storage_hosts']['host1']['ip'])
        self.assertEqual('N/A', result['storage_hosts']['host2']['ip'])

    def test_missing_hostname(self):
        self.ofg.gen_dict = {
            'nodes': {
                'controllers': [
                    {
                        'host_name': 'host1',  # should be 'hostname'
                        'openstack-stg-addr': '11.22.33.44',
                    }
                ]
            }
        }

        self.ofg._configure_storage_hosts()
        result = self.ofg.user_config

        self.assertIn('storage_hosts', result)
        self.assertEqual({}, result['storage_hosts'])


@mock.patch.object(guc.OSAFileGenerator, '_load_yml')
@mock.patch.object(guc.OSAFileGenerator, '_configure_cidr_networks')
@mock.patch.object(guc.OSAFileGenerator, '_configure_infra_hosts')
@mock.patch.object(guc.OSAFileGenerator, '_configure_global_overrides')
@mock.patch.object(guc.OSAFileGenerator, '_configure_compute_hosts')
@mock.patch.object(guc.OSAFileGenerator, '_configure_storage_hosts')
@mock.patch.object(guc.OSAFileGenerator, '_dump_yml')
class TestCreateUserConfig(unittest.TestCase):
    def setUp(self):
        super(TestCreateUserConfig, self).setUp()
        self.ofg = guc.OSAFileGenerator('input-file', 'output-dir')

    def test_normal(self, mock_dump, mock_stg, mock_comp, mock_glb, mock_inf,
                    mock_cidr, mock_load):
        res = self.ofg.create_user_config()

        self.assertIsNone(res)
        mock_load.assert_called_once_with()
        mock_cidr.assert_called_once_with()
        mock_inf.assert_called_once_with()
        mock_glb.assert_called_once_with()
        mock_comp.assert_called_once_with()
        mock_stg.assert_called_once_with()
        mock_dump.assert_called_once_with(
            self.ofg.user_config, 'openstack_user_config.yml')

    def test_data_mutation(self, mock_dump, mock_stg, mock_comp, mock_glb,
                           mock_inf, mock_cidr, mock_load):
        def fake_load():
            self.ofg.user_config = {'load': 'called'}

        def fake_cidr():
            if 'load' in self.ofg.user_config:
                self.ofg.user_config['cidr_networks'] = 'configured'

        def fake_inf():
            if 'cidr_networks' in self.ofg.user_config:
                self.ofg.user_config['infra_hosts'] = 'configured'

        def fake_glb():
            if 'infra_hosts' in self.ofg.user_config:
                self.ofg.user_config['global_overrides'] = 'configured'

        def fake_comp():
            if 'global_overrides' in self.ofg.user_config:
                self.ofg.user_config['compute_hosts'] = 'configured'

        def fake_stg():
            if 'compute_hosts' in self.ofg.user_config:
                self.ofg.user_config['storage_hosts'] = 'configured'

        def fake_dump(data, fname):
            if 'storage_hosts' in self.ofg.user_config:
                self.ofg.user_config['dump'] = 'called'

        mock_load.side_effect = fake_load
        mock_cidr.side_effect = fake_cidr
        mock_inf.side_effect = fake_inf
        mock_glb.side_effect = fake_glb
        mock_comp.side_effect = fake_comp
        mock_stg.side_effect = fake_stg
        mock_dump.side_effect = fake_dump

        res = self.ofg.create_user_config()

        self.assertIsNone(res)
        mock_load.assert_called_once_with()
        mock_cidr.assert_called_once_with()
        mock_inf.assert_called_once_with()
        mock_glb.assert_called_once_with()
        mock_comp.assert_called_once_with()
        mock_stg.assert_called_once_with()
        mock_dump.assert_called_once_with(self.ofg.user_config,
                                          'openstack_user_config.yml')
        expected = {
            'load': 'called',
            'cidr_networks': 'configured',
            'infra_hosts': 'configured',
            'global_overrides': 'configured',
            'compute_hosts': 'configured',
            'storage_hosts': 'configured',
            'dump': 'called',
        }
        self.assertEqual(expected, self.ofg.user_config)


@mock.patch.object(guc.OSAFileGenerator, '_dump_yml')
class TestGenerateHAProxy(unittest.TestCase):

    networks = {
        'openstack-mgmt': {
            'bridge': 'br-mgmt',
            'eth-port': 'eth10'
        }
    }

    def test_generate(self, mock_dump):
        ofg = guc.OSAFileGenerator('input-file', 'output-dir')
        ofg.gen_dict = {
            'internal-floating-ipaddr': '1.2.3.4/22',
            'external-floating-ipaddr': '2.3.4.5/22',
            'networks': self.networks,
        }

        ofg.generate_haproxy()

        expected = {
            'haproxy_keepalived_external_vip_cidr': '2.3.4.5/22',
            'haproxy_keepalived_internal_vip_cidr': '1.2.3.4/22',
            'haproxy_keepalived_external_interface': 'eth10',
            'haproxy_keepalived_internal_interface': 'br-mgmt',
        }
        mock_dump.assert_called_once_with(expected, 'user_var_haproxy.yml')

    def test_generate_missing_inputs(self, mock_dump):
        ofg = guc.OSAFileGenerator('input-file', 'output-dir')
        ofg.gen_dict = {
            'internal-floating-ip-addr': '1.2.3.4',  # mis-spelled key
            'external-floating-ip-addr': '2.3.4.5',  # mis-spelled key
            'networks': self.networks,
        }

        ofg.generate_haproxy()

        expected = {
            'haproxy_keepalived_external_vip_cidr': 'N/A',
            'haproxy_keepalived_internal_vip_cidr': 'N/A',
            'haproxy_keepalived_external_interface': 'eth10',
            'haproxy_keepalived_internal_interface': 'br-mgmt',
        }
        mock_dump.assert_called_once_with(expected, 'user_var_haproxy.yml')


@mock.patch.object(guc.OSAFileGenerator, '_dump_yml')
class TestGenerateCeilometer(unittest.TestCase):

    def test_generate(self, mock_dump):
        ofg = guc.OSAFileGenerator('input-file', 'output-dir')

        ofg.generate_ceilometer()

        expected = {
            'swift_ceilometer_enabled': False,
            'nova_ceilometer_enabled': False,
        }
        mock_dump.assert_called_once_with(expected, 'user_var_ceilometer.yml')


@mock.patch.object(guc.OSAFileGenerator, '_dump_yml')
class TestGenerateCeph(unittest.TestCase):

    def test_generate(self, mock_dump):
        ofg = guc.OSAFileGenerator('input-file', 'output-dir')
        ofg.gen_dict = {
            'nodes': {
                'controllers': [
                    {
                        'openstack-stg-addr': '1.2.3.4'
                    },
                    {
                        'openstack-stg-addr': '5.6.7.8'
                    }
                ]
            }
        }

        ofg.generate_ceph()

        expected = {
            'ceph_pkg_source': 'uca',
            'glance_default_store': 'rbd',
            'glance_rbd_store_pool': 'images',
            'nova_libvirt_images_rbd_pool': 'vms',
            'ceph_mons': [
                '1.2.3.4',
                '5.6.7.8',
            ]
        }
        mock_dump.assert_called_once_with(expected, 'user_var_ceph.yml')

    def test_generate_no_nodes(self, mock_dump):
        ofg = guc.OSAFileGenerator('input-file', 'output-dir')
        # ofg.gen_dict is empty

        ofg.generate_ceph()

        self.assertEqual(0, mock_dump.call_count)

    def test_generate_no_controllers(self, mock_dump):
        ofg = guc.OSAFileGenerator('input-file', 'output-dir')
        # ofg.gen_dict is empty
        ofg.gen_dict = {
            'nodes': {
                'hosts': [  # this key is wrong!!!
                    {
                        'openstack-stg-addr': '1.2.3.4'
                    },
                    {
                        'openstack-stg-addr': '5.6.7.8'
                    }
                ]
            }
        }

        ofg.generate_ceph()

        self.assertEqual(0, mock_dump.call_count)

    def test_generate_no_storage(self, mock_dump):
        ofg = guc.OSAFileGenerator('input-file', 'output-dir')
        # ofg.gen_dict is empty
        ofg.gen_dict = {
            'nodes': {
                'controllers': [
                    {
                        'openstack-mgmt-addr': '1.2.3.4'  # no stg-addr
                    },
                    {
                        'openstack-mgmt-addr': '5.6.7.8'
                    }
                ]
            }
        }

        ofg.generate_ceph()

        expected = {
            'ceph_pkg_source': 'uca',
            'glance_default_store': 'rbd',
            'glance_rbd_store_pool': 'images',
            'nova_libvirt_images_rbd_pool': 'vms',
            'ceph_mons': [
                'N/A',
                'N/A',
            ]
        }
        mock_dump.assert_called_once_with(expected, 'user_var_ceph.yml')


if __name__ == '__main__':
    unittest.main()
