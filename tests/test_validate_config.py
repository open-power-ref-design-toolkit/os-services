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

import copy
import os
from os import path
import sys

import mock
import unittest

TOP_DIR = path.join(os.getcwd(), path.dirname(__file__), '..')
SCRIPT_DIR = 'scripts'
sys.path.append(path.join(TOP_DIR, SCRIPT_DIR))

import validate_config as test_mod


class TestValidateConfig(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_validate_reference_architecture(self):
        inv = {}
        # Test no ref arch
        self.assertRaises(test_mod.UnsupportedConfig,
                          test_mod.validate_reference_architecture,
                          inv)

        # test no base
        inv['reference-architecture'] = ["these aren't the droids you're "
                                         "looking for"]
        self.assertRaises(test_mod.UnsupportedConfig,
                          test_mod.validate_reference_architecture,
                          inv)

        # test dbaas w/o private compute base
        inv['reference-architecture'] = ['dbaas']
        self.assertRaises(test_mod.UnsupportedConfig,
                          test_mod.validate_reference_architecture,
                          inv)

        # DBaaS, with swift
        inv['reference-architecture'] = ['swift', 'dbaas']
        self.assertRaises(test_mod.UnsupportedConfig,
                          test_mod.validate_reference_architecture,
                          inv)

        # test min hardware, no base
        inv['reference-architecture'] = ['swift-minimum-hardware']
        self.assertRaises(test_mod.UnsupportedConfig,
                          test_mod.validate_reference_architecture,
                          inv)

        # test min hardware, with swift
        inv['reference-architecture'] = ['swift-minimum-hardware', 'swift']
        test_mod.validate_reference_architecture(inv)

        # test min hardware, with private cloud
        inv['reference-architecture'] = ['swift-minimum-hardware',
                                         'swift',
                                         'private-compute-cloud']
        test_mod.validate_reference_architecture(inv)

        # test ceph standalone with private cloud
        inv['reference-architecture'] = ['ceph-standalone',
                                         'private-compute-cloud']
        self.assertRaises(test_mod.UnsupportedConfig,
                          test_mod.validate_reference_architecture,
                          inv)

        # Test ceph standalone
        inv['reference-architecture'] = ['ceph-standalone']
        test_mod.validate_reference_architecture(inv)

        # Test base refs by themselves and together
        inv['reference-architecture'] = ['private-compute-cloud']
        test_mod.validate_reference_architecture(inv)

        inv['reference-architecture'] = ['private-compute-cloud', 'swift']
        test_mod.validate_reference_architecture(inv)

        inv['reference-architecture'] = ['private-compute-cloud', 'dbaas']
        test_mod.validate_reference_architecture(inv)

        # Test base refs by themselves and together
        inv['reference-architecture'] = ['swift']
        test_mod.validate_reference_architecture(inv)

    @mock.patch.object(test_mod, '_has_converged_metadata_object')
    @mock.patch.object(test_mod, '_has_separate_metadata_object')
    def test_validate_swift(self, separate, converged):

        # Test minimum hardware options
        inv = {'reference-architecture': ['swift', 'swift-minimum-hardware'],
               'node-templates': {'swift-proxy': {}}}
        self.assertRaises(test_mod.UnsupportedConfig,
                          test_mod.validate_swift,
                          inv)

        converged.return_value = False
        inv['node-templates'].pop('swift-proxy')
        self.assertRaises(test_mod.UnsupportedConfig,
                          test_mod.validate_swift,
                          inv)

        converged.return_value = True
        test_mod.validate_swift(inv)

        # Test non-minimum configs
        inv['node-templates'] = {'swift-proxy': {}}
        inv['reference-architecture'] = ['swift']
        converged.return_value = True
        separate.return_value = False
        test_mod.validate_swift(inv)

        converged.return_value = False
        separate.return_value = True
        test_mod.validate_swift(inv)

        # This one isn't really valid but the converged vs separate
        # method themselves check for this.
        converged.return_value = True
        separate.return_value = True
        test_mod.validate_swift(inv)

        converged.return_value = False
        separate.return_value = False
        self.assertRaises(test_mod.UnsupportedConfig,
                          test_mod.validate_swift,
                          inv)

    def test_has_converged_metadata_object(self):
        node_tmpl = {}
        inv = {'node-templates': node_tmpl}

        # Test good case first
        ds = {'account-ring-devices': [],
              'container-ring-devices': [],
              'object-ring-devices': []}
        node_tmpl['swift-object'] = {'domain-settings': ds}
        self.assertTrue(test_mod._has_converged_metadata_object(inv))

        # Test missing services
        ds = {'account-ring-devices': []}
        node_tmpl['swift-object'] = {'domain-settings': ds}
        self.assertFalse(test_mod._has_converged_metadata_object(inv))

        ds = {'account-ring-devices': [],
              'container-ring-devices': []}
        node_tmpl['swift-object'] = {'domain-settings': ds}
        self.assertFalse(test_mod._has_converged_metadata_object(inv))

        ds = {'account-ring-devices': [],
              'object-ring-devices': []}
        node_tmpl['swift-object'] = {'domain-settings': ds}
        self.assertFalse(test_mod._has_converged_metadata_object(inv))

        # Test swift-metadata in the mix
        ds = {'account-ring-devices': [],
              'container-ring-devices': [],
              'object-ring-devices': []}
        node_tmpl['swift-metadata'] = {'domain-settings': ds}
        self.assertFalse(test_mod._has_converged_metadata_object(inv))

    def test_has_separate_metadata_object(self):
        node_tmpl = {}
        inv = {'node-templates': node_tmpl}

        # Test good case first
        obj_ds = {'object-ring-devices': []}
        node_tmpl['swift-object'] = {'domain-settings': obj_ds}
        meta_ds = {'account-ring-devices': [],
                   'container-ring-devices': []}
        node_tmpl['swift-metadata'] = {'domain-settings': meta_ds}
        self.assertTrue(test_mod._has_separate_metadata_object(inv))

        # Test missing metadata services
        obj_ds = {'object-ring-devices': []}
        node_tmpl['swift-object'] = {'domain-settings': obj_ds}
        meta_ds = {'account-ring-devices': []}
        node_tmpl['swift-metadata'] = {'domain-settings': meta_ds}
        self.assertFalse(test_mod._has_separate_metadata_object(inv))

        # Test missing metadata template
        ds = {'account-ring-devices': [],
              'container-ring-devices': []}
        node_tmpl['swift-object'] = {'domain-settings': ds}
        self.assertFalse(test_mod._has_separate_metadata_object(inv))

        # Test missing swift-object template
        meta_ds = {'account-ring-devices': [],
                   'container-ring-devices': []}
        node_tmpl['swift-metadata'] = {'domain-settings': meta_ds}
        self.assertFalse(test_mod._has_separate_metadata_object(inv))

        # Test missing object ring
        obj_ds = {}
        node_tmpl['swift-object'] = {'domain-settings': obj_ds}
        meta_ds = {'account-ring-devices': [],
                   'container-ring-devices': []}
        node_tmpl['swift-metadata'] = {'domain-settings': meta_ds}
        self.assertFalse(test_mod._has_separate_metadata_object(inv))

    def test_validate_ops_mgr(self):
        # Test valid case
        net = 'openstack-mgmt'
        config = {'networks': {net: {}},
                  'node-templates': {'a': {'networks': [net]},
                                     'b': {'networks': [net]}}}
        test_mod.validate_ops_mgr(config)

        # Test missing network
        config['networks'].pop(net)
        self.assertRaisesRegexp(test_mod.UnsupportedConfig,
                                'required openstack-mgmt network',
                                test_mod.validate_ops_mgr,
                                config)
        # Test one template missing the network
        config['networks'][net] = {}
        config['node-templates']['a']['networks'].pop(0)
        expected_msg = 'The node template a is missing network openstack-mgmt'
        self.assertRaisesRegexp(test_mod.UnsupportedConfig,
                                expected_msg,
                                test_mod.validate_ops_mgr,
                                config)

    @mock.patch.object(test_mod, 'validate_ops_mgr')
    @mock.patch.object(test_mod, 'validate_ceph')
    @mock.patch.object(test_mod, 'validate_swift')
    @mock.patch.object(test_mod, 'validate_reference_architecture')
    @mock.patch.object(test_mod, '_load_yml')
    def test_validate(self, load, ra, swift, ceph, opsmgr):
        file_path = 'path'
        test_mod.validate(file_path)
        load.assert_called_once_with(file_path)
        ra.assert_called_once_with(load.return_value)
        swift.assert_called_once_with(load.return_value)
        ceph.assert_called_once_with(load.return_value)
        opsmgr.assert_called_once_with(load.return_value)

    @mock.patch.object(test_mod, '_get_roles_to_templates')
    @mock.patch.object(test_mod, '_validate_ceph_node_templates')
    @mock.patch.object(test_mod, '_validate_ceph_networks')
    @mock.patch.object(test_mod, '_validate_ceph_devices')
    def test_validate_ceph(self, devices, networks, templates, get_r2t):
        # Validate without ceph-standalone or private compute
        config = {'reference-architecture': ['swift']}
        test_mod.validate_ceph(config)
        self.assertEqual(get_r2t.call_count, 0)
        self.assertEqual(templates.call_count, 0)
        self.assertEqual(networks.call_count, 0)
        self.assertEqual(devices.call_count, 0)

        config = {'reference-architecture': ['private-compute-cloud']}
        test_mod.validate_ceph(config)
        get_r2t.assert_called_once_with(config)
        templates.assert_called_once_with(get_r2t.return_value)
        networks.assert_called_once_with(config, get_r2t.return_value)
        devices.assert_called_once_with(config, get_r2t.return_value)

    def test_validate_ceph_networks(self):
        # Test valid network configurations
        valid_combos = {test_mod.CEPH: 'ceph-public-storage',
                        test_mod.COMPUTE: 'openstack-stg'}
        for arch, net in valid_combos.iteritems():
            node_templ = {'controllers': {'networks': [net]},
                          'ceph-osd': {'networks': [net],
                                       'domain-settings': {
                                           'osd-devices': ['a']}}}
            role_to_template = {'ceph-osd': [node_templ['ceph-osd']],
                                'ceph-monitor': [node_templ['controllers']]}
            config = {'reference-architecture': [arch],
                      'networks': {net: {}},
                      'node-templates': node_templ}
            test_mod._validate_ceph_networks(config, role_to_template)

        # Test bad network configurations
        bad_combos = {test_mod.CEPH: 'external',
                      test_mod.COMPUTE: 'ceph-public-storage'}
        for arch, net in bad_combos.iteritems():
            node_templ = {'controllers': {'networks': [net]},
                          'ceph-osd': {'networks': [net],
                                       'domain-settings': {
                                           'osd-devices': ['a']}}}
            role_to_template = {'ceph-osd': [node_templ['ceph-osd']],
                                'ceph-monitor': [node_templ['controllers']]}
            config = {'reference-architecture': [arch],
                      'networks': {net: {}},
                      'node-templates': node_templ}
            self.assertRaisesRegexp(test_mod.UnsupportedConfig,
                                    'Ceph storage network',
                                    test_mod._validate_ceph_networks,
                                    config, role_to_template)

        # Test when the network exists but ceph monitor
        # node templates don't have it
        for arch, net in valid_combos.iteritems():
            node_templ = {'controllers': {'networks': ['somenet']},
                          'ceph-osd': {'networks': ['somenet'],
                                       'domain-settings': {
                                           'osd-devices': ['a']}}}
            role_to_template = {'ceph-osd': [node_templ['ceph-osd']],
                                'ceph-monitor': [node_templ['controllers']]}
            config = {'reference-architecture': [arch],
                      'networks': {net: {}},
                      'node-templates': node_templ}
            self.assertRaisesRegexp(test_mod.UnsupportedConfig,
                                    'are missing network',
                                    test_mod._validate_ceph_networks,
                                    config, role_to_template)
        # Test when the network exists but ceph osd
        # node templates don't have it
        for arch, net in valid_combos.iteritems():
            node_templ = {'controllers': {'networks': [net]},
                          'ceph-osd': {'networks': ['somenet'],
                                       'domain-settings': {
                                           'osd-devices': ['a']}}}
            role_to_template = {'ceph-osd': [node_templ['ceph-osd']],
                                'ceph-monitor': [node_templ['controllers']]}
            config = {'reference-architecture': [arch],
                      'networks': {net: {}},
                      'node-templates': node_templ}
            self.assertRaisesRegexp(test_mod.UnsupportedConfig,
                                    'are missing network',
                                    test_mod._validate_ceph_networks,
                                    config, role_to_template)

    def test_validate_ceph_node_templates(self):
        # Test good case with ceph-monitor and ceph-osd
        roles_to_templates = {'ceph-osd': 'a',
                              'ceph-monitor': 'b'}

        test_mod._validate_ceph_node_templates(roles_to_templates)
        roles_to_templates.pop('ceph-monitor')
        self.assertRaisesRegexp(test_mod.UnsupportedConfig,
                                'ceph-monitor',
                                test_mod._validate_ceph_node_templates,
                                roles_to_templates)

        roles_to_templates['ceph-monitor'] = 'a'
        roles_to_templates.pop('ceph-osd')
        self.assertRaisesRegexp(test_mod.UnsupportedConfig,
                                'ceph-osd',
                                test_mod._validate_ceph_node_templates,
                                roles_to_templates)

    def test_validate_ceph_devices(self):
        # Test missing device list in the backward compatible,
        # single ceph-osd template path
        arch = test_mod.CEPH
        node_templ = {'ceph-osd': {'domain-settings': {'osd-devices': []}}}
        role_to_template = {'ceph-osd': [node_templ['ceph-osd']]}
        config = {'reference-architecture': [arch],
                  'node-templates': node_templ}
        self.assertRaisesRegexp(test_mod.UnsupportedConfig,
                                'missing the osd-devices',
                                test_mod._validate_ceph_devices,
                                config, role_to_template)

        node_templ['ceph-osd']['domain-settings'].pop('osd-devices')
        self.assertRaisesRegexp(test_mod.UnsupportedConfig,
                                'missing the osd-devices',
                                test_mod._validate_ceph_devices,
                                config, role_to_template)

        node_templ['ceph-osd'].pop('domain-settings')
        self.assertRaisesRegexp(test_mod.UnsupportedConfig,
                                'missing the osd-devices',
                                test_mod._validate_ceph_devices,
                                config, role_to_template)
        # Test when multiple node templates have journal devices

        templates = {'t1': {'domain-settings': {'journal-devices': ['a'],
                                                'osd-devices': ['b']}},
                     't2': {'domain-settings': {'journal-devices': ['a'],
                                                'osd-devices': ['b']}},
                     't3': {'domain-settings': {'journal-devices': ['a'],
                                                'osd-devices': ['b']}},
                     't4': {'domain-settings': {'journal-devices': ['a'],
                                                'osd-devices': ['b']}}}
        config['node-templates'] = templates
        role_to_template = {'ceph-osd': [templ for templ in
                                         templates.values()]}
        test_mod._validate_ceph_devices(config, role_to_template)

        # Test when one template doesn't have journal devices but another does
        templates['t2']['domain-settings'].pop('journal-devices')
        self.assertRaisesRegexp(test_mod.UnsupportedConfig,
                                'specifying journal devices, all Ceph',
                                test_mod._validate_ceph_devices,
                                config, role_to_template)

    def test_get_roles_to_templates(self):
        # Test backward compatible for ceph monitor
        config = {'node-templates': {'controllers': {},
                                     'something': {},
                                     'another-thing': {}}}
        r2t = test_mod._get_roles_to_templates(config)
        self.assertItemsEqual(['controllers', 'something', 'another-thing',
                               'ceph-monitor'], r2t.keys())

        # Test roles
        nt = {'a': {'roles': ['1', '2', '3']},
              'b': {'roles': ['1', '4']},
              'c': {'roles': ['3']}}
        config = {'node-templates': nt}
        expected = {'1': [nt['a'], nt['b']],
                    '2': [nt['a']],
                    '3': [nt['a'], nt['c']],
                    '4': [nt['b']],
                    'a': [nt['a']],
                    'b': [nt['b']],
                    'c': [nt['c']]}
        r2t = test_mod._get_roles_to_templates(config)
        self.assertEqual(expected.keys(), r2t.keys())
        for key, value in expected.iteritems():
            ret_value = r2t[key]
            self.assertItemsEqual(value, ret_value,
                                  'For template %s' % key)

        # Test when a node template has a role that matches its name
        mon = 'ceph-monitor'
        config = {'node-templates': {'controllers': {},
                                     'ceph-monitor': {'roles': [mon]},
                                     'ceph-osd': {'roles': ['ceph-osd']}}}
        r2t = test_mod._get_roles_to_templates(config)
        self.assertItemsEqual(['controllers', 'ceph-monitor', 'ceph-osd'],
                              r2t.keys())
        self.assertEqual(2, len(r2t.get('ceph-monitor')))
        self.assertEqual(1, len(r2t.get('ceph-osd')))

    def test_validate_devices_lists(self):
        devices = ['/dev/sde',
                   '/dev/sdf',
                   '/dev/sdg',
                   '/dev/sdh',
                   '/dev/sdi']
        dk = 'device_key'
        # Test where the lists are equal
        osd_tmpls = [{'domain-settings': {dk: devices}}]
        osd_tmpls.append({'domain-settings': {dk: copy.deepcopy(devices)}})
        osd_tmpls.append({'domain-settings': {dk: copy.deepcopy(devices)}})
        osd_tmpls.append({'domain-settings': {dk: copy.deepcopy(devices)}})
        test_mod._validate_devices_lists(osd_tmpls, dk)

        # Test where one list on one host is shorter
        osd_tmpls = [{'domain-settings': {dk: devices}}]
        osd_tmpls.append({'domain-settings': {dk: copy.deepcopy(devices)}})
        osd_tmpls.append({'domain-settings': {dk: copy.deepcopy(devices)}})
        devices2 = devices[:-2]
        osd_tmpls.append({'domain-settings': {dk: copy.deepcopy(devices2)}})
        osd_tmpls.append({'domain-settings': {dk: copy.deepcopy(devices)}})

        self.assertRaises(test_mod.InvalidDeviceList,
                          test_mod._validate_devices_lists, osd_tmpls, dk)

        # Test where one of the lists is longer
        osd_tmpls = [{'domain-settings': {dk: devices}}]
        osd_tmpls.append({'domain-settings': {dk: copy.deepcopy(devices)}})
        osd_tmpls.append({'domain-settings': {dk: copy.deepcopy(devices)}})
        devices2 = copy.deepcopy(devices).append('somethingMore')
        osd_tmpls.append({'domain-settings': {dk: copy.deepcopy(devices2)}})
        osd_tmpls.append({'domain-settings': {dk: copy.deepcopy(devices)}})

        self.assertRaises(test_mod.InvalidDeviceList,
                          test_mod._validate_devices_lists, osd_tmpls, dk)

        # Test where one of the lists has a different value
        osd_tmpls = [{'domain-settings': {dk: devices}}]
        osd_tmpls.append({'domain-settings': {dk: copy.deepcopy(devices)}})
        osd_tmpls.append({'domain-settings': {dk: copy.deepcopy(devices)}})
        devices2 = copy.deepcopy(devices)
        devices2[4] = '/different'
        osd_tmpls.append({'domain-settings': {dk: copy.deepcopy(devices2)}})
        osd_tmpls.append({'domain-settings': {dk: copy.deepcopy(devices)}})

        self.assertRaises(test_mod.InvalidDeviceList,
                          test_mod._validate_devices_lists, osd_tmpls, dk)
