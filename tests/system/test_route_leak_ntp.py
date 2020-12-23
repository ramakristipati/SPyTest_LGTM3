import pytest
from spytest import st
from spytest.dicts import SpyTestDict
import apis.system.reboot as reboot_obj
import apis.system.ntp as ntp_obj
import apis.routing.vrf as vrfapi
import apis.routing.ip as ipapi
import apis.switching.vlan as vlanapi
from apis.system.interface import interface_operation
from utilities.parallel import exec_all, exec_parallel, ExecAllFunc, ensure_no_exception
from utilities.common import random_vlan_list, poll_wait
import apis.switching.portchannel as pc_obj

def global_vars():
    global data
    data = SpyTestDict()
    data.ntp_service = 'ntp'
    data.loopback_intf = 'Loopback1'
    data.loopback_intf_1= 'Loopback99'
    data.ip_addresses = ['99.1.1.1', '88.1.1.1', '88.1.1.2', '77.1.1.1', '77.1.1.2','22.2.2.2']
    data.ip_addresses_nw = ['99.1.1.0', '88.1.1.0','77.1.1.0','22.2.2.0']
    data.subnets = ['32', '24']
    data.vrf_names = ['mgmt', 'Vrf-common']
    data.default = 'default'
    data.max_loopback_ip = "127.0.0.1"
    data.ntp_master = "134.214.100.6"
    data.random_vlan = str(random_vlan_list()[0])
    data.random_vlan2 = str(random_vlan_list(exclude=[data.random_vlan])[0])
    data.unreachable_server = "10.10.10.1"
    data.auth_type = ['md5', 'sha1', 'sha2-256']
    data.auth_key_id = ['1', '65']
    data.auth_string = ['lvl7india', 'india']
    data.trusted_key = ['1', '65']
    data.port_channel = 'PortChannel1'

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
    if not ipapi.config_ip_addr_interface(vars.D1, interface_name=data.loopback_intf, ip_address=data.ip_addresses[0], subnet=data.subnets[0]):
        st.report_fail("msg", "Failed to configure IP: {}/{} on loopback interface: {}".format(data.ip_addresses[0], data.subnets[0], data.loopback_intf))
    dict1 = {"interface_name": "Vlan{}".format(data.random_vlan), "ip_address": data.ip_addresses[1], "subnet": data.subnets[1]}
    dict2 = {"interface_name": "Vlan{}".format(data.random_vlan), "ip_address": data.ip_addresses[2], "subnet": data.subnets[1]}
    [output, exceptions] = exec_parallel(True, [vars.D1, vars.D2], ipapi.config_ip_addr_interface, [dict1, dict2])
    ensure_no_exception(exceptions)
    if not all(output):
        st.report_fail("msg", "Failed to configure IP addresses on interfaces")

    dict1 = {"interface_name": vars.D1D3P1, "ip_address": data.ip_addresses[3], "subnet": data.subnets[1]}
    dict2 = {"interface_name": vars.D3D1P1, "ip_address": data.ip_addresses[4], "subnet": data.subnets[1]}
    [output, exceptions] = exec_parallel(True, [vars.D1, vars.D3], ipapi.config_ip_addr_interface, [dict1, dict2])
    ensure_no_exception(exceptions)
    if not all(output):
        st.report_fail("msg", "Failed to configure IP addresses on interfaces")

    st.banner("Route-Leak Configuration")
    [output, exceptions] = exec_all(True, [ExecAllFunc(ipapi.create_static_route, vars.D1, vrf=data.vrf_names[1], static_ip="{}/{}".format(data.ip_addresses[0], data.subnets[0]), interface=data.loopback_intf, nexthop_vrf=data.vrf_names[0]),
                                           ExecAllFunc(ipapi.create_static_route, vars.D2, next_hop=data.ip_addresses[1], static_ip="{}/{}".format(data.ip_addresses[0], data.subnets[0]))])
    ensure_no_exception(exceptions)
    if not all(output):
        st.report_fail("msg", "Failed to configure static routes")

    [output, exceptions] = exec_all(True, [ExecAllFunc(ipapi.create_static_route, vars.D1, vrf=data.vrf_names[0], static_ip="{}/{}".format(data.ip_addresses[1], data.subnets[1]), interface="Vlan{}".format(data.random_vlan), nexthop_vrf=data.vrf_names[1]),
                                           ExecAllFunc(ipapi.create_static_route, vars.D3, next_hop=data.ip_addresses[3], static_ip="{}/{}".format(data.ip_addresses[0], data.subnets[0]))])
    ensure_no_exception(exceptions)
    if not all(output):
        st.report_fail("msg", "Failed to configure static routes")

    if not ipapi.create_static_route(vars.D1, vrf=data.vrf_names[0], static_ip="{}/{}".format(data.ip_addresses[3], data.subnets[1]), interface=vars.D1D3P1, nexthop_vrf=data.default):
        st.report_fail("msg", "Failed to configure static routes")

    if not ipapi.create_static_route(vars.D1, static_ip="{}/{}".format(data.ip_addresses[0], data.subnets[0]), interface=data.loopback_intf, nexthop_vrf=data.vrf_names[0]):
        st.report_fail("msg", "Failed to configure static routes")

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
    if st.get_func_name(request) in ['test_ft_verify_ntp_sych', 'test_verify_ntp_synch_after_shut_no_shut',
                                     'test_verify_ntp_synch_after_save_reload', 'test_verify_ntp_synch_after_warm_boot',
                                     'test_verify_ntp_synch_after_fast_boot']:
        st.banner("Verifying the connectivity")
        if not ipapi.ping_poll(vars.D2, data.ip_addresses[0], iter=3):
            st.report_fail("msg", "Failed to ping Loop-back IP on DUT1 from DUT2")
        if not ipapi.ping_poll(vars.D3, data.ip_addresses[0], iter=3):
            st.report_fail("msg", "Failed to ping Loop-back IP on DUT1 from DUT3")
    elif st.get_func_name(request) == 'test_check_ntp_authetication':
        st.banner("configuring static route")
        if not ipapi.create_static_route(vars.D3, next_hop=data.ip_addresses[3], static_ip="{}/{}".format(data.ip_addresses[0], data.subnets[0])):
            st.report_fail("msg", "Failed to configure static route")
    elif st.get_func_name(request) == 'test_check_ntp_with_unreachable_server':
        ntp_obj.config_ntp_parameters(vars.D3, servers=data.ip_addresses[0], config=False)
        ntp_obj.config_ntp_parameters(vars.D3, servers=data.unreachable_server)
    elif st.get_func_name(request) == 'test_verify_ntp_server_client_sync_when_eth0_and_client_in_default_vrf':
        st.banner("static route UnConfiguration")
        [output, exceptions] = exec_all(True, [ExecAllFunc(ipapi.delete_static_route, vars.D1, next_hop=None, vrf=data.vrf_names[1],
                                                           static_ip="{}/{}".format(data.ip_addresses[0],
                                                                                    data.subnets[0]),
                                                           interface=data.loopback_intf, nexthop_vrf=data.vrf_names[0]),
                                               ExecAllFunc(ipapi.delete_static_route, vars.D2,
                                                           next_hop=data.ip_addresses[1],
                                                           static_ip="{}/{}".format(data.ip_addresses[0],
                                                                                    data.subnets[0]))])
        ensure_no_exception(exceptions)
        if not all(output):
            st.report_fail("msg", "Failed to unconfigure static routes")
        [output, exceptions] = exec_all(True, [ExecAllFunc(ipapi.delete_static_route, vars.D1, next_hop=None, vrf=data.vrf_names[0],
                                                           static_ip="{}/{}".format(data.ip_addresses_nw[1],
                                                                                    data.subnets[1]),
                                                           interface="Vlan{}".format(data.random_vlan),
                                                           nexthop_vrf=data.vrf_names[1]),
                                               ExecAllFunc(ipapi.delete_static_route, vars.D3,
                                                           next_hop=data.ip_addresses[3],
                                                           static_ip="{}/{}".format(data.ip_addresses[0],
                                                                                    data.subnets[0]))])
        ensure_no_exception(exceptions)
        if not all(output):
            st.report_fail("msg", "Failed to unconfigure static routes")

        if not ipapi.delete_static_route(vars.D1, next_hop=None, static_ip="{}/{}".format(data.ip_addresses_nw[2], data.subnets[1]),
                                         interface=vars.D1D3P1, vrf=data.vrf_names[0], nexthop_vrf=data.default):
            st.report_fail("msg", "Failed to unconfigure route leak")
        if not ipapi.delete_static_route(vars.D1, next_hop=None, static_ip="{}/{}".format(data.ip_addresses[0], data.subnets[0]),
                                         interface=data.loopback_intf, nexthop_vrf=data.vrf_names[0]):
            st.report_fail("msg", "Failed to unconfigure route leak")

        st.banner("NTP UnConfiguration")
        dict1 = {'source_intf': ['Management0', data.loopback_intf], 'servers': data.ntp_master, 'config':False}
        dict2 = {'source_intf': "Vlan{}".format(data.random_vlan), 'servers': data.ip_addresses[0], 'config':False}
        if not ntp_obj.config_ntp_parameters(vars.D1, **dict1):
            st.report_fail("msg", "Failed to configure NTP server")
        if not ntp_obj.config_ntp_parameters(vars.D2, **dict2):
            st.report_fail("msg", "Failed to configure NTP client")
        st.banner("IP Address Unconfiguration")
        if not ipapi.config_ip_addr_interface(vars.D1, interface_name=data.loopback_intf,
                                              ip_address=data.ip_addresses[0],
                                              subnet=data.subnets[0], config='remove'):
            st.report_fail("msg",
                           "Failed to unconfigure IP: {}/{} on loopback interface: {}".format(data.ip_addresses[0],
                                                                                              data.subnets[0],
                                                                                              data.loopback_intf))
        dict1 = {"interface_name": "Vlan{}".format(data.random_vlan), "ip_address": data.ip_addresses[1],
                 "subnet": data.subnets[1], "config":'remove'}
        dict2 = {"interface_name": "Vlan{}".format(data.random_vlan), "ip_address": data.ip_addresses[2],
                 "subnet": data.subnets[1], "config":'remove'}
        [output, exceptions] = exec_parallel(True, [vars.D1, vars.D2], ipapi.config_ip_addr_interface, [dict1, dict2])
        ensure_no_exception(exceptions)
        if not all(output):
            st.report_fail("msg", "Failed to configure IP addresses on interfaces")
        st.banner("UnBinding VRFs to interfaces")
        if not vrfapi.bind_vrf_interface(vars.D1, vrf_name=data.vrf_names[0], intf_name=data.loopback_intf,
                                         config='no'):
            st.report_fail("msg",
                           "Failed to unbind interface: {} to VRF: {}".format(data.loopback_intf, data.vrf_names[0]))
        if not vrfapi.bind_vrf_interface(vars.D1, vrf_name=data.vrf_names[1],
                                         intf_name="Vlan{}".format(data.random_vlan), config='no'):
            st.report_fail("msg", "Failed to unbind interface: {} to VRF: {}".format("Vlan{}".format(data.random_vlan),
                                                                                     data.vrf_names[1]))
        if not vlanapi.clear_vlan_configuration([vars.D1, vars.D2]):
            st.report_fail("msg", "Failed to remove Vlan configuration")

        st.banner("unconfiguring VRFs")
        if not vrfapi.config_vrf(vars.D1, vrf_name=data.vrf_names, config='no'):
            st.report_fail("msg", "Failed to unconfigure VRFs")
    elif st.get_func_name(request) == 'test_verify_ntp_with_vrf_and_with_out_vrf':
        st.banner("Unconfiguring ip addresses")
        dict1 = {"interface_name": vars.D1D3P1, "ip_address": data.ip_addresses[3], "subnet": data.subnets[1], 'config':'remove'}
        dict2 = {"interface_name": vars.D3D1P1, "ip_address": data.ip_addresses[4], "subnet": data.subnets[1], 'config':'remove'}
        [output, exceptions] = exec_parallel(True, [vars.D1, vars.D3], ipapi.config_ip_addr_interface, [dict1, dict2])
        ensure_no_exception(exceptions)
        if not all(output):
            st.report_fail("msg", "Failed to unconfigure IP addresses on interfaces")
        st.banner("unconfiguring ntp client")

    yield
    if st.get_func_name(request) == 'test_verify_switch_over_ntp_servers_working':
        if not ipapi.delete_static_route(vars.D3, next_hop=data.ip_addresses[3],
                                         static_ip="{}/{}".format(data.ip_addresses[5],
                                                                  data.subnets[0])):
            st.report_fail("msg", "Failed to unconfigure static route")
        if not ipapi.delete_static_route(vars.D1, next_hop=None, static_ip="{}/{}".format(data.ip_addresses[5], data.subnets[0]),
                                         interface=data.loopback_intf_1, nexthop_vrf=data.vrf_names[0]):
            st.report_fail("msg", "Failed to unconfigure route leak")
        st.banner("IP Address unconfiguration")
        if not ipapi.config_ip_addr_interface(vars.D1, interface_name=data.loopback_intf_1,
                                              ip_address=data.ip_addresses[5],
                                              subnet=data.subnets[0], config='remove'):
            st.report_fail("msg", "Failed to configure IP: {}/{} on loopback interface: {}".format(data.ip_addresses[5],
                                                                                                   data.subnets[0],
                                                                                                   data.loopback_intf_1))
        if not ntp_obj.config_ntp_parameters(vars.D1, source_intf=data.loopback_intf_1, config=False):
            st.report_fail("msg", "Failed to configure NTP server parameters")
        if not ntp_obj.config_ntp_parameters(vars.D3, servers=data.ip_addresses[5], config=False):
            st.report_fail("msg", "Failed to configure NTP server parameters")
        st.banner("unbinding VRFs to interfaces")
        if not vrfapi.bind_vrf_interface(vars.D1, vrf_name=data.vrf_names[0], intf_name=data.loopback_intf_1, config = 'no'):
            st.report_fail("msg",
                           "Failed to unbind interface: {} to VRF: {}".format(data.loopback_intf_1, data.vrf_names[0]))
    elif st.get_func_name(request) == 'test_check_ntp_with_unreachable_server':
        ntp_obj.config_ntp_parameters(vars.D3, servers=data.unreachable_server, config=False)

def test_ft_verify_ntp_sych():
    """
    Verify the loopback ip address is assigned to mgmt-vrf and verify the switch acts as a NTP Server and client is in user-vrf.
    Verify the loopback ip address is assigned to mgmt-vrf and verify the switch acts as a NTP Server and client is in default-vrf.
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


def test_verify_switch_over_ntp_servers_working():
    st.banner("Configuring Loop-back interface")
    if not ipapi.config_loopback_interfaces(vars.D1, loopback_name=data.loopback_intf_1, config="yes"):
        st.report_fail("msg", "Failed to configure Loop-back interface: {}".format(data.loopback_intf_1))
    st.banner("Binding VRFs to interfaces")
    if not vrfapi.bind_vrf_interface(vars.D1, vrf_name=data.vrf_names[0], intf_name=data.loopback_intf_1):
        st.report_fail("msg", "Failed to bind interface: {} to VRF: {}".format(data.loopback_intf_1, data.vrf_names[0]))
    st.banner("IP Address configuration")
    if not ipapi.config_ip_addr_interface(vars.D1, interface_name=data.loopback_intf_1, ip_address=data.ip_addresses[5],
                                          subnet=data.subnets[0]):
        st.report_fail("msg", "Failed to configure IP: {}/{} on loopback interface: {}".format(data.ip_addresses[5],
                                                                                               data.subnets[0],
                                                                                               data.loopback_intf_1))
    st.banner("Route-Leak Configuration")
    if not ipapi.create_static_route(vars.D1, static_ip="{}/{}".format(data.ip_addresses[5], data.subnets[0]),
                                     interface=data.loopback_intf_1, nexthop_vrf=data.vrf_names[0]):
        st.report_fail("msg", "Failed to configure route leak")
    if not ipapi.create_static_route(vars.D3, next_hop=data.ip_addresses[3],
                                                       static_ip="{}/{}".format(data.ip_addresses[5],
                                                                                data.subnets[0])):
        st.report_fail("msg", "Failed to configure route leak")
    if not ipapi.delete_static_route(vars.D3, next_hop=data.ip_addresses[3],
                                                       static_ip="{}/{}".format(data.ip_addresses[0],
                                                                                data.subnets[0])):
        st.report_fail("msg", "Failed to unconfigure static route")
    st.banner("configuring ntp client")
    if not ntp_obj.config_ntp_parameters(vars.D1, source_intf=data.loopback_intf_1):
        st.report_fail("msg", "Failed to configure NTP server parameters")
    if not ntp_obj.config_ntp_parameters(vars.D3, source_intf=vars.D3D1P1, servers=data.ip_addresses[5]):
        st.report_fail("msg", "Failed to configure NTP server parameters")
    st.banner("Verifying the connectivity")
    if  ipapi.ping_poll(vars.D3, data.ip_addresses[0], iter=1):
        st.report_fail("msg", "passed ping Loop-back IP on DUT1 from DUT3")
    if not ipapi.ping_poll(vars.D3, data.ip_addresses[5], iter=3):
        st.report_fail("msg", "Failed to ping Loop-back IP on DUT1 from DUT3")
    if not poll_wait(ntp_obj.verify_ntp_synch, 100, vars.D3,
                     data.ip_addresses[5]):
        st.report_fail("msg", "NTP client-1 is not synch with NTP server")
    st.report_pass("test_case_passed")


def test_verify_rm_add_route_leak_in_user_vrf():
    st.banner("unconfiguring static route")
    if not ipapi.delete_static_route(vars.D1, next_hop=None, static_ip="{}/{}".format(data.ip_addresses[0], data.subnets[0]),
                                                        interface=data.loopback_intf, vrf=data.vrf_names[1], nexthop_vrf=data.vrf_names[0]):
        st.report_fail("msg", "Failed to unconfigure route leak")
    st.log("restart ntp service in client")
    st.config(vars.D2,"service ntp restart")
    st.banner("Verifying the connectivity")
    if ipapi.ping_poll(vars.D2, data.ip_addresses[0], iter=1):
        st.report_fail("msg", "Even after removing the leaked route successfully pinged Loop-back IP on DUT1 from DUT2")
    if poll_wait(ntp_obj.verify_ntp_synch, 30, vars.D2,
                     data.ip_addresses[0]):
        st.report_fail("msg", "Even after leaked route is removed NTP client-1 is synch with NTP server")
    st.banner("configuring static route")
    if not ipapi.create_static_route(vars.D1, vrf=data.vrf_names[1], static_ip="{}/{}".format(data.ip_addresses[0], data.subnets[0]),
                                                        interface=data.loopback_intf, nexthop_vrf=data.vrf_names[0]):
        st.report_fail("msg", "Failed to configure route leak")
    if not ipapi.ping_poll(vars.D2, data.ip_addresses[0], iter=3):
        st.report_fail("msg", "successfully pinged Loop-back IP on DUT1 from DUT2")
    st.log("restart ntp service in client")
    st.config(vars.D2,"service ntp restart")
    if not poll_wait(ntp_obj.verify_ntp_synch, 100, vars.D2,
                     data.ip_addresses[0]):
        st.report_fail("msg", "NTP client-1 is not synch with NTP server after adding route leak in user-vrf")
    st.report_pass("test_case_passed")


def test_check_ntp_authetication():
    """
    Verify NTP server is accepted if authentication keys match on NTP server and NTP client.
    Verify NTP server is rejected if authentication keys mismatch on NTP server and NTP client
    Verify that clients get syncing with NTP server, when one client is configured with authentication key and another client with out authentication key.
    """
    st.banner("Configure the NTP server authentication as MD5")
    if not ntp_obj.config_ntp_parameters(vars.D1, authenticate=True):
        st.report_fail("msg", "Failed to configure authenticate on NTP server")
    if not ntp_obj.config_ntp_parameters(vars.D1, auth_key_id=data.auth_key_id[0], auth_type=data.auth_type[0],
                                         auth_string=data.auth_string[0], trusted_key=data.trusted_key[0]):
        st.report_fail("msg", "Failed to configure auth-key, auth-type and trusted-key on NTP server")
    st.banner("Configure the NTP authentication on client-1(which is connected on non-default vrf) as MD5 ")
    if not ntp_obj.config_ntp_parameters(vars.D2, config=False, servers=data.ip_addresses[0]):
        st.report_fail("msg", "Failed to unconfigure server on client-1")
    if not ntp_obj.config_ntp_parameters(vars.D2, authenticate=True):
        st.report_fail("msg", "Failed to configure authenticate on client-1")
    if not ntp_obj.config_ntp_parameters(vars.D2, auth_key_id=data.auth_key_id[0], auth_type=data.auth_type[0],
                                         auth_string=data.auth_string[0], trusted_key=data.trusted_key[0],
                                         servers=data.ip_addresses[0],
                                         server_key=data.auth_key_id[0]):
        st.report_fail("msg", "Failed to configure auth-key, auth-type and trusted-key on client-1")
    if not poll_wait(ntp_obj.verify_ntp_synch, 100, vars.D2,
                     data.ip_addresses[0]):
        st.report_fail("msg", "NTP client-1 is not synch with NTP server")
    st.banner(
        "Checking that  client-2(with out Authentication) is syncing with server, which is created with authentication")
    if not ntp_obj.config_ntp_parameters(vars.D3, servers=data.ip_addresses[0], config=False):
        st.report_fail("msg", "Failed to unconfigure server on client-1")
    if not ntp_obj.config_ntp_parameters(vars.D3, servers=data.ip_addresses[0]):
        st.report_fail("msg", "Failed to configure server on client-1")
    if not poll_wait(ntp_obj.verify_ntp_synch, 100, vars.D3,
                     data.ip_addresses[0]):
        st.report_fail("msg",
                       "NTP is not synching with NTP server even the authentication is None in client and present in server")
    st.banner("Checking the client is not synching with server when authentication-key mismatch")
    if not ntp_obj.config_ntp_parameters(vars.D2, servers=data.ip_addresses[0], config=False):
        st.report_fail("msg", "Failed to unconfigure server on client-1")
    st.wait(2,"to sync the changes done")
    if not ntp_obj.config_ntp_parameters(vars.D2, trusted_key=data.trusted_key[0], config=False):
        st.report_fail("msg", "Failed to unconfigure trusted-key on client-1")
    if not ntp_obj.config_ntp_parameters(vars.D2, auth_key_id=data.auth_key_id[0], config=False):
        st.report_fail("msg", "Failed to unconfigure auth-key, auth-type  on client-1")
    if not ntp_obj.config_ntp_parameters(vars.D2, auth_key_id=data.auth_key_id[1], auth_type=data.auth_type[0],
                                         auth_string=data.auth_string[0],
                                         trusted_key=data.trusted_key[1], servers=data.ip_addresses[0],
                                         server_key=data.auth_key_id[1]):
        st.report_fail("msg", "Failed to configure auth-key, auth-type and trusted-key on client-1")
    if poll_wait(ntp_obj.verify_ntp_synch, 80, vars.D2,
                 data.ip_addresses[0]):
        st.report_fail("msg", "NTP client is synch with NTP server")
    st.banner("Checking the client is not synching with server when auth-type mismatch")
    if not ntp_obj.config_ntp_parameters(vars.D2, servers=data.ip_addresses[0], config=False):
        st.report_fail("msg", "Failed to unconfigure server on client-1")
    st.wait(2,"to sync the changes done")
    if not ntp_obj.config_ntp_parameters(vars.D2, trusted_key=data.trusted_key[1], config=False):
        st.report_fail("msg", "Failed to unconfigure trusted-key on client-1")
    if not ntp_obj.config_ntp_parameters(vars.D2, auth_key_id=data.auth_key_id[1], config=False):
        st.report_fail("msg", "Failed to unconfigure auth-key, auth-type  on client-1")
    if not ntp_obj.config_ntp_parameters(vars.D2, auth_key_id=data.auth_key_id[0], auth_type=data.auth_type[1],
                                         auth_string=data.auth_string[0], trusted_key=data.trusted_key[0],
                                         servers=data.ip_addresses[0], server_key=data.auth_key_id[0]):
        st.report_fail("msg", "Failed to configure auth-key, auth-type and trusted-key on client-1")
    if poll_wait(ntp_obj.verify_ntp_synch, 80, vars.D2,
                 data.ip_addresses[0]):
        st.report_fail("msg", "NTP client is synch with NTP server")
    st.banner("Checking the client is not synching with server when auth-string mismatch")
    if not ntp_obj.config_ntp_parameters(vars.D2, servers=data.ip_addresses[0], config=False):
        st.report_fail("msg", "Failed to unconfigure server on client-1")
    st.wait(2,"to sync the changes done")
    if not ntp_obj.config_ntp_parameters(vars.D2, trusted_key=data.trusted_key[0], config=False):
        st.report_fail("msg", "Failed to unconfigure trusted-key on client-1")
    if not ntp_obj.config_ntp_parameters(vars.D2, auth_key_id=data.auth_key_id[0], config=False):
        st.report_fail("msg", "Failed to unconfigure auth-key, auth-type  on client-1")
    if not ntp_obj.config_ntp_parameters(vars.D2, auth_key_id=data.auth_key_id[0], auth_type=data.auth_type[0],
                                         auth_string=data.auth_string[1],
                                         trusted_key=data.trusted_key[0], servers=data.ip_addresses[0],
                                         server_key=data.auth_key_id[0]):
        st.report_fail("msg", "Failed to configure auth-key, auth-type and trusted-key on client-1")
    if poll_wait(ntp_obj.verify_ntp_synch, 80, vars.D2,
                 data.ip_addresses[0]):
        st.report_fail("msg", "NTP client is synch with NTP server")
    st.banner("Checking the client is not synching with server when authentication is not enabled in server")
    if not ntp_obj.config_ntp_parameters(vars.D2, servers=data.ip_addresses[0], config=False):
        st.report_fail("msg", "Failed to unconfigure server on client-1")
    st.wait(2,"to sync the changes done")
    if not ntp_obj.config_ntp_parameters(vars.D2, trusted_key=data.trusted_key[0], config=False):
        st.report_fail("msg", "Failed to unconfigure trusted-key on client-1")
    if not ntp_obj.config_ntp_parameters(vars.D2, auth_key_id=data.auth_key_id[0], config=False):
        st.report_fail("msg", "Failed to unconfigure auth-key, auth-type  on client-1")
    if not ntp_obj.config_ntp_parameters(vars.D1, authenticate=False, config=False):
        st.report_fail("msg", "Failed to unconfigure authenticate on client-1")
    if not ntp_obj.config_ntp_parameters(vars.D2, auth_key_id=data.auth_key_id[0], auth_type=data.auth_type[0],
                                         auth_string=data.auth_string[0],
                                         trusted_key=data.trusted_key[0], servers=data.ip_addresses[0],
                                         server_key=data.auth_key_id[0]):
        st.report_fail("msg", "Failed to configure auth-key, auth-type and trusted-key on client-1")
    if poll_wait(ntp_obj.verify_ntp_synch, 80, vars.D2,
                 data.ip_addresses[0]):
        st.report_fail("msg", "NTP client is synch with NTP server, even though no authenticate disabled in server")
    st.banner("Checking the client is not synching with server, if trusted key is not configure in client")
    if not ntp_obj.config_ntp_parameters(vars.D2, servers=data.ip_addresses[0], config=False):
        st.report_fail("msg", "Failed to unconfigure server on client-1")
    st.wait(2,"to sync the changes done")
    if not ntp_obj.config_ntp_parameters(vars.D2, trusted_key=data.trusted_key[0], config=False):
        st.report_fail("msg", "Failed to unconfigure trusted-key on client-1")
    if not ntp_obj.config_ntp_parameters(vars.D2, auth_key_id=data.auth_key_id[0], config=False):
        st.report_fail("msg", "Failed to unconfigure auth-key, auth-type  on client-1")
    if not ntp_obj.config_ntp_parameters(vars.D1, authenticate='authenticate'):
        st.report_fail("msg", "Failed to configure  authenticate on client-1")
    if not ntp_obj.config_ntp_parameters(vars.D2, auth_key_id=data.auth_key_id[0], auth_type=data.auth_type[0],
                                         auth_string=data.auth_string[0],
                                         servers=data.ip_addresses[0], server_key=data.auth_key_id[0]):
        st.report_fail("msg", "Failed to configure auth-key, auth-type and trusted-key on client-1")
    if poll_wait(ntp_obj.verify_ntp_synch, 80, vars.D2,
                 data.ip_addresses[0]):
        st.report_fail("msg", "NTP client is synch with NTP server, even though trusted key is not configure in client-1")
    st.banner(
        "Checking the client is  synching with server, when both server and client  authentication type configured as sha1")
    if not ntp_obj.config_ntp_parameters(vars.D1, trusted_key=data.trusted_key[0], config=False):
        st.report_fail("msg", "Failed to unconfigure trusted-key on client-1")
    if not ntp_obj.config_ntp_parameters(vars.D1, auth_key_id=data.auth_key_id[0], config=False):
        st.report_fail("msg", "Failed to unconfigure auth-key, auth-type  on client-1")
    if not ntp_obj.config_ntp_parameters(vars.D2, servers=data.ip_addresses[0], config=False):
        st.report_fail("msg", "Failed to unconfigure server on client-1")
    st.wait(2,"to sync the changes done")
    if not ntp_obj.config_ntp_parameters(vars.D2, trusted_key=data.trusted_key[0], config=False):
        st.report_fail("msg", "Failed to unconfigure trusted-key on client-1")
    if not ntp_obj.config_ntp_parameters(vars.D2, auth_key_id=data.auth_key_id[0], config=False):
        st.report_fail("msg", "Failed to unconfigure auth-key, auth-type  on client-1")
    if not ntp_obj.config_ntp_parameters(vars.D1, auth_key_id=data.auth_key_id[0], auth_type=data.auth_type[1],
                                         auth_string=data.auth_string[0],
                                         trusted_key=data.trusted_key[0]):
        st.report_fail("msg", "Failed to configure auth-key, auth-type and trusted-key on client-1")
    if not ntp_obj.config_ntp_parameters(vars.D2, auth_key_id=data.auth_key_id[0], auth_type=data.auth_type[1],
                                         auth_string=data.auth_string[0],
                                         trusted_key=data.trusted_key[0], servers=data.ip_addresses[0],
                                         server_key=data.auth_key_id[0]):
        st.report_fail("msg", "Failed to configure auth-key, auth-type and trusted-key on client-1")
    if not poll_wait(ntp_obj.verify_ntp_synch, 100, vars.D2,
                     data.ip_addresses[0]):
        st.report_fail("msg", "NTP client is  not synch with NTP server with auth-type sh1")
    st.banner(
        "Checking the client is  synching with server, when both server and client  authentication type configured as sha2-256")
    if not ntp_obj.config_ntp_parameters(vars.D1, trusted_key=data.trusted_key[0], config=False):
        st.report_fail("msg", "Failed to unconfigure trusted-key on server")
    if not ntp_obj.config_ntp_parameters(vars.D1, auth_key_id=data.auth_key_id[0], config=False):
        st.report_fail("msg", "Failed to unconfigure auth-key, auth-type  on server")
    if not ntp_obj.config_ntp_parameters(vars.D2, servers=data.ip_addresses[0], config=False):
        st.report_fail("msg", "Failed to unconfigure server on client-1")
    st.wait(2,"to sync the changes done")
    if not ntp_obj.config_ntp_parameters(vars.D2, trusted_key=data.trusted_key[0], config=False):
        st.report_fail("msg", "Failed to unconfigure trusted-key on client-1")
    if not ntp_obj.config_ntp_parameters(vars.D2, auth_key_id=data.auth_key_id[0], config=False):
        st.report_fail("msg", "Failed to unconfigure auth-key, auth-type  on client-1")
    if not ntp_obj.config_ntp_parameters(vars.D1, auth_key_id=data.auth_key_id[0], auth_type=data.auth_type[2],
                                         auth_string=data.auth_string[0],
                                         trusted_key=data.trusted_key[0]):
        st.report_fail("msg", "Failed to configure auth-key, auth-type and trusted-key on client-1")
    if not ntp_obj.config_ntp_parameters(vars.D2, auth_key_id=data.auth_key_id[0], auth_type=data.auth_type[2],
                                         auth_string=data.auth_string[0],
                                         trusted_key=data.trusted_key[0], servers=data.ip_addresses[0],
                                         server_key=data.auth_key_id[0]):
        st.report_fail("msg", "Failed to configure auth-key, auth-type and trusted-key on client-1")
    if not poll_wait(ntp_obj.verify_ntp_synch, 100, vars.D2, data.ip_addresses[0]):
        st.report_fail("msg", "NTP client is  not synch with NTP server")
    st.report_pass("test_case_passed")


def test_verify_ntp_synch_after_shut_no_shut():
    """
    verify that NTP synchronizes again, when interface link down and up.
    Author:
    """
    if not ntp_obj.config_ntp_parameters(vars.D1, trusted_key=data.trusted_key[0], config=False):
        st.report_fail("msg", "Failed to unconfigure  trusted-key on server")
    if not ntp_obj.config_ntp_parameters(vars.D1,  auth_key_id=data.auth_key_id[0], config=False):
        st.report_fail("msg", "Failed to unconfigure auth-key on server")
    if not ntp_obj.config_ntp_parameters(vars.D2, trusted_key=data.trusted_key[0], servers=data.ip_addresses[0], config=False):
        st.report_fail("msg", "Failed to unconfigure  trusted-key on client-1")
    if not ntp_obj.config_ntp_parameters(vars.D2,  auth_key_id=data.auth_key_id[0], config=False):
        st.report_fail("msg", "Failed to unconfigure auth-key on server")
    if not ntp_obj.config_ntp_parameters(vars.D2, servers=data.ip_addresses[0]):
        st.report_fail("msg", "Failed to configure server on client-1")

    st.debug("Verify whether the NTP got synch or not")
    [output, exceptions] = exec_all(True,
                                [ExecAllFunc(poll_wait, ntp_obj.verify_ntp_synch, 100, vars.D1, data.ntp_master),
                                 ExecAllFunc(poll_wait, ntp_obj.verify_ntp_synch, 100, vars.D2,
                                             data.ip_addresses[0])])
    ensure_no_exception(exceptions)
    if not all(output):
        st.report_fail("msg", "NTP is not synchronized")

    st.debug("Shutdown and no-shutdown the inter-connect port")
    interface_operation(vars.D2, vars.D2D1P1, operation="shutdown")
    interface_operation(vars.D2, vars.D2D1P1, operation="startup")
    st.wait(10)
    st.debug("Verify whether the NTP got synch or not")
    [output, exceptions] = exec_all(True,
                                [ExecAllFunc(poll_wait, ntp_obj.verify_ntp_synch, 100, vars.D1, data.ntp_master),
                                 ExecAllFunc(poll_wait, ntp_obj.verify_ntp_synch, 100, vars.D2,
                                             data.ip_addresses[0])])
    ensure_no_exception(exceptions)
    if not all(output):
        st.report_fail("msg", "NTP is not synchronized after shut and no shut of inter-connect port")
    [output, exceptions] = exec_all(True, [[ntp_obj.show_clock, vars.D1], [ntp_obj.show_clock, vars.D2]])
    ensure_no_exception(exceptions)
    if not ntp_obj.verify_time_synch(output[0], output[1]):
        st.report_fail("msg", "The server and client(default VRF) times are not in synch")
    st.report_pass("test_case_passed")


def test_verify_ntp_synch_after_save_reload():
    """
    Verify that the save and reload works with time sync (client and server).
    Author:
    """
    st.debug("Save and reload the configuration")
    reboot_obj.config_save_reload([vars.D1, vars.D2, vars.D3])
    st.log("verify ping is successful after reboot")
    st.banner("Verifying the connectivity")
    if not ipapi.ping_poll(vars.D2, data.ip_addresses[0], iter=3):
        st.report_fail("msg", "Failed to ping Loop-back IP on DUT1 from DUT2")
    if not ipapi.ping_poll(vars.D3, data.ip_addresses[0], iter=3):
        st.report_fail("msg", "Failed to ping Loop-back IP on DUT1 from DUT3")
    [output, exceptions] = exec_all(True,
                                    [ExecAllFunc(poll_wait, ntp_obj.verify_ntp_synch, 100, vars.D1, data.ntp_master),
                                     ExecAllFunc(poll_wait, ntp_obj.verify_ntp_synch, 100, vars.D2,
                                                 data.ip_addresses[0]),
                                     ExecAllFunc(poll_wait, ntp_obj.verify_ntp_synch, 100, vars.D3,
                                                 data.ip_addresses[0])])
    ensure_no_exception(exceptions)
    if not all(output):
        st.report_fail("msg", "NTP is not synchronized after save reload of the DUTs")
    st.report_pass("test_case_passed")


def test_verify_ntp_synch_after_warm_boot():
    """
    Verify that the NTP configuration is retained and  works fine after warmboot (client and server).
    Author:
    """
    st.debug("Warm-boot the device")
    st.reboot(vars.D1, 'warm')
    if not poll_wait(ntp_obj.verify_ntp_synch, 100, vars.D1, data.ntp_master):
        st.report_fail("msg", "NTP client is not synch with NTP server after warm reboot.")
    st.report_pass('test_case_passed')


def test_verify_ntp_synch_after_fast_boot():
    """
    Verify that the NTP configuration is retained and  works fine after fastboot (client and server).
    Author:
    """
    st.debug("Fast-boot the device")
    st.reboot(vars.D3, 'fast')
    st.log("verify ping is successful after reboot")
    st.banner("Verifying the connectivity")
    if not ipapi.ping_poll(vars.D3, data.ip_addresses[0], iter=3):
        st.report_fail("msg", "Failed to ping Loop-back IP on DUT1 from DUT3")
    if not poll_wait(ntp_obj.verify_ntp_synch, 120, vars.D3,  data.ip_addresses[0]):
        st.report_fail("msg", "NTP client is not synch with NTP server after fast reboot.")
    st.report_pass('test_case_passed')


def test_check_ntp_with_unreachable_server():
    """
    Verify the behavior of client when unreachable NTP server is configured.
    """
    if poll_wait(ntp_obj.verify_ntp_synch, 30, vars.D3, data.unreachable_server):
        st.report_fail("msg", "NTP got synch with unreachable NTP server")
    st.report_pass("test_case_passed")


def test_verify_ntp_server_client_sync_when_eth0_and_client_in_default_vrf():
    st.banner("Configuring Loop-back interface")
    if not ipapi.config_loopback_interfaces(vars.D1, loopback_name=data.loopback_intf, config="yes"):
        st.report_fail("msg", "Failed to configure Loop-back interface: {}".format(data.loopback_intf))

    st.banner("IP Address configuration")
    if not ipapi.config_ip_addr_interface(vars.D1, interface_name=data.loopback_intf, ip_address=data.ip_addresses[0],
                                          subnet=data.subnets[0]):
        st.report_fail("msg", "Failed to configure IP: {}/{} on loopback interface: {}".format(data.ip_addresses[0],
                                                                                               data.subnets[0],
                                                                                               data.loopback_intf))
    dict1 = {"interface_name": vars.D1D2P1, "ip_address": data.ip_addresses[1],
             "subnet": data.subnets[1]}
    dict2 = {"interface_name": vars.D2D1P1, "ip_address": data.ip_addresses[2],
             "subnet": data.subnets[1]}
    [output, exceptions] = exec_parallel(True, [vars.D1, vars.D2], ipapi.config_ip_addr_interface, [dict1, dict2])
    ensure_no_exception(exceptions)
    if not all(output):
        st.report_fail("msg", "Failed to configure IP addresses on interfaces")
    st.banner("static route Configuration")
    if not ipapi.create_static_route(vars.D1, static_ip="{}/{}".format(data.ip_addresses[1], data.subnets[1]),
                                     next_hop=data.ip_addresses[2]):
        st.report_fail("msg", "Failed to configure static route")
    if not ipapi.create_static_route(vars.D2, static_ip="{}/{}".format(data.ip_addresses[0], data.subnets[0]),
                                     next_hop=data.ip_addresses[1]):
        st.report_fail("msg", "Failed to configure static route")
    if not ipapi.ping_poll(vars.D2, data.ip_addresses[0], iter=3):
        st.report_fail("msg", "Failed to ping Loop-back IP on DUT1 from DUT2")
    st.debug("Verify whether the NTP got synch or not")
    st.debug("NTP Configuration")
    dict1 = {'source_intf': ['Management0', data.loopback_intf], 'servers': data.ntp_master}
    dict2 = {'source_intf': vars.D2D1P1, 'servers': data.ip_addresses[0]}
    if not ntp_obj.config_ntp_parameters(vars.D1, **dict1):
        st.report_fail("msg", "Failed to configure NTP server")
    if not ntp_obj.config_ntp_parameters(vars.D2, **dict2):
        st.report_fail("msg", "Failed to configure NTP client")
    if not poll_wait(ntp_obj.verify_ntp_synch, 100, vars.D1,
                     data.ntp_master):
        st.report_fail("msg", "NTP client-1 is not synch with NTP server")
    if not poll_wait(ntp_obj.verify_ntp_synch, 120, vars.D2,
                 data.ip_addresses[0]):
        st.report_fail("msg", "NTP client-1 is not synch with NTP server")
        st.banner(
        "remove and re configure the ip address on the source interface (Loopback interface) and check the wheather sync between client and server is  happening")
    st.banner("IP Address unconfiguration on loopback")
    if not ipapi.config_ip_addr_interface(vars.D1, interface_name=data.loopback_intf, ip_address=data.ip_addresses[0],
                                      subnet=data.subnets[0], config='remove'):
        st.report_fail("msg", "Failed to unconfigure IP: {}/{} on loopback interface: {}".format(data.ip_addresses[0],
                                                                                             data.subnets[0],
                                                                                             data.loopback_intf))
    st.banner("IP Address configuration on loopback")
    if not ipapi.config_ip_addr_interface(vars.D1, interface_name=data.loopback_intf, ip_address=data.ip_addresses[0],
                                          subnet=data.subnets[0]):
        st.report_fail("msg", "Failed to configure IP: {}/{} on loopback interface: {}".format(data.ip_addresses[0],
                                                                                               data.subnets[0],
                                                                                               data.loopback_intf))
    if not poll_wait(ntp_obj.verify_ntp_synch, 100, vars.D2,
                     data.ip_addresses[0]):
        st.report_fail("msg", "NTP client-1 is not synch with NTP server")
    st.banner("Unconfiguring static route to server on  client")
    if not ipapi.delete_static_route(vars.D2, next_hop=data.ip_addresses[1], static_ip="{}/{}".format(data.ip_addresses[0], data.subnets[0])):
        st.report_fail("msg", "Failed to unconfigure static route")
    if ipapi.ping_poll(vars.D2, data.ip_addresses[0], iter=3):
        st.report_fail("msg", "Even after removing the route to Server ip, successfully  pinged to Loop-back IP on DUT1 from DUT2")
    st.banner("configuring static route to server on  client")
    if not ipapi.create_static_route(vars.D2, static_ip="{}/{}".format(data.ip_addresses[0], data.subnets[0]),
                                     next_hop=data.ip_addresses[1]):
        st.report_fail("msg", "Failed to configure static route")
    if not ipapi.ping_poll(vars.D2, data.ip_addresses[0], iter=3):
        st.report_fail("msg", "Failed to ping Loop-back IP on DUT1 from DUT2")
    if not poll_wait(ntp_obj.verify_ntp_synch, 100, vars.D2,
                     data.ip_addresses[0]):
        st.report_fail("msg", "NTP client-1 is not synch with NTP server when eth0 and client in default vrf")
    st.report_pass("test_case_passed")


def test_verify_ntp_server_client_sync_when_port_channel_configured():
    st.banner("Remove IP Address configuration")
    dict1 = {"interface_name": vars.D1D2P1, "ip_address": data.ip_addresses[1],
             "subnet": data.subnets[1], "config": "remove"}
    dict2 = {"interface_name": vars.D2D1P1, "ip_address": data.ip_addresses[2],
             "subnet": data.subnets[1], "config": "remove"}
    [output, exceptions] = exec_parallel(True, [vars.D1, vars.D2], ipapi.config_ip_addr_interface, [dict1, dict2])
    ensure_no_exception(exceptions)
    if not all(output):
        st.report_fail("msg", "Failed to unconfigure IP addresses on interfaces")
    dict3 = {'source_intf': vars.D2D1P1, 'servers': data.ip_addresses[0], 'config':False}
    if not ntp_obj.config_ntp_parameters(vars.D2, **dict3):
        st.report_fail("msg", "Failed to unconfigure NTP client")
    pc_obj.config_portchannel(vars.D1, vars.D2, data.port_channel, [vars.D1D2P1],[vars.D2D1P1], config='add', thread=True)
    dict1 = {"interface_name": data.port_channel, "ip_address": data.ip_addresses[1],
             "subnet": data.subnets[1], "config": "add"}
    dict2 = {"interface_name": data.port_channel, "ip_address": data.ip_addresses[2],
             "subnet": data.subnets[1], "config": "add"}
    [output, exceptions] = exec_parallel(True, [vars.D1, vars.D2], ipapi.config_ip_addr_interface, [dict1, dict2])
    ensure_no_exception(exceptions)
    if not all(output):
        st.report_fail("msg", "Failed to configure IP addresses on portchannel interfaces")
    st.banner("static route Configuration")
    if not ipapi.create_static_route(vars.D2, static_ip="{}/{}".format(data.ip_addresses[0], data.subnets[1]),
                                     next_hop=data.ip_addresses[1]):
        st.report_fail("msg", "Failed to configure static route")
    dict2 = {'source_intf': data.port_channel, 'servers': data.ip_addresses[0], 'config': True}
    if not ntp_obj.config_ntp_parameters(vars.D2, **dict2):
        st.report_fail("msg", "Failed to configure NTP client with source-interface as porthcannel")
    if not poll_wait(ntp_obj.verify_ntp_synch, 100, vars.D2,
                     data.ip_addresses[0]):
        st.report_fail("msg", "NTP client-1 is not synch with NTP server when source-interface as porthcannel")
    st.report_pass("test_case_passed")


def test_verify_ntp_with_vrf_and_with_out_vrf():
    st.banner("Configuring Loop-back interface")
    if not ipapi.config_loopback_interfaces(vars.D3, loopback_name=data.loopback_intf, config="yes"):
        st.report_fail("msg", "Failed to configure Loop-back interface: {}".format(data.loopback_intf))
    st.banner("Configuring Ip-address to loopback")
    if not ipapi.config_ip_addr_interface(vars.D3, interface_name=data.loopback_intf,
                                              ip_address=data.ip_addresses[0],
                                              subnet=data.subnets[0]):
        st.report_fail("msg", "Failed to configure IP: {}/{} on loopback interface: {}".format(data.ip_addresses[0],
                                                                                                   data.subnets[0], data.loopback_intf))
    st.banner("Configuring ntp server")
    if not ntp_obj.config_ntp_parameters(vars.D3,  servers= data.ntp_master):
        st.report_fail("msg", "Failed to configure NTP server")
    if poll_wait(ntp_obj.verify_ntp_synch, 30, vars.D3,
                     data.ntp_master):
        st.report_fail("msg", "NTP client-2 is  synch with NTP server, even though eth0 is  not configured as source-interface")
    st.banner("configuring eth0 as source interface")
    if not ntp_obj.config_ntp_parameters(vars.D3, source_intf="Management0"):
        st.report_fail("msg", "Failed to configure eth0 as source_intf")
    if not poll_wait(ntp_obj.verify_ntp_synch, 100, vars.D3,
                     data.ntp_master):
        st.report_fail("msg", "NTP client-2 is not synch with NTP server")
    st.banner("setting ntp vrf to mgmt, without configuring mgmt vrf")
    if ntp_obj.config_ntp_parameters(vars.D3, vrf=data.vrf_names[0], skip_error=True):
        st.report_fail("msg", "even  though mgmt is not exist the device accepting the command NTP vrf mgmt")
    if not ntp_obj.config_ntp_parameters(vars.D3, servers= data.ntp_master, config=False):
        st.report_fail("msg", "Failed to unconfigure NTP server")
    st.banner("binding  eth0 to mgmt")
    if not vrfapi.config_vrf(vars.D3, vrf_name=data.vrf_names[0]):
        st.report_fail("msg", "Failed to configure VRFs")
    if not ntp_obj.config_ntp_parameters(vars.D3, vrf=data.vrf_names[0]):
        st.report_fail("msg", "Failed to configure NTP vrf mgmt")
    if not ntp_obj.config_ntp_parameters(vars.D3, source_intf = "Management0", servers= data.ntp_master):
        st.report_fail("msg", "Failed to configure NTP server")
    if not poll_wait(ntp_obj.verify_ntp_synch, 100, vars.D3,
                     data.ntp_master):
        st.report_fail("msg", "NTP client-2 is not synch with NTP server after enabling ntp vrf mgmt")
    st.banner("setting ntp vrf to default, with eth0 in mgmt vrf")
    if not ntp_obj.config_ntp_parameters(vars.D3, vrf=data.default):
        st.report_fail("msg", "Failed to configure NTP vrf default")
    if poll_wait(ntp_obj.verify_ntp_synch, 30, vars.D3,
                     data.ntp_master):
        st.report_fail("msg", "NTP client-2 is  synch with NTP server, even though ntp vrf is set default with eth0 in mgmt vrf")
    st.report_pass("test_case_passed")
