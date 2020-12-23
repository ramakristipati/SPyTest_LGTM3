import pytest
from spytest import st
from spytest.dicts import SpyTestDict
import apis.system.ntp as ntp_obj
import apis.routing.vrf as vrfapi
import apis.routing.ip as ipapi
import apis.switching.vlan as vlanapi
from utilities.parallel import exec_all, exec_parallel, ExecAllFunc, ensure_no_exception
from utilities.common import random_vlan_list, poll_wait

def global_vars():
    global data
    data = SpyTestDict()
    data.ntp_service = 'ntp'
    data.loopback_intf = 'Loopback1'
    data.ip_addresses = ['1::1', '2001::1', '2001::2', '3001::1', '3001::2']
    data.subnets = ['128', '64']
    data.vrf_names = ['mgmt', 'Vrf-common']
    data.default = "default"
    data.max_loopback_ip = "127.0.0.1"
    data.ntp_master = "134.214.100.6"
    data.random_vlan = str(random_vlan_list()[0])
    data.random_vlan2 = str(random_vlan_list(exclude=[data.random_vlan])[0])
    data.unreachable_server = "10.10.10.1"

@pytest.fixture(scope="module", autouse=True)
def ntp_module_hooks(request):
    global vars
    vars = st.ensure_min_topology("D1D2:1", "D1D3:1")
    global_vars()
    st.banner("Configuring VRFs")
    if not vrfapi.config_vrf(vars.D1, vrf_name=data.vrf_names):
        st.report_fail("msg", "Failed to configure VRFs")

    st.banner("Configuring Loop-back interface")
    if not ipapi.config_loopback_interfaces(vars.D1, loopback_name=data.loopback_intf, config="yes"):
        st.report_fail("msg", "Failed to configure Loop-back interface: {}".format(data.loopback_intf))

    st.banner("Creating VLANs on all the DUTs")
    dict1 = {'vlan_list': data.random_vlan}
    [output, exceptions] = exec_parallel(True, [vars.D1, vars.D2], vlanapi.create_vlan, [dict1, dict1])
    ensure_no_exception(exceptions)
    if not all(output):
        st.report_fail("msg", "Failed to create VLAN:{}".format(data.random_vlan))

    st.banner("Adding members to the configured vlans")
    dict1 = {'vlan': data.random_vlan, 'port_list': vars.D1D2P1, 'tagging_mode': True}
    dict2 = {'vlan': data.random_vlan, 'port_list': vars.D2D1P1, 'tagging_mode': True}
    [output, exceptions] = exec_parallel(True, [vars.D1, vars.D2], vlanapi.add_vlan_member, [dict1, dict2])
    ensure_no_exception(exceptions)
    if not all(output):
        st.report_fail("msg", "Failed to add members as tagged members of VLAN")

    st.banner("Binding VRFs to interfaces")
    if not vrfapi.bind_vrf_interface(vars.D1, vrf_name=data.vrf_names[0], intf_name=data.loopback_intf):
        st.report_fail("msg", "Failed to bind interface: {} to VRF: {}".format(data.loopback_intf, data.vrf_names[0]))
    if not vrfapi.bind_vrf_interface(vars.D1, vrf_name=data.vrf_names[1], intf_name="Vlan{}".format(data.random_vlan)):
        st.report_fail("msg", "Failed to bind interface: {} to VRF: {}".format("Vlan{}".format(data.random_vlan), data.vrf_names[1]))

    st.banner("IP Address configuration")
    if not ipapi.config_ip_addr_interface(vars.D1, interface_name=data.loopback_intf, ip_address=data.ip_addresses[0], subnet=data.subnets[0], family="ipv6"):
        st.report_fail("msg", "Failed to configure IP: {}/{} on loopback interface: {}".format(data.ip_addresses[0], data.subnets[0], data.loopback_intf))
    dict1 = {"interface_name": "Vlan{}".format(data.random_vlan), "ip_address": data.ip_addresses[1], "subnet": data.subnets[1], "family" : "ipv6"}
    dict2 = {"interface_name": "Vlan{}".format(data.random_vlan), "ip_address": data.ip_addresses[2], "subnet": data.subnets[1], "family" : "ipv6"}
    [output, exceptions] = exec_parallel(True, [vars.D1, vars.D2], ipapi.config_ip_addr_interface, [dict1, dict2])
    ensure_no_exception(exceptions)
    if not all(output):
        st.report_fail("msg", "Failed to configure IP addresses on interfaces")
    dict1 = {"interface_name": vars.D1D3P1, "ip_address": data.ip_addresses[3], "subnet": data.subnets[1], "family" : "ipv6"}
    dict2 = {"interface_name": vars.D3D1P1, "ip_address": data.ip_addresses[4], "subnet": data.subnets[1], "family" : "ipv6"}
    [output, exceptions] = exec_parallel(True, [vars.D1, vars.D3], ipapi.config_ip_addr_interface, [dict1, dict2])
    ensure_no_exception(exceptions)
    if not all(output):
        st.report_fail("msg", "Failed to configure IP addresses on interfaces")

    st.banner("Route-Leak Configuration")
    [output, exceptions] = exec_all(True, [ExecAllFunc(ipapi.create_static_route, vars.D1, vrf=data.vrf_names[1], static_ip="{}/{}".format(data.ip_addresses[0], data.subnets[0]), interface=data.loopback_intf, nexthop_vrf=data.vrf_names[0], family='ipv6'),
                                           ExecAllFunc(ipapi.create_static_route, vars.D2, next_hop=data.ip_addresses[1], static_ip="{}/{}".format(data.ip_addresses[0], data.subnets[0]), family='ipv6')])
    ensure_no_exception(exceptions)
    if not all(output):
        st.report_fail("msg", "Failed to configure static routes")

    [output, exceptions] = exec_all(True, [ExecAllFunc(ipapi.create_static_route, vars.D1, vrf=data.vrf_names[0], static_ip="{}/{}".format(data.ip_addresses[1], data.subnets[1]), interface="Vlan{}".format(data.random_vlan), nexthop_vrf=data.vrf_names[1], family='ipv6'),
                                           ExecAllFunc(ipapi.create_static_route, vars.D3, next_hop=data.ip_addresses[3], static_ip="{}/{}".format(data.ip_addresses[0], data.subnets[0]), family='ipv6')])
    ensure_no_exception(exceptions)
    if not all(output):
        st.report_fail("msg", "Failed to configure static routes")

    if not ipapi.create_static_route(vars.D1, vrf=data.vrf_names[0], static_ip="{}/{}".format(data.ip_addresses[3], data.subnets[1]), interface=vars.D1D3P1, nexthop_vrf=data.default, family='ipv6'):
        st.report_fail("msg", "Failed to configure route leak")

    if not ipapi.create_static_route(vars.D1, static_ip="{}/{}".format(data.ip_addresses[0], data.subnets[0]), family='ipv6', interface=data.loopback_intf, nexthop_vrf=data.vrf_names[0]):
        st.report_fail("msg", "Failed to configure route leak")

    st.debug("NTP Configuration")
    dict1 = {'source_intf': ['Management0', data.loopback_intf], 'servers': data.ntp_master}
    dict2 = {'source_intf': "Vlan{}".format(data.random_vlan), 'servers': data.ip_addresses[0]}
    if not ntp_obj.config_ntp_parameters(vars.D1, **dict1):
        st.report_fail("msg", "Failed to configure NTP server")
    if not ntp_obj.config_ntp_parameters(vars.D2, **dict2):
        st.report_fail("msg", "Failed to configure NTP client")
    if not ntp_obj.config_ntp_parameters(vars.D3, source_intf=vars.D3D1P1, servers=data.ip_addresses[0]):
        st.report_fail("msg", "Failed to configure NTP server parameters")
    yield
    ntp_obj.delete_ntp_servers(vars.D1)
    vlanapi.clear_vlan_configuration([vars.D1, vars.D2, vars.D3])

@pytest.fixture(scope="function", autouse=True)
def ntp_func_hooks(request):
    if st.get_func_name(request) in ['test_ft_verify_ntp_sych_v6']:
        st.banner("Verifying the connectivity")
        if not ipapi.ping_poll(vars.D2, data.ip_addresses[0], family='ipv6', iter=3):
            st.report_fail("msg", "Failed to ping Loop-back IP on DUT1 from DUT2")
        if not ipapi.ping_poll(vars.D3, data.ip_addresses[0], iter=3):
            st.report_fail("msg", "Failed to ping Loop-back IP on DUT1 from DUT3")
    yield

def test_verify_ntp_sych_v6():
    """
    Verify the loopback ipv6 address is assigned to mgmt-vrf and verify the switch acts as a NTP Server and client is in user-vrf.
	Verify the loopback ipv6 address is assigned to mgmt-vrf and verify the switch acts as a NTP Server and client is in default-vrf.
	Author:
    """
    st.debug("Verify whether the NTP got synch or not")
    [output, exceptions] = exec_all(True,
                                    [ExecAllFunc(poll_wait, ntp_obj.verify_ntp_synch, 100, vars.D1, data.ntp_master),
                                     ExecAllFunc(poll_wait, ntp_obj.verify_ntp_synch, 100, vars.D2,
                                                 data.ip_addresses[0]),
                                     ExecAllFunc(poll_wait, ntp_obj.verify_ntp_synch, 100, vars.D3,
                                                 data.ip_addresses[0])])
    ensure_no_exception(exceptions)
    if not all(output):
        st.report_fail("msg", "NTP is not synchronized")
    [output, exceptions] = exec_all(True, [[ntp_obj.show_clock, vars.D1], [ntp_obj.show_clock, vars.D2],
                                           [ntp_obj.show_clock, vars.D3]])
    ensure_no_exception(exceptions)
    if not ntp_obj.verify_time_synch(output[0], output[1]):
        st.report_fail("msg", "The server and client(non-default VRF) times are not in synch")
    if not ntp_obj.verify_time_synch(output[0], output[2]):
        st.report_fail("msg", "The server and client(default VRF) times are not in synch")
    st.report_pass("test_case_passed")