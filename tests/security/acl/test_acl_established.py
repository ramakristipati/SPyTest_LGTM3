import pytest
from spytest import st, tgapi
from utilities import parallel
import apis.system.basic as basic
import apis.system.connection as con_obj
import apis.system.interface as interf
import apis.qos.acl as acl_obj
from acl_established_lib import acl_dict, tg_dict, stream_dict
import acl_established_lib as loc_obj
import apis.routing.ip as ip_obj
import utilities.common as utils_obj

@pytest.fixture(scope="module", autouse=True)
def acl_est_hooks(request):
    global vars
    loc_obj.create_glob_vars()
    vars = st.get_testbed_vars()
    ip1 = st.get_mgmt_ip(vars.D1)
    ip2 = st.get_mgmt_ip(vars.D3)
    if ip1 and ip2:
        acl_dict["dut1_mgmt_ip"] = ip1
        acl_dict["dut3_mgmt_ip"] = ip2
    else:
        st.error("DUT1 and/or DUT3 management IP not found; Abort the suite")
        st.report_fail("base_config_verification_failed")
    api_list = [[loc_obj.setup_tg_config],[loc_obj.setup_dut_config]]
    st.exec_all(api_list, True)
    acl_dict["dut1_ssh_obj"] = con_obj.connect_to_device(ip=acl_dict["dut1_mgmt_ip"],
                                                         username=acl_dict["d1_uname"],
                                                         password=acl_dict["d1_pwd"])
    acl_dict["dut3_ssh_obj"] = con_obj.connect_to_device(ip=acl_dict["dut3_mgmt_ip"],
                                                         username=acl_dict["d3_uname"],
                                                         password=acl_dict["d3_pwd"])
    if acl_dict["dut1_ssh_obj"] and acl_dict["dut3_ssh_obj"]:
        st.log("########## Established SSH to both DUT1 and DUT3 ##########")
    else:
        st.error("########## FAIL: Failed to establish SSH to DUT1 and/or DUT3 management IP;"
                                     " Abort the suite ##########")
        st.report_fail("base_config_verification_failed")
    interface1 = st.get_mgmt_ifname(vars.D1)
    interface2 = st.get_mgmt_ifname(vars.D3)
    st.exec_all([[interf.enable_dhcp_on_interface, vars.D1, interface1],
                 [interf.enable_dhcp_on_interface, vars.D3, interface2]])
    input = {"mode" : "update"}
    parallel.exec_parallel(True, [vars.D1,vars.D3], basic.deploy_package, [input]*2)
    st.exec_all([[basic.deploy_package,vars.D1,'ftp','install',False],
                 [basic.deploy_package,vars.D3,'ftp','install',False]])
    st.exec_all([[basic.deploy_package,vars.D1,'ftpd','install',False],
                 [basic.deploy_package,vars.D3,'ftpd','install',False]])
    st.exec_all([[basic.deploy_package,vars.D1,'vsftpd','install',False],
                 [basic.deploy_package,vars.D3,'vsftpd','install',False]])
    st.exec_all([[basic.flush_iptable,vars.D1],[basic.flush_iptable,vars.D3]])
    yield


@pytest.fixture(scope="function")
def acl_any_any_fixture(request,acl_est_hooks):
    tg_dict["tg"].tg_traffic_control(action='clear_stats', port_handle=[tg_dict["d1_tg_ph1"],tg_dict["d3_tg_ph1"]])
    acl_obj.create_acl_table(vars.D2, name=acl_dict["dut2"]["acl_name"], type="ip",stage='INGRESS',
                             ports=[acl_dict["dut2"]["intf_list_dut3"][0],acl_dict["dut2"]["intf_list_dut3"][1]])
    acl_obj.create_acl_rule(vars.D2,acl_type='ip',rule_name=acl_dict["dut2"]["acl_name"],rule_seq='100',
                            packet_action='permit',src_ip='any', dst_ip='any',l4_protocol='tcp',
                            tcp_flag='established',table_name=acl_dict["dut2"]["acl_name"])
    yield
    acl_obj.delete_acl_table(vars.D2, acl_type="ip", acl_table_name=[acl_dict["dut2"]["acl_name"]])


def test_acl_est_permit_any_any(acl_any_any_fixture):
    success = True
    st.log("########## Test SSH and FTP from local host to remote host with ACL established rule ##########")
    if loc_obj.verify_ssh_session(vars.D1, acl_dict["d3_uname"], acl_dict["d3_pwd"],
                                  acl_dict["dut3"]["ip_addr_list"][0], rem_dut_mgmt=acl_dict["dut3_mgmt_ip"],
                                                             interface=acl_dict["dut1"]["ip_addr_list"][0]):
        st.log("########## PASS: Successfully established SSH session from localhost to remote host ##########")
    else:
        success=False
        st.error("########## FAIL: Failed to establish SSH session from localhost to remote host ##########")
    if loc_obj.verify_ssh_session(vars.D3, acl_dict["d1_uname"], acl_dict["d1_pwd"],
                                  acl_dict["dut1"]["ip_addr_list"][0], rem_dut_mgmt=acl_dict["dut1_mgmt_ip"],
                                                              interface=acl_dict["dut3"]["ip_addr_list"][0]):
        success=False
        st.error("########## FAIL: Established SSH session from remote host to local host which is"
                                                              " NOT expected ##########")
    else:
        st.log("########## PASS: As expected SSH session from remote host to local host fails ##########")

    if loc_obj.verify_ftp_session("dut1", acl_dict["d3_uname"], acl_dict["d3_pwd"],
                                   acl_dict["dut1_ssh_obj"],dest_ip=acl_dict["dut3"]["ip_addr_list"][0]):
        st.log("########## PASS: Successfully established FTP session from DUT1 to DUT3 IP {} ########"
                                 "##".format(acl_dict["dut3"]["ip_addr_list"][0]))
    else:
        success=False
        st.error("########## FAIL: Failed to establish FTP session from DUT1 to DUT3 IP {} ########"
                                 "##".format(acl_dict["dut3"]["ip_addr_list"][0]))
    if loc_obj.verify_ftp_session("dut3", acl_dict["d1_uname"], acl_dict["d1_pwd"],
                                   acl_dict["dut3_ssh_obj"],dest_ip=acl_dict["dut1"]["ip_addr_list"][0]):
        success=False
        st.error("########## FAIL: Established FTP session from DUT3 to DUT1 IP {} which is"
                                " NOT expected ##########".format(acl_dict["dut1"]["ip_addr_list"][0]))
    else:
        st.log("########## PASS: As expected FTP session from DUT3 to DUT1 IP {} fails ########"
                                "##".format(acl_dict["dut1"]["ip_addr_list"][0]))
    if not ip_obj.ping(dut=vars.D3, addresses="{} -I {}".format(acl_dict["dut1"]["ip_addr_list"][0],
                                                                acl_dict["dut3"]["ip_addr_list"][0])):
        st.log("########## PASS: As expected ping failed from {} to {} in"
               "DUT3 ##########".format(acl_dict["dut1"]["ip_addr_list"][0],acl_dict["dut3"]["ip_addr_list"][0]))
    else:
        st.error("########## FAIL: Ping success from {} to {} in DUT3 which is NOT expected ########"
                           "##".format(acl_dict["dut1"]["ip_addr_list"][0],acl_dict["dut3"]["ip_addr_list"][0]))
    if success:
        st.report_pass("test_case_id_passed","test_acl_est_permit_any_any")
    else:
        st.report_fail("test_case_id_failed","test_acl_est_permit_any_any")


def test_acl_est_on_the_fly(acl_any_any_fixture):
    success = True
    st.log("###### Test on the fly changes of ACL with established keyword ######")
    if loc_obj.verify_ssh_session(vars.D3, acl_dict["d1_uname"], acl_dict["d1_pwd"],
                                  acl_dict["dut1"]["ip_addr_list"][0], rem_dut_mgmt=acl_dict["dut1_mgmt_ip"],
                                                              interface=acl_dict["dut3"]["ip_addr_list"][0]):
        success=False
        st.error("########## FAIL: Established SSH session from remote host to local host which is NOT"
                                                                      " expected ##########")
    else:
        st.log("########## PASS: As expected SSH session from remote host to local host fails ##########")

    if loc_obj.verify_ftp_session("dut3", acl_dict["d1_uname"], acl_dict["d1_pwd"],
                                  acl_dict["dut3_ssh_obj"],dest_ip=acl_dict["dut1"]["ip_addr_list"][0]):
        success=False
        st.error("########## FAIL: Established FTP session from DUT3 to DUT1 IP {} which is NOT"
                                   " expected ##########".format(acl_dict["dut1"]["ip_addr_list"][0]))
    else:
        st.log("########## PASS: As expected FTP session from DUT3 to DUT1 IP {} fails ########"
                                   "##".format(acl_dict["dut1"]["ip_addr_list"][0]))

    st.log("########## Unbind ACL from interface {} and {} in DUT2 #######"
           "###".format(acl_dict["dut2"]["intf_list_dut3"][0],acl_dict["dut2"]["intf_list_dut3"][1]))
    acl_obj.config_access_group(vars.D2, acl_type="ip", table_name=acl_dict["dut2"]["acl_name"],
                                access_group_action="in",port=acl_dict["dut2"]["intf_list_dut3"][0],
                                config="no")
    acl_obj.config_access_group(vars.D2, acl_type="ip", table_name=acl_dict["dut2"]["acl_name"],
                                access_group_action="in",port=acl_dict["dut2"]["intf_list_dut3"][1],
                                config="no")
    if loc_obj.verify_ssh_session(vars.D3, acl_dict["d1_uname"], acl_dict["d1_pwd"],
                                  acl_dict["dut1"]["ip_addr_list"][0], rem_dut_mgmt=acl_dict["dut1_mgmt_ip"],
                                                              interface=acl_dict["dut3"]["ip_addr_list"][0]):
        st.log("########## PASS: Established SSH session from remote host to local host"
                                                                             " after unbind ACL ##########")
    else:
        success=False
        st.error("########## FAIL: Failed to establish SSH session from remote host to local host even after"
                                                                                      " unbind ACL ##########")

    if loc_obj.verify_ftp_session("dut3", acl_dict["d1_uname"], acl_dict["d1_pwd"],
                                  acl_dict["dut3_ssh_obj"],dest_ip=acl_dict["dut1"]["ip_addr_list"][0]):
        st.log("########## PASS: Established FTP session from DUT3 to DUT1 IP {} after"
                                  "unbind ACL ##########".format(acl_dict["dut1"]["ip_addr_list"][0]))
    else:
        success=False
        st.error("########## FAIL: Failed to establish FTP session from DUT3 to DUT1 IP {} after"
                                 " unbind ACL ##########".format(acl_dict["dut1"]["ip_addr_list"][0]))

    st.log("########## Bind ACL to ports {} and {} in DUT2 ##########".format(acl_dict["dut2"]["intf_list_dut3"][0],
                                                                acl_dict["dut2"]["intf_list_dut3"][1]))
    acl_obj.config_access_group(vars.D2, acl_type="ip", table_name=acl_dict["dut2"]["acl_name"],
                                access_group_action="in",port=acl_dict["dut2"]["intf_list_dut3"][0],
                                config="yes")
    acl_obj.config_access_group(vars.D2, acl_type="ip", table_name=acl_dict["dut2"]["acl_name"],
                                access_group_action="in",port=acl_dict["dut2"]["intf_list_dut3"][1],
                                config="yes")
    if loc_obj.verify_ssh_session(vars.D3, acl_dict["d1_uname"], acl_dict["d1_pwd"],
                                  acl_dict["dut1"]["ip_addr_list"][0], rem_dut_mgmt=acl_dict["dut1_mgmt_ip"],
                                                              interface=acl_dict["dut3"]["ip_addr_list"][0]):
        success=False
        st.error("########## FAIL: After bind ACL, Established SSH session from remote host to local host"
                                                         " which is NOT expected ##########")
    else:
        st.log("########## PASS: As expected after bind ACL, SSH session from remote host to local"
                                                                                        " host fails ##########")

    if loc_obj.verify_ftp_session("dut3", acl_dict["d1_uname"], acl_dict["d1_pwd"],
                                  acl_dict["dut3_ssh_obj"],dest_ip=acl_dict["dut1"]["ip_addr_list"][0]):
        success=False
        st.error("########## FAIL: After bind ACL, Established FTP session from DUT3 to DUT1 IP {}"
                             " which is NOT expected ##########".format(acl_dict["dut1"]["ip_addr_list"][0]))
    else:
        st.log("########## As expected after bind ACL, FTP session from DUT3 to DUT1 IP {}"
                             " fails ##########".format(acl_dict["dut1"]["ip_addr_list"][0]))

    if success:
        st.report_pass("test_case_id_passed","test_acl_est_on_the_fly")
    else:
        st.report_fail("test_case_id_failed","test_acl_est_on_the_fly")


@pytest.fixture(scope="function")
def acl_rst_flag_fixture(request,acl_est_hooks):
    tg_dict["tg"].tg_traffic_control(action='clear_stats', port_handle=[tg_dict["d1_tg_ph1"],tg_dict["d3_tg_ph1"]])
    acl_obj.create_acl_table(vars.D2, name=acl_dict["dut2"]["acl_name"], type="ip",stage='INGRESS',
                             ports=[acl_dict["dut2"]["intf_list_dut3"][0],acl_dict["dut2"]["intf_list_dut3"][1]])
    acl_obj.create_acl_rule(vars.D2,acl_type='ip',rule_name=acl_dict["dut2"]["acl_name"],rule_seq='100',
                            packet_action='permit',src_ip='any', dst_ip='any',l4_protocol='tcp',
                            tcp_flag='established',table_name=acl_dict["dut2"]["acl_name"])
    acl_obj.clear_acl_counter(vars.D2, acl_type="ip")
    yield
    acl_obj.delete_acl_table(vars.D2, acl_type="ip", acl_table_name=[acl_dict["dut2"]["acl_name"]])
    loc_obj.start_traffic(stream_han_list=tg_dict["live_stream"],action="stop")


def test_acl_est_rst_flag_set(acl_rst_flag_fixture):
    success = True
    st.log("###### Test packet with RST bit set is allowed from remote host to local host ######")
    tg_dict["live_stream"] = tg_dict["v4_2"]
    loc_obj.start_traffic(stream_han_list=tg_dict["v4_2"])
    st.wait(5,"wait for traffic duration to be over")
    if loc_obj.verify_traffic(tx_stream_list=tg_dict["v4_2"],tx_port=tg_dict["d3_tg_port1"],
                                                            rx_port=tg_dict["d1_tg_port1"]):
        st.log("########## PASS: Packet with RST flag 1 is forwarded from DUT3 to DUT1 ##########")
    else:
        success=False
        st.error("########## FAIL: Packet with RST flag 1 is NOT forwarded from DUT3 to DUT1 ##########")
    if utils_obj.poll_wait(loc_obj.verify_acl_counters, 20,vars.D2,acl_dict["dut2"]["acl_name"],acl_type="ip"):
        st.log("########## PASS: Statistics incremented for ACL established rule ##########")
    else:
        success=False
        st.error("########## FAIL: Statistics NOT incremented for ACL established rule ##########")
    loc_obj.start_traffic(stream_han_list=tg_dict["v4_2"],action="stop")
    loc_obj.start_traffic(stream_han_list=tg_dict["v4_3"])
    st.wait(5,"wait for traffic duration to be over")
    tg_dict["live_stream"] = tg_dict["v4_3"]
    if not loc_obj.verify_traffic(tx_stream_list=tg_dict["v4_3"],tx_port=tg_dict["d3_tg_port1"],
                                                                 rx_port=tg_dict["d1_tg_port1"]):
        st.log("########## PASS: Packet with RST flag 0 is NOT forwarded from DUT3 to DUT1"
                                                                   " as expected ##########")
    else:
        success=False
        st.error("########## FAIL: Packet with RST flag 0 is forwarded from DUT3 to DUT1 which is NOT"
                                                                                " expected ##########")
    if success:
        st.report_pass("test_case_id_passed","test_acl_est_rst_flag_set")
    else:
        st.report_fail("test_case_id_failed","test_acl_est_rst_flag_set")


@pytest.fixture(scope="function")
def acl_specific_prefix_fixture(request,acl_est_hooks):
    tg_dict["tg"].tg_traffic_control(action='clear_stats', port_handle=[tg_dict["d1_tg_ph1"],tg_dict["d3_tg_ph1"]])
    acl_obj.create_acl_table(vars.D2, name=acl_dict["dut2"]["acl_name"], type="ip",stage='INGRESS',
                             ports=[acl_dict["dut2"]["intf_list_dut3"][0],acl_dict["dut2"]["intf_list_dut3"][1]])
    acl_obj.create_acl_rule(vars.D2,acl_type='ip',rule_name=acl_dict["dut2"]["acl_name"],rule_seq='100',
                            packet_action='permit',src_ip=acl_dict["dut3"]["prefix_list"][0],
                            dst_ip=acl_dict["dut1"]["prefix_list"][0],l4_protocol='tcp',
                            tcp_flag='established',table_name=acl_dict["dut2"]["acl_name"])
    acl_obj.create_acl_rule(vars.D2,acl_type='ip',rule_name=acl_dict["dut2"]["acl_name"],rule_seq='101',
                            packet_action='permit',src_ip=acl_dict["dut3"]["prefix_list"][1],
                            dst_ip="any",l4_protocol='tcp', table_name=acl_dict["dut2"]["acl_name"])
    yield
    acl_obj.delete_acl_table(vars.D2, acl_type="ip", acl_table_name=[acl_dict["dut2"]["acl_name"]])


def test_acl_est_specific_prefix(acl_specific_prefix_fixture):
    success = True
    st.log("###### Test ACL with established keyword for specific prefix ######")
    if loc_obj.verify_ssh_session(vars.D3, acl_dict["d1_uname"], acl_dict["d1_pwd"],
                                  acl_dict["dut1"]["ip_addr_list"][0],rem_dut_mgmt=acl_dict["dut1_mgmt_ip"],
                                                             interface=acl_dict["dut3"]["ip_addr_list"][0]):
        success=False
        st.error("########## FAIL: SSH session to {} with source ip as {} goes through which is NOT expected ##"
                 "########".format(acl_dict["dut1"]["ip_addr_list"][0], acl_dict["dut3"]["ip_addr_list"][0]))
    else:
        st.log("########## PASS: SSH session to {} with source ip as {} fails as expected ########"
                        "##".format(acl_dict["dut1"]["ip_addr_list"][0], acl_dict["dut3"]["ip_addr_list"][0]))
    if loc_obj.verify_ssh_session(vars.D3, acl_dict["d1_uname"], acl_dict["d1_pwd"],
                                  acl_dict["dut1"]["ip_addr_list"][0],rem_dut_mgmt=acl_dict["dut1_mgmt_ip"],
                                                             interface=acl_dict["dut3"]["ip_addr_list"][1]):
        st.log("########## PASS: SSH session successful to {} with source ip as {} #######"
                      "###".format(acl_dict["dut1"]["ip_addr_list"][0],acl_dict["dut3"]["ip_addr_list"][1]))
    else:
        success=False
        st.error("########## FAIL: SSH session failed to {} with source ip as {} ########"
                         "##".format(acl_dict["dut1"]["ip_addr_list"][0],acl_dict["dut3"]["ip_addr_list"][1]))
    if not loc_obj.verify_ssh_session(vars.D3, acl_dict["d1_uname"], acl_dict["d1_pwd"],
                                  acl_dict["dut1"]["ip_addr_list"][1],rem_dut_mgmt=acl_dict["dut1_mgmt_ip"],
                                                             interface=acl_dict["dut3"]["ip_addr_list"][0]):
        st.log("########## PASS: As expected, SSH session failed to {} with source ip as {} #######"
                         "###".format(acl_dict["dut1"]["ip_addr_list"][1],acl_dict["dut3"]["ip_addr_list"][0]))
    else:
        success=False
        st.error("########## FAIL: SSH session established to {} with source ip as {} which is NOT expected "
                          "##########".format(acl_dict["dut1"]["ip_addr_list"][1],
                                              acl_dict["dut3"]["ip_addr_list"][0]))
    if loc_obj.verify_ssh_session(vars.D3, acl_dict["d1_uname"], acl_dict["d1_pwd"],
                                  acl_dict["dut1"]["ip_addr_list"][1],rem_dut_mgmt=acl_dict["dut1_mgmt_ip"],
                                                             interface=acl_dict["dut3"]["ip_addr_list"][1]):
        st.log("########## PASS: SSH session successful to {} with source ip as {} ########"
                        "##".format(acl_dict["dut1"]["ip_addr_list"][1],acl_dict["dut3"]["ip_addr_list"][1]))
    else:
        success=False
        st.error("########## FAIL: SSH session failed to {} with source ip as {} ########"
                       "##".format(acl_dict["dut1"]["ip_addr_list"][1],acl_dict["dut3"]["ip_addr_list"][1]))
    if success:
        st.report_pass("test_case_id_passed","test_acl_est_specific_prefix")
    else:
        st.report_fail("test_case_id_failed","test_acl_est_specific_prefix")


@pytest.fixture(scope="function")
def acl_specific_port_fixture(request,acl_est_hooks):
    tg_dict["tg"].tg_traffic_control(action='clear_stats', port_handle=[tg_dict["d1_tg_ph1"],tg_dict["d3_tg_ph1"]])
    acl_obj.create_acl_table(vars.D2, name=acl_dict["dut2"]["acl_name"], type="ip",stage='INGRESS',
                             ports=[acl_dict["dut2"]["intf_list_dut3"][0],acl_dict["dut2"]["intf_list_dut3"][1]])
    acl_obj.create_acl_rule(vars.D2,acl_type='ip',rule_name=acl_dict["dut2"]["acl_name"],rule_seq='100',
                            packet_action='permit',src_ip=acl_dict["dut3"]["prefix_list"][0],
                            dst_ip=acl_dict["dut1"]["prefix_list"][0],l4_protocol='tcp',tcp_flag='established',
                            table_name=acl_dict["dut2"]["acl_name"],
                            dst_port="21",dst_comp_operator="gt")
    acl_obj.create_acl_rule(vars.D2,acl_type='ip',rule_name=acl_dict["dut2"]["acl_name"],rule_seq='101',
                            packet_action='permit',src_ip=acl_dict["dut3"]["prefix_list"][1],
                            dst_ip="any",l4_protocol='tcp',table_name=acl_dict["dut2"]["acl_name"])
    acl_obj.create_acl_rule(vars.D2,acl_type='ip',rule_name=acl_dict["dut2"]["acl_name"],rule_seq='102',
                            packet_action='permit',src_ip=acl_dict["dut3"]["prefix_list"][0],
                            dst_ip=acl_dict["dut1"]["prefix_list"][0],l4_protocol='tcp',
                            table_name=acl_dict["dut2"]["acl_name"],
                            dst_port="21",dst_comp_operator="lt")
    yield
    acl_obj.delete_acl_table(vars.D2, acl_type="ip", acl_table_name=[acl_dict["dut2"]["acl_name"]])


def test_acl_est_specific_port(acl_specific_port_fixture):
    success = True
    st.log("###### Test ACL with established keyword for specific port ######")
    if loc_obj.verify_ssh_session(vars.D3, acl_dict["d1_uname"], acl_dict["d1_pwd"],
                                  acl_dict["dut1"]["ip_addr_list"][0],rem_dut_mgmt=acl_dict["dut1_mgmt_ip"],
                                  interface=acl_dict["dut3"]["ip_addr_list"][0]):
        success=False
        st.error("########## FAIL: SSH session to {} with source ip {} goes through which is NOT "
                 "expected ##########".format(acl_dict["dut1"]["ip_addr_list"][0],
                                   acl_dict["dut3"]["ip_addr_list"][0]))
    else:
        st.log("########## PASS: SSH session to {} with source ip {} fails as"
               " expected ##########".format(acl_dict["dut1"]["ip_addr_list"][0],
                                 acl_dict["dut3"]["ip_addr_list"][0]))
    if loc_obj.verify_ssh_session(vars.D3, acl_dict["d1_uname"], acl_dict["d1_pwd"],
                                  acl_dict["dut1"]["ip_addr_list"][0],rem_dut_mgmt=acl_dict["dut1_mgmt_ip"],
                                  interface=acl_dict["dut3"]["ip_addr_list"][1]):
        st.log("########## PASS: SSH session successful to {} with source ip {}#######"
                   "###".format(acl_dict["dut1"]["ip_addr_list"][0],acl_dict["dut3"]["ip_addr_list"][1]))
    else:
        success=False
        st.error("########## FAIL: SSH session failed to {} with source ip {} ########"
                       "##".format(acl_dict["dut1"]["ip_addr_list"][0],acl_dict["dut3"]["ip_addr_list"][1]))
    if not loc_obj.verify_ssh_session(vars.D3, acl_dict["d1_uname"], acl_dict["d1_pwd"],
                                  acl_dict["dut1"]["ip_addr_list"][1],rem_dut_mgmt=acl_dict["dut1_mgmt_ip"],
                                  interface=acl_dict["dut3"]["ip_addr_list"][0]):
        st.log("########## PASS: As expected, SSH session failed to {} with source ip {} ########"
                 "##".format(acl_dict["dut1"]["ip_addr_list"][1],acl_dict["dut3"]["ip_addr_list"][0]))
    else:
        success=False
        st.error("########## FAIL: SSH session established to {} with source ip {} which is NOT "
                               " expected ##########".format(acl_dict["dut1"]["ip_addr_list"][1],
                               acl_dict["dut3"]["ip_addr_list"][0]))
    if loc_obj.verify_ssh_session(vars.D3, acl_dict["d1_uname"], acl_dict["d1_pwd"],
                                  acl_dict["dut1"]["ip_addr_list"][1],rem_dut_mgmt=acl_dict["dut1_mgmt_ip"],
                                  interface=acl_dict["dut3"]["ip_addr_list"][1]):
        st.log("########## PASS: SSH session successful to {} with source ip {} ########"
                  "##".format(acl_dict["dut1"]["ip_addr_list"][1],acl_dict["dut3"]["ip_addr_list"][1]))
    else:
        success=False
        st.error("########## FAIL: SSH session failed to {} with source ip {} ########"
                               "##".format(acl_dict["dut1"]["ip_addr_list"][1],
                               acl_dict["dut3"]["ip_addr_list"][1]))
    if loc_obj.verify_ftp_session("dut3", acl_dict["d1_uname"], acl_dict["d1_pwd"],
                                   acl_dict["dut3_ssh_obj"],dest_ip=acl_dict["dut1"]["ip_addr_list"][0]):
        st.log("########## PASS: FTP session is successful from DUT3 to DUT1 IP {} ########"
                           "##".format(acl_dict["dut1"]["ip_addr_list"][0]))
    else:
        success = False
        st.error("########## FAIL: FTP session failed from DUT3 to DUT1 IP {} ########"
                           "##".format(acl_dict["dut1"]["ip_addr_list"][0]))

    if success:
        st.report_pass("test_case_id_passed","test_acl_est_specific_port")
    else:
        st.report_fail("test_case_id_failed","test_acl_est_specific_port")


@pytest.fixture(scope="function")
def acl_any_any_egress_fixture(request,acl_est_hooks):
    tg_dict["tg"].tg_traffic_control(action='clear_stats', port_handle=[tg_dict["d1_tg_ph1"],tg_dict["d3_tg_ph1"]])
    acl_obj.create_acl_table(vars.D2, name=acl_dict["dut2"]["acl_name"], type="ip",stage='EGRESS',
                             ports=[acl_dict["dut2"]["intf_list_dut3"][0],acl_dict["dut2"]["intf_list_dut3"][1]])
    acl_obj.create_acl_rule(vars.D2,acl_type='ip',rule_name=acl_dict["dut2"]["acl_name"],rule_seq='100',
                            packet_action='permit',src_ip='any', dst_ip='any',l4_protocol='tcp',
                            tcp_flag='established',table_name=acl_dict["dut2"]["acl_name"])
    yield
    acl_obj.delete_acl_table(vars.D2, acl_type="ip", acl_table_name=[acl_dict["dut2"]["acl_name"]])


def test_acl_est_permit_any_any_egress(acl_any_any_egress_fixture):
    success = True
    st.log("########## Test SSH and FTP from local host to remote host with ACL established Egress rule ##########")
    if loc_obj.verify_ssh_session(vars.D1, acl_dict["d3_uname"], acl_dict["d3_pwd"],
                                  acl_dict["dut3"]["ip_addr_list"][0], rem_dut_mgmt=acl_dict["dut3_mgmt_ip"],
                                                             interface=acl_dict["dut1"]["ip_addr_list"][0]):
        success=False
        st.error("########## FAIL: Established SSH session from DUT1 to DUT3 {} with source IP as {}"
                                   "which is not expected #########"
                        "#".format(acl_dict["dut3"]["ip_addr_list"][0],acl_dict["dut1"]["ip_addr_list"][0]))
    else:
        st.log("########## PASS: As expected, Failed to establish SSH session from DUT1 to"
                                " DUT3 {} with source IP as {} #########"
                        "#".format(acl_dict["dut3"]["ip_addr_list"][0],acl_dict["dut1"]["ip_addr_list"][0]))
    if loc_obj.verify_ssh_session(vars.D3, acl_dict["d1_uname"], acl_dict["d1_pwd"],
                                  acl_dict["dut1"]["ip_addr_list"][0], rem_dut_mgmt=acl_dict["dut1_mgmt_ip"],
                                                              interface=acl_dict["dut3"]["ip_addr_list"][0]):
        st.log("########## PASS: Established SSH session from DUT3 to DUT1 {} with source IP as {} ########"
                        "##".format(acl_dict["dut1"]["ip_addr_list"][0],acl_dict["dut3"]["ip_addr_list"][0]))
    else:
        success=False
        st.error("########## FAIL: SSH session from DUT3 to DUT1 {} with source IP as {} fails ########"
                        "##".format(acl_dict["dut1"]["ip_addr_list"][0],acl_dict["dut3"]["ip_addr_list"][0]))

    if loc_obj.verify_ftp_session("dut1", acl_dict["d3_uname"], acl_dict["d3_pwd"],
                                   acl_dict["dut1_ssh_obj"],dest_ip=acl_dict["dut3"]["ip_addr_list"][0]):
        success=False
        st.error("########## FAIL: Established FTP session from DUT1 to DUT3 IP {}"
                                  " which is not expected ##########".format(acl_dict["dut3"]["ip_addr_list"][0]))
    else:
        st.log("########## PASS: As expected, Failed to establish FTP session from DUT1 to DUT3 IP {}"
                           " ##########".format(acl_dict["dut3"]["ip_addr_list"][0]))

    if loc_obj.verify_ftp_session("dut3", acl_dict["d1_uname"], acl_dict["d1_pwd"],
                                   acl_dict["dut3_ssh_obj"],dest_ip=acl_dict["dut1"]["ip_addr_list"][0]):
        st.log("########## PASS: Established FTP session from DUT3 to DUT1 IP {} as expected"
                                 " ##########".format(acl_dict["dut1"]["ip_addr_list"][0]))
    else:
        success=False
        st.error("########## FAIL: FTP session from DUT3 to DUT1 IP {} fails"
                             " ##########".format(acl_dict["dut1"]["ip_addr_list"][0]))
    if success:
        st.report_pass("test_case_id_passed","test_acl_est_permit_any_any_egress")
    else:
        st.report_fail("test_case_id_failed","test_acl_est_permit_any_any_egress")


def test_acl_est_on_the_fly_egress(acl_any_any_egress_fixture):
    success = True
    st.log("###### Test on the fly changes of ACL with established egress keyword ######")
    if loc_obj.verify_ssh_session(vars.D1, acl_dict["d3_uname"], acl_dict["d3_pwd"],
                                  acl_dict["dut3"]["ip_addr_list"][0], rem_dut_mgmt=acl_dict["dut3_mgmt_ip"],
                                                             interface=acl_dict["dut1"]["ip_addr_list"][0]):
        success=False
        st.error("########## FAIL: Established SSH session from DUT1 to DUT3 {} with source IP as {}"
                                  " which is not expected #########"
                         "#".format(acl_dict["dut3"]["ip_addr_list"][0],acl_dict["dut1"]["ip_addr_list"][0]))
    else:
        st.log("########## PASS: As expected, Failed to establish SSH session from DUT1 to DUT3 {} with"
                       " source IP as {} #########"
                       "#".format(acl_dict["dut3"]["ip_addr_list"][0],acl_dict["dut1"]["ip_addr_list"][0]))
    if loc_obj.verify_ftp_session("dut1", acl_dict["d3_uname"], acl_dict["d3_pwd"],
                                   acl_dict["dut1_ssh_obj"],dest_ip=acl_dict["dut3"]["ip_addr_list"][0]):
        success=False
        st.error("########## FAIL: Established FTP session from DUT1 to DUT3 IP {} which is not"
                                   " expected ##########".format(acl_dict["dut3"]["ip_addr_list"][0]))
    else:
        st.log("########## PASS: As expected, Failed to establish FTP session from DUT1 to DUT3"
                                   " IP {} ##########".format(acl_dict["dut3"]["ip_addr_list"][0]))
    st.log("########## Unbind ACL from interface {} and {} in DUT2 #######"
           "###".format(acl_dict["dut2"]["intf_list_dut3"][0],acl_dict["dut2"]["intf_list_dut3"][1]))
    acl_obj.config_access_group(vars.D2, acl_type="ip", table_name=acl_dict["dut2"]["acl_name"],
                                access_group_action="out",port=acl_dict["dut2"]["intf_list_dut3"][0],
                                config="no")
    acl_obj.config_access_group(vars.D2, acl_type="ip", table_name=acl_dict["dut2"]["acl_name"],
                                access_group_action="out",port=acl_dict["dut2"]["intf_list_dut3"][1],
                                config="no")

    if loc_obj.verify_ssh_session(vars.D1, acl_dict["d3_uname"], acl_dict["d3_pwd"],
                                  acl_dict["dut3"]["ip_addr_list"][0], rem_dut_mgmt=acl_dict["dut3_mgmt_ip"],
                                                             interface=acl_dict["dut1"]["ip_addr_list"][0]):
        st.log("########## PASS: Established SSH session from DUT1 to DUT3 {} with source IP {}"
                     " as expected after unbind ACL#########"
                     "#".format(acl_dict["dut3"]["ip_addr_list"][0],acl_dict["dut1"]["ip_addr_list"][0]))
    else:
        success=False
        st.error("########## FAIL: SSH session from DUT1 to DUT3 {} with source IP {} fails after unbind ACL "
                    " which is not expected #########"
                    "#".format(acl_dict["dut3"]["ip_addr_list"][0],acl_dict["dut1"]["ip_addr_list"][0]))
    if loc_obj.verify_ftp_session("dut1", acl_dict["d3_uname"], acl_dict["d3_pwd"],
                                   acl_dict["dut1_ssh_obj"],dest_ip=acl_dict["dut3"]["ip_addr_list"][0]):
        st.log("########## PASS: Established FTP session from DUT1 to DUT3 IP {} as expected "
                       " after unbind ACL ##########".format(acl_dict["dut3"]["ip_addr_list"][0]))
    else:
        success=False
        st.error("########## FAIL: FTP session from DUT1 to DUT3 IP {} fails after unbind ACL"
                       "which is not expected ##########".format(acl_dict["dut3"]["ip_addr_list"][0]))

    st.log("########## Bind ACL to ports {} and {} in DUT2 ##########".format(acl_dict["dut2"]["intf_list_dut3"][0],
                                                                acl_dict["dut2"]["intf_list_dut3"][1]))
    acl_obj.config_access_group(vars.D2, acl_type="ip", table_name=acl_dict["dut2"]["acl_name"],
                                access_group_action="out",port=acl_dict["dut2"]["intf_list_dut3"][0],
                                config="yes")
    acl_obj.config_access_group(vars.D2, acl_type="ip", table_name=acl_dict["dut2"]["acl_name"],
                                access_group_action="out",port=acl_dict["dut2"]["intf_list_dut3"][1],
                                config="yes")
    if loc_obj.verify_ssh_session(vars.D1, acl_dict["d3_uname"], acl_dict["d3_pwd"],
                                  acl_dict["dut3"]["ip_addr_list"][0], rem_dut_mgmt=acl_dict["dut3_mgmt_ip"],
                                                             interface=acl_dict["dut1"]["ip_addr_list"][0]):
        success=False
        st.error("########## FAIL: Established SSH session from DUT1 to DUT3 {} with source IP {} "
                           "after bind ACL which is not expected #########"
                           "#".format(acl_dict["dut3"]["ip_addr_list"][0],acl_dict["dut1"]["ip_addr_list"][0]))
    else:
        st.log("########## PASS: As expected, Failed to establish SSH session from DUT1 to DUT3 {}"
                         " with source IP {} after bind ACL #########"
                         "#".format(acl_dict["dut3"]["ip_addr_list"][0],acl_dict["dut1"]["ip_addr_list"][0]))
    if loc_obj.verify_ftp_session("dut1", acl_dict["d3_uname"], acl_dict["d3_pwd"],
                                   acl_dict["dut1_ssh_obj"],dest_ip=acl_dict["dut3"]["ip_addr_list"][0]):
        success=False
        st.error("########## FAIL: Established FTP session from DUT1 to DUT3 IP {} after bind ACL"
                       " which is not expected ##########".format(acl_dict["dut3"]["ip_addr_list"][0]))
    else:
        st.log("########## PASS: As expected, Failed to establish FTP session from DUT1 to DUT3"
                       " IP {} after bind ACL ##########".format(acl_dict["dut3"]["ip_addr_list"][0]))

    if success:
        st.report_pass("test_case_id_passed","test_acl_est_on_the_fly_egress")
    else:
        st.report_fail("test_case_id_failed","test_acl_est_on_the_fly_egress")


@pytest.fixture(scope="function")
def aclv6_any_any_fixture(request,acl_est_hooks):
    tg_dict["tg"].tg_traffic_control(action='clear_stats', port_handle=[tg_dict["d1_tg_ph1"],tg_dict["d3_tg_ph1"]])
    acl_obj.create_acl_table(vars.D2, name=acl_dict["dut2"]["acl_name_v6"], type="ipv6",stage='INGRESS',
                             ports=[acl_dict["dut2"]["intf_list_dut3"][0],acl_dict["dut2"]["intf_list_dut3"][1]])
    acl_obj.create_acl_rule(vars.D2,acl_type='ipv6',rule_name=acl_dict["dut2"]["acl_name_v6"],rule_seq='200',
                            packet_action='permit',src_ip='any', dst_ip='any',l4_protocol='tcp',
                            tcp_flag='established',table_name=acl_dict["dut2"]["acl_name_v6"])
    yield
    acl_obj.delete_acl_table(vars.D2, acl_type="ipv6", acl_table_name=[acl_dict["dut2"]["acl_name_v6"]])


def test_aclv6_est_permit_any_any(aclv6_any_any_fixture):
    success = True
    st.log("###### Test IPv6 SSH and FTP from local host to remote host with ACL established rule ######")
    if loc_obj.verify_ssh_session(vars.D1, acl_dict["d3_uname"], acl_dict["d3_pwd"],
                                  acl_dict["dut3"]["ipv6_addr_list"][0], rem_dut_mgmt=acl_dict["dut3_mgmt_ip"],
                                                             interface=acl_dict["dut1"]["ipv6_addr_list"][0]):
        st.log("########## PASS: Successfully established IPv6 SSH session from localhost to remote"
                                                                                   " host ##########")
    else:
        success=False
        st.error("########## FAIL: Failed to establish SSH IPv6 session from localhost to remote host"
                                                                                          " ##########")
    if loc_obj.verify_ssh_session(vars.D3, acl_dict["d1_uname"], acl_dict["d1_pwd"],
                                  acl_dict["dut1"]["ipv6_addr_list"][0], rem_dut_mgmt=acl_dict["dut1_mgmt_ip"],
                                                              interface=acl_dict["dut3"]["ipv6_addr_list"][0]):
        success=False
        st.error("########## FAIL: Established IPv6 SSH session from remote host to local host which is NOT"
                                                                                        " expected ##########")
    else:
        st.log("########## PASS: Failed to establish IPv6 SSH session from remote host to local host as"
                                                                                        " expected ##########")
    if loc_obj.verify_ftp_session("dut1", acl_dict["d3_uname"], acl_dict["d3_pwd"],
                                   acl_dict["dut1_ssh_obj"],dest_ip=acl_dict["dut3"]["ipv6_addr_list"][0]):
        st.log("########## PASS: Successfully established IPv6 FTP session from DUT1 to DUT3 IP {}"
                            " ##########".format(acl_dict["dut3"]["ipv6_addr_list"][0]))
    else:
        success=False
        st.error("########## FAIL: Failed to establish IPv6 FTP session from DUT1 to DUT3 IP {}"
                            " ##########".format(acl_dict["dut3"]["ipv6_addr_list"][0]))
    if loc_obj.verify_ftp_session("dut3", acl_dict["d1_uname"], acl_dict["d1_pwd"],
                                   acl_dict["dut3_ssh_obj"],dest_ip=acl_dict["dut1"]["ipv6_addr_list"][0]):
        success=False
        st.error("########## FAIL: Established IPv6 FTP session from DUT3 to DUT1 IP {} which is NOT"
                            " expected ##########".format(acl_dict["dut1"]["ipv6_addr_list"][0]))
    else:
        st.log("########## PASS: As expected IPv6 FTP session from DUT3 to DUT1 IP {} fails ########"
                            "##".format(acl_dict["dut1"]["ipv6_addr_list"][0]))
    if success:
        st.report_pass("test_case_id_passed","test_aclv6_est_permit_any_any")
    else:
        st.report_fail("test_case_id_failed","test_aclv6_est_permit_any_any")


def test_aclv6_est_on_the_fly(aclv6_any_any_fixture):
    success = True
    st.log("###### Test on the fly changes of IPv6 ACL with established keyword ######")
    if loc_obj.verify_ssh_session(vars.D3, acl_dict["d1_uname"], acl_dict["d1_pwd"],
                                  acl_dict["dut1"]["ipv6_addr_list"][0], rem_dut_mgmt=acl_dict["dut1_mgmt_ip"],
                                                              interface=acl_dict["dut3"]["ipv6_addr_list"][0]):
        success=False
        st.error("########## FAIL: Established IPv6 SSH session from remote host to local host which is NOT"
                                                                                       " expected ##########")
    else:
        st.log("########## PASS: As expected IPv6 SSH session from remote host to local host fails ##########")
    if loc_obj.verify_ftp_session("dut3", acl_dict["d1_uname"], acl_dict["d1_pwd"],
                                  acl_dict["dut3_ssh_obj"],dest_ip=acl_dict["dut1"]["ipv6_addr_list"][0]):
        success=False
        st.error("########## FAIL: Established IPv6 FTP session from DUT3 to DUT1 IP {} which is NOT"
                                  " expected ##########".format(acl_dict["dut1"]["ipv6_addr_list"][0]))
    else:
        st.log("########## PASS: As expected IPv6 FTP session from DUT3 to DUT1 IP {} fails ########"
                                  "##".format(acl_dict["dut1"]["ipv6_addr_list"][0]))
    st.log("########## Unbind ACL from interface {} and {} in DUT2 ##########".format(acl_dict["dut2"]["intf_list_dut3"][0],
                                                                acl_dict["dut2"]["intf_list_dut3"][1]))
    acl_obj.config_access_group(vars.D2, acl_type="ipv6", table_name=acl_dict["dut2"]["acl_name_v6"],
                                access_group_action="in",port=acl_dict["dut2"]["intf_list_dut3"][0],
                                config="no")
    acl_obj.config_access_group(vars.D2, acl_type="ipv6", table_name=acl_dict["dut2"]["acl_name_v6"],
                                access_group_action="in",port=acl_dict["dut2"]["intf_list_dut3"][1],
                                config="no")
    if loc_obj.verify_ssh_session(vars.D3, acl_dict["d1_uname"], acl_dict["d1_pwd"],
                                  acl_dict["dut1"]["ipv6_addr_list"][0], rem_dut_mgmt=acl_dict["dut1_mgmt_ip"],
                                                              interface=acl_dict["dut3"]["ipv6_addr_list"][0]):
        st.log("########## PASS: Established IPv6 SSH session from remote host to local host after unbind"
                                                                                              " ACL ##########")
    else:
        success=False
        st.error("########## FAIL: Failed to establish IPv6 SSH session from remote host to local host even after"
                                                                                           " unbind ACL ##########")
    if loc_obj.verify_ftp_session("dut3", acl_dict["d1_uname"], acl_dict["d1_pwd"],
                                  acl_dict["dut3_ssh_obj"],dest_ip=acl_dict["dut1"]["ipv6_addr_list"][0]):
        st.log("########## PASS: Established IPv6 FTP session from DUT3 to DUT1 IP {} after unbind"
                                " ACL ##########".format(acl_dict["dut1"]["ipv6_addr_list"][0]))
    else:
        success=False
        st.error("########## FAIL: Failed to establish IPv6 FTP session from DUT3 to DUT1 IP {} after unbind"
                                " ACL ##########".format(acl_dict["dut1"]["ipv6_addr_list"][0]))
    st.log("########## Bind ACL to ports {} and {} in DUT2 ##########".format(acl_dict["dut2"]["intf_list_dut3"][0],
                                                                acl_dict["dut2"]["intf_list_dut3"][1]))
    acl_obj.config_access_group(vars.D2, acl_type="ipv6", table_name=acl_dict["dut2"]["acl_name_v6"],
                                access_group_action="in",port=acl_dict["dut2"]["intf_list_dut3"][0],
                                config="yes")
    acl_obj.config_access_group(vars.D2, acl_type="ipv6", table_name=acl_dict["dut2"]["acl_name_v6"],
                                access_group_action="in",port=acl_dict["dut2"]["intf_list_dut3"][1],
                                config="yes")
    if loc_obj.verify_ssh_session(vars.D3, acl_dict["d1_uname"], acl_dict["d1_pwd"],
                                  acl_dict["dut1"]["ipv6_addr_list"][0], rem_dut_mgmt=acl_dict["dut1_mgmt_ip"],
                                                              interface=acl_dict["dut3"]["ipv6_addr_list"][0]):
        success=False
        st.error("A########## FAIL: fter bind ACL, Established IPv6 SSH session from remote host to local host which"
                                                                                         " is NOT expected ##########")
    else:
        st.log("########## PASS: As expected after bind ACL,IPv6 SSH session from remote host to local host"
                                                                                                 " fails ##########")
    if loc_obj.verify_ftp_session("dut3", acl_dict["d1_uname"], acl_dict["d1_pwd"],
                                  acl_dict["dut3_ssh_obj"],dest_ip=acl_dict["dut1"]["ipv6_addr_list"][0]):
        success=False
        st.error("########## FAIL: After bind ACL. Established IPv6 FTP session from DUT3 to DUT1 IP {}"
                              " which is NOT expected ##########".format(acl_dict["dut1"]["ipv6_addr_list"][0]))
    else:
        st.log("########## PASS: As expected after bind ACL, IPv6 FTP session from DUT3 to DUT1 IP {}"
                              " fails ##########".format(acl_dict["dut1"]["ipv6_addr_list"][0]))
    if success:
        st.report_pass("test_case_id_passed","test_acl_est_on_the_fly")
    else:
        st.report_fail("test_case_id_failed","test_acl_est_on_the_fly")


@pytest.fixture(scope="function")
def aclv6_rst_flag_fixture(request,acl_est_hooks):
    tg_dict["tg"].tg_traffic_control(action='clear_stats', port_handle=[tg_dict["d1_tg_ph1"],tg_dict["d3_tg_ph1"]])
    acl_obj.create_acl_table(vars.D2, name=acl_dict["dut2"]["acl_name_v6"], type="ipv6",stage='INGRESS',
                             ports=[acl_dict["dut2"]["intf_list_dut3"][0],acl_dict["dut2"]["intf_list_dut3"][1]])
    acl_obj.create_acl_rule(vars.D2,acl_type='ipv6',rule_name=acl_dict["dut2"]["acl_name_v6"],rule_seq='200',
                            packet_action='permit',src_ip='any', dst_ip='any',l4_protocol='tcp',
                            tcp_flag='established',table_name=acl_dict["dut2"]["acl_name_v6"])
    yield
    acl_obj.delete_acl_table(vars.D2, acl_type="ipv6", acl_table_name=[acl_dict["dut2"]["acl_name_v6"]])
    loc_obj.start_traffic(stream_han_list=tg_dict["live_stream"],action="stop")


def test_aclv6_est_rst_flag_set(aclv6_rst_flag_fixture):
    success = True
    st.log("###### Test IPv6 packet with RST bit set is allowed from remote host to local host ######")
    tg_dict["live_stream"] = tg_dict["v6_2"]
    loc_obj.start_traffic(stream_han_list=tg_dict["v6_2"])
    st.wait(5,"wait for traffic duration to be over")
    if loc_obj.verify_traffic(tx_stream_list=tg_dict["v6_2"],tx_port=tg_dict["d3_tg_port1"],
                                                            rx_port=tg_dict["d1_tg_port1"]):
        st.log("########## PASS: IPv6 Packet with RST flag 1 is forwarded from DUT3 to DUT1 ##########")
    else:
        success=False
        st.error("########## FAIL: IPv6 Packet with RST flag 1 is NOT forwarded from DUT3 to DUT1 ##########")
    loc_obj.start_traffic(stream_han_list=tg_dict["v6_2"],action="stop")
    loc_obj.start_traffic(stream_han_list=tg_dict["v6_3"])
    st.wait(5,"wait for traffic duration to be over")
    tg_dict["live_stream"] = tg_dict["v6_3"]
    if not loc_obj.verify_traffic(tx_stream_list=tg_dict["v6_3"],tx_port=tg_dict["d3_tg_port1"],
                                                                 rx_port=tg_dict["d1_tg_port1"]):
        st.log("########## PASS: IPv6 Packet with RST flag 0 is NOT forwarded from DUT3 to DUT1 as"
                                                                              " expected ##########")
    else:
        success=False
        st.error("########## FAIL: IPv6 Packet with RST flag 0 is forwarded from DUT3 to DUT1 which is"
                                                                           " NOT expected ##########")
    if success:
        st.report_pass("test_case_id_passed","test_aclv6_est_rst_flag_set")
    else:
        st.report_fail("test_case_id_failed","test_aclv6_est_rst_flag_set")


@pytest.fixture(scope="function")
def aclv6_specific_prefix_fixture(request,acl_est_hooks):
    tg_dict["tg"].tg_traffic_control(action='clear_stats', port_handle=[tg_dict["d1_tg_ph1"],tg_dict["d3_tg_ph1"]])
    acl_obj.create_acl_table(vars.D2, name=acl_dict["dut2"]["acl_name_v6"], type="ipv6",stage='INGRESS',
                             ports=[acl_dict["dut2"]["intf_list_dut3"][0],acl_dict["dut2"]["intf_list_dut3"][1]])
    acl_obj.create_acl_rule(vars.D2,acl_type='ipv6',rule_name=acl_dict["dut2"]["acl_name_v6"],rule_seq='200',
                            packet_action='permit',src_ip=acl_dict["dut3"]["prefix_v6_list"][0],
                            dst_ip=acl_dict["dut1"]["prefix_v6_list"][0],l4_protocol='tcp',tcp_flag='established',
                            table_name=acl_dict["dut2"]["acl_name_v6"])
    acl_obj.create_acl_rule(vars.D2,acl_type='ipv6',rule_name=acl_dict["dut2"]["acl_name_v6"],rule_seq='201',
                            packet_action='permit',src_ip=acl_dict["dut3"]["prefix_v6_list"][1],
                            dst_ip="any",l4_protocol='tcp',table_name=acl_dict["dut2"]["acl_name_v6"])
    yield
    acl_obj.delete_acl_table(vars.D2, acl_type="ipv6", acl_table_name=[acl_dict["dut2"]["acl_name_v6"]])


def test_aclv6_est_specific_prefix(aclv6_specific_prefix_fixture):
    success = True
    st.log("###### Test IPv6 ACL with established keyword for specific prefix ######")
    if loc_obj.verify_ssh_session(vars.D3, acl_dict["d1_uname"], acl_dict["d1_pwd"],
                                  acl_dict["dut1"]["ipv6_addr_list"][0],rem_dut_mgmt=acl_dict["dut1_mgmt_ip"],
                                                             interface=acl_dict["dut3"]["ipv6_addr_list"][0]):
        success=False
        st.error("########## FAIL: IPv6 SSH session to {} with source ip as {} goes through which is NOT "
                 "expected ##########".format(acl_dict["dut1"]["ipv6_addr_list"][0],
                                                                    acl_dict["dut3"]["ipv6_addr_list"][0]))
    else:
        st.log("########## PASS: IPv6 SSH session to {} with source ip as {} fails as expected #######"
                       "###".format(acl_dict["dut1"]["ipv6_addr_list"][0],acl_dict["dut3"]["ipv6_addr_list"][0]))
    if loc_obj.verify_ssh_session(vars.D3, acl_dict["d1_uname"], acl_dict["d1_pwd"],
                                  acl_dict["dut1"]["ipv6_addr_list"][0],rem_dut_mgmt=acl_dict["dut1_mgmt_ip"],
                                                             interface=acl_dict["dut3"]["ipv6_addr_list"][1]):
        st.log("########## PASS: IPv6 SSH session success to {} with source ip as {} ########"
                         "##".format(acl_dict["dut1"]["ipv6_addr_list"][0],acl_dict["dut3"]["ipv6_addr_list"][1]))
    else:
        success=False
        st.error("########## FAIL: IPv6 SSH session failed to {} with source ip as {} ########"
                       "##".format(acl_dict["dut1"]["ipv6_addr_list"][0],acl_dict["dut3"]["ipv6_addr_list"][1]))
    if not loc_obj.verify_ssh_session(vars.D3, acl_dict["d1_uname"], acl_dict["d1_pwd"],
                                  acl_dict["dut1"]["ipv6_addr_list"][1],rem_dut_mgmt=acl_dict["dut1_mgmt_ip"],
                                                             interface=acl_dict["dut3"]["ipv6_addr_list"][0]):
        st.log("########## PASS: As expected, IPv6 SSH session failed to {} with source ip as {} ########"
                       "##".format(acl_dict["dut1"]["ipv6_addr_list"][1],acl_dict["dut3"]["ipv6_addr_list"][0]))
    else:
        success=False
        st.error("########## FAIL: IPv6 SSH session established to {} with source ip as {} which is NOT"
                       " expected ##########".format(acl_dict["dut1"]["ipv6_addr_list"][1],
                                                     acl_dict["dut3"]["ipv6_addr_list"][0]))
    if loc_obj.verify_ssh_session(vars.D3, acl_dict["d1_uname"], acl_dict["d1_pwd"],
                                  acl_dict["dut1"]["ipv6_addr_list"][1],rem_dut_mgmt=acl_dict["dut1_mgmt_ip"],
                                                             interface=acl_dict["dut3"]["ipv6_addr_list"][1]):
        st.log("########## PASS: IPv6 SSH session established to {} with source ip as {} ########"
                       "##".format(acl_dict["dut1"]["ipv6_addr_list"][1],acl_dict["dut3"]["ipv6_addr_list"][1]))
    else:
        success=False
        st.error("########## FAIL: IPv6 SSH session failed to {} with source ip as {} ########"
                       "##".format(acl_dict["dut1"]["ipv6_addr_list"][1],acl_dict["dut3"]["ipv6_addr_list"][1]))
    if success:
        st.report_pass("test_case_id_passed","test_aclv6_est_specific_prefix")
    else:
        st.report_fail("test_case_id_failed","test_aclv6_est_specific_prefix")


@pytest.fixture(scope="function")
def aclv6_specific_port_fixture(request,acl_est_hooks):
    tg_dict["tg"].tg_traffic_control(action='clear_stats', port_handle=[tg_dict["d1_tg_ph1"],tg_dict["d3_tg_ph1"]])
    acl_obj.create_acl_table(vars.D2, name=acl_dict["dut2"]["acl_name_v6"], type="ipv6",stage='INGRESS',
                             ports=[acl_dict["dut2"]["intf_list_dut3"][0],acl_dict["dut2"]["intf_list_dut3"][1]])
    acl_obj.create_acl_rule(vars.D2,acl_type='ipv6',rule_name=acl_dict["dut2"]["acl_name_v6"],rule_seq='200',
                            packet_action='permit',src_ip=acl_dict["dut3"]["prefix_v6_list"][0],
                            dst_ip=acl_dict["dut1"]["prefix_v6_list"][0],l4_protocol='tcp',tcp_flag='established',
                            table_name=acl_dict["dut2"]["acl_name_v6"],
                            dst_port="21",dst_comp_operator="gt")
    acl_obj.create_acl_rule(vars.D2,acl_type='ipv6',rule_name=acl_dict["dut2"]["acl_name_v6"],rule_seq='201',
                            packet_action='permit',src_ip=acl_dict["dut3"]["prefix_v6_list"][1],
                            dst_ip="any",l4_protocol='tcp',table_name=acl_dict["dut2"]["acl_name_v6"])
    acl_obj.create_acl_rule(vars.D2,acl_type='ipv6',rule_name=acl_dict["dut2"]["acl_name_v6"],rule_seq='202',
                            packet_action='permit',src_ip=acl_dict["dut3"]["prefix_v6_list"][0],
                            dst_ip=acl_dict["dut1"]["prefix_v6_list"][0],l4_protocol='tcp',
                            table_name=acl_dict["dut2"]["acl_name_v6"],
                            dst_port="21",dst_comp_operator="lt")
    yield
    acl_obj.delete_acl_table(vars.D2, acl_type="ipv6", acl_table_name=[acl_dict["dut2"]["acl_name_v6"]])


def test_aclv6_est_specific_port(aclv6_specific_port_fixture):
    success = True
    st.log("###### Test IPv6 ACL with established keyword for specific port ######")
    if loc_obj.verify_ssh_session(vars.D3, acl_dict["d1_uname"], acl_dict["d1_pwd"],
                                  acl_dict["dut1"]["ipv6_addr_list"][0],rem_dut_mgmt=acl_dict["dut1_mgmt_ip"],
                                  interface=acl_dict["dut3"]["ipv6_addr_list"][0]):
        success=False
        st.error("########## FAIL: IPv6 SSH session established to {} with source ip {} which is NOT "
                 "expected ##########".format(acl_dict["dut1"]["ipv6_addr_list"][0],
                                   acl_dict["dut3"]["ipv6_addr_list"][0]))
    else:
        st.log("########## PASS: IPv6 SSH session to {} with source ip {} fails as"
               " expected ##########".format(acl_dict["dut1"]["ipv6_addr_list"][0],
                                 acl_dict["dut3"]["ipv6_addr_list"][0]))
    if loc_obj.verify_ssh_session(vars.D3, acl_dict["d1_uname"], acl_dict["d1_pwd"],
                                  acl_dict["dut1"]["ipv6_addr_list"][0],rem_dut_mgmt=acl_dict["dut1_mgmt_ip"],
                                  interface=acl_dict["dut3"]["ipv6_addr_list"][1]):
        st.log("########## PASS: IPv6 SSH session successful to {} with source ip {} ########"
                               "##".format(acl_dict["dut1"]["ipv6_addr_list"][0],
                               acl_dict["dut3"]["ipv6_addr_list"][1]))
    else:
        success=False
        st.error("########## FAIL: IPv6 SSH session failed to {} with source ip {} ########"
                               "##".format(acl_dict["dut1"]["ipv6_addr_list"][0],
                               acl_dict["dut3"]["ipv6_addr_list"][1]))
    if not loc_obj.verify_ssh_session(vars.D3, acl_dict["d1_uname"], acl_dict["d1_pwd"],
                                  acl_dict["dut1"]["ipv6_addr_list"][1],rem_dut_mgmt=acl_dict["dut1_mgmt_ip"],
                                  interface=acl_dict["dut3"]["ipv6_addr_list"][0]):
        st.log("########## PASS: As expected, IPv6 SSH session failed to {} with source ip {} ########"
                               "##".format(acl_dict["dut1"]["ipv6_addr_list"][1],
                               acl_dict["dut3"]["ipv6_addr_list"][0]))
    else:
        success=False
        st.error("########## FAIL: IPv6 SSH session established to {} with source ip {} which is NOT "
                               " expected ##########".format(acl_dict["dut1"]["ipv6_addr_list"][1],
                               acl_dict["dut3"]["ipv6_addr_list"][0]))
    if loc_obj.verify_ssh_session(vars.D3, acl_dict["d1_uname"], acl_dict["d1_pwd"],
                                  acl_dict["dut1"]["ipv6_addr_list"][1],rem_dut_mgmt=acl_dict["dut1_mgmt_ip"],
                                  interface=acl_dict["dut3"]["ipv6_addr_list"][1]):
        st.log("########## PASS: IPv6 SSH session successful to {} with source ip {} ########"
                               "##".format(acl_dict["dut1"]["ipv6_addr_list"][1],
                               acl_dict["dut3"]["ipv6_addr_list"][1]))
    else:
        success=False
        st.error("########## FAIL: IPv6 SSH session failed to {} with source ip {} ########"
                               "##".format(acl_dict["dut1"]["ipv6_addr_list"][1],
                               acl_dict["dut3"]["ipv6_addr_list"][1]))
    if loc_obj.verify_ftp_session("dut3", acl_dict["d1_uname"], acl_dict["d1_pwd"],
                                   acl_dict["dut3_ssh_obj"],dest_ip=acl_dict["dut1"]["ipv6_addr_list"][0]):
        st.log("########## PASS: IPv6 FTP session from DUT3 to DUT1 IP {} is successful ########"
                                  "##".format(acl_dict["dut1"]["ipv6_addr_list"][0]))
    else:
        success = False
        st.error("########## FAIL: IPv6 FTP session from DUT3 to DUT1 IP {} failed ########"
                                  "##".format(acl_dict["dut1"]["ipv6_addr_list"][0]))

    if success:
        st.report_pass("test_case_id_passed","test_aclv6_est_specific_port")
    else:
        st.report_fail("test_case_id_failed","test_aclv6_est_specific_port")


@pytest.fixture(scope="function")
def aclv6_specific_prefix_egress_fixture(request,acl_est_hooks):
    tg_dict["tg"].tg_traffic_control(action='clear_stats', port_handle=[tg_dict["d1_tg_ph1"],tg_dict["d3_tg_ph1"]])
    acl_obj.create_acl_table(vars.D2, name=acl_dict["dut2"]["acl_name_v6"], type="ipv6",stage='EGRESS',
                             ports=[acl_dict["dut2"]["intf_list_dut3"][0],acl_dict["dut2"]["intf_list_dut3"][1]])
    acl_obj.create_acl_rule(vars.D2,acl_type='ipv6',rule_name=acl_dict["dut2"]["acl_name_v6"],rule_seq='200',
                            packet_action='permit',src_ip=acl_dict["dut1"]["prefix_v6_list"][0],
                            dst_ip=acl_dict["dut3"]["prefix_v6_list"][0],l4_protocol='tcp',tcp_flag='established',
                            table_name=acl_dict["dut2"]["acl_name_v6"])
    acl_obj.create_acl_rule(vars.D2,acl_type='ipv6',rule_name=acl_dict["dut2"]["acl_name_v6"],rule_seq='201',
                            packet_action='permit',src_ip=acl_dict["dut1"]["prefix_v6_list"][1],
                            dst_ip="any",l4_protocol='tcp',table_name=acl_dict["dut2"]["acl_name_v6"])
    yield
    acl_obj.delete_acl_table(vars.D2, acl_type="ipv6", acl_table_name=[acl_dict["dut2"]["acl_name_v6"]])


def test_aclv6_est_specific_egress_prefix(aclv6_specific_prefix_egress_fixture):
    success = True
    st.log("###### Test Egress IPv6 ACL with established keyword for specific prefix ######")
    if loc_obj.verify_ssh_session(vars.D1, acl_dict["d3_uname"], acl_dict["d3_pwd"],
                                  acl_dict["dut3"]["ipv6_addr_list"][0],rem_dut_mgmt=acl_dict["dut3_mgmt_ip"],
                                                             interface=acl_dict["dut1"]["ipv6_addr_list"][0]):
        success=False
        st.error("########## FAIL: IPv6 SSH session to {} with source ip as {} goes through which is NOT "
                 "expected ##########".format(acl_dict["dut3"]["ipv6_addr_list"][0],
                                                                    acl_dict["dut1"]["ipv6_addr_list"][0]))
    else:
        st.log("########## PASS: IPv6 SSH session to {} with source ip as {} fails as expected #######"
                       "###".format(acl_dict["dut3"]["ipv6_addr_list"][0],acl_dict["dut1"]["ipv6_addr_list"][0]))
    if loc_obj.verify_ssh_session(vars.D1, acl_dict["d3_uname"], acl_dict["d3_pwd"],
                                  acl_dict["dut3"]["ipv6_addr_list"][0],rem_dut_mgmt=acl_dict["dut3_mgmt_ip"],
                                                             interface=acl_dict["dut1"]["ipv6_addr_list"][1]):
        st.log("########## PASS: IPv6 SSH session success to {} with source ip as {} ########"
                         "##".format(acl_dict["dut3"]["ipv6_addr_list"][0],acl_dict["dut1"]["ipv6_addr_list"][1]))
    else:
        success=False
        st.error("########## FAIL: IPv6 SSH session failed to {} with source ip as {} ########"
                       "##".format(acl_dict["dut3"]["ipv6_addr_list"][0],acl_dict["dut1"]["ipv6_addr_list"][1]))
    if not loc_obj.verify_ssh_session(vars.D1, acl_dict["d3_uname"], acl_dict["d3_pwd"],
                                  acl_dict["dut3"]["ipv6_addr_list"][1],rem_dut_mgmt=acl_dict["dut3_mgmt_ip"],
                                                             interface=acl_dict["dut1"]["ipv6_addr_list"][0]):
        st.log("########## PASS: As expected, IPv6 SSH session failed to {} with source ip as {} ########"
                       "##".format(acl_dict["dut3"]["ipv6_addr_list"][1],acl_dict["dut1"]["ipv6_addr_list"][0]))
    else:
        success=False
        st.error("########## FAIL: IPv6 SSH session established to {} with source ip as {} which is NOT"
                       " expected ##########".format(acl_dict["dut3"]["ipv6_addr_list"][1],
                                                     acl_dict["dut1"]["ipv6_addr_list"][0]))
    if loc_obj.verify_ssh_session(vars.D1, acl_dict["d3_uname"], acl_dict["d3_pwd"],
                                  acl_dict["dut3"]["ipv6_addr_list"][1],rem_dut_mgmt=acl_dict["dut3_mgmt_ip"],
                                                             interface=acl_dict["dut1"]["ipv6_addr_list"][1]):
        st.log("########## PASS: IPv6 SSH session established to {} with source ip as {} ########"
                       "##".format(acl_dict["dut3"]["ipv6_addr_list"][1],acl_dict["dut1"]["ipv6_addr_list"][1]))
    else:
        success=False
        st.error("########## FAIL: IPv6 SSH session failed to {} with source ip as {} ########"
                       "##".format(acl_dict["dut3"]["ipv6_addr_list"][1],acl_dict["dut1"]["ipv6_addr_list"][1]))
    if success:
        st.report_pass("test_case_id_passed","test_aclv6_est_specific_egress_prefix")
    else:
        st.report_fail("test_case_id_failed","test_aclv6_est_specific_egress_prefix")


@pytest.fixture(scope="function")
def cleanup_fixture_01(request,acl_est_hooks):
    yield
    acl_type_tcp = 'ip'
    table_name_tcp = 'TCP_Flags'
    #######################################
    st.banner("ClEANUP....Starts for test function test_acl_tcpflags")
    #######################################
    loc_obj.start_traffic(stream_han_list=[stream_dict["tcp_flags"]],action="stop")
    acl_obj.delete_acl_table(vars.D1, acl_type=acl_type_tcp, acl_table_name=[table_name_tcp])


def test_acl_tcpflags(cleanup_fixture_01):
    success = True
    #tc_list = ['FtOpSoRoacltcpflags01','FtOpSoRoacltcpflags02','FtOpSoRoacltcpflags03']
    # Start traffic streams to validate TCP_Flags
    # Validate traffic statistcs
    # Validate the ACL stats

    rule_name_tcp = 'TCP_Flags'
    acl_type_tcp = 'ip'
    table_name_tcp = 'TCP_Flags'
    ##########################################################################
    st.banner('Create acl and its rules')
    ##########################################################################
    acl_obj.create_acl_table(vars.D1, name=rule_name_tcp, type=acl_type_tcp,stage='INGRESS',
                             ports=[acl_dict["dut1"]["intf_list_tg"][0]])
    acl_obj.create_acl_rule(vars.D1,acl_type=acl_type_tcp,rule_name=rule_name_tcp,rule_seq='10',packet_action='permit',
                            src_ip='any', dst_ip='any',l4_protocol='tcp',tcp_flag='rst',table_name=table_name_tcp,src_port='1023',dst_port='50',src_comp_operator="gt",dst_comp_operator="lt")
    acl_obj.create_acl_rule(vars.D1,acl_type=acl_type_tcp,rule_name=rule_name_tcp,rule_seq='20',packet_action='deny',
                            src_ip='any', dst_ip='any',l4_protocol='tcp',tcp_flag='fin',table_name=table_name_tcp,src_port='500',dst_port='50',src_comp_operator="eq",dst_comp_operator="eq")

    acl_obj.create_acl_rule(vars.D1,acl_type=acl_type_tcp,rule_name=rule_name_tcp,rule_seq='30',packet_action='deny',
                            src_ip='any', dst_ip='any',l4_protocol='tcp',tcp_flag='psh',table_name=table_name_tcp,src_port='100',dst_port='50',src_comp_operator="gt",dst_comp_operator="lt")
    acl_obj.create_acl_rule(vars.D1,acl_type=acl_type_tcp,rule_name=rule_name_tcp,rule_seq='40',packet_action='deny',
                            src_ip='any', dst_ip='any',l4_protocol='tcp',tcp_flag='urg',table_name=table_name_tcp,src_port='500',dst_port='50',src_comp_operator="eq",dst_comp_operator="eq")
    acl_obj.create_acl_rule(vars.D1,acl_type=acl_type_tcp,rule_name=rule_name_tcp,rule_seq='50',packet_action='permit',
                            src_ip='any', dst_ip='any',l4_protocol='tcp',tcp_flag='syn ack',table_name=table_name_tcp,src_port_range='1 500',dst_port_range='1 50')
    acl_obj.create_acl_rule(vars.D1,acl_type=acl_type_tcp,rule_name=rule_name_tcp,rule_seq='60',packet_action='permit',
                            src_ip='any', dst_ip='any',l4_protocol='tcp',tcp_flag='not-syn not-rst',table_name=table_name_tcp,src_port_range='5000 5001',dst_port_range='6000 10000')
    ########################################################################
    st.banner('Clear ACL statistics/counters ')
    ########################################################################
    acl_obj.clear_acl_counter(vars.D1, acl_table=table_name_tcp,acl_type=acl_type_tcp)

    ###################################################################################################
    st.banner("Start traffic streams to validate TCP_Flags")
    ###################################################################################################
    loc_obj.clear_stats(port_han_list=[tg_dict['d1_tg_ph1'],tg_dict['d3_tg_ph1']])
    loc_obj.start_traffic(stream_han_list=[stream_dict["tcp_flags"]],action="run")

    ##########################################################
    st.banner("Validate Traffic statistics ")
    ##########################################################
    traffic_details = {'1': {'tx_ports':[vars.T1D1P1], 'tx_obj':[tg_dict["tg"]], 'exp_ratio':[[1,0,0,0,1,1]], 'rx_ports':[vars.T1D3P1], 'rx_obj':[tg_dict["tg"]], 'stream_list' : [[stream_dict["tcp_flags"][0],stream_dict["tcp_flags"][1],stream_dict["tcp_flags"][2],stream_dict["tcp_flags"][3],stream_dict["tcp_flags"][4],stream_dict["tcp_flags"][5]]]}}

    result = utils_obj.poll_wait(tgapi.validate_tgen_traffic, 20,traffic_details=traffic_details, mode='streamblock', comp_type='packet_count')
    if result is False:
        st.error("Traffic Verification Failed with tcpflags ")
        success = False

    ######################################################
    st.banner("Validate ACL statistics ")
    ######################################################
    result= utils_obj.poll_wait(loc_obj.verify_acl_counters, 20,vars.D1,table_name_tcp , acl_type=acl_type_tcp)
    if result is False:
        st.error("ACL statistics verification Failed")
        success = False

    ###################################################
    st.banner('Remove acl rule with seq no 10 and then send traffic')
    ###################################################
    acl_obj.delete_acl_rule(vars.D1,acl_type=acl_type_tcp,acl_table_name=table_name_tcp,rule_seq=10,acl_rule_name=rule_name_tcp)

    #############################################################################################
    st.banner('Send stream1 traffic with matches seq no 10 and verify this time traffic is denied due to implicit deny')
    ########################################################################################
    loc_obj.clear_stats(port_han_list=[tg_dict['d1_tg_ph1'],tg_dict['d3_tg_ph1']])
    loc_obj.start_traffic(stream_han_list=[stream_dict["tcp_flags"][0]],action="run")

    traffic_details = {'1': {'tx_ports':[vars.T1D1P1], 'tx_obj':[tg_dict["tg"]], 'exp_ratio':[[0]], 'rx_ports':[vars.T1D3P1], 'rx_obj':[tg_dict["tg"]], 'stream_list' : [[stream_dict["tcp_flags"][0]]]}}
    result = utils_obj.poll_wait(tgapi.validate_tgen_traffic, 20,traffic_details=traffic_details, mode='streamblock', comp_type='packet_count')
    if result is False:
        st.error("Traffic Verification Failed with tcpflags ")
        success = False

    ###################################################
    st.banner('Add back acl rule with seq no 10 and then send traffic')
    ###################################################
    acl_obj.create_acl_rule(vars.D1,acl_type=acl_type_tcp,rule_name=rule_name_tcp,rule_seq='10',packet_action='permit',
                            src_ip='any', dst_ip='any',l4_protocol='tcp',tcp_flag='rst',table_name=table_name_tcp,src_port='1023',dst_port='50',src_comp_operator="gt",dst_comp_operator="lt")


    #############################################################################################
    st.banner('Send stream1 traffic with matches seq no 10 and verify this time traffic is permitted')
    ########################################################################################
    loc_obj.clear_stats(port_han_list=[tg_dict['d1_tg_ph1'],tg_dict['d3_tg_ph1']])
    loc_obj.start_traffic(stream_han_list=[stream_dict["tcp_flags"][0]],action="run")

    traffic_details = {'1': {'tx_ports':[vars.T1D1P1], 'tx_obj':[tg_dict["tg"]], 'exp_ratio':[[1]], 'rx_ports':[vars.T1D3P1], 'rx_obj':[tg_dict["tg"]], 'stream_list' : [[stream_dict["tcp_flags"][0]]]}}
    result = utils_obj.poll_wait(tgapi.validate_tgen_traffic, 20,traffic_details=traffic_details, mode='streamblock', comp_type='packet_count')
    if result is False:
        st.error("Traffic Verification Failed with tcpflags ")
        success = False

    if success:
        st.report_pass("test_case_id_passed","test_acl_tcpflags")
    else:
        acl_obj.show_acl_counters(vars.D1, acl_type=acl_type_tcp, acl_table=table_name_tcp)
        st.report_fail("test_case_id_failed","test_acl_tcpflags")


@pytest.fixture(scope="function")
def cleanup_fixture_02(request,acl_est_hooks):
    yield
    acl_type_tcp = 'ipv6'
    table_name_tcp = 'TCP_Flags_ipv6'
    #######################################
    st.banner("ClEANUP....Starts for test function test_acl_tcpflags_ipv6")
    #######################################
    loc_obj.start_traffic(stream_han_list=[stream_dict["tcp_flags"]],action="stop")

    ###############################################
    st.banner('Remove/unbind acl from inbound direction')
    ###############################################
    acl_obj.delete_acl_table(vars.D1, acl_type=acl_type_tcp, acl_table_name=[table_name_tcp])


def test_acl_tcpflags_ipv6(cleanup_fixture_02):
    success = True
    #tc_list = ['FtOpSoRoacltcpflags01','FtOpSoRoacltcpflags02','FtOpSoRoacltcpflags03']
    # Start traffic streams to validate TCP_Flags
    # Validate traffic statistcs
    # Validate the ACL stats

    rule_name_tcp = 'TCP_Flags_ipv6'
    acl_type_tcp = 'ipv6'
    table_name_tcp = 'TCP_Flags_ipv6'
    ##########################################################################
    st.banner('Create ipv6 acl and its rules')
    ##########################################################################
    acl_obj.create_acl_table(vars.D1, name=rule_name_tcp, type=acl_type_tcp,stage='INGRESS',
                             ports=[acl_dict["dut1"]["intf_list_tg"][0]])
    acl_obj.create_acl_rule(vars.D1,acl_type=acl_type_tcp,rule_name=rule_name_tcp,rule_seq='10',packet_action='permit',
                            src_ip='any', dst_ip='any',l4_protocol='tcp',tcp_flag='syn',table_name=table_name_tcp,src_port='10',dst_port='210',src_comp_operator="eq",dst_comp_operator="gt")
    acl_obj.create_acl_rule(vars.D1,acl_type=acl_type_tcp,rule_name=rule_name_tcp,rule_seq='20',packet_action='permit',
                            src_ip='any', dst_ip='any',l4_protocol='tcp',tcp_flag='ack',table_name=table_name_tcp,src_port='50',dst_port='100',src_comp_operator="lt",dst_comp_operator="eq")
    acl_obj.create_acl_rule(vars.D1,acl_type=acl_type_tcp,rule_name=rule_name_tcp,rule_seq='30',packet_action='deny',
                            src_ip='any', dst_ip='any',l4_protocol='tcp',tcp_flag='rst',table_name=table_name_tcp,src_port='100',dst_port='50',src_comp_operator="gt",dst_comp_operator="lt")
    acl_obj.create_acl_rule(vars.D1,acl_type=acl_type_tcp,rule_name=rule_name_tcp,rule_seq='40',packet_action='deny',
                            src_ip='any', dst_ip='any',l4_protocol='tcp',tcp_flag='fin',table_name=table_name_tcp,src_port='500',dst_port='50',src_comp_operator="eq",dst_comp_operator="eq")

    acl_obj.create_acl_rule(vars.D1,acl_type=acl_type_tcp,rule_name=rule_name_tcp,rule_seq='50',packet_action='deny',
                            src_ip='any', dst_ip='any',l4_protocol='tcp',tcp_flag='psh',table_name=table_name_tcp,src_port='100',dst_port='50',src_comp_operator="gt",dst_comp_operator="lt")
    acl_obj.create_acl_rule(vars.D1,acl_type=acl_type_tcp,rule_name=rule_name_tcp,rule_seq='60',packet_action='deny',
                            src_ip='any', dst_ip='any',l4_protocol='tcp',tcp_flag='urg',table_name=table_name_tcp,src_port='500',dst_port='50',src_comp_operator="eq",dst_comp_operator="eq")
    acl_obj.create_acl_rule(vars.D1,acl_type=acl_type_tcp,rule_name=rule_name_tcp,rule_seq='70',packet_action='permit',
                            src_ip='any', dst_ip='any',l4_protocol='tcp',tcp_flag='fin ack',table_name=table_name_tcp,src_port_range='1 500',dst_port_range='1 50')
    acl_obj.create_acl_rule(vars.D1,acl_type=acl_type_tcp,rule_name=rule_name_tcp,rule_seq='80',packet_action='permit',
                            src_ip='any', dst_ip='any',l4_protocol='tcp',tcp_flag='not-fin not-ack',table_name=table_name_tcp,src_port_range='500 700',dst_port_range='6000 10000')
    ########################################################################
    st.banner('Clear ACL statistics/counters ')
    ########################################################################
    acl_obj.clear_acl_counter(vars.D1, acl_table=table_name_tcp,acl_type=acl_type_tcp)

    ###################################################################################################
    st.banner("Start traffic streams to validate TCP_Flags")
    ###################################################################################################
    loc_obj.clear_stats(port_han_list=[tg_dict['d1_tg_ph1'],tg_dict['d3_tg_ph1']])
    loc_obj.start_traffic(stream_han_list=[stream_dict["tcp_flags_ipv6"]],action="run")

    ##########################################################
    st.banner("Validate Traffic statistics ")
    ##########################################################
    traffic_details = {'1': {'tx_ports':[vars.T1D1P1], 'tx_obj':[tg_dict["tg"]], 'exp_ratio':[[1,1,0,0,0,0,1,1]], 'rx_ports':[vars.T1D3P1], 'rx_obj':[tg_dict["tg"]], 'stream_list' : [[stream_dict["tcp_flags_ipv6"][0],stream_dict["tcp_flags_ipv6"][1],stream_dict["tcp_flags_ipv6"][2],stream_dict["tcp_flags_ipv6"][3],stream_dict["tcp_flags_ipv6"][4],stream_dict["tcp_flags_ipv6"][5],stream_dict["tcp_flags_ipv6"][6],stream_dict["tcp_flags_ipv6"][7]]]}}

    result = utils_obj.poll_wait(tgapi.validate_tgen_traffic, 20,traffic_details=traffic_details, mode='streamblock', comp_type='packet_count')
    if result is False:
        st.error("Traffic Verification Failed with tcpflags ")
        success = False

    ######################################################
    st.banner("Validate ACL statistics ")
    ######################################################
    result= utils_obj.poll_wait(loc_obj.verify_acl_counters, 20,vars.D1,table_name_tcp , acl_type=acl_type_tcp)
    if result is False:
        st.error("ACL statistics verification Failed")
        success = False

    ###################################################
    st.banner('Remove acl rule with seq no 10 and then send traffic')
    ###################################################
    acl_obj.delete_acl_rule(vars.D1,acl_type=acl_type_tcp,acl_table_name=table_name_tcp,rule_seq=10,acl_rule_name=rule_name_tcp)

    #############################################################################################
    st.banner('Send stream1 traffic with matches seq no 10 and verify this time traffic is denied due to implicit deny')
    ########################################################################################
    loc_obj.clear_stats(port_han_list=[tg_dict['d1_tg_ph1'],tg_dict['d3_tg_ph1']])
    loc_obj.start_traffic(stream_han_list=[stream_dict["tcp_flags_ipv6"][0]],action="run")

    traffic_details = {'1': {'tx_ports':[vars.T1D1P1], 'tx_obj':[tg_dict["tg"]], 'exp_ratio':[[0]], 'rx_ports':[vars.T1D3P1], 'rx_obj':[tg_dict["tg"]], 'stream_list' : [[stream_dict["tcp_flags_ipv6"][0]]]}}
    result = utils_obj.poll_wait(tgapi.validate_tgen_traffic, 20,traffic_details=traffic_details, mode='streamblock', comp_type='packet_count')
    if result is False:
        st.error("Traffic Verification Failed with tcpflags ")
        success = False

    ###################################################
    st.banner('Add back acl rule with seq no 10 and then send traffic')
    ###################################################
    acl_obj.create_acl_rule(vars.D1,acl_type=acl_type_tcp,rule_name=rule_name_tcp,rule_seq='10',packet_action='permit',
                            src_ip='any', dst_ip='any',l4_protocol='tcp',tcp_flag='syn',table_name=table_name_tcp,src_port='10',dst_port='210',src_comp_operator="eq",dst_comp_operator="gt")


    #############################################################################################
    st.banner('Send stream1 traffic with matches seq no 10 and verify this time traffic is permitted')
    ########################################################################################
    loc_obj.clear_stats(port_han_list=[tg_dict['d1_tg_ph1'],tg_dict['d3_tg_ph1']])
    loc_obj.start_traffic(stream_han_list=[stream_dict["tcp_flags_ipv6"][0]],action="run")

    traffic_details = {'1': {'tx_ports':[vars.T1D1P1], 'tx_obj':[tg_dict["tg"]], 'exp_ratio':[[1]], 'rx_ports':[vars.T1D3P1], 'rx_obj':[tg_dict["tg"]], 'stream_list' : [[stream_dict["tcp_flags_ipv6"][0]]]}}
    result = utils_obj.poll_wait(tgapi.validate_tgen_traffic, 20,traffic_details=traffic_details, mode='streamblock', comp_type='packet_count')
    if result is False:
        st.error("Traffic Verification Failed with tcpflags ")
        success = False

    if success:
        st.report_pass("test_case_id_passed","test_acl_tcpflags_ipv6")
    else:
        acl_obj.show_acl_counters(vars.D1, acl_type=acl_type_tcp, acl_table=table_name_tcp)
        st.report_fail("test_case_id_failed","test_acl_tcpflags_ipv6")


@pytest.fixture(scope="function")
def cleanup_fixture_03(request,acl_est_hooks):
    yield
    table_name_tcp_ipv6 = 'TCP_Flags_ipv6'
    #######################################
    st.banner("ClEANUP....Starts for test function test_acl_tcpflags_03")
    #######################################
    loc_obj.start_traffic(stream_han_list=[stream_dict["tcp_flags"]],action="stop")

    ###########################################################
    st.banner('Remove/unbind ipv6 acl from outbound direction')
    ###########################################################
    acl_obj.delete_acl_table(vars.D1, acl_type='ipv6', acl_table_name=[table_name_tcp_ipv6])


def test_acl_tcpflags_03(cleanup_fixture_03):
    success = True
    # Create ipv4/v6 ACL and apply it on egress direction
    # Start traffic streams to validate TCP_Flags
    # Validate traffic statistcs
    # Validate the ACL stats

    rule_name_tcp = 'TCP_Flags'
    table_name_tcp = 'TCP_Flags'
    ##########################################################################
    st.banner('Create ipv4 acl and its rules')
    ##########################################################################
    acl_obj.create_acl_table(vars.D1, name=rule_name_tcp, type='ip',stage='EGRESS',
                             ports=[acl_dict["dut1"]["intf_list_dut2"][0]])
    acl_obj.create_acl_rule(vars.D1,acl_type='ip',rule_name=rule_name_tcp,rule_seq='300',packet_action='deny',
                            src_ip='any', dst_ip='any',l4_protocol='tcp',tcp_flag='psh',table_name=table_name_tcp,src_port='233',dst_port='20',src_comp_operator="eq",dst_comp_operator="eq")
    acl_obj.create_acl_rule(vars.D1,acl_type='ip',rule_name=rule_name_tcp,rule_seq='400',packet_action='permit',
                            src_ip='any', dst_ip='any',l4_protocol='tcp',tcp_flag='syn ack',table_name=table_name_tcp,src_port='444',dst_port='44',src_comp_operator="eq",dst_comp_operator="eq")
    acl_obj.create_acl_rule(vars.D1,acl_type='ip',rule_name=rule_name_tcp,rule_seq='500',packet_action='permit',
                            src_ip='any', dst_ip='any',l4_protocol='tcp',tcp_flag='not-syn not-rst',table_name=table_name_tcp,src_port='5001',dst_port='8877',src_comp_operator="eq",dst_comp_operator="eq")


    ########################################################################
    st.banner('Clear ACL statistics/counters ')
    ########################################################################
    acl_obj.clear_acl_counter(vars.D1, acl_table=table_name_tcp,acl_type='ip')

    ###################################################################################################
    st.banner("Start traffic streams to validate TCP_Flags")
    ###################################################################################################
    loc_obj.clear_stats(port_han_list=[tg_dict['d1_tg_ph1'],tg_dict['d3_tg_ph1']])
    loc_obj.start_traffic(stream_han_list=[stream_dict["tcp_flags_v4"]],action="run")

    ##########################################################
    st.banner("Validate Traffic statistics ")
    ##########################################################
    traffic_details = {'1': {'tx_ports':[vars.T1D1P1], 'tx_obj':[tg_dict["tg"]], 'exp_ratio':[[0,1,1]], 'rx_ports':[vars.T1D3P1], 'rx_obj':[tg_dict["tg"]], 'stream_list' : [[stream_dict["tcp_flags"][2],stream_dict["tcp_flags"][4],stream_dict["tcp_flags"][5]]]}}

    result = utils_obj.poll_wait(tgapi.validate_tgen_traffic,20,traffic_details=traffic_details, mode='streamblock', comp_type='packet_count')
    if result is False:
        st.error("Traffic Verification Failed with tcpflags ")
        success = False

    ######################################################
    st.banner("Validate ACL statistics ")
    ######################################################
    result= utils_obj.poll_wait(loc_obj.verify_acl_counters, 20,vars.D1,table_name_tcp , acl_type='ip')
    if result is False:
        st.error("ACL statistics verification Failed")
        st.generate_tech_support(dut=None,name='test_acl_tcpflags_03')
        success = False

    ###############################################
    st.banner('Remove/unbind ipv4 acl from outbound direction')
    ###############################################
    acl_obj.config_access_group(vars.D1, acl_type='ip', table_name=table_name_tcp, access_group_action="out",
                                port=acl_dict["dut1"]["intf_list_dut2"][0],config="no")

    rule_list =[300,400,500]
    for rule in rule_list:
        acl_obj.delete_acl_rule(vars.D1,acl_type='ip',acl_table_name=table_name_tcp,rule_seq=rule,acl_rule_name=rule_name_tcp)

    rule_name_tcp_ipv6 = 'TCP_Flags_ipv6'
    table_name_tcp_ipv6 = 'TCP_Flags_ipv6'
    ##########################################################################
    st.banner('Create ipv6 acl and its rules')
    ##########################################################################
    acl_obj.create_acl_table(vars.D1, name=rule_name_tcp_ipv6, type='ipv6',stage='EGRESS',
                             ports=[acl_dict["dut1"]["intf_list_dut2"][0]])
    acl_obj.create_acl_rule(vars.D1,acl_type='ipv6',rule_name=rule_name_tcp_ipv6,rule_seq='100',packet_action='deny',
                            src_ip='any', dst_ip='any',l4_protocol='tcp',tcp_flag='rst',table_name=table_name_tcp_ipv6,src_port='233',dst_port='20',src_comp_operator="eq",dst_comp_operator="eq")
    acl_obj.create_acl_rule(vars.D1,acl_type='ipv6',rule_name=rule_name_tcp_ipv6,rule_seq='200',packet_action='deny',
                            src_ip='any', dst_ip='any',l4_protocol='tcp',tcp_flag='fin',table_name=table_name_tcp_ipv6,src_port='500',dst_port='50',src_comp_operator="eq",dst_comp_operator="eq")
    acl_obj.create_acl_rule(vars.D1,acl_type='ipv6',rule_name=rule_name_tcp_ipv6,rule_seq='300',packet_action='deny',
                            src_ip='any', dst_ip='any',l4_protocol='tcp',tcp_flag='urg',table_name=table_name_tcp_ipv6,src_port='500',dst_port='50',src_comp_operator="eq",dst_comp_operator="eq")
    acl_obj.create_acl_rule(vars.D1,acl_type='ipv6',rule_name=rule_name_tcp_ipv6,rule_seq='400',packet_action='permit',
                            src_ip='any', dst_ip='any',l4_protocol='tcp',tcp_flag='fin ack',table_name=table_name_tcp_ipv6,src_port='444',dst_port='44',src_comp_operator="eq",dst_comp_operator="eq")
    acl_obj.create_acl_rule(vars.D1,acl_type='ipv6',rule_name=rule_name_tcp_ipv6,rule_seq='500',packet_action='permit',
                            src_ip='any', dst_ip='any',l4_protocol='tcp',tcp_flag='not-fin not-ack',table_name=table_name_tcp_ipv6,src_port='650',dst_port='8877',src_comp_operator="eq",dst_comp_operator="eq")


    ########################################################################
    st.banner('Clear ACL statistics/counters ')
    ########################################################################
    acl_obj.clear_acl_counter(vars.D1, acl_table=table_name_tcp_ipv6,acl_type='ipv6')

    ###################################################################################################
    st.banner("Start traffic streams to validate TCP_Flags")
    ###################################################################################################
    loc_obj.clear_stats(port_han_list=[tg_dict['d1_tg_ph1'],tg_dict['d3_tg_ph1']])
    loc_obj.start_traffic(stream_han_list=[stream_dict["tcp_flags_v6"]],action="run")

    ##########################################################
    st.banner("Validate Traffic statistics ")
    ##########################################################
    traffic_details = {'1': {'tx_ports':[vars.T1D1P1], 'tx_obj':[tg_dict["tg"]], 'exp_ratio':[[0,0,0,1,1]], 'rx_ports':[vars.T1D3P1], 'rx_obj':[tg_dict["tg"]], 'stream_list' : [[stream_dict["tcp_flags_ipv6"][2],stream_dict["tcp_flags_ipv6"][3],stream_dict["tcp_flags_ipv6"][5],stream_dict["tcp_flags_ipv6"][6],stream_dict["tcp_flags_ipv6"][7]]]}}

    result = utils_obj.poll_wait(tgapi.validate_tgen_traffic,20,traffic_details=traffic_details, mode='streamblock', comp_type='packet_count')
    if result is False:
        st.error("Traffic Verification Failed with tcpflags ")
        success = False

    ######################################################
    st.banner("Validate ACL statistics ")
    ######################################################
    result= utils_obj.poll_wait(loc_obj.verify_acl_counters, 20,vars.D1,table_name_tcp_ipv6 , acl_type='ipv6')
    if result is False:
        st.error("ACL statistics verification Failed")
        success = False


    if success:
        st.report_pass("test_case_id_passed","test_acl_tcpflags_03")
    else:
        st.report_fail("test_case_id_failed","test_acl_tcpflags_03")


