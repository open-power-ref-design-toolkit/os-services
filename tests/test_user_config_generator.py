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

import copy
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

# Common services for the minimum control plane
MIN_CONTROLLER_SERVICES = {
    'shared-infra_hosts',
    'repo-infra_hosts',
    'identity_hosts',
    'dashboard_hosts',
    'haproxy_hosts',
    'log_hosts'
}

# Services added to the control plane for compute clouds
COMPUTE_CONTROLLER_ADDITIONS = {
    'storage-infra_hosts',
    'network_hosts',
    'image_hosts',
    'compute-infra_hosts',
    'orchestration_hosts'
}

COMPUTE_CONTROLLER_SERVICES = (MIN_CONTROLLER_SERVICES |
                               COMPUTE_CONTROLLER_ADDITIONS)

SWIFT_NORMAL_INPUT_DICT = {
    'reference-architecture': ['private-compute-cloud', 'swift'],
    'networks': {
        'openstack-stg': {
            'bridge': 'br-storage',
        },
        'swift-replication': {
            'bridge': 'br-swift-repl',
        },
    },
    'nodes': {
        'swift-proxy': [
            {
                'hostname': 'swiftproxy1',
                'openstack-mgmt-addr': '1.2.3.4',
            },
        ],
        'controllers': [
            {
                'hostname': 'controller1',
                'openstack-mgmt-addr': '1.2.3.9',
            },
        ],
        'swift-metadata': [
            {
                'hostname': 'swiftmetadata1',
                'openstack-mgmt-addr': '1.2.3.5',
                'domain-settings': {
                    'account-ring-disks': [
                        'meta1',
                        'meta2',
                        'meta3',
                    ],
                    'container-ring-disks': [
                        'meta1',
                        'meta2',
                        'meta3',
                    ],
                },
            },
        ],
        'swift-object': [
            {
                'hostname': 'swiftobject1',
                'openstack-mgmt-addr': '1.2.3.6',
                'domain-settings': {
                    'object-ring-disks': [
                        'disk1',
                        'disk2',
                        'disk3',
                    ],
                },
            },
            {
                'hostname': 'swiftobject2',
                'openstack-mgmt-addr': '1.2.3.7',
                'domain-settings': {
                    'object-ring-disks': [
                        'disk1',
                        'disk2',
                        'disk3',
                    ],
                },
            },
            {
                'hostname': 'swiftobject3',
                'openstack-mgmt-addr': '1.2.3.8',
                'domain-settings': {
                    'object-ring-disks': [
                        'disk1',
                        'disk2',
                        'disk3',
                    ],
                },
            },
        ],
    },
}

E_SWIFT_HOSTS = {
    'swiftmetadata1': {
        'ip': '1.2.3.5',
        'container_vars': {
            'swift_vars': {
                'zone': 0,
                'drives': [
                    {'name': 'meta1',
                     'groups': ['account', 'container']},
                    {'name': 'meta2',
                     'groups': ['account', 'container']},
                    {'name': 'meta3',
                     'groups': ['account', 'container']}
                ],
            },
        },
    },
    'swiftobject1': {
        'ip': '1.2.3.6',
        'container_vars': {
            'swift_vars': {
                'zone': 0,
                'drives': [
                    {'name': 'disk1',
                     'groups': ['default']},
                    {'name': 'disk2',
                     'groups': ['default']},
                    {'name': 'disk3',
                     'groups': ['default']},
                ],
            },
        },
    },
    'swiftobject2': {
        'ip': '1.2.3.7',
        'container_vars': {
            'swift_vars': {
                'zone': 1,
                'drives': [
                    {'name': 'disk1',
                     'groups': ['default']},
                    {'name': 'disk2',
                     'groups': ['default']},
                    {'name': 'disk3',
                     'groups': ['default']},
                ],
            },
        },
    },
    'swiftobject3': {
        'ip': '1.2.3.8',
        'container_vars': {
            'swift_vars': {
                'zone': 2,
                'drives': [
                    {'name': 'disk1',
                     'groups': ['default']},
                    {'name': 'disk2',
                     'groups': ['default']},
                    {'name': 'disk3',
                     'groups': ['default']},
                ],
            },
        },
    },
}


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
                },
                'swift-replication': {
                    'addr': '4.5.6.7/20'
                }
            },
            'reference-architecture': ['private-compute-cloud']
        }

        self.ofg._configure_cidr_networks()
        result = self.ofg.user_config

        self.assertIn('cidr_networks', result)
        networks = result['cidr_networks']
        self.assertIn('container', networks)
        self.assertIn('storage', networks)
        self.assertIn('tunnel', networks)
        self.assertIn('swift_repl', networks)
        self.assertEqual('1.2.3.4/20', networks['container'])
        self.assertEqual('2.3.4.5/20', networks['storage'])
        self.assertEqual('3.4.5.6/20', networks['tunnel'])
        self.assertEqual('4.5.6.7/20', networks['swift_repl'])

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
                },
                'swift-replication': {
                    'addr': '4.5.6.7/20'
                }
            },
            'reference-architecture': ['private-compute-cloud']
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
                },
                'swift-replication': {
                    'addr': '4.5.6.7/20'
                }
            },
            'reference-architecture': ['private-compute-cloud']
        }

        self.ofg._configure_cidr_networks()
        result = self.ofg.user_config

        self.assertIn('cidr_networks', result)
        networks = result['cidr_networks']
        self.assertNotIn('container', networks)
        self.assertIn('storage', networks)
        self.assertIn('tunnel', networks)
        self.assertIn('swift_repl', networks)

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
                },
                'swift-replication': {
                    'addr': '4.5.6.7/20'
                }
            },
            'reference-architecture': ['private-compute-cloud']
        }

        self.ofg._configure_cidr_networks()
        result = self.ofg.user_config

        self.assertIn('cidr_networks', result)
        networks = result['cidr_networks']
        self.assertIn('container', networks)
        self.assertNotIn('storage', networks)
        self.assertIn('tunnel', networks)
        self.assertIn('swift_repl', networks)

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
                },
                'swift-replication': {
                    'addr': '4.5.6.7/20'
                }
            },
            'reference-architecture': ['private-compute-cloud']
        }

        self.ofg._configure_cidr_networks()
        result = self.ofg.user_config

        self.assertIn('cidr_networks', result)
        networks = result['cidr_networks']
        self.assertIn('container', networks)
        self.assertIn('storage', networks)
        self.assertNotIn('tunnel', networks)
        self.assertIn('swift_repl', networks)

    def test_get_missing_swift_network(self):
        self.ofg.gen_dict = {
            'networks': {
                'openstack-mgmt': {
                    'addr': '1.2.3.4/20'
                },
                'openstack-stg': {
                    'addr': '2.3.4.5/20'
                },
                'openstack-tenant-vxlan': {  # should be 'open....-vxlan'
                    'addr': '3.4.5.6/20'
                },
                'swift-REPlication': {
                    'addr': '4.5.6.7/20'
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
        self.assertNotIn('swift_repl', networks)

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
            },
            'reference-architecture': ['private-compute-cloud']
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

        for svc in COMPUTE_CONTROLLER_SERVICES:
            self.assertIn(svc, result)
            self.assertEqual(expected, result[svc])

    def test_reference_architectures(self):
        # Test a reference architecture that will produce the minimal
        # control plane set of services
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
            },
            'reference-architecture': ['swift']
        }
        self.ofg._configure_infra_hosts()
        result = self.ofg.user_config
        for svc in MIN_CONTROLLER_SERVICES:
            self.assertIn(svc, result)
        for svc in COMPUTE_CONTROLLER_ADDITIONS:
            self.assertNotIn(svc, result)
        self.assertNotIn('trove-infra_hosts', result)

        # Now test the private compute cloud reference architecture
        self.ofg.gen_dict['reference-architecture'] = ['private-compute-cloud']
        self.ofg._configure_infra_hosts()
        result = self.ofg.user_config
        for svc in COMPUTE_CONTROLLER_SERVICES:
            self.assertIn(svc, result)
        self.assertNotIn('trove-infra_hosts', result)

        # Test the DBaaS reference architecture
        # Now test the private compute cloud reference architecture
        ra = ['private-compute-cloud', 'dbaas']
        self.ofg.gen_dict['reference-architecture'] = ra
        self.ofg._configure_infra_hosts()
        result = self.ofg.user_config
        for svc in COMPUTE_CONTROLLER_SERVICES:
            self.assertIn(svc, result)
        self.assertIn('trove-infra_hosts', result)

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
            },
            'reference-architecture': ['private-compute-cloud']
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
            },
            'reference-architecture': ['private-compute-cloud']
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
            },
            'reference-architecture': ['private-compute-cloud']
        }

        self.ofg._configure_infra_hosts()
        result = self.ofg.user_config

        expected = {
            'host2': {
                'ip': '55.66.77.88',
            }
        }
        for svc in COMPUTE_CONTROLLER_SERVICES:
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
            },
            'reference-architecture': ['private-compute-cloud']
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

        for svc in COMPUTE_CONTROLLER_SERVICES:
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
                    'bridge-port': 'veth12',
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
            },
            'reference-architecture': ['private-compute-cloud']
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
                'range': '1:4094',
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

    def test_ref_arch_not_found(self):
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
            },
            'reference-architecture': ['swift']
        }

        self.ofg._configure_global_overrides()
        result = self.ofg.user_config

        overrides = result['global_overrides']
        self.assertEqual('11.22.33.44', overrides['internal_lb_vip_address'])
        self.assertEqual('22.33.44.55', overrides['external_lb_vip_address'])
        self.assertNotIn('tunnel_bridge', overrides)
        self.assertEqual('br-mgmt', overrides['management_bridge'])

        provider_networks = overrides['provider_networks']

        def _contains_network(provider_networks, bridge_name):
            for network in provider_networks:
                for n in network.values():
                    bridge = n.get('container_bridge')
                    if bridge == bridge_name:
                        return True
            return False

        self.assertTrue(_contains_network(provider_networks, 'br-mgmt'))
        self.assertTrue(_contains_network(provider_networks, 'br-stg'))
        self.assertFalse(_contains_network(provider_networks, 'br-vxlan'))
        self.assertFalse(_contains_network(provider_networks, 'br-vlan'))

    def test_dbaas_mgmt_network(self):
        self.ofg.gen_dict = {
            'internal-floating-ipaddr': '11.22.33.44/22',
            'external-floating-ipaddr': '22.33.44.55/22',
            'networks': {
                'openstack-mgmt': {
                    'bridge': 'br-mgmt',
                    'eth-port': 'eth0',
                    'bridge-port': 'veth-infra'
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
            },
            'reference-architecture': ['private-compute-cloud', 'dbaas']
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
                'type': 'flat',
                'host_bind_override': 'veth-infra',
                'net_name': 'infra',
                'group_binds': [
                    'all_containers',
                    'hosts'
                ],
                'is_container_address': True,
                'is_ssh_address': True
            }
        }
        self.assertEqual(mgmt_network, provider_networks[0])

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
            },
            'reference-architecture': ['private-compute-cloud']
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
            },
            'reference-architecture': ['private-compute-cloud']
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
            },
            'reference-architecture': ['private-compute-cloud']
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
            },
            'reference-architecture': ['private-compute-cloud']
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
                'range': '1:4094',
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
                'host_bind_override': 'eth12',
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
                    'bridge-port': 'veth12',
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
            },
            'reference-architecture': ['private-compute-cloud']
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
                'range': '1:4094',
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
            },
            'reference-architecture': ['private-compute-cloud']
        }

        self.ofg._configure_global_overrides()
        result = self.ofg.user_config

        # only verify lb values here, others are covered in different tests
        overrides = result['global_overrides']
        self.assertEqual('N/A', overrides['internal_lb_vip_address'])
        self.assertEqual('N/A', overrides['external_lb_vip_address'])

    def test_jumbo_frame(self):
        self.ofg.gen_dict = {
            'internal-floating-ipaddr': '11.22.33.44/22',
            'external-floating-ipaddr': '22.33.44.55/22',
            'networks': {
                'openstack-mgmt': {
                    'bridge': 'br-mgmt',
                    'eth-port': 'eth0',
                    'mtu': 9000
                },
                'openstack-stg': {
                    'bridge': 'br-stg',
                    'eth-port': 'eth1',
                    'mtu': 9000
                },
                'openstack-tenant-vxlan': {
                    'bridge': 'br-vxlan',
                    'eth-port': 'eth10',
                    'mtu': 9000
                },
                'openstack-tenant-vlan': {
                    'bridge': 'br-vlan',
                    'eth-port': 'eth11',
                    'bridge-port': 'veth12',
                    'mtu': 9000
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
            },
            'reference-architecture': ['private-compute-cloud']
        }

        self.ofg._configure_global_overrides()
        result = self.ofg.user_config
        overrides = result['global_overrides']

        provider_networks = overrides['provider_networks']

        # Verify networks
        for x in range(5):
            mtu = provider_networks[x]['network'].get('container_mtu')
            self.assertEqual(mtu, 9000,
                             'Network %s does not have the right MTU' % x)

        # Let's verify that not specifying MTU on one network works.
        self.ofg.gen_dict['networks'].get('openstack-tenant-vxlan').pop('mtu')
        self.ofg._configure_global_overrides()
        result = self.ofg.user_config
        overrides = result['global_overrides']
        provider_networks = overrides['provider_networks']
        for x in range(1):
            mtu = provider_networks[x]['network'].get('container_mtu')
            self.assertEqual(mtu, 9000,
                             'Network %s does not have the right MTU' % x)
        mtu = provider_networks[2]['network'].get('container_mtu')
        self.assertEqual(mtu, None)
        for x in range(3, 5):
            mtu = provider_networks[x]['network'].get('container_mtu')
            self.assertEqual(mtu, 9000,
                             'Network %s does not have the right MTU' % x)

    def test_optional_networks(self):
        # Verify the storage, vlan, and vxlan networks are optional.
        # For non private-compute reference architectures
        self.ofg.gen_dict = {
            'internal-floating-ipaddr': '11.22.33.44/22',
            'external-floating-ipaddr': '22.33.44.55/22',
            'networks': {
                'openstack-mgmt': {
                    'bridge': 'br-mgmt',
                    'eth-port': 'eth0',
                    'mtu': 9000
                },
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
            },
            'reference-architecture': ['ceph-standalone']
        }

        self.ofg._configure_global_overrides()
        result = self.ofg.user_config
        overrides = result['global_overrides']
        provider_networks = overrides['provider_networks']
        self.assertEqual(len(provider_networks), 1)
        self.assertEqual(provider_networks[0]['network']['container_bridge'],
                         'br-mgmt')


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
            },
            'reference-architecture': ['private-compute-cloud']
        }

        self.ofg._configure_compute_hosts()
        result = self.ofg.user_config

        self.assertIn('compute_hosts', result)
        compute_hosts = result['compute_hosts']
        self.assertIn('host1', compute_hosts)
        self.assertEqual({'ip': '11.22.33.44'}, compute_hosts['host1'])
        self.assertIn('host2', compute_hosts)
        self.assertEqual({'ip': '55.66.77.88'}, compute_hosts['host2'])

    def test_ref_arch_not_found(self):
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
            },
            'reference-architecture': ['swift']
        }
        self.ofg._configure_compute_hosts()
        self.assertEqual({}, self.ofg.user_config)

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
            },
            'reference-architecture': ['private-compute-cloud']
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
            },
            'reference-architecture': ['private-compute-cloud']
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
            },
            'reference-architecture': ['private-compute-cloud']
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
            },
            'reference-architecture': ['private-compute-cloud']
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
            },
            'reference-architecture': ['private-compute-cloud']
        }

        self.ofg._configure_storage_hosts()
        self.assertEqual({}, self.ofg.user_config)

    def test_ref_arch_not_found(self):
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
            },
            'reference-architecture': ['swift']
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
            },
            'reference-architecture': ['private-compute-cloud']
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
            },
            'reference-architecture': ['private-compute-cloud']
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
            },
            'reference-architecture': ['private-compute-cloud']
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
        'external1': {
            'eth-port': 'eth10',
            'addr': '2.3.4.0/22'
        },
        'openstack-mgmt': {
            'bridge': 'br-mgmt',
            'eth-port': 'eth11'
        }
    }

    networks_bonded = dict(networks)
    networks_bonded.update({
        'external-bond0': {
            'bond': 'osbond0',
            'addr': '5.6.7.0/22'
        }
    })

    def test_generate(self, mock_dump):
        ofg = guc.OSAFileGenerator('input-file', 'output-dir')
        ofg.gen_dict = {
            'internal-floating-ipaddr': '1.2.3.4',
            'external-floating-ipaddr': '2.3.4.5',
            'networks': self.networks,
        }

        ofg.generate_haproxy()

        expected = {
            'haproxy_keepalived_external_vip_cidr': '2.3.4.5',
            'haproxy_keepalived_internal_vip_cidr': '1.2.3.4',
            'haproxy_keepalived_external_interface': 'eth10',
            'haproxy_keepalived_internal_interface': 'br-mgmt',
        }
        mock_dump.assert_called_once_with(expected, 'user_var_haproxy.yml')

    def test_generate_with_bonded_networks(self, mock_dump):
        ofg = guc.OSAFileGenerator('input-file', 'output-dir')
        ofg.gen_dict = {
            'internal-floating-ipaddr': '1.2.3.4',
            'external-floating-ipaddr': '5.6.7.8',
            'networks': self.networks_bonded,
        }

        ofg.generate_haproxy()

        expected = {
            'haproxy_keepalived_external_vip_cidr': '5.6.7.8',
            'haproxy_keepalived_internal_vip_cidr': '1.2.3.4',
            'haproxy_keepalived_external_interface': 'osbond0',
            'haproxy_keepalived_internal_interface': 'br-mgmt',
        }
        mock_dump.assert_called_once_with(expected, 'user_var_haproxy.yml')

    def test_generate_without_matching_network(self, mock_dump):
        """ external-floating-ipaddr not matching with any
            network addr from self.networks_bonded.
        """
        ofg = guc.OSAFileGenerator('input-file', 'output-dir')
        ofg.gen_dict = {
            'internal-floating-ipaddr': '1.2.3.4',
            'external-floating-ipaddr': '3.6.9.3',  # not matching
            'networks': self.networks_bonded,
        }

        ofg.generate_haproxy()

        expected = {
            'haproxy_keepalived_external_vip_cidr': '3.6.9.3',
            'haproxy_keepalived_internal_vip_cidr': '1.2.3.4',
            'haproxy_keepalived_external_interface': 'eth11',
            'haproxy_keepalived_internal_interface': 'br-mgmt',
        }
        mock_dump.assert_called_once_with(expected, 'user_var_haproxy.yml')

    def test_generate_ignore_cidr_prefix(self, mock_dump):
        """ Veify that the cidr prefix in external-floating-ipaddr
            is ignored.
        """
        ofg = guc.OSAFileGenerator('input-file', 'output-dir')
        ofg.gen_dict = {
            'internal-floating-ipaddr': '1.2.3.4',
            'external-floating-ipaddr': '5.6.7.8/22',
            'networks': self.networks_bonded,
        }

        ofg.generate_haproxy()

        expected = {
            'haproxy_keepalived_external_vip_cidr': '5.6.7.8',
            'haproxy_keepalived_internal_vip_cidr': '1.2.3.4',
            'haproxy_keepalived_external_interface': 'osbond0',
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
            'haproxy_keepalived_external_interface': None,
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
            },
            'reference-architecture': ['private-compute-cloud']
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
        ofg.gen_dict = {
            'reference-architecture': ['private-compute-cloud']
        }

        ofg.generate_ceph()
        self.assertEqual(0, mock_dump.call_count)

    def test_generate_no_arch(self, mock_dump):
        ofg = guc.OSAFileGenerator('input-file', 'output-dir')
        ofg.gen_dict = {
            'reference-architecture': ['swift']
        }

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
            },
            'reference-architecture': ['private-compute-cloud']
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
            },
            'reference-architecture': ['private-compute-cloud']
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


class TestConfigureSwift(unittest.TestCase):
    def setUp(self):
        super(TestConfigureSwift, self).setUp()
        self.ofg = guc.OSAFileGenerator('input-file', 'output-dir')
        self.maxDiff = None

    def test_normal(self):
        self.ofg.gen_dict = copy.deepcopy(SWIFT_NORMAL_INPUT_DICT)

        # Expected global_overrides.swift dict.
        e_go_swift = {
            'mount_point': '/srv/node',
            'part_power': 8,
            'storage_network': 'br-storage',
            'repl_network': 'br-swift-repl',
            'storage_policies': [
                {
                    'policy': {
                        'default': 'True',
                        'index': 0,
                        'name': 'default'
                    },
                },
            ],
        }

        # Expected swift-proxy_hosts dict.
        e_proxy_hosts = {
            'swiftproxy1': {
                'ip': '1.2.3.4'
            },
        }

        # Expected swift_hosts dict.
        e_swift_hosts = copy.deepcopy(E_SWIFT_HOSTS)

        self.ofg.user_config['global_overrides'] = {}
        self.ofg.user_config['global_overrides']['swift'] = {}

        self.ofg._configure_swift()
        result = self.ofg.user_config

        go_swift = result['global_overrides']['swift']
        proxy_hosts = result['swift-proxy_hosts']
        swift_hosts = result['swift_hosts']

        self.assertDictEqual(go_swift, e_go_swift)
        self.assertDictEqual(proxy_hosts, e_proxy_hosts)
        self.assertDictEqual(swift_hosts, e_swift_hosts)

    def test_swift_replication_network_not_found(self):

        self.ofg.gen_dict = copy.deepcopy(SWIFT_NORMAL_INPUT_DICT)
        networks = self.ofg.gen_dict.get('networks')
        if networks:
            networks.pop('swift-replication', None)

        # Expected global_overrides.swift dict.
        e_go_swift = {
            'mount_point': '/srv/node',
            'part_power': 8,
            'storage_network': 'br-storage',
            'storage_policies': [
                {
                    'policy': {
                        'default': 'True',
                        'index': 0,
                        'name': 'default'
                    },
                },
            ],
        }

        # Expected swift-proxy_hosts dict.
        e_proxy_hosts = {
            'swiftproxy1': {
                'ip': '1.2.3.4'
            },
        }

        # Expected swift_hosts dict.
        e_swift_hosts = E_SWIFT_HOSTS

        self.ofg.user_config['global_overrides'] = {}
        self.ofg.user_config['global_overrides']['swift'] = {}

        self.ofg._configure_swift()
        result = self.ofg.user_config

        go_swift = result['global_overrides']['swift']
        proxy_hosts = result['swift-proxy_hosts']
        swift_hosts = result['swift_hosts']

        self.assertDictEqual(go_swift, e_go_swift)
        self.assertDictEqual(proxy_hosts, e_proxy_hosts)
        self.assertDictEqual(swift_hosts, e_swift_hosts)

    def test_non_swift_refarch(self):
        self.ofg.gen_dict = {
            'reference-architecture': [
                'private-compute-cloud',    # notice no swift in list
            ],
        }

        self.ofg.user_config['global_overrides'] = {}

        self.ofg._configure_swift()
        result = self.ofg.user_config

        # Refarch specified no swift, so we should not see
        # swift in the output.
        self.assertNotIn('swift', result['global_overrides'])

    def test_valid_swift_minimum_harware_refarch(self):
        self.ofg.gen_dict = copy.deepcopy(SWIFT_NORMAL_INPUT_DICT)

        self.ofg.gen_dict['reference-architecture'] = [
            'swift',
            'swift-minimum-hardware',
        ]

        nodes = self.ofg.gen_dict.get('nodes')
        if nodes:
            nodes.pop('swift-proxy', None)

        # Expected swift-proxy_hosts dict.
        e_proxy_hosts = {
            'controller1': {
                'ip': '1.2.3.9'
            },
        }

        self.ofg._configure_swift_proxy_hosts()
        result = self.ofg.user_config

        proxy_hosts = result['swift-proxy_hosts']
        self.assertDictEqual(proxy_hosts, e_proxy_hosts)

    def test_valid_swift_refarch(self):
        self.ofg.gen_dict = copy.deepcopy(SWIFT_NORMAL_INPUT_DICT)

        self.ofg.gen_dict['reference-architecture'] = [
            'swift',
        ]

        # Expected swift-proxy_hosts dict.
        e_proxy_hosts = {
            'swiftproxy1': {
                'ip': '1.2.3.4'
            },
        }

        self.ofg._configure_swift_proxy_hosts()
        result = self.ofg.user_config

        proxy_hosts = result['swift-proxy_hosts']
        self.assertDictEqual(proxy_hosts, e_proxy_hosts)

    def test_invalid_swift_minimum_harware_refarch(self):
        self.ofg.gen_dict = copy.deepcopy(SWIFT_NORMAL_INPUT_DICT)

        self.ofg.gen_dict['reference-architecture'] = [
            'swift-minimum-hardware',  # swift not in list
        ]

        self.ofg._configure_swift_proxy_hosts()
        result = self.ofg.user_config

        proxy_hosts = result['swift-proxy_hosts']
        self.assertDictEqual({}, proxy_hosts)

    def test_template_vars(self):
        self.ofg.gen_dict = copy.deepcopy(SWIFT_NORMAL_INPUT_DICT)

        self.ofg.gen_dict['node-templates'] = {}
        self.ofg.gen_dict['node-templates']['swift-object'] = {}

        (self.ofg.gen_dict['node-templates']['swift-object']
            ['domain-settings']) = {
                'mount-point': '/alt/srv/node',
                'zone-count': 2
        }

        self.ofg.user_config['global_overrides'] = {}
        self.ofg.user_config['global_overrides']['swift'] = {}

        self.ofg._configure_swift()
        result = self.ofg.user_config

        swift_hosts = result['swift_hosts']

        # Because of the node-templates section we added to the
        # input dictionary, we expect to see the following
        # modifications in the output dictionary.
        e_swift_hosts = copy.deepcopy(E_SWIFT_HOSTS)

        # Mount point for swiftobjectX hosts will be alternate value.
        # Note that swiftmetadata1 is not impacted because it is not
        # part of the swift-object template that was modified.
        for hostname in ('swiftobject1', 'swiftobject2', 'swiftobject3'):
            (e_swift_hosts[hostname]['container_vars']['swift_vars']
                ['mount_point']) = '/alt/srv/node'

        # Zone values for the 3 object nodes should be (0,1,0) not (0,1,2).
        (e_swift_hosts['swiftobject3']['container_vars']['swift_vars']
            ['zone']) = 0

        self.assertDictEqual(swift_hosts, e_swift_hosts)

    def test_converged_metadata(self):
        self.ofg.gen_dict = copy.deepcopy(SWIFT_NORMAL_INPUT_DICT)

        # Remove swift metadata nodes.
        del self.ofg.gen_dict['nodes']['swift-metadata']

        # Add metadata rings to object nodes.
        a_disks = ['meta1', 'meta2', 'meta3']  # account-ring-disks
        c_disks = ['meta1', 'meta2', 'meta3']  # container-ring-disks

        swift_object = self.ofg.gen_dict['nodes']['swift-object']
        for host in swift_object:
            host['domain-settings']['account-ring-disks'] = a_disks
            host['domain-settings']['container-ring-disks'] = c_disks

        self.ofg.user_config['global_overrides'] = {}
        self.ofg.user_config['global_overrides']['swift'] = {}

        self.ofg._configure_swift()
        result = self.ofg.user_config

        swift_hosts = result['swift_hosts']

        # Because of the changes to the input dictionary we expect
        # to see the following modifications in the output dictionary.
        e_swift_hosts = copy.deepcopy(E_SWIFT_HOSTS)

        # Expect swift-metadata to be removed.
        del e_swift_hosts['swiftmetadata1']

        # Expect metadata rings on swift object nodes.
        e_drives = [
            {'name': 'disk1',
             'groups': ['default']},
            {'name': 'disk2',
             'groups': ['default']},
            {'name': 'disk3',
             'groups': ['default']},
            {'name': 'meta1',
             'groups': ['account', 'container']},
            {'name': 'meta2',
             'groups': ['account', 'container']},
            {'name': 'meta3',
             'groups': ['account', 'container']},
        ]

        for hostname in ('swiftobject1', 'swiftobject2', 'swiftobject3'):
            host = e_swift_hosts[hostname]
            host['container_vars']['swift_vars']['drives'] = e_drives

        self.assertDictEqual(swift_hosts, e_swift_hosts)

    def test_account_container_on_separate_disks(self):
        host = {'domain-settings': {'account-ring-disks': ['a', 'b', 'c'],
                                    'container-ring-disks': ['d', 'e', 'f'],
                                    'object-ring-disks': ['g', 'h', 'i']}}
        swift_vars = {}
        self.ofg._configure_swift_host(host, 0, None, swift_vars)
        expected_disks = [{'name': 'a',
                           'groups': ['account']},
                          {'name': 'b',
                           'groups': ['account']},
                          {'name': 'c',
                           'groups': ['account']},
                          {'name': 'd',
                           'groups': ['container']},
                          {'name': 'e',
                           'groups': ['container']},
                          {'name': 'f',
                           'groups': ['container']},
                          {'name': 'g',
                           'groups': ['default']},
                          {'name': 'h',
                           'groups': ['default']},
                          {'name': 'i',
                           'groups': ['default']}]
        self.assertEqual(swift_vars['drives'], expected_disks)

    def test_all_rings_on_same_disks(self):
        host = {'domain-settings': {'account-ring-disks': ['a', 'b', 'c'],
                                    'container-ring-disks': ['a', 'b', 'c'],
                                    'object-ring-disks': ['a', 'b', 'c']}}
        swift_vars = {}
        self.ofg._configure_swift_host(host, 0, None, swift_vars)
        expected_disks = [{'name': 'a',
                           'groups': ['account', 'container', 'default']},
                          {'name': 'b',
                           'groups': ['account', 'container', 'default']},
                          {'name': 'c',
                           'groups': ['account', 'container', 'default']}]
        self.assertEqual(swift_vars['drives'], expected_disks)

    def test_container_account_on_same_disks(self):
        host = {'domain-settings': {'account-ring-disks': ['a', 'b', 'c'],
                                    'container-ring-disks': ['a', 'b', 'c'],
                                    'object-ring-disks': ['d', 'e', 'f']}}
        swift_vars = {}
        self.ofg._configure_swift_host(host, 0, None, swift_vars)
        expected_disks = [{'name': 'a',
                           'groups': ['account', 'container']},
                          {'name': 'b',
                           'groups': ['account', 'container']},
                          {'name': 'c',
                           'groups': ['account', 'container']},
                          {'name': 'd',
                           'groups': ['default']},
                          {'name': 'e',
                           'groups': ['default']},
                          {'name': 'f',
                           'groups': ['default']}]
        self.assertEqual(swift_vars['drives'], expected_disks)

if __name__ == '__main__':
    unittest.main()
