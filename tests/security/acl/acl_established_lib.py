import re
from spytest import st, tgapi
import apis.routing.ip as ip
from apis.system import basic
import apis.qos.acl as acl_obj
import apis.system.connection as con_obj
import spytest.access.sonic_connection as sonic_obj

acl_dict = {"dut1" : {"ip_addr_list" : ["12.12.1.1","12.12.2.1","10.10.10.1","10.10.10.2"], 
                      "ip_mask_list" : ["24","24","24","24"], "dname" : "dut1",
                      "prefix_list" : ["12.12.1.0/24","12.12.2.0/24","10.10.10.0/24"],
                      "ipv6_addr_list" : ["1212:01::01","1212:02::01","1010::01","1010::02"],
                      "ipv6_mask_list" : ["96","96","96","96"], 
                      "prefix_v6_list" : ["1212:01::/96","1212:02::/96","1010::01/96"],
                      "mac_addr_list" : ["00.04.01.00.00.01","00.06.01.00.00.01"]},
            "dut2" : {"ip_addr_list" : ["12.12.1.2","12.12.2.2","13.13.1.2","13.13.2.2"], 
                      "ip_mask_list" : ["24","24","24","24"], "prefix_list" : ["12.12.1.0/24",
                                               "12.12.2.0/24","13.13.1.0/24","13.13.2.0/24"],
                      "ipv6_addr_list" : ["1212:01::02","1212:02::02","1313:01::02","1313:02::02"],
                      "ipv6_mask_list" : ["96","96","96","96"], "prefix_v6_list" : ["1212:01::/96",
                                               "1212:02::/96","1313:01::/96","1313:02::/96"],   
                      "acl_name" : "acl_est", "dname" : "dut2", "port" : "2000",
                      "acl_name_v6" : "acl_est_v6"},
            "dut3" : {"ip_addr_list" : ["13.13.1.3","13.13.2.3","30.30.30.1","30.30.30.2"], 
                      "ip_mask_list" : ["24","24","24","24"],"dname" : "dut3",
                      "prefix_list" : ["13.13.1.0/24","13.13.2.0/24","30.30.30.0/24"],
                      "ipv6_addr_list" : ["1313:01::01","1313:02::01","3030::01","3030::02"],
                      "ipv6_mask_list" : ["96","96","96","96"],
                      "prefix_v6_list" : ["1313:01::/96","1313:02::/96","3030::01/96"],
                      "mac_addr_list" : ["00.04.03.00.00.01","00.06.03.00.00.01"]}}
tg_dict = {}
stream_dict = {}

def create_glob_vars():
    global vars
    vars = st.ensure_min_topology("D1D2:2","D2D3:2","D1T1:1","D3T1:1")
    tg_dict["tg"], tg_dict["d1_tg_ph1"] = tgapi.get_handle_byname("T1D1P1")
    tg_dict["tg"], tg_dict["d3_tg_ph1"] = tgapi.get_handle_byname("T1D3P1")
    tg_dict["d1_tg_port1"],tg_dict["d3_tg_port1"] = vars.T1D1P1, vars.T1D3P1
    tg_dict["tgen_rate_pps"] = '1000'
    tg_dict["l3_len"] = '512'
    tg_dict["duration"] = 5
    acl_dict["dut_list"] = [vars.D1, vars.D2, vars.D3]
    acl_dict["dut1"]["intf_list_tg"] = [vars.D1T1P1]
    acl_dict["dut1"]["intf_list_dut2"] = [vars.D1D2P1, vars.D1D2P2]
    acl_dict["dut2"]["intf_list_tg"] = [vars.D2T1P1]
    acl_dict["dut2"]["intf_list_dut1"] = [vars.D2D1P1, vars.D2D1P2]
    acl_dict["dut2"]["intf_list_dut3"] = [vars.D2D3P1, vars.D2D3P2]
    acl_dict["dut3"]["intf_list_tg"] = [vars.D3T1P1]
    acl_dict["dut3"]["intf_list_dut2"] = [vars.D3D2P1, vars.D3D2P2]
    acl_dict["dut1_gw_mac"] = basic.get_ifconfig(vars.D1, vars.D1T1P1)[0]['mac']
    acl_dict["dut3_gw_mac"] = basic.get_ifconfig(vars.D3, vars.D3T1P1)[0]['mac']
    d1_out = st.get_credentials(vars.D1)
    d3_out = st.get_credentials(vars.D3)
    acl_dict["d1_uname"] = d1_out[0]
    acl_dict["d3_uname"] = d3_out[0]
    acl_dict["d1_pwd"] = d1_out[3]
    acl_dict["d3_pwd"] = d3_out[3]
    tg_dict["live_stream"] = ""

 
def setup_dut_config():
    st.exec_all([[dut1_ip_addr_config], [dut2_ip_addr_config], [dut3_ip_addr_config]])
    st.exec_all([[dut1_static_route_config], [dut2_static_route_config], [dut3_static_route_config]])
    st.exec_all([[dut1_ipv6_addr_config], [dut2_ipv6_addr_config], [dut3_ipv6_addr_config]])
    st.exec_all([[dut1_static_route_v6_config], [dut2_static_route_v6_config], 
                                               [dut3_static_route_v6_config]])


def dut1_ip_addr_config():
    st.log("config IP address in DUT1")
    ip.config_ip_addr_interface(dut=acl_dict["dut_list"][0],
                                interface_name=acl_dict["dut1"]["intf_list_dut2"][0],
                                ip_address=acl_dict["dut1"]["ip_addr_list"][0],
                                subnet=acl_dict["dut1"]["ip_mask_list"][0])
    ip.config_ip_addr_interface(dut=acl_dict["dut_list"][0],
                                interface_name=acl_dict["dut1"]["intf_list_dut2"][1],
                                ip_address=acl_dict["dut1"]["ip_addr_list"][1],
                                subnet=acl_dict["dut1"]["ip_mask_list"][1])
    ip.config_ip_addr_interface(dut=acl_dict["dut_list"][0],
                                interface_name=acl_dict["dut1"]["intf_list_tg"][0],
                                ip_address=acl_dict["dut1"]["ip_addr_list"][2],
                                subnet=acl_dict["dut1"]["ip_mask_list"][2])


def dut1_static_route_config():
    st.log("config static route in DUT1")
    ip.create_static_route(dut=acl_dict["dut_list"][0], next_hop=acl_dict["dut2"]["ip_addr_list"][0],
                           static_ip=acl_dict["dut3"]["prefix_list"][0])
    ip.create_static_route(dut=acl_dict["dut_list"][0], next_hop=acl_dict["dut2"]["ip_addr_list"][1],
                           static_ip=acl_dict["dut3"]["prefix_list"][0])
    ip.create_static_route(dut=acl_dict["dut_list"][0], next_hop=acl_dict["dut2"]["ip_addr_list"][0],
                           static_ip=acl_dict["dut3"]["prefix_list"][1])
    ip.create_static_route(dut=acl_dict["dut_list"][0], next_hop=acl_dict["dut2"]["ip_addr_list"][1],
                           static_ip=acl_dict["dut3"]["prefix_list"][1])
    ip.create_static_route(dut=acl_dict["dut_list"][0], next_hop=acl_dict["dut2"]["ip_addr_list"][0],
                           static_ip=acl_dict["dut3"]["prefix_list"][2])


def dut1_ipv6_addr_config():
    st.log("config IPv6 address in DUT1")
    ip.config_ip_addr_interface(dut=acl_dict["dut_list"][0],
                                interface_name=acl_dict["dut1"]["intf_list_dut2"][0],
                                ip_address=acl_dict["dut1"]["ipv6_addr_list"][0],
                                subnet=acl_dict["dut1"]["ipv6_mask_list"][0],family="ipv6")
    ip.config_ip_addr_interface(dut=acl_dict["dut_list"][0],
                                interface_name=acl_dict["dut1"]["intf_list_dut2"][1],
                                ip_address=acl_dict["dut1"]["ipv6_addr_list"][1],
                                subnet=acl_dict["dut1"]["ipv6_mask_list"][1],family="ipv6")
    ip.config_ip_addr_interface(dut=acl_dict["dut_list"][0],
                                interface_name=acl_dict["dut1"]["intf_list_tg"][0],
                                ip_address=acl_dict["dut1"]["ipv6_addr_list"][2],
                                subnet=acl_dict["dut1"]["ipv6_mask_list"][2],family="ipv6")


def dut1_static_route_v6_config():
    st.log("config IPv6 static route in DUT1")
    ip.create_static_route(dut=acl_dict["dut_list"][0], next_hop=acl_dict["dut2"]["ipv6_addr_list"][0],
                           static_ip=acl_dict["dut3"]["prefix_v6_list"][0], family="ipv6")
    ip.create_static_route(dut=acl_dict["dut_list"][0], next_hop=acl_dict["dut2"]["ipv6_addr_list"][1],
                           static_ip=acl_dict["dut3"]["prefix_v6_list"][0], family="ipv6")
    ip.create_static_route(dut=acl_dict["dut_list"][0], next_hop=acl_dict["dut2"]["ipv6_addr_list"][0],
                           static_ip=acl_dict["dut3"]["prefix_v6_list"][1], family="ipv6")
    ip.create_static_route(dut=acl_dict["dut_list"][0], next_hop=acl_dict["dut2"]["ipv6_addr_list"][1],
                           static_ip=acl_dict["dut3"]["prefix_v6_list"][1], family="ipv6")
    ip.create_static_route(dut=acl_dict["dut_list"][0], next_hop=acl_dict["dut2"]["ipv6_addr_list"][0],
                           static_ip=acl_dict["dut3"]["prefix_v6_list"][2], family="ipv6")


def dut2_ip_addr_config():
    st.log("config IP address in DUT2")
    ip.config_ip_addr_interface(dut=acl_dict["dut_list"][1],
                                interface_name=acl_dict["dut2"]["intf_list_dut1"][0],
                                ip_address=acl_dict["dut2"]["ip_addr_list"][0],
                                subnet=acl_dict["dut2"]["ip_mask_list"][0])
    ip.config_ip_addr_interface(dut=acl_dict["dut_list"][1],
                                interface_name=acl_dict["dut2"]["intf_list_dut1"][1],
                                ip_address=acl_dict["dut2"]["ip_addr_list"][1],
                                subnet=acl_dict["dut2"]["ip_mask_list"][1])
    ip.config_ip_addr_interface(dut=acl_dict["dut_list"][1],
                                interface_name=acl_dict["dut2"]["intf_list_dut3"][0],
                                ip_address=acl_dict["dut2"]["ip_addr_list"][2],
                                subnet=acl_dict["dut2"]["ip_mask_list"][2])
    ip.config_ip_addr_interface(dut=acl_dict["dut_list"][1],
                                interface_name=acl_dict["dut2"]["intf_list_dut3"][1],
                                ip_address=acl_dict["dut2"]["ip_addr_list"][3],
                                subnet=acl_dict["dut2"]["ip_mask_list"][3])


def dut2_static_route_config():
    st.log("config static route in DUT2")
    ip.create_static_route(dut=acl_dict["dut_list"][1], next_hop=acl_dict["dut3"]["ip_addr_list"][0],
                           static_ip=acl_dict["dut3"]["prefix_list"][2])
    ip.create_static_route(dut=acl_dict["dut_list"][1], next_hop=acl_dict["dut1"]["ip_addr_list"][0],
                           static_ip=acl_dict["dut1"]["prefix_list"][2])


def dut2_ipv6_addr_config():
    st.log("config IPv6 address in DUT2")
    ip.config_ip_addr_interface(dut=acl_dict["dut_list"][1],
                                interface_name=acl_dict["dut2"]["intf_list_dut1"][0],
                                ip_address=acl_dict["dut2"]["ipv6_addr_list"][0],
                                subnet=acl_dict["dut2"]["ipv6_mask_list"][0],family="ipv6")
    ip.config_ip_addr_interface(dut=acl_dict["dut_list"][1],
                                interface_name=acl_dict["dut2"]["intf_list_dut1"][1],
                                ip_address=acl_dict["dut2"]["ipv6_addr_list"][1],
                                subnet=acl_dict["dut2"]["ipv6_mask_list"][1],family="ipv6")
    ip.config_ip_addr_interface(dut=acl_dict["dut_list"][1],
                                interface_name=acl_dict["dut2"]["intf_list_dut3"][0],
                                ip_address=acl_dict["dut2"]["ipv6_addr_list"][2],
                                subnet=acl_dict["dut2"]["ipv6_mask_list"][2],family="ipv6")
    ip.config_ip_addr_interface(dut=acl_dict["dut_list"][1],
                                interface_name=acl_dict["dut2"]["intf_list_dut3"][1],
                                ip_address=acl_dict["dut2"]["ipv6_addr_list"][3],
                                subnet=acl_dict["dut2"]["ipv6_mask_list"][3],family="ipv6")


def dut2_static_route_v6_config():
    st.log("config IPv6 static route in DUT2")
    ip.create_static_route(dut=acl_dict["dut_list"][1], next_hop=acl_dict["dut3"]["ipv6_addr_list"][0],
                           static_ip=acl_dict["dut3"]["prefix_v6_list"][2],family="ipv6")
    ip.create_static_route(dut=acl_dict["dut_list"][1], next_hop=acl_dict["dut1"]["ipv6_addr_list"][0],
                           static_ip=acl_dict["dut1"]["prefix_v6_list"][2],family="ipv6")


def dut3_ip_addr_config():
    st.log("config IP address in DUT3")
    ip.config_ip_addr_interface(dut=acl_dict["dut_list"][2],
                                interface_name=acl_dict["dut3"]["intf_list_dut2"][0],
                                ip_address=acl_dict["dut3"]["ip_addr_list"][0],
                                subnet=acl_dict["dut3"]["ip_mask_list"][0])
    ip.config_ip_addr_interface(dut=acl_dict["dut_list"][2],
                                interface_name=acl_dict["dut3"]["intf_list_dut2"][1],
                                ip_address=acl_dict["dut3"]["ip_addr_list"][1],
                                subnet=acl_dict["dut3"]["ip_mask_list"][1])
    ip.config_ip_addr_interface(dut=acl_dict["dut_list"][2],
                                interface_name=acl_dict["dut3"]["intf_list_tg"][0],
                                ip_address=acl_dict["dut3"]["ip_addr_list"][2],
                                subnet=acl_dict["dut3"]["ip_mask_list"][2])


def dut3_static_route_config():
    st.log("config static route in DUT3")
    ip.create_static_route(dut=acl_dict["dut_list"][2], next_hop=acl_dict["dut2"]["ip_addr_list"][2],
                           static_ip=acl_dict["dut1"]["prefix_list"][0])
    ip.create_static_route(dut=acl_dict["dut_list"][2], next_hop=acl_dict["dut2"]["ip_addr_list"][3],
                           static_ip=acl_dict["dut1"]["prefix_list"][0])
    ip.create_static_route(dut=acl_dict["dut_list"][2], next_hop=acl_dict["dut2"]["ip_addr_list"][2],
                           static_ip=acl_dict["dut1"]["prefix_list"][1])
    ip.create_static_route(dut=acl_dict["dut_list"][2], next_hop=acl_dict["dut2"]["ip_addr_list"][3],
                           static_ip=acl_dict["dut1"]["prefix_list"][1])
    ip.create_static_route(dut=acl_dict["dut_list"][2], next_hop=acl_dict["dut2"]["ip_addr_list"][2],
                           static_ip=acl_dict["dut1"]["prefix_list"][2])


def dut3_ipv6_addr_config():
    st.log("config IPv6 address in DUT3")
    ip.config_ip_addr_interface(dut=acl_dict["dut_list"][2],
                                interface_name=acl_dict["dut3"]["intf_list_dut2"][0],
                                ip_address=acl_dict["dut3"]["ipv6_addr_list"][0],
                                subnet=acl_dict["dut3"]["ipv6_mask_list"][0],family="ipv6")
    ip.config_ip_addr_interface(dut=acl_dict["dut_list"][2],
                                interface_name=acl_dict["dut3"]["intf_list_dut2"][1],
                                ip_address=acl_dict["dut3"]["ipv6_addr_list"][1],
                                subnet=acl_dict["dut3"]["ipv6_mask_list"][1],family="ipv6")
    ip.config_ip_addr_interface(dut=acl_dict["dut_list"][2],
                                interface_name=acl_dict["dut3"]["intf_list_tg"][0],
                                ip_address=acl_dict["dut3"]["ipv6_addr_list"][2],
                                subnet=acl_dict["dut3"]["ipv6_mask_list"][2],family="ipv6")


def dut3_static_route_v6_config():
    st.log("config IPv6 static route in DUT3")
    ip.create_static_route(dut=acl_dict["dut_list"][2], next_hop=acl_dict["dut2"]["ipv6_addr_list"][2],
                           static_ip=acl_dict["dut1"]["prefix_v6_list"][0],family="ipv6")
    ip.create_static_route(dut=acl_dict["dut_list"][2], next_hop=acl_dict["dut2"]["ipv6_addr_list"][3],
                           static_ip=acl_dict["dut1"]["prefix_v6_list"][0],family="ipv6")
    ip.create_static_route(dut=acl_dict["dut_list"][2], next_hop=acl_dict["dut2"]["ipv6_addr_list"][2],
                           static_ip=acl_dict["dut1"]["prefix_v6_list"][1],family="ipv6")
    ip.create_static_route(dut=acl_dict["dut_list"][2], next_hop=acl_dict["dut2"]["ipv6_addr_list"][3],
                           static_ip=acl_dict["dut1"]["prefix_v6_list"][1],family="ipv6")
    ip.create_static_route(dut=acl_dict["dut_list"][2], next_hop=acl_dict["dut2"]["ipv6_addr_list"][2],
                           static_ip=acl_dict["dut1"]["prefix_v6_list"][2],family="ipv6")


def setup_tg_config():
    dut3_gateway_mac = acl_dict["dut3_gw_mac"]
    dut1_gateway_mac = acl_dict["dut1_gw_mac"]
    stream = tg_dict["tg"].tg_traffic_config(mac_src=acl_dict["dut1"]["mac_addr_list"][0],mac_dst=dut1_gateway_mac,
                                  rate_pps=tg_dict["tgen_rate_pps"], mode='create',port_handle=tg_dict["d1_tg_ph1"],
                                  ip_src_addr=acl_dict["dut1"]["ip_addr_list"][3],
                                  ip_dst_addr=acl_dict["dut3"]["ip_addr_list"][3],
                                  l3_protocol='ipv4',l3_length=tg_dict["l3_len"],
                                  mac_discovery_gw=acl_dict["dut1"]["ip_addr_list"][2],
                                  duration=tg_dict["duration"],port_handle2=tg_dict["d3_tg_ph1"])
    stream1 = stream['stream_id']
    st.log("Ipv4 stream {} is created in DUT1 TgenPort1 {}".format(stream1, vars.T1D1P1))
    tg_dict["v4_1"] = [stream1]
    han = tg_dict["tg"].tg_interface_config(port_handle=tg_dict["d1_tg_ph1"], mode='config',
                                 intf_ip_addr=acl_dict["dut1"]["ip_addr_list"][3],
                                 gateway=acl_dict["dut1"]["ip_addr_list"][2], arp_send_req='1',
                                 gateway_step='0.0.0.0',intf_ip_addr_step='0.0.0.1', count=1,
                                 src_mac_addr=acl_dict["dut1"]["mac_addr_list"][0])
    host1 = han["handle"]
    tg_dict["v4_host1"] = host1
    st.log("Ipv4 host {} is created at DUT1 TgenPort1 {}".format(host1, vars.T1D1P1))

    stream = tg_dict["tg"].tg_traffic_config(mac_src=acl_dict["dut3"]["mac_addr_list"][0],mac_dst=dut3_gateway_mac,
                                  rate_pps=tg_dict["tgen_rate_pps"], mode='create',port_handle=tg_dict["d3_tg_ph1"],
                                  ip_src_addr=acl_dict["dut3"]["ip_addr_list"][3],
                                  ip_dst_addr=acl_dict["dut1"]["ip_addr_list"][3],
                                  l3_protocol='ipv4',l3_length=tg_dict["l3_len"],
                                  mac_discovery_gw=acl_dict["dut3"]["ip_addr_list"][2],
                                  duration=tg_dict["duration"],port_handle2=tg_dict["d1_tg_ph1"],
                                  l4_protocol='tcp',tcp_rst_flag=1,tcp_ack_flag=0)
    stream2 = stream['stream_id']
    st.log("Ipv4 stream {} with TCP RST flag 1 is created in DUT3 TgenPort1 {}".format(stream2, vars.T1D3P1))
    tg_dict["v4_2"] = [stream2]
    han = tg_dict["tg"].tg_interface_config(port_handle=tg_dict["d3_tg_ph1"], mode='config',
                                 intf_ip_addr=acl_dict["dut3"]["ip_addr_list"][3],
                                 gateway=acl_dict["dut3"]["ip_addr_list"][2], arp_send_req='1',
                                 gateway_step='0.0.0.0',intf_ip_addr_step='0.0.0.1', count=1,
                                 src_mac_addr=acl_dict["dut3"]["mac_addr_list"][0])
    host2 = han["handle"]
    tg_dict["v4_host2"] = host2
    st.log("Ipv4 host {} is created at DUT3 TgenPort1 {}".format(host2, vars.T1D3P1))

    stream = tg_dict["tg"].tg_traffic_config(mac_src=acl_dict["dut3"]["mac_addr_list"][0],mac_dst=dut3_gateway_mac,
                                  rate_pps=tg_dict["tgen_rate_pps"], mode='create',port_handle=tg_dict["d3_tg_ph1"],
                                  ip_src_addr=acl_dict["dut3"]["ip_addr_list"][3],
                                  ip_dst_addr=acl_dict["dut1"]["ip_addr_list"][3],
                                  l3_protocol='ipv4',l3_length=tg_dict["l3_len"],
                                  mac_discovery_gw=acl_dict["dut3"]["ip_addr_list"][2],
                                  duration=tg_dict["duration"],port_handle2=tg_dict["d1_tg_ph1"],
                                  l4_protocol='tcp',tcp_rst_flag=0,tcp_ack_flag=0)
    stream3 = stream['stream_id']
    st.log("Ipv4 stream {} with TCP RST flag 0 is created in DUT3 TgenPort1 {}".format(stream2, vars.T1D3P1))
    tg_dict["v4_3"] = [stream3]

    stream = tg_dict["tg"].tg_traffic_config(mac_src=acl_dict["dut1"]["mac_addr_list"][1],mac_dst=dut1_gateway_mac,
                                  rate_pps=tg_dict["tgen_rate_pps"], mode='create',port_handle=tg_dict["d1_tg_ph1"],
                                  ipv6_src_addr=acl_dict["dut1"]["ipv6_addr_list"][3],
                                  ipv6_dst_addr=acl_dict["dut3"]["ipv6_addr_list"][3],
                                  l3_protocol='ipv6',l3_length=tg_dict["l3_len"],
                                  mac_discovery_gw=acl_dict["dut1"]["ipv6_addr_list"][2],
                                  duration=tg_dict["duration"],port_handle2=tg_dict["d3_tg_ph1"],
                                  l4_protocol='tcp',tcp_rst_flag=1,tcp_ack_flag=0)
    stream4 = stream['stream_id']
    st.log("Ipv6 stream {} with TCP RST flag 1 is created in DUT1 TgenPort1 {}".format(stream4, vars.T1D1P1))
    tg_dict["v6_1"] = [stream4]
    han = tg_dict["tg"].tg_interface_config(port_handle=tg_dict["d1_tg_ph1"], mode='config',
                                 ipv6_intf_addr=acl_dict["dut1"]["ipv6_addr_list"][3],
                                 ipv6_gateway=acl_dict["dut1"]["ipv6_addr_list"][2], arp_send_req='1',
                                 ipv6_gateway_step='0::1',ipv6_intf_addr_step='0::1', count=1,
                                 src_mac_addr=acl_dict["dut1"]["mac_addr_list"][1],ipv6_prefix_length='96')
    host3 = han["handle"]
    tg_dict["v6_host1"] = host3

    stream = tg_dict["tg"].tg_traffic_config(mac_src=acl_dict["dut3"]["mac_addr_list"][1],mac_dst=dut3_gateway_mac,
                                  rate_pps=tg_dict["tgen_rate_pps"], mode='create',port_handle=tg_dict["d3_tg_ph1"],
                                  ipv6_src_addr=acl_dict["dut3"]["ipv6_addr_list"][3],
                                  ipv6_dst_addr=acl_dict["dut1"]["ipv6_addr_list"][3],
                                  l3_protocol='ipv6',l3_length=tg_dict["l3_len"],
                                  mac_discovery_gw=acl_dict["dut3"]["ipv6_addr_list"][2],
                                  duration=tg_dict["duration"],port_handle2=tg_dict["d1_tg_ph1"],
                                  l4_protocol='tcp',tcp_rst_flag=1,tcp_ack_flag=0)
    stream5 = stream['stream_id']
    st.log("Ipv6 stream {} with TCP RST flag 1 is created in DUT3 TgenPort1 {}".format(stream5, vars.T1D3P1))
    tg_dict["v6_2"] = [stream5]
    han = tg_dict["tg"].tg_interface_config(port_handle=tg_dict["d3_tg_ph1"], mode='config',
                                 ipv6_intf_addr=acl_dict["dut3"]["ipv6_addr_list"][3],
                                 ipv6_gateway=acl_dict["dut3"]["ipv6_addr_list"][2], arp_send_req='1',
                                 ipv6_gateway_step='0::1',ipv6_intf_addr_step='0::1', count=1,
                                 src_mac_addr=acl_dict["dut3"]["mac_addr_list"][1],ipv6_prefix_length='96')
    host4 = han["handle"]
    tg_dict["v6_host2"] = host4
    st.log("Ipv6 host {} is created at DUT3 TgenPort1 {}".format(host4, vars.T1D3P1))

    stream = tg_dict["tg"].tg_traffic_config(mac_src=acl_dict["dut3"]["mac_addr_list"][1],mac_dst=dut3_gateway_mac,
                                  rate_pps=tg_dict["tgen_rate_pps"], mode='create',port_handle=tg_dict["d3_tg_ph1"],
                                  ipv6_src_addr=acl_dict["dut3"]["ipv6_addr_list"][3],
                                  ipv6_dst_addr=acl_dict["dut1"]["ipv6_addr_list"][3],
                                  l3_protocol='ipv6',l3_length=tg_dict["l3_len"],
                                  mac_discovery_gw=acl_dict["dut3"]["ipv6_addr_list"][2],
                                  duration=tg_dict["duration"],port_handle2=tg_dict["d1_tg_ph1"],
                                  l4_protocol='tcp',tcp_rst_flag=0,tcp_ack_flag=0)
    stream6 = stream['stream_id']
    st.log("Ipv6 stream {} with TCP RST flag 0 is created in DUT3 TgenPort1 {}".format(stream6, vars.T1D3P1))
    tg_dict["v6_3"] = [stream6]
    
    ##########################################################################################
    #                           Streams created to validate supported TCP_Flgs                         #
    ##########################################################################################
    st.banner('Streams created to validate TCP_Flgs')
    '''    
    stream = tg_dict["tg"].tg_traffic_config(mac_src=acl_dict["dut1"]["mac_addr_list"][0],mac_dst=dut1_gateway_mac,
                                      rate_pps=tg_dict["tgen_rate_pps"], mode='create', port_handle=tg_dict["d1_tg_ph1"],
                                      ip_src_addr=acl_dict["dut1"]["ip_addr_list"][3],
                                      ip_dst_addr=acl_dict["dut3"]["ip_addr_list"][3],
                                      l3_protocol='ipv4',l3_length=tg_dict["l3_len"],
                                      l4_protocol='tcp',tcp_dst_port='322',tcp_src_port='10',tcp_syn_flag=1,duration=tg_dict["duration"],port_handle2=tg_dict["d3_tg_ph1"])
    stream7 = stream['stream_id']
    st.log("Ipv4 stream {} is created in DUT1 TgenPort1 {}".format(stream7, vars.T1D1P1))
    
    stream = tg_dict["tg"].tg_traffic_config(mac_src=acl_dict["dut1"]["mac_addr_list"][0],mac_dst=dut1_gateway_mac,
                                      rate_pps=tg_dict["tgen_rate_pps"], mode='create', port_handle=tg_dict["d1_tg_ph1"],
                                      ip_src_addr=acl_dict["dut1"]["ip_addr_list"][3],
                                      ip_dst_addr=acl_dict["dut3"]["ip_addr_list"][3],
                                      l3_protocol='ipv4',l3_length=tg_dict["l3_len"],
                                      l4_protocol='tcp',tcp_dst_port='100',tcp_src_port='10',tcp_ack_flag=1,duration=tg_dict["duration"],port_handle2=tg_dict["d3_tg_ph1"])

    stream8 = stream['stream_id']
    st.log("Ipv4 stream {} is created in DUT1 TgenPort1 {}".format(stream8, vars.T1D1P1))
    '''
    stream = tg_dict["tg"].tg_traffic_config(mac_src=acl_dict["dut1"]["mac_addr_list"][0],mac_dst=dut1_gateway_mac,
                                      rate_pps=tg_dict["tgen_rate_pps"], mode='create', port_handle=tg_dict["d1_tg_ph1"],
                                      ip_src_addr=acl_dict["dut1"]["ip_addr_list"][3],
                                      ip_dst_addr=acl_dict["dut3"]["ip_addr_list"][3],
                                      l3_protocol='ipv4',l3_length=tg_dict["l3_len"],
                                      l4_protocol='tcp',tcp_dst_port='20',tcp_src_port='1024',tcp_rst_flag=1,duration=tg_dict["duration"],port_handle2=tg_dict["d3_tg_ph1"])

    stream7 = stream['stream_id']   
    st.log("Ipv4 stream {} is created in DUT1 TgenPort1 {}".format(stream7, vars.T1D1P1))
    
    stream = tg_dict["tg"].tg_traffic_config(mac_src=acl_dict["dut1"]["mac_addr_list"][0],mac_dst=dut1_gateway_mac,
                                      rate_pps=tg_dict["tgen_rate_pps"], mode='create', port_handle=tg_dict["d1_tg_ph1"],
                                      ip_src_addr=acl_dict["dut1"]["ip_addr_list"][3],
                                      ip_dst_addr=acl_dict["dut3"]["ip_addr_list"][3],
                                      l3_protocol='ipv4',l3_length=tg_dict["l3_len"],
                                      l4_protocol='tcp',tcp_dst_port='50',tcp_src_port='500',tcp_fin_flag=1,duration=tg_dict["duration"],port_handle2=tg_dict["d3_tg_ph1"])

    stream8 = stream['stream_id']
    st.log("Ipv4 stream {} is created in DUT1 TgenPort1 {}".format(stream8, vars.T1D1P1))
    
    stream = tg_dict["tg"].tg_traffic_config(mac_src=acl_dict["dut1"]["mac_addr_list"][0],mac_dst=dut1_gateway_mac,
                                      rate_pps=tg_dict["tgen_rate_pps"], mode='create', port_handle=tg_dict["d1_tg_ph1"],
                                      ip_src_addr=acl_dict["dut1"]["ip_addr_list"][3],
                                      ip_dst_addr=acl_dict["dut3"]["ip_addr_list"][3],
                                      l3_protocol='ipv4',l3_length=tg_dict["l3_len"],
                                      l4_protocol='tcp',tcp_dst_port='20',tcp_src_port='233',tcp_psh_flag=1,duration=tg_dict["duration"],port_handle2=tg_dict["d3_tg_ph1"])

    stream9 = stream['stream_id']   
    st.log("Ipv4 stream {} is created in DUT1 TgenPort1 {}".format(stream9, vars.T1D1P1))
    
    stream = tg_dict["tg"].tg_traffic_config(mac_src=acl_dict["dut1"]["mac_addr_list"][0],mac_dst=dut1_gateway_mac,
                                      rate_pps=tg_dict["tgen_rate_pps"], mode='create', port_handle=tg_dict["d1_tg_ph1"],
                                      ip_src_addr=acl_dict["dut1"]["ip_addr_list"][3],
                                      ip_dst_addr=acl_dict["dut3"]["ip_addr_list"][3],
                                      l3_protocol='ipv4',l3_length=tg_dict["l3_len"],
                                      l4_protocol='tcp',tcp_dst_port='50',tcp_src_port='500',tcp_urg_flag=1,duration=tg_dict["duration"],port_handle2=tg_dict["d3_tg_ph1"])

    stream10 = stream['stream_id']
    st.log("Ipv4 stream {} is created in DUT1 TgenPort1 {}".format(stream10, vars.T1D1P1))    
    
    stream = tg_dict["tg"].tg_traffic_config(mac_src=acl_dict["dut1"]["mac_addr_list"][0],mac_dst=dut1_gateway_mac,
                                      rate_pps=tg_dict["tgen_rate_pps"], mode='create', port_handle=tg_dict["d1_tg_ph1"],
                                      ip_src_addr=acl_dict["dut1"]["ip_addr_list"][3],
                                      ip_dst_addr=acl_dict["dut3"]["ip_addr_list"][3],
                                      l3_protocol='ipv4',l3_length=tg_dict["l3_len"],
                                      l4_protocol='tcp',tcp_dst_port='44',tcp_src_port='444',tcp_syn_flag=1, tcp_ack_flag=1,duration=tg_dict["duration"],port_handle2=tg_dict["d3_tg_ph1"])

    stream11 = stream['stream_id']
    st.log("Ipv4 stream {} is created in DUT1 TgenPort1 {}".format(stream11, vars.T1D1P1))
    
    stream = tg_dict["tg"].tg_traffic_config(mac_src=acl_dict["dut1"]["mac_addr_list"][0],mac_dst=dut1_gateway_mac,
                                      rate_pps=tg_dict["tgen_rate_pps"], mode='create', port_handle=tg_dict["d1_tg_ph1"],
                                      ip_src_addr=acl_dict["dut1"]["ip_addr_list"][3],
                                      ip_dst_addr=acl_dict["dut3"]["ip_addr_list"][3],
                                      l3_protocol='ipv4',l3_length=tg_dict["l3_len"],
                                      l4_protocol='tcp',tcp_dst_port='8877',tcp_src_port='5001',tcp_syn_flag=0, tcp_rst_flag=0,duration=tg_dict["duration"],port_handle2=tg_dict["d3_tg_ph1"])

    stream12 = stream['stream_id']
    st.log("Ipv4 stream {} is created in DUT1 TgenPort1 {}".format(stream12, vars.T1D1P1))       
    stream_dict["tcp_flags"]=[stream7,stream8,stream9,stream10,stream11,stream12]
    stream_dict["tcp_flags_v4"]=[stream9,stream11,stream12]
    
    st.banner('Streams created to validate TCP_Flgs_ipv6')        
    stream = tg_dict["tg"].tg_traffic_config(mac_src=acl_dict["dut1"]["mac_addr_list"][1],mac_dst=dut1_gateway_mac,
                                      rate_pps=tg_dict["tgen_rate_pps"], mode='create', port_handle=tg_dict["d1_tg_ph1"],
                                      ipv6_src_addr=acl_dict["dut1"]["ipv6_addr_list"][3],
                                      ipv6_dst_addr=acl_dict["dut3"]["ipv6_addr_list"][3],
                                      l3_protocol='ipv6',l3_length=tg_dict["l3_len"],
                                      l4_protocol='tcp',tcp_dst_port='322',tcp_src_port='10',tcp_syn_flag=1,duration=tg_dict["duration"],port_handle2=tg_dict["d3_tg_ph1"])
    stream15 = stream['stream_id']
    st.log("Ipv6 stream {} is created in DUT1 TgenPort1 {}".format(stream15, vars.T1D1P1))
    
    stream = tg_dict["tg"].tg_traffic_config(mac_src=acl_dict["dut1"]["mac_addr_list"][1],mac_dst=dut1_gateway_mac,
                                      rate_pps=tg_dict["tgen_rate_pps"], mode='create', port_handle=tg_dict["d1_tg_ph1"],
                                      ipv6_src_addr=acl_dict["dut1"]["ipv6_addr_list"][3],
                                      ipv6_dst_addr=acl_dict["dut3"]["ipv6_addr_list"][3],
                                      l3_protocol='ipv6',l3_length=tg_dict["l3_len"],
                                      l4_protocol='tcp',tcp_dst_port='100',tcp_src_port='10',tcp_ack_flag=1,duration=tg_dict["duration"],port_handle2=tg_dict["d3_tg_ph1"])

    stream16 = stream['stream_id']
    st.log("Ipv6 stream {} is created in DUT1 TgenPort1 {}".format(stream16, vars.T1D1P1))
    
    stream = tg_dict["tg"].tg_traffic_config(mac_src=acl_dict["dut1"]["mac_addr_list"][1],mac_dst=dut1_gateway_mac,
                                      rate_pps=tg_dict["tgen_rate_pps"], mode='create', port_handle=tg_dict["d1_tg_ph1"],
                                      ipv6_src_addr=acl_dict["dut1"]["ipv6_addr_list"][3],
                                      ipv6_dst_addr=acl_dict["dut3"]["ipv6_addr_list"][3],
                                      l3_protocol='ipv6',l3_length=tg_dict["l3_len"],
                                      l4_protocol='tcp',tcp_dst_port='20',tcp_src_port='233',tcp_rst_flag=1,duration=tg_dict["duration"],port_handle2=tg_dict["d3_tg_ph1"])

    stream17 = stream['stream_id']   
    st.log("Ipv6 stream {} is created in DUT1 TgenPort1 {}".format(stream17, vars.T1D1P1))
    
    stream = tg_dict["tg"].tg_traffic_config(mac_src=acl_dict["dut1"]["mac_addr_list"][1],mac_dst=dut1_gateway_mac,
                                      rate_pps=tg_dict["tgen_rate_pps"], mode='create', port_handle=tg_dict["d1_tg_ph1"],
                                      ipv6_src_addr=acl_dict["dut1"]["ipv6_addr_list"][3],
                                      ipv6_dst_addr=acl_dict["dut3"]["ipv6_addr_list"][3],
                                      l3_protocol='ipv6',l3_length=tg_dict["l3_len"],
                                      l4_protocol='tcp',tcp_dst_port='50',tcp_src_port='500',tcp_fin_flag=1,duration=tg_dict["duration"],port_handle2=tg_dict["d3_tg_ph1"])

    stream18 = stream['stream_id']
    st.log("Ipv6 stream {} is created in DUT1 TgenPort1 {}".format(stream18, vars.T1D1P1))
    
    stream = tg_dict["tg"].tg_traffic_config(mac_src=acl_dict["dut1"]["mac_addr_list"][1],mac_dst=dut1_gateway_mac,
                                      rate_pps=tg_dict["tgen_rate_pps"], mode='create', port_handle=tg_dict["d1_tg_ph1"],
                                      ipv6_src_addr=acl_dict["dut1"]["ipv6_addr_list"][3],
                                      ipv6_dst_addr=acl_dict["dut3"]["ipv6_addr_list"][3],
                                      l3_protocol='ipv6',l3_length=tg_dict["l3_len"],
                                      l4_protocol='tcp',tcp_dst_port='20',tcp_src_port='233',tcp_psh_flag=1,duration=tg_dict["duration"],port_handle2=tg_dict["d3_tg_ph1"])

    stream19 = stream['stream_id']   
    st.log("Ipv6 stream {} is created in DUT1 TgenPort1 {}".format(stream19, vars.T1D1P1))
    
    stream = tg_dict["tg"].tg_traffic_config(mac_src=acl_dict["dut1"]["mac_addr_list"][1],mac_dst=dut1_gateway_mac,
                                      rate_pps=tg_dict["tgen_rate_pps"], mode='create', port_handle=tg_dict["d1_tg_ph1"],
                                      ipv6_src_addr=acl_dict["dut1"]["ipv6_addr_list"][3],
                                      ipv6_dst_addr=acl_dict["dut3"]["ipv6_addr_list"][3],
                                      l3_protocol='ipv6',l3_length=tg_dict["l3_len"],
                                      l4_protocol='tcp',tcp_dst_port='50',tcp_src_port='500',tcp_urg_flag=1,duration=tg_dict["duration"],port_handle2=tg_dict["d3_tg_ph1"])

    stream20 = stream['stream_id']
    st.log("Ipv6 stream {} is created in DUT1 TgenPort1 {}".format(stream20, vars.T1D1P1))    
    
    stream = tg_dict["tg"].tg_traffic_config(mac_src=acl_dict["dut1"]["mac_addr_list"][1],mac_dst=dut1_gateway_mac,
                                      rate_pps=tg_dict["tgen_rate_pps"], mode='create', port_handle=tg_dict["d1_tg_ph1"],
                                      ipv6_src_addr=acl_dict["dut1"]["ipv6_addr_list"][3],
                                      ipv6_dst_addr=acl_dict["dut3"]["ipv6_addr_list"][3],
                                      l3_protocol='ipv6',l3_length=tg_dict["l3_len"],
                                      l4_protocol='tcp',tcp_dst_port='44',tcp_src_port='444',tcp_fin_flag=1, tcp_ack_flag=1,duration=tg_dict["duration"],port_handle2=tg_dict["d3_tg_ph1"])

    stream21 = stream['stream_id']
    st.log("Ipv6 stream {} is created in DUT1 TgenPort1 {}".format(stream21, vars.T1D1P1))
    
    stream = tg_dict["tg"].tg_traffic_config(mac_src=acl_dict["dut1"]["mac_addr_list"][1],mac_dst=dut1_gateway_mac,
                                      rate_pps=tg_dict["tgen_rate_pps"], mode='create', port_handle=tg_dict["d1_tg_ph1"],
                                      ipv6_src_addr=acl_dict["dut1"]["ipv6_addr_list"][3],
                                      ipv6_dst_addr=acl_dict["dut3"]["ipv6_addr_list"][3],
                                      l3_protocol='ipv6',l3_length=tg_dict["l3_len"],
                                      l4_protocol='tcp',tcp_dst_port='8877',tcp_src_port='650',tcp_fin_flag=0, tcp_ack_flag=0,duration=tg_dict["duration"],port_handle2=tg_dict["d3_tg_ph1"])

    stream22 = stream['stream_id']
    st.log("Ipv6 stream {} is created in DUT1 TgenPort1 {}".format(stream22, vars.T1D1P1))       
    stream_dict["tcp_flags_ipv6"]=[stream15,stream16,stream17,stream18,stream19,stream20,stream21,stream22]
    stream_dict["tcp_flags_v6"]=[stream17,stream18,stream20,stream21,stream22]  
            
        
    
def start_traffic(stream_han_list=[],action="run"):
    if action=="run":
        if tg_dict["tg"].tg_type == 'stc':
            tg_dict["tg"].tg_traffic_control(action="run", stream_handle=stream_han_list,
                                                            duration=tg_dict["duration"])
        else:
            tg_dict["tg"].tg_traffic_control(action="run", stream_handle=stream_han_list)
    else:
        tg_dict["tg"].tg_traffic_control(action="stop", stream_handle=stream_han_list)


def clear_stats(port_han_list):
    tg_dict["tg"].tg_traffic_control(action='clear_stats',port_handle=port_han_list)


def verify_traffic(tx_stream_list, rx_stream_list=[], tx_port="", rx_port="", 
                   tx_ratio=1, rx_ratio=1, mode="streamblock", field="packet_count"):
    '''
    :param tx_port:
    :param rx_port:
    :param tx_ratio:
    :param rx_ratio:
    :param mode:
    :param field:
    :param tx_stream_list:
    :param rx_stream_list:
    :return:
    '''

    if not tx_port:
        tx_port=tg_dict["d1_tg_port1"]
    if not rx_port:
        rx_port=tg_dict["d3_tg_port1"]
    
    if rx_stream_list:
        traffic_details = {
            '1': {
                'tx_ports': [tx_port],
                'tx_obj': [tg_dict["tg"]],
                'exp_ratio': [tx_ratio],
                'rx_ports': [rx_port],
                'rx_obj': [tg_dict["tg"]],
                'stream_list': [tuple(tx_stream_list)]
            },
            '2': {
                'tx_ports': [rx_port],
                'tx_obj': [tg_dict["tg"]],
                'exp_ratio': [rx_ratio],
                'rx_ports': [tx_port],
                'rx_obj': [tg_dict["tg"]],
                'stream_list': [tuple(rx_stream_list)]
            }
        }
    else:
        traffic_details = {
            '1': {
                'tx_ports': [tx_port],
                'tx_obj': [tg_dict["tg"]],
                'exp_ratio': [tx_ratio],
                'rx_ports': [rx_port],
                'rx_obj': [tg_dict["tg"]],
                'stream_list': [tuple(tx_stream_list)]
            }
        }       
    return tgapi.validate_tgen_traffic(traffic_details=traffic_details, mode=mode, comp_type=field, tolerance_factor=1)


def verify_ssh_session(dut, username, pwd, dest_ip, rem_dut_mgmt, interface=None, port=None):
    if interface:
        dest_ip += " -b {}".format(interface)
    if port:
        dest_ip = dest_ip + " -p {}".format(port)
    output=st.exec_ssh_remote_dut(dut, dest_ip, username, pwd, 
                                  command="show ip interfaces", timeout=30)
    if rem_dut_mgmt in output:
        return True
    else:
        return False


def verify_ftp_session(dut_name, username, pwd, ssh_obj, dest_ip):
    command = "ftp {}".format(dest_ip)    
    try:
        prompt,ssh_obj = find_prompt(dut_name, username, pwd, ssh_obj)
        result = ssh_obj.send_command(command, expect_string="{}|:|>".format(prompt),delay_factor=30)
        st.log("read data : {}".format(result))
        ssh_obj.send_command('\x03', expect_string="{}|:|>".format(prompt),delay_factor=30)
        ssh_obj.send_command('bye', expect_string="{}|:|>".format(prompt),delay_factor=30)
        if dest_ip+":"+username in result:
            return True
        else:
            return False
    except Exception as e:
        st.log("Exception occurred : {}".format(e))
        ssh_obj.send_command('\x03', expect_string="{}|:|>".format(prompt),delay_factor=30)
        ssh_obj.send_command('bye', expect_string="{}|:|>".format(prompt),delay_factor=30)
        return False


def find_prompt(dut_name, username, pwd, ssh_obj, delay_factor=1):
    try:
        ssh_obj.clear_cached_read_data()
        rv = super(sonic_obj.SonicBaseConnection, ssh_obj).find_prompt(delay_factor)
        rv = re.escape(rv)
        ssh_obj.clear_cached_read_data()
        st.log("read data1 : {}".format(rv))
        return rv,ssh_obj
    except Exception as exp:
        st.log("getting error as {} while checking the prompt".format(exp))
        if dut_name == "dut1":
            ssh_obj = con_obj.connect_to_device(acl_dict["dut1_mgmt_ip"], username, pwd)
            acl_dict["dut1_ssh_obj"] = ssh_obj
        elif dut_name == "dut3":
            ssh_obj = con_obj.connect_to_device(acl_dict["dut3_mgmt_ip"], username, pwd)
            acl_dict["dut3_ssh_obj"] = ssh_obj
        try:
            ssh_obj.clear_cached_read_data()
            rv = super(sonic_obj.SonicBaseConnection, ssh_obj).find_prompt(delay_factor)
            rv = re.escape(rv)
            ssh_obj.clear_cached_read_data()
            st.log("read data2 : {}".format(rv))
            return rv,ssh_obj
        except Exception as exp:
            st.log("getting error again as {} while checking the prompt".format(exp))
            return False
                
def verify_acl_counters(dut, table_name, acl_type="ip"):
    result = True
    acl_rule_counters = acl_obj.show_acl_counters(dut, acl_type=acl_type, acl_table=table_name)
    for rule in acl_rule_counters:
        if rule['packetscnt'] < str(5000):
            return False
    return result
