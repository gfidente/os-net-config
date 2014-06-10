# -*- coding: utf-8 -*-

# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import tempfile

from os_net_config import impl_ifcfg
from os_net_config import objects
from os_net_config.openstack.common import processutils
from os_net_config.tests import base
from os_net_config import utils


_BASE_IFCFG = """DEVICE=em1
ONBOOT=yes
HOTPLUG=no
"""

_V4_IFCFG = _BASE_IFCFG + """BOOTPROTO=static
IPADDR=192.168.1.2
NETMASK=255.255.255.0
"""

_V6_IFCFG = _BASE_IFCFG + """IPV6INIT=yes
IPV6_AUTOCONF=no
IPV6ADDR=2001:abc:a::
"""

_OVS_IFCFG = _BASE_IFCFG + "DEVICETYPE=ovs\n"


_OVS_BRIDGE_IFCFG = _BASE_IFCFG + "DEVICETYPE=ovs\n"


_ROUTES = """default via 192.168.1.1 dev em1
172.19.0.0/24 via 192.168.1.1 dev em1
"""


class TestIfcfgNetConfig(base.TestCase):

    def setUp(self):
        super(TestIfcfgNetConfig, self).setUp()
        self.temp_ifcfg_file = tempfile.NamedTemporaryFile()
        self.temp_route_file = tempfile.NamedTemporaryFile()

        def test_ifcfg_path(name):
            return self.temp_ifcfg_file.name
        self.stubs.Set(impl_ifcfg, 'ifcfg_config_path', test_ifcfg_path)

        def test_routes_path(name):
            return self.temp_route_file.name
        self.stubs.Set(impl_ifcfg, 'route_config_path', test_routes_path)

        self.provider = impl_ifcfg.IfcfgNetConfig()

    def tearDown(self):
        self.temp_ifcfg_file.close()
        self.temp_route_file.close()
        super(TestIfcfgNetConfig, self).tearDown()

    def get_interface_config(self):
        return self.provider.interfaces['em1']

    def get_route_config(self):
        return self.provider.routes['em1']

    def test_add_base_interface(self):
        interface = objects.Interface('em1')
        self.provider.addInterface(interface)
        self.assertEqual(_BASE_IFCFG, self.get_interface_config())

    def test_add_ovs_interface(self):
        interface = objects.Interface('em1')
        interface.type = 'ovs'
        self.provider.addInterface(interface)
        self.assertEqual(_OVS_IFCFG, self.get_interface_config())

    def test_add_interface_with_v4(self):
        v4_addr = objects.Address('192.168.1.2/24')
        interface = objects.Interface('em1', addresses=[v4_addr])
        self.provider.addInterface(interface)
        self.assertEqual(_V4_IFCFG, self.get_interface_config())

    def test_add_interface_with_v6(self):
        v6_addr = objects.Address('2001:abc:a::/64')
        interface = objects.Interface('em1', addresses=[v6_addr])
        self.provider.addInterface(interface)

    def test_network_with_routes(self):
        route1 = objects.Route('192.168.1.1', default=True)
        route2 = objects.Route('192.168.1.1', '172.19.0.0/24')
        v4_addr = objects.Address('192.168.1.2/24')
        interface = objects.Interface('em1', addresses=[v4_addr],
                                      routes=[route1, route2])
        self.provider.addInterface(interface)
        self.assertEqual(_V4_IFCFG, self.get_interface_config())
        self.assertEqual(_ROUTES, self.get_route_config())

    def test_apply(self):
        route1 = objects.Route('192.168.1.1', default=True)
        route2 = objects.Route('192.168.1.1', '172.19.0.0/24')
        v4_addr = objects.Address('192.168.1.2/24')
        interface = objects.Interface('em1', addresses=[v4_addr],
                                      routes=[route1, route2])
        self.provider.addInterface(interface)

        def test_execute(*args, **kwargs):
            pass
        self.stubs.Set(processutils, 'execute', test_execute)

        self.provider.apply()

        ifcfg_data = utils.get_file_data(self.temp_ifcfg_file.name)
        self.assertEqual(_V4_IFCFG, ifcfg_data)
        route_data = utils.get_file_data(self.temp_route_file.name)
        self.assertEqual(_ROUTES, route_data)
