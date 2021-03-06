##########################################################################################
# Title: LDAP interaction with RADIUS
# Author: Chandra Sekhar Reddy <Chandra.vedanaparthi@broadcom.com>
##########################################################################################

import pytest

from spytest import st, SpyTestDict

import apis.switching.vlan as vlan
import apis.routing.ip as ip
import apis.system.interface as intf
import apis.system.basic as basic_api
import apis.system.reboot as reboot_api
import apis.routing.bgp as bgp_api
import apis.security.ldap as ldap
import apis.security.tacacs as tacacs
import apis.security.radius as radius
import apis.security.user as user
import apis.system.connection as ssh
import apis.system.ssh as ssh_api
import apis.system.management_vrf as mvrf
from ldap_vars import *

import utilities.common as utils

data = SpyTestDict()
ldap_servers_data = {}
ldap_servers_global_data = {}

def print_log(message,alert_type="LOW"):
    '''
    Uses st.log procedure with some formatting to display proper log messages
    :param message: Message to be printed
    :param alert_level:
    :return:
    '''
    log_start = "\n======================================================================================\n"
    log_end =   "\n======================================================================================"
    log_delimiter ="\n###############################################################################################\n"

    if alert_type == "HIGH":
        st.log("{} {} {}".format(log_delimiter,message,log_delimiter))
    elif alert_type == "MED":
        st.log("{} {} {}".format(log_start,message,log_end))
    elif alert_type == "LOW":
        st.log(message)
    elif alert_type == "ERROR":
        st.error("{} {} {}".format(log_start,message,log_start))

def retry_func(func,**kwargs):
    retry_count = kwargs.get("retry_count", 3)
    delay = kwargs.get("delay", 2)
    comp_flag = kwargs.get("comp_flag", True)
    if 'retry_count' in kwargs: del kwargs['retry_count']
    if 'delay' in kwargs: del kwargs['delay']
    if 'comp_flag' in kwargs: del kwargs['comp_flag']
    for i in range(retry_count):
        st.log("Attempt %s of %s" %((i+1),retry_count))
        if kwargs.keys() == []:
            if comp_flag:
                if func():
                    return True
            else:
                if not func():
                    return False
        else:
            if comp_flag:
                if func(**kwargs):
                    return True
            else:
                if not func(**kwargs):
                    return False
        if retry_count != (i+1):
            st.log("waiting for %s seconds before retrying again"%delay)
            st.wait(delay)
    if comp_flag:
        return False
    else:
        return True


def initialize_topology():
    global vars, dut1, dut2, dut_list,mgmt_ipv4_add,ldap1,cli_type

    ### Verify Minimum topology requirement is met
    vars = st.ensure_min_topology("D1D2:2")

    print_log("Start Test with topology D1D2:2",'HIGH')
    print_log(
        "Test Topology Description\n==============================\n\
        - Test script uses two DUTS, DUT1 as SSH client and DUT2 as LDAP Client\n\
        - DUT1 to DUT2 has two links one is for IPv4 and other one for IPv6.\n\
        - DUT2 Management port to LDAP server,RADIUS and TACACS+ for Authetication and Authorization.\n\
        In addition, each test case will have trigger configs/unconfigs",'HIGH')

    dut_list = vars.dut_list
    dut1 = vars.D1
    dut2 = vars.D2
    ldap1 = dut1

    ldap_servers_data.update({
        ldap1: {
            'server_ip': ldap_server_ips1[0],
            'server_ip_nss': ldap_server_ips1[0],
            'server_ip_pam': ldap_server_ips1[1],
            'auth_type': 'ALL',
            'auth_type_nss': 'NSS',
            'auth_type_pam': 'PAM',
            'auth_type_sudo': 'SUDO',
            'ldap_port': 636,
            'ldap_pri': 1,
            'ldap_ssl': 'ON',
            'ldap_retry': 1,
            'ldap_servers': ['100.1.1.2','100.1.1.3','100.1.1.4','100.1.1.5','100.1.1.6','100.1.1.7','100.1.1.8',ldap_server_ips1[0]],
            'ldap_server_pri': [1,2,3,4,5,6,7,8],
            'config': 'yes'
        }
    })

    ldap_servers_global_data.update({
        ldap1: {
            'time_limit': 10,
            'bind_time_limit': 10,
            'idle_time_limit': 10,
            'retry_count': 1,
            'port': 636,
            'search_scope': 'SUB',
            'version': 3,
            'base_dn': "dc=brcm,dc=com",
            'ssl': 'ON',
            'bind_dn': "cn=admin,dc=brcm,dc=com",
            'pam_group_dn': "cn=docker,ou=Group,dc=brcm,dc=com",
            'pam_member_attr': "memberUid",
            'sudoers_base': "ou=Sudoers,dc=brcm,dc=com",
            'bind_pwd' : 'brcm123',
            'config': 'yes'
        }
    })
    ip_address_list = basic_api.get_ifconfig_inet(dut2, 'eth0')
    mgmt_ipv4_add = ip_address_list[0]

    cli_type = st.get_ui_type(dut2)
    if cli_type == "click":
        st.report_unsupported("test_execution_skipped", "LDAP Integration not supported in click")

def validate_topology():
    # Enable all links in the topology and verify links up
    dut_port_dict = {}
    for dut in dut_list:
        port_list = st.get_dut_links_local(dut, peer=None, index=None)
        dut_port_dict[dut] = port_list
    #Usage: exec_all(use_threads, list_of_funcs)
    [result, exceptions] = utils.exec_all(True, [[intf.interface_operation, dut, dut_port_dict[dut], 'startup',False]
                                          for dut in dut_port_dict.keys()])
    if not all(i is None for i in exceptions):
        print_log(exceptions)

    return False if False in result else True


@pytest.fixture(scope="module",autouse=True)
def prologue_epilogue():
    print_log("Starting to initialize and validate topology...",'MED')
    initialize_topology()
    validate_topology()
    ldap_module_config()
    ldap_basic_validations()
    yield
    ldap_module_unconfig()

def config_vlan():
    # Create trunk VLANs on all DUTs using range command
    trunk_vlan_range = str(trunk_base_vlan) + " " + str(trunk_base_vlan + trunk_vlan_count - 1)
    utils.exec_all(True,[[vlan.config_vlan_range, dut, trunk_vlan_range] for dut in dut_list])

    ### Add trunk ports between DUT1<->DUT2 first link in vlan 10
    api_list = []
    api_list.append([vlan.add_vlan_member, dut1, trunk_base_vlan, [vars.D1D2P1], True])
    api_list.append([vlan.add_vlan_member, dut2, trunk_base_vlan, [vars.D2D1P1], True])
    utils.exec_all(True, api_list)

    ### Add trunk ports between DUT1<->DUT2 Second link in vlan 11
    api_list = []
    api_list.append([vlan.add_vlan_member, dut1, trunk_base_vlan+1, [vars.D1D2P2], True])
    api_list.append([vlan.add_vlan_member, dut2, trunk_base_vlan+1, [vars.D2D1P2], True])
    utils.exec_all(True, api_list)

def unconfig_vlan():
    ### Remove trunk ports between DUT1<->DUT2 first link in vlan 10
    api_list = []
    api_list.append([vlan.delete_vlan_member, dut1, trunk_base_vlan, [vars.D1D2P1], True])
    api_list.append([vlan.delete_vlan_member, dut2, trunk_base_vlan, [vars.D2D1P1], True])
    utils.exec_all(True, api_list)

    ### Remove trunk ports between DUT1<->DUT2 Second link in vlan 11
    api_list = []
    api_list.append([vlan.delete_vlan_member, dut1, trunk_base_vlan+1, [vars.D1D2P2], True])
    api_list.append([vlan.delete_vlan_member, dut2, trunk_base_vlan+1, [vars.D2D1P2], True])
    utils.exec_all(True, api_list)

    # Remove trunk VLANs 10 and 11 on all DUTs using range command
    trunk_vlan_range = str(trunk_base_vlan) + " " + str(trunk_base_vlan + trunk_vlan_count - 1)
    utils.exec_all(True,[[vlan.config_vlan_range, dut, trunk_vlan_range, 'del'] for dut in dut_list])

def config_ip_v4_v6():
    ### Assign IPv4 addresses between DUt1 and DUT2
    api_list = []
    api_list.append([ip.config_ip_addr_interface, dut1, 'Vlan' + str(trunk_base_vlan), d1d2_ipv4, maskV4])
    api_list.append([ip.config_ip_addr_interface, dut2, 'Vlan' + str(trunk_base_vlan), d2d1_ipv4, maskV4])
    utils.exec_all(True, api_list)

    ### Assign IPv6 addresses between DUT1 and DUT2
    api_list = []
    api_list.append([ip.config_ip_addr_interface, dut1, 'Vlan' + str(trunk_base_vlan+1), d1d2_ipv6, maskV6,'ipv6'])
    api_list.append([ip.config_ip_addr_interface, dut2, 'Vlan' + str(trunk_base_vlan+1), d2d1_ipv6, maskV6,'ipv6'])
    utils.exec_all(True, api_list)

def unconfig_ip_v4_v6():
    ### Unconfig IPv4 addresses between DUt1 and DUT2
    api_list = []
    api_list.append([ip.delete_ip_interface, dut1, 'Vlan' + str(trunk_base_vlan), d1d2_ipv4, maskV4])
    api_list.append([ip.delete_ip_interface, dut2, 'Vlan' + str(trunk_base_vlan), d2d1_ipv4, maskV4])
    utils.exec_all(True, api_list)

    ### Unconfig IPv6 addresses between DUT1 and DUT2
    api_list = []
    api_list.append([ip.delete_ip_interface, dut1, 'Vlan' + str(trunk_base_vlan+1), d1d2_ipv6, maskV6,'ipv6'])
    api_list.append([ip.delete_ip_interface, dut2, 'Vlan' + str(trunk_base_vlan+1), d2d1_ipv6, maskV6,'ipv6'])
    utils.exec_all(True, api_list)

def config_ldap_server():
    ###Configure the LDAP server
    ldap.config_ldap_server_host(dut2,server = ldap_servers_data[ldap1]['server_ip'],\
    use_type = ldap_servers_data[ldap1]['auth_type'],\
    port = ldap_servers_data[ldap1]['ldap_port'], priority = ldap_servers_data[ldap1]['ldap_pri'],\
    ssl = ldap_servers_data[ldap1]['ldap_ssl'],retry = ldap_servers_data[ldap1]['ldap_retry'],\
    config = ldap_servers_data[ldap1]['config'])

def unconfig_ldap_server():
    ###Configure the LDAP server
    ldap.config_ldap_server_host(dut2,server = ldap_servers_data[ldap1]['server_ip'], \
    use_type = ldap_servers_data[ldap1]['auth_type'],\
    port = ldap_servers_data[ldap1]['ldap_port'], priority = ldap_servers_data[ldap1]['ldap_pri'],\
    ssl = ldap_servers_data[ldap1]['ldap_ssl'],retry = ldap_servers_data[ldap1]['ldap_retry'],\
    config = 'no')

def config_ldap_server_attributes(dut,mode):
    if mode == "ldap_global":
        ldap.config_ldap_server_global_attributes(dut,timelimit = ldap_servers_global_data[ldap1]['time_limit'], \
        bind_timelimit = ldap_servers_global_data[ldap1]['bind_time_limit'],\
        idle_timelimit = ldap_servers_global_data[ldap1]['idle_time_limit'], retry = ldap_servers_global_data[ldap1]['retry_count'],\
        port = ldap_servers_global_data[ldap1]['port'],scope = ldap_servers_global_data[ldap1]['search_scope'],\
        ldap_version = ldap_servers_global_data[ldap1]['version'],base_dn = ldap_servers_global_data[ldap1]['base_dn'],\
        ssl = ldap_servers_global_data[ldap1]['ssl'],config = 'yes')
    elif mode ==  "pam_global":
        ldap.config_ldap_server_pam_global_attributes(dut,pam_group_dn = ldap_servers_global_data[ldap1]['pam_group_dn'], \
        pam_member_attribute = ldap_servers_global_data[ldap1]['pam_member_attr'],config = 'yes')
    elif mode ==  "sudo_global":
        ldap.config_ldap_server_nss_sudo_global_attributes(dut,sudoers_base = ldap_servers_global_data[ldap1]['sudoers_base'],config = 'yes')
    elif mode == "nss_sudo":
        ldap.config_ldap_server_nss_specific_attributes(dut,timelimit = ldap_servers_global_data[ldap1]['time_limit'], \
        bind_timelimit = ldap_servers_global_data[ldap1]['bind_time_limit'],\
        idle_timelimit = ldap_servers_global_data[ldap1]['idle_time_limit'], retry = ldap_servers_global_data[ldap1]['retry_count'],\
        port = ldap_servers_global_data[ldap1]['port'],scope = ldap_servers_global_data[ldap1]['search_scope'],\
        ldap_version = ldap_servers_global_data[ldap1]['version'],base_dn = ldap_servers_global_data[ldap1]['base_dn'],\
        ssl = ldap_servers_global_data[ldap1]['ssl'],nss_base_sudoers = ldap_servers_global_data[ldap1]['sudoers_base'],config = 'yes')
    elif mode == "pam_specific":
        ldap.config_ldap_server_pam_specific_attributes(dut,timelimit = ldap_servers_global_data[ldap1]['time_limit'], \
        bind_timelimit = ldap_servers_global_data[ldap1]['bind_time_limit'],\
        retry = ldap_servers_global_data[ldap1]['retry_count'],\
        port = ldap_servers_global_data[ldap1]['port'],scope = ldap_servers_global_data[ldap1]['search_scope'],\
        ldap_version = ldap_servers_global_data[ldap1]['version'],base_dn = ldap_servers_global_data[ldap1]['base_dn'],\
        ssl = ldap_servers_global_data[ldap1]['ssl'],pam_group_dn = ldap_servers_global_data[ldap1]['pam_group_dn'],\
        pam_member_attribute = ldap_servers_global_data[ldap1]['pam_member_attr'],config = 'yes')

def unconfig_ldap_server_attributes(dut,mode):
    if mode == "ldap_global":
        ldap.config_ldap_server_global_attributes(dut,timelimit = '', \
        bind_timelimit = '',idle_timelimit = '', retry = '',\
        port = '',scope = '',ldap_version = '',base_dn = '',\
        ssl = '',config = 'no')
    elif mode ==  "pam_global":
        ldap.config_ldap_server_pam_global_attributes(dut,pam_group_dn = '', \
        pam_member_attribute = '',config = 'no')
    elif mode ==  "sudo_global":
        ldap.config_ldap_server_nss_sudo_global_attributes(dut,sudoers_base = '',config = 'no')
    elif mode == "nss_sudo":
        ldap.config_ldap_server_nss_specific_attributes(dut,timelimit = '', \
        bind_timelimit = '',idle_timelimit = '', retry = '',\
        port = '',scope = '',ldap_version = '',base_dn = '',\
        ssl = '',nss_base_sudoers = '',config = 'no')
    elif mode == "pam_specific":
        ldap.config_ldap_server_pam_specific_attributes(dut,timelimit = '', \
        bind_timelimit = '',retry = '',port = '',scope = '',\
        ldap_version = '',base_dn = '',ssl = '',pam_group_dn = '',\
        pam_member_attribute = '',config = 'no')

def config_login_method(dut,login_via):
    ###Configure the user login method either local or ldap and local or radius and local or tacacs and local
    tacacs.set_aaa_authentication_properties(dut,"login",login_via)

def config_failthrough(dut,mode):
    ###Configure the user login failthrough mode either enable/disable
    tacacs.set_aaa_authentication_properties(dut,"failthrough",mode)

def config_radius_server():
    ###Configure the RADIUS server
    radius.config_server(dut2, ip_address=radius_server_ipv4, key=radius_key, action="add")

def unconfig_radius_server():
    ###UnConfigure the RADIUS server
    radius.config_server(dut2,no_form = True, ip_address=radius_server_ipv4, action="delete")

def config_name_service_password(dut,value):
    ###Configure the nss password as ldap
    tacacs.set_aaa_name_service_properties(dut,"passwd",value)

def config_name_service_group(dut,value):
    ###Configure the nss group as ldap
    tacacs.set_aaa_name_service_properties(dut,"group",value)

def config_aaa_login_autorization(dut,value):
    ###Configure the authorization as ldap or local
    tacacs.set_aaa_authorization_properties(dut,"login",value)

def config_name_service_shadow(dut,value):
    ###Configure the nss shadow as ldap
    tacacs.set_aaa_name_service_properties(dut,"shadow",value)

def config_name_service_sudoers(dut,value):
    ###Configure the nss sudoer as ldap
    tacacs.set_aaa_name_service_properties(dut,"sudoers",value)

def show_radius_server():
    ###show the RADIUS server
    radius.show_config(dut2)

def config_max_ldap_servers():
    ###Configure the LDAP server
    for ipaddr, pri in zip(ldap_servers_data[ldap1]['ldap_servers'], ldap_servers_data[ldap1]['ldap_server_pri']):
        ldap.config_ldap_server_host(dut2,server = ipaddr,priority = pri,config = "yes")

def unconfig_max_ldap_servers():
    ###UnConfigure the LDAP server
    for ipaddr, pri in zip(ldap_servers_data[ldap1]['ldap_servers'], ldap_servers_data[ldap1]['ldap_server_pri']):
        ldap.config_ldap_server_host(dut2,server = ipaddr,priority = pri,config = "no")

def config_nss_ldap_server():
    ###Configure the NSS LDAP server
    ldap.config_ldap_server_host(dut2,server = ldap_servers_data[ldap1]['server_ip_nss'],\
    use_type = ldap_servers_data[ldap1]['auth_type_nss'],\
    port = ldap_servers_data[ldap1]['ldap_port'], priority = ldap_servers_data[ldap1]['ldap_pri'],\
    ssl = ldap_servers_data[ldap1]['ldap_ssl'],retry = ldap_servers_data[ldap1]['ldap_retry'],\
    config = ldap_servers_data[ldap1]['config'])

def config_pam_ldap_server():
    ###Configure the PAM LDAP server
    ldap.config_ldap_server_host(dut2,server = ldap_servers_data[ldap1]['server_ip_pam'],\
    use_type = ldap_servers_data[ldap1]['auth_type_pam'],\
    port = ldap_servers_data[ldap1]['ldap_port'], priority = ldap_servers_data[ldap1]['ldap_pri'],\
    ssl = ldap_servers_data[ldap1]['ldap_ssl'],retry = ldap_servers_data[ldap1]['ldap_retry'],\
    config = ldap_servers_data[ldap1]['config'])


def unconfig_nss_ldap_server():
    ###Configure the NSS LDAP server
    ldap.config_ldap_server_host(dut2,server = ldap_servers_data[ldap1]['server_ip_nss'],\
    use_type = ldap_servers_data[ldap1]['auth_type_nss'],\
    port = ldap_servers_data[ldap1]['ldap_port'], priority = ldap_servers_data[ldap1]['ldap_pri'],\
    ssl = ldap_servers_data[ldap1]['ldap_ssl'],retry = ldap_servers_data[ldap1]['ldap_retry'],\
    config = 'no')

def unconfig_pam_ldap_server():
    ###Configure the PAM LDAP server
    ldap.config_ldap_server_host(dut2,server = ldap_servers_data[ldap1]['server_ip_pam'],\
    use_type = ldap_servers_data[ldap1]['auth_type_pam'],\
    port = ldap_servers_data[ldap1]['ldap_port'], priority = ldap_servers_data[ldap1]['ldap_pri'],\
    ssl = ldap_servers_data[ldap1]['ldap_ssl'],retry = ldap_servers_data[ldap1]['ldap_retry'],\
    config = 'no')

def display_ldap_servers():
    ldap.verify_ldap_server_details(dut2,return_output = '')

def check_ping(src_dut,dest_ip_list,family="ipv4"):
    '''
    Verify ping to given list of IPs from src_dut
    :param src_dut: dut in which ping initiated
    :param dest_ip_list: list of IPs which need to be ping
    :return:
    '''
    dest_ip_list = [dest_ip_list] if type(dest_ip_list) is str else dest_ip_list
    ver_flag = True
    for ip_addr in dest_ip_list:
        if family == "ipv4":
            result = ip.ping(src_dut, ip_addr)
        elif family == "ipv6":
            result = ip.ping(src_dut, ip_addr,'ipv6')
        if not result:
            print_log("FAIL:Ping failed to {} ".format(ip_addr),'ERROR')
            ver_flag = False

    return ver_flag

def check_aaa_login(dut,mode, Fail_through):
    '''
    Verify AAA login method details
    :return:
    '''
    ver_flag = True
    if mode == "ldap":
        login_method = ldap_only
    elif mode == "radius":
        login_method = radius_only
    elif mode == "ldap local":
        login_method = ldap_local
    elif mode == "radius local":
        login_method = radius_local
    elif mode == "tacacs+ local":
        login_method = tacacs_local
    result = tacacs.verify_aaa(dut,login = login_method,failthrough = Fail_through,cli_type = cli_type )
    if result == False:
        print_log('AAA Login method and Failthrough','ERROR')
        ver_flag = False
    return ver_flag

def check_aaa_login_nss(dut, passwd = "", group ="", shadow ="", sudoers ="", netgrp =""):
    '''
    Verify AAA login nss details
    :return:
    '''
    ver_flag = True
    result = tacacs.verify_aaa(dut,nss_passwd = passwd,nss_group = group,nss_shadow = shadow,cli_type = cli_type )
    if result == False:
        print_log('AAA Name service details Failed','ERROR')
        ver_flag = False
    return ver_flag

def check_aaa_login_auth(dut,value):
    '''
    Verify AAA login Authorization details
    :return:
    '''
    ver_flag = True
    result = tacacs.verify_aaa(dut,authorization_login= value,cli_type = cli_type )
    if result == False:
        print_log('AAA login Authorization details Failed','ERROR')
        ver_flag = False
    return ver_flag

def check_aaa_login_sudoers(dut,value):
    '''
    Verify AAA login sudoers details
    :return:
    '''
    ver_flag = True
    result = tacacs.verify_aaa(dut,nss_sudoers = value,cli_type = cli_type )
    if result == False:
        print_log('AAA login sudoers details Failed','ERROR')
        ver_flag = False
    return ver_flag

def check_ldap_server_global(dut,mode):
    '''
    Verify ldap server details global
    :return:
    '''
    ver_flag = True
    auth = ldap_servers_data[ldap1]['auth_type']
    sl = ldap_servers_data[ldap1]['ldap_ssl']
    scope = ldap_servers_global_data[ldap1]['search_scope']

    if mode == "ldapglobal":
        result = ldap.verify_ldap_server_details(dut,global_base_dn = "dc=brcm,dc=com",\
        address = ldap_servers_data[ldap1]['server_ip'],\
        priority = ldap_servers_data[ldap1]['ldap_pri'],\
        retry = ldap_servers_data[ldap1]['ldap_retry'],\
        port = ldap_servers_data[ldap1]['ldap_port'],\
        use_type = auth.upper(),\
        ssl = sl.upper(),\
        global_scope = scope.upper(),\
        global_search_time_limit = ldap_servers_global_data[ldap1]['time_limit'],\
        global_retry = ldap_servers_global_data[ldap1]['retry_count'],\
        global_bind_time_limit = ldap_servers_global_data[ldap1]['bind_time_limit'],\
        global_idle_time_limit = ldap_servers_global_data[ldap1]['idle_time_limit'],\
        global_ldap_version = ldap_servers_global_data[ldap1]['version'])
    elif mode == "ldapglobalpam":
        result = ldap.verify_ldap_server_details(dut,global_base_dn = "dc=brcm,dc=com",\
        address = ldap_servers_data[ldap1]['server_ip'],\
        priority = ldap_servers_data[ldap1]['ldap_pri'],\
        retry = ldap_servers_data[ldap1]['ldap_retry'],\
        port = ldap_servers_data[ldap1]['ldap_port'],\
        use_type = auth.upper(),\
        ssl = sl.upper(),\
        global_scope = scope.upper(),\
        global_search_time_limit = ldap_servers_global_data[ldap1]['time_limit'],\
        global_retry = ldap_servers_global_data[ldap1]['retry_count'],\
        global_bind_time_limit = ldap_servers_global_data[ldap1]['bind_time_limit'],\
        global_idle_time_limit = ldap_servers_global_data[ldap1]['idle_time_limit'],\
        global_pam_group_dn = ldap_servers_global_data[ldap1]['pam_group_dn'],\
        global_pam_mem_attri = ldap_servers_global_data[ldap1]['pam_member_attr'],\
        global_ldap_version = ldap_servers_global_data[ldap1]['version'])
    elif mode == "ldapglobalsudo":
        result = ldap.verify_ldap_server_details(dut,global_base_dn = "dc=brcm,dc=com",\
        address = ldap_servers_data[ldap1]['server_ip'],\
        priority = ldap_servers_data[ldap1]['ldap_pri'],\
        retry = ldap_servers_data[ldap1]['ldap_retry'],\
        port = ldap_servers_data[ldap1]['ldap_port'],\
        use_type = auth.upper(),\
        ssl = sl.upper(),\
        global_scope = scope.upper(),\
        global_search_time_limit = ldap_servers_global_data[ldap1]['time_limit'],\
        global_retry = ldap_servers_global_data[ldap1]['retry_count'],\
        global_bind_time_limit = ldap_servers_global_data[ldap1]['bind_time_limit'],\
        global_idle_time_limit = ldap_servers_global_data[ldap1]['idle_time_limit'],\
        global_pam_group_dn = ldap_servers_global_data[ldap1]['pam_group_dn'],\
        global_pam_mem_attri = ldap_servers_global_data[ldap1]['pam_member_attr'],\
        global_sudoer_base = ldap_servers_global_data[ldap1]['sudoers_base'],\
        global_ldap_version = ldap_servers_global_data[ldap1]['version'])
    if result == False:
        print_log('LDAP server details Failed','ERROR')
        ver_flag = False
    return ver_flag

def check_login(ipaddr, username, password):
    ver_flag = True
    con = ssh.connect_to_device(ipaddr, username, password)
    if not con:
        st.error("SSH v4 Connection Failed: IP-{}, User-{}, Password-{}".format(ipaddr, username, password))
        ver_flag = False
    ssh.ssh_disconnect(con)
    return ver_flag

def check_login_v6(dut,ipaddr,username,password):
    output = st.exec_ssh_remote_dut(dut, ipaddr, username, password,command="")
    if "Connection timed out" in output or "Permission denied" in output or "Connection refused" in output:
        st.error("SSH v6 Connection Failed: IP-{}, User-{}, Password-{}".format(ipaddr, username, password))
        return False
    st.log("SSH Connection sucess: IP-{}, User-{}, Password-{}".format(ipaddr, username, password))
    return True

def creating_local_user(dut,usernm,passwd,role,mode):
    flag = True
    st.log("DUT => {}".format(dut))
    st.log("usename1 => {}".format(usernm))
    st.log("passwd => {}".format(passwd))
    st.log("mod => {}".format(mode))
    result = user.config(dut, username=usernm,password = passwd, role= role, no_form = mode)
    if result == False:
        st.log("Creating local user failed")
        flag = False
    return flag
def ldap_module_config():
    '''
    - Configure vlans and add members
    - Configure IPv4 between DUT1 and DUT2 first link
    - Configure IPv6 between DUT1 and DUT2 second link
    '''
    print_log("Starting LDAP Base Configurations...\n\
    STEPS:\n\
    - Configure vlans and add members \n\
    - Configure IPv4 between DUT1 and DUT2 first link\n\
    - Configure IPv6 between DUT1 and DUT2 second link.", "HIGH")
    config_vlan()
    config_ip_v4_v6()
    config_ldap_server()

def ldap_module_unconfig():
    print_log("Starting LDAP Base UnConfigurations...", "HIGH")
    unconfig_ip_v4_v6()
    unconfig_vlan()

def ldap_basic_validations():
    '''

    1. Verify IPv4 reachability
    2. Verify IPv6 reachability
    2. Verify the reachability of LDAP server via management interface


    '''
    final_result = True
    pingv4_fail = 0
    pingv6_fail = 0
    ldap_pingv4_fail = 0

    ### Display IP interfaces
    utils.exec_all(True, [[ip.get_interface_ip_address, dut] for dut in dut_list])
    ### Display IPv6 interfaces
    utils.exec_all(True, [[ip.get_interface_ip_address, dut, None, 'ipv6'] for dut in dut_list])

    ### Verify L3 reachability is fine
    print_log("Verify L3 reachability is from DUT1 to DUT2", 'MED')
    if retry_func(check_ping,src_dut=dut1,dest_ip_list=d2d1_ipv4):
        print_log("Ipv4 reachabilty between DUT1 to DUT2 PASSED", "HIGH")
    else:
        print_log("IPv4 reachabilty between DUT1 to DUT2 FAILED", "HIGH")
        pingv4_fail += 1
        final_result = False

    print_log("Verify IPv6 reachability is from DUT1 to DUT2", 'MED')
    if retry_func(check_ping, src_dut=dut1, dest_ip_list=d2d1_ipv6, family="ipv6"):
        print_log("IPv6 reachabilty between DUT1 to DUT2 PASSED", "HIGH")
    else:
        print_log("IPv6 reachabilty between DUT1 to DUT2 FAILED", "HIGH")
        pingv6_fail += 1
        final_result = False

    print_log("Verify L3 reachability is from DUT2 to LDAP server", 'MED')
    if retry_func(check_ping,src_dut=dut2,dest_ip_list=ldap_server_ips1[0]):
        print_log("Ipv4 reachabilty between DUT2 to LDAP Server PASSED", "HIGH")
    else:
        print_log("IPv4 reachabilty between DUT2 to LDAP Server FAILED", "HIGH")
        ldap_pingv4_fail += 1
        final_result = False


    if not final_result:
        fail_msg = ''
        if pingv4_fail > 0:
            fail_msg += 'Pingv4 Failed:'
        if pingv6_fail > 0:
            fail_msg += 'Pingv6 Failed:'
        if ldap_pingv4_fail > 0:
            fail_msg += 'Pingv4 to LDAP server Failed:'

        st.report_fail("test_case_failure_message", fail_msg.strip(':'))


def test_ldap_radius():
    '''
        Verify the IPv4 SSH login from client with LDAP User with LDAP Authentication
        Verify the IPv6 SSH login from client with LDAP User with LDAP Authentication
        Verify the IPv4 SSH login from client with LDAP User with LDAP Authentication and Local with failthrough enabled
        Verify the IPv6 SSH login from client with LDAP User with LDAP Authentication and Local with failthrough enabled
        Verify the IPv4 SSH login from client with LDAP User with LDAP name service and RADIUS Authentication
        Verify the IPv6 SSH login from client with LDAP User with LDAP name service and RADIUS Authentication
        Verify the IPv4 SSH login from client with LDAP User with LDAP name service and RADIUS Authentication and Local with failthrough enabled
        Verify the IPv6 SSH login from client with LDAP User with LDAP name service and RADIUS Authentication and Local with failthrough enabled
        Verify the IPv4 SSH login from client with LDAP User with Authentication RADIUS password, Authorization LDAP, Name Service LDAP
        Verify the IPv6 SSH login from client with LDAP User with Authentication RADIUS password, Authorization LDAP, Name Service LDAP
        Verify the IPv4 SSH login from client with LDAP User with Authentication RADIUS, Name Service LDAP, sudo Authorization LDAP
        Verify the IPv6 SSH login from client with LDAP User with Authentication TACACS+, Name Service LDAP, sudo Authorization LDAP
        Verify the IPv4 SSH login from client with LDAP User with Authentication RADIUS, Name Service LDAP, sudo Authorization LDAP with Mgmt VRF with source IP
        Verify the IPv6 SSH login from client with LDAP User with Authentication RADIUS, Name Service LDAP, sudo Authorization LDAP with Mgmt VRF with source IP
        Verify the IPv4 SSH login from client after config reload with LDAP User with Authentication RADIUS, Name Service LDAP, sudo Authorization LDAP
        Verify the IPv6 SSH login from client after config reload with LDAP User with Authentication RADIUS, Name Service LDAP, sudo Authorization LDAP
        Verify the IPv4 SSH login from client after Cold Reboot with LDAP User with Authentication RADIUS, Name Service LDAP, sudo Authorization LDAP
        Verify the IPv6 SSH login from client after Cold Reboot with LDAP User with Authentication RADIUS, Name Service LDAP, sudo Authorization LDAP
        Verify the LDAP Scale testing with 8 IPv4 servers configured in the Device with SSH login from client with LDAP User with Authentication RADIUS,\
          Authorization LDAP, Name Service LDAP
        Verify the IPv4 SSH login with NSS SUDO ldap user and PAM Authorize LDAP group with RADIUS Authentication
        Verify the IPv6 SSH login with NSS SUDO ldap user and PAM Authorize LDAP group with RADIUS Authentication

    '''
    tc_list = ['FtLdapRadiusAuthv4001','FtLdapRadiusAuthv6001',\
    'FtLdapRadiusAuthLdapLocalv4001','FtLdapRadiusAuthLdapLocalv6001',\
    'FtLdapRadiusNssAuthv4001','FtLdapRadiusNssAuthv6001',\
    'FtLdapRadiusNssAuthLdapLocalv4001','FtLdapRadiusNssAuthLdapLocalv6001',\
    'FtLdapRadiusNssAuthPamv4001','FtLdapRadiusNssAuthPamv6001',\
    'FtLdapRadiusNssAuthSudov4001','FtLdapRadiusNssAuthSudov6001',\
    'FtLdapRadiusNssAuthSudoVrfSrcIntfv4001','FtLdapRadiusNssAuthSudoVrfSrcIntfv6001',\
    'FtLdapRadiusNssAuthSudoVrfSrcIntfConfigReloadv4001','FtLdapRadiusNssAuthSudoVrfSrcIntfConfigReloadv6001',\
    'FtLdapRadiusNssAuthSudoVrfSrcIntfColdRebootv4001','FtLdapRadiusNssAuthSudoVrfSrcIntfColdRebootv6001',\
    'FtLdapScaleRadiusNssAuthSudoVrfSrcIntfv4001','FtLdapRadiusNssSudoLdapandPamldapv4001',\
    'FtLdapRadiusNssSudoLdapandPamldapv6001']
    print_log("START of TC:test_ldap_radius ==>Sub-Test:Verify LDAP Intercation with RADIUS for AAA\n TCs:<{}>".format(tc_list), "HIGH")
    final_result = True
    tc_result1 = 0
    tc_result2 = 0
    tc_result3 = 0
    tc_result4 = 0
    tc_result5 = 0
    tc_result6 = 0
    tc_result7 = 0
    tc_result8 = 0
    tc_result9 = 0
    tc_result10 = 0
    tc_result11 = 0
    tc_result12 = 0
    tc_result13 = 0
    tc_result14 = 0
    tc_result15 = 0
    tc_result16 = 0
    tc_result17 = 0
    tc_result18 = 0
    tc_result19 = 0
    tc_result20 = 0
    tc_result21 = 0
#    aaa_login_ldap_only = 0
    ldap_server_global = 0
    ldap_login_v4_1  = 0
    ldap_login_v4_2  = 0
    ldap_login_v6  = 0
    aaa_login_ldap_local = 0
    ldap_local_login_v4_1 = 0
    ldap_local_login_v4_2 = 0
    ldap_local_login_v6 = 0
    local_user_create = 0
    local_user_delete = 0
    aaa_login_radius_only = 0
    aaa_login_radius_nss_only = 0
    ldap_radius_login_v4 = 0
    ldap_radius_login_v6 = 0
    ldap_radius_local_login_v4_1 = 0
    ldap_radius_local_login_v4_2 = 0
    ldap_radius_local_login_v6 = 0
    aaa_login_radius_local = 0
    aaa_login_authorize_radius_local_nss = 0
    ldap_server_global_pam = 0
    ldap_radius_local_login_pam_v4 = 0
    ldap_radius_local_login_pam_v6 = 0
    aaa_login_authorize_radius_local_nss_sudo = 0
    ldap_server_global_sudo = 0
    ldap_radius_local_login_sudo_v4 = 0
    ldap_radius_local_login_sudo_v6 = 0
    ldap_radius_local_login_sudo_vrf_srcint_v4 = 0
    ldap_radius_local_login_sudo_vrf_srcint_v6 = 0
    ldap_radius_local_login_sudo_vrf_srcint_config_reload_v4 = 0
    ldap_radius_local_login_sudo_vrf_srcint_config_reload_v6 = 0
    ldap_radius_local_login_sudo_vrf_srcint_cold_reboot_v4 = 0
    ldap_radius_local_login_sudo_vrf_srcint_cold_reboot_v6 = 0
    ldap_scale_radius_local_login_sudo_vrf_srcint_v4 = 0
    ldap_nss_sudo_pam_specific_radius_login_v4 = 0
    ldap_nss_sudo_pam_specific_radius_login_v6 = 0

    print_log("Configure  the login-method as ldap local ..",'MED')
    config_login_method(dut2,ldap_local)

    print_log("Configure  the failthrough True ..",'MED')
    config_failthrough(dut2,'enable')

    print_log("Configure  the ldap server global attributes ..",'MED')
    config_ldap_server_attributes(dut2,'ldap_global')

    print_log("Verify the AAA Login details when configured ldap local...",'MED')
    if check_aaa_login(dut2,ldap_local,fail_through_true):
        print_log("AAA Login details verification PASSED", "HIGH")
    else:
        print_log("AAA Login details verification FAILED", "HIGH")
        aaa_login_ldap_local += 1
        tc_result1 += 1
        final_result = False

    mode = "ldapglobal"
    print_log("Verify the ldap server details when configured globaly...",'MED')
    if check_ldap_server_global(dut2,mode):
        print_log("LDAP server global detail verification PASSED", "HIGH")
    else:
        print_log("LDAP server global detail verification FAILED", "HIGH")
        ldap_server_global += 1
        tc_result1 += 1
        final_result = False
    st.wait(5)
    print_log("Verify the ldap admin user login with ldap only login-method...",'MED')
    if check_login(mgmt_ipv4_add,ldap_admin_user,ldap_admin_password):
        print_log("Login to device with LDAP admin user verification PASSED", "HIGH")
    else:
        print_log("Login to device with LDAP admin user verification FAILED", "HIGH")
        ldap_login_v4_1 += 1
        tc_result1 += 1
        final_result = False

    print_log("Verify the ldap admin user login with ldap and invalid password only login-method...",'MED')
    if not check_login(mgmt_ipv4_add,ldap_admin_user,invalid_password):
        print_log("Login to device with LDAP admin user and invalid passwd verification PASSED", "HIGH")
    else:
        print_log("Login to device with LDAP admin user and invalid passwd verification FAILED", "HIGH")
        ldap_login_v4_2 += 1
        tc_result1 += 1
        final_result = False

    if tc_result1 > 0:
       st.report_tc_fail("FtLdapRadiusAuthv4001", "IPv4_SSH_login_LDAP_User_LDAP_Authentication_Failed", "test_ldap_radius")
    else:
       st.report_tc_pass("FtLdapRadiusAuthv4001", "IPv4_SSH_login_LDAP_User_LDAP_Authentication_Passed", "test_ldap_radius")

    print_log("Enable the sshv6 on DUT2...",'MED')
    ssh_api.enable_sshv6(dut2)

    print_log("Verify the ldap admin user login with ldap only login-method...",'MED')
    if check_login_v6(dut1,d2d1_ipv6,ldap_admin_user,ldap_admin_password):
        print_log("Login to device with LDAP admin user verification PASSED", "HIGH")
    else:
        print_log("Login to device with LDAP admin user verification FAILED", "HIGH")
        ldap_login_v6 += 1
        tc_result2 += 1
        final_result = False

    if tc_result2 > 0:
       st.report_tc_fail("FtLdapRadiusAuthv6001", "IPv6_SSH_login_LDAP_User_LDAP_Authentication_Failed", "test_ldap_radius")
    else:
       st.report_tc_pass("FtLdapRadiusAuthv6001", "IPv6_SSH_login_LDAP_User_LDAP_Authentication_Passed", "test_ldap_radius")

    st.wait(5)
    print_log("Verify the ldap admin user login with ldap local login-method...",'MED')
    if check_login(mgmt_ipv4_add,ldap_admin_user,ldap_admin_password):
        print_log("Login to device with LDAP admin user verification PASSED", "HIGH")
    else:
        print_log("Login to device with LDAP admin user verification FAILED", "HIGH")
        ldap_local_login_v4_1 += 1
        tc_result3 += 1
        final_result = False

    print_log("Creating the Local user to check the failthrough with ldap and local...",'MED')
    if creating_local_user(dut2,local_user,local_user_password,role_admin,user_add):
        print_log("Local user creation verification PASSED", "HIGH")
    else:
        print_log("Local user creation verification FAILED", "HIGH")
        local_user_create += 1
        tc_result3 += 1
        final_result = False

    st.wait(5)
    print_log("Verify the ldap admin user login with ldap local login-method with failthrough enabled...",'MED')
    if check_login(mgmt_ipv4_add,local_user,local_user_password):
        print_log("Login to device with local admin user verification PASSED", "HIGH")
    else:
        print_log("Login to device with local admin user verification FAILED", "HIGH")
        ldap_local_login_v4_2 += 1
        tc_result3 += 1
        final_result = False

    if tc_result3 > 0:
       st.report_tc_fail("FtLdapRadiusAuthLdapLocalv4001", "IPv4_SSH_login_LDAP_User_LDAP_Local_failthrough_Failed", "test_ldap_radius")
    else:
       st.report_tc_pass("FtLdapRadiusAuthLdapLocalv4001", "IPv6_SSH_login_LDAP_User_LDAP_Local_failthrough_Passed", "test_ldap_radius")

    print_log("Verify the ldap admin user login with ldap local login-method with failthrough enabled...",'MED')
    if check_login_v6(dut1,d2d1_ipv6,ldap_admin_user,ldap_admin_password):
        print_log("Login to device with local admin user verification PASSED", "HIGH")
    else:
        print_log("Login to device with local admin user verification FAILED", "HIGH")
        ldap_local_login_v6 += 1
        tc_result4 += 1
        final_result = False

    if tc_result4 > 0:
       st.report_tc_fail("FtLdapRadiusAuthLdapLocalv6001", "IPv4_SSH_LDAP_name_service_RADIUS_Authentication_Failed", "test_ldap_radius")
    else:
       st.report_tc_pass("FtLdapRadiusAuthLdapLocalv6001", "IPv4_SSH_LDAP_name_service_RADIUS_Authentication_Passed", "test_ldap_radius")

    print_log("Configure  RADIUS server on DUT2 ..",'MED')
    config_radius_server()

    print_log("Display the  RADIUS server on DUT2 ..",'MED')
    show_radius_server()

    print_log("Configure  the login-method as radius local ..",'MED')
    config_login_method(dut2,radius_local)

    print_log("Configure  the failthrough True ..",'MED')
    config_failthrough(dut2,'enable')

    print_log("Configure  the name service password as ldap ..",'MED')
    config_name_service_password(dut2,'ldap')

    print_log("Configure  the name service group as ldap ..",'MED')
    config_name_service_group(dut2,'ldap')

    print_log("Configure  the name service shadow as ldap ..",'MED')
    config_name_service_shadow(dut2,'ldap')

    print_log("Verify the AAA Login details when configured radius only...",'MED')
    if check_aaa_login(dut2,radius_only,fail_through_false):
        print_log("AAA Login details radius only verification PASSED", "HIGH")
    else:
        print_log("AAA Login details radius only verification FAILED", "HIGH")
        aaa_login_radius_only += 1
        tc_result5 += 1
        final_result = False

    print_log("Verify the AAA Login Name Service details when configured radius only...",'MED')
    if check_aaa_login_nss(dut2,"ldap","ldap","ldap"):
        print_log("AAA Login name service details radius only verification PASSED", "HIGH")
    else:
        print_log("AAA Login name service details radius only verification FAILED", "HIGH")
        aaa_login_radius_nss_only += 1
        tc_result5 += 1
        final_result = False

    st.wait(5)
    print_log("Verify the ldap admin user login with radius only login-method...",'MED')
    if check_login(mgmt_ipv4_add,ldap_admin_user,ldap_admin_password):
        print_log("Login to device with LDAP admin user with radius only verification PASSED", "HIGH")
    else:
        print_log("Login to device with LDAP admin user with radius only verification FAILED", "HIGH")
        ldap_radius_login_v4 += 1
        tc_result5 += 1
        final_result = False
    if tc_result5 > 0:
       st.report_tc_fail("FtLdapRadiusNssAuthv4001", "IPv4_SSH_LDAP_name_service_RADIUS_Authentication_Failed", "test_ldap_radius")
    else:
       st.report_tc_pass("FtLdapRadiusNssAuthv4001", "IPv4_SSH_LDAP_name_service_RADIUS_Authentication_Passed", "test_ldap_radius")

    print_log("Verify the ldap admin user login with radius only login-method...",'MED')
    if check_login_v6(dut1,d2d1_ipv6,ldap_admin_user,ldap_admin_password):
        print_log("Login to device with LDAP admin user with radius only verification PASSED", "HIGH")
    else:
        print_log("Login to device with LDAP admin user with radius only verification FAILED", "HIGH")
        ldap_radius_login_v6 += 1
        tc_result6 += 1
        final_result = False

    if tc_result6 > 0:
       st.report_tc_fail("FtLdapRadiusNssAuthv6001", "IPv6_SSH_LDAP_name_service_RADIUS_Authentication_Failed", "test_ldap_radius")
    else:
       st.report_tc_pass("FtLdapRadiusNssAuthv6001", "IPv6_SSH_LDAP_name_service_RADIUS_Authentication_Passed", "test_ldap_radius")
    print_log("Configure  the login-method as radius local ..",'MED')
    config_login_method(dut2,radius_local)

    print_log("Verify the AAA Login details when configured radius local...",'MED')
    if check_aaa_login(dut2,radius_local,fail_through_false):
        print_log("AAA Login details radius local verification PASSED", "HIGH")
    else:
        print_log("AAA Login details radius local verification FAILED", "HIGH")
        aaa_login_radius_local += 1
        tc_result7 += 1
        final_result = False

    st.wait(5)
    print_log("Verify the ldap admin user login with radius local login-method...",'MED')
    if check_login(mgmt_ipv4_add,ldap_admin_user,ldap_admin_password):
        print_log("Login to device with LDAP admin user with radius local verification PASSED", "HIGH")
    else:
        print_log("Login to device with LDAP admin user with radius local verification FAILED", "HIGH")
        ldap_radius_local_login_v4_1 += 1
        tc_result7 += 1
        final_result = False

    print_log("Configure  the failthrough True ..",'MED')
    config_failthrough(dut2,'enable')

    print_log("Verify the ldap admin user login with radius local login-method with failthrough enabled...",'MED')
    if check_login(mgmt_ipv4_add,local_user,local_user_password):
        print_log("Login to device with local admin user verification PASSED", "HIGH")
    else:
        print_log("Login to device with local admin user verification FAILED", "HIGH")
        ldap_radius_local_login_v4_2 += 1
        tc_result7 += 1
        final_result = False
    if tc_result7 > 0:
       st.report_tc_fail("FtLdapRadiusNssAuthLdapLocalv4001", "IPv4_SSH_login_LDAP_name_service_RADIUS_Auth_and_Local_failthrough_Failed", "test_ldap_radius")
    else:
       st.report_tc_pass("FtLdapRadiusNssAuthLdapLocalv4001", "IPv4_SSH_login_LDAP_name_service_RADIUS_Auth_and_Local_failthrough_Passed", "test_ldap_radius")

    print_log("Verify the ldap admin user login with radius local login-method with failthrough enabled...",'MED')
    if check_login_v6(dut1,d2d1_ipv6,ldap_admin_user,ldap_admin_password):
        print_log("Login to device with ldap admin user verification PASSED", "HIGH")
    else:
        print_log("Login to device with ldap admin user verification FAILED", "HIGH")
        ldap_radius_local_login_v6 += 1
        tc_result8 += 1
        final_result = False

    if tc_result8 > 0:
       st.report_tc_fail("FtLdapRadiusNssAuthLdapLocalv6001", "IPv6_SSH_login_LDAP_name_service_RADIUS_Auth_and_Local_failthrough_Failed", "test_ldap_radius")
    else:
       st.report_tc_pass("FtLdapRadiusNssAuthLdapLocalv6001", "IPv6_SSH_login_LDAP_name_service_RADIUS_Auth_and_Local_failthrough_Passed", "test_ldap_radius")
    print_log("Configure  the pam group dn and pam member attribute on DUT2 ..",'MED')
    config_ldap_server_attributes(dut2,'pam_global')

    print_log("Configure  the local as Authorization ..",'MED')
    config_aaa_login_autorization(dut2,local_only)

    print_log("Verify the AAA Login Authorization details when configured radius local...",'MED')
    if check_aaa_login_auth(dut2,"local"):
        print_log("AAA Login Authorization details radius local verification PASSED", "HIGH")
    else:
        print_log("AAA Login Authorization details radius local verification FAILED", "HIGH")
        aaa_login_authorize_radius_local_nss += 1
        tc_result9 += 1
        final_result = False

    mode = "ldapglobalpam"
    print_log("Verify the ldap server pam group and attributes details when configured globaly...",'MED')
    if check_ldap_server_global(dut2,mode):
        print_log("LDAP server pam global detail verification PASSED", "HIGH")
    else:
        print_log("LDAP server pam global detail verification FAILED", "HIGH")
        ldap_server_global_pam += 1
        tc_result9 += 1
        final_result = False

    st.wait(5)
    print_log("Verify the ldap admin user login with ldap authorization with radius local login-method...",'MED')
    if check_login(mgmt_ipv4_add,ldap_admin_user,ldap_admin_password):
        print_log("Login to device with LDAP admin user with ldap authorization with radius local verification PASSED", "HIGH")
    else:
        print_log("Login to device with LDAP admin user with ldap authorization with radius local verification FAILED", "HIGH")
        ldap_radius_local_login_pam_v4 += 1
        tc_result9 += 1
        final_result = False

    if tc_result9 > 0:
       st.report_tc_fail("FtLdapRadiusNssAuthPamv4001","IPv4_SSH_client_LDAP_User_Auth_RADIUS_password_Authorize_LDAP_Name_Service_LDAP_Failed", "test_ldap_radius")
    else:
       st.report_tc_pass("FtLdapRadiusNssAuthPamv4001","IPv4_SSH_client_LDAP_User_Auth_RADIUS_password_Authorize_LDAP_Name_Service_LDAP_Passed", "test_ldap_radius")

    print_log("Verify the ldap admin user login with ldap authorization with radius local login-method...",'MED')
    if check_login_v6(dut1,d2d1_ipv6,ldap_admin_user,ldap_admin_password):
        print_log("Login to device with LDAP admin user with ldap authorization with radius local verification PASSED", "HIGH")
    else:
        print_log("Login to device with LDAP admin user with ldap authorization with radius local verification FAILED", "HIGH")
        ldap_radius_local_login_pam_v6 += 1
        tc_result10 += 1
        final_result = False

    if tc_result10 > 0:
       st.report_tc_fail("FtLdapRadiusNssAuthPamv6001", "IPv6_SSH_client_LDAP_User_Auth_RADIUS_password_Authorize_LDAP_Name_Service_LDAP_Failed", "test_ldap_radius")
    else:
       st.report_tc_pass("FtLdapRadiusNssAuthPamv6001","IPv6_SSH_client_LDAP_User_Auth_RADIUS_password_Authorize_LDAP_Name_Service_LDAP_Passed", "test_ldap_radius")

    print_log("Configure  the global sudoers base on DUT2 ..",'MED')
    config_ldap_server_attributes(dut2,'sudo_global')

    print_log("Configure  the ldap login sudoders ..",'MED')
    config_name_service_sudoers(dut2,ldap_only)

    print_log("Verify the AAA Login sudoers details when configured radius local...",'MED')
    if check_aaa_login_auth(dut2,"local"):
        print_log("AAA Login sudoers details radius local verification PASSED", "HIGH")
    else:
        print_log("AAA Login sudoers details radius local verification FAILED", "HIGH")
        aaa_login_authorize_radius_local_nss_sudo += 1
        tc_result11 += 1
        final_result = False

    mode = "ldapglobalsudo"
    print_log("Verify the ldap server sudoers base group globaly...",'MED')
    if check_ldap_server_global(dut2,mode):
        print_log("LDAP server sudoers global detail verification PASSED", "HIGH")
    else:
        print_log("LDAP server sudoers global detail verification FAILED", "HIGH")
        ldap_server_global_sudo += 1
        tc_result11 += 1
        final_result = False

    st.wait(5)
    print_log("Verify the sudoer user login with ldap authorization with radius local login-method...",'MED')
    if check_login(mgmt_ipv4_add,ldap_operator_user,ldap_operator_password):
        print_log("Login to device with LDAP sudoer user with ldap authorization with radius local verification PASSED", "HIGH")
    else:
        print_log("Login to device with LDAP sudoer user with ldap authorization with radius local verification FAILED", "HIGH")
        ldap_radius_local_login_sudo_v4 += 1
        tc_result11 += 1
        final_result = False

    if tc_result11 > 0:
       st.report_tc_fail("FtLdapRadiusNssAuthSudov4001","IPv4_SSH_login_LDAP_User_Auth_RADIUS_Name_Service_LDAP_sudo_Authorize_LDAP_Failed", "test_ldap_radius")
    else:
       st.report_tc_pass("FtLdapRadiusNssAuthSudov4001", "IPv4_SSH_login_LDAP_User_Auth_RADIUS_Name_Service_LDAP_sudo_Authorize_LDAP_Passed", "test_ldap_radius")
    print_log("Verify the ldap admin user login with ldap authorization with radius local login-method...",'MED')
    if check_login_v6(dut1,d2d1_ipv6,ldap_operator_user,ldap_operator_password):
        print_log("Login to device with LDAP sudoer user with ldap authorization with radius local verification PASSED", "HIGH")
    else:
        print_log("Login to device with LDAP sudoer user with ldap authorization with radius local verification FAILED", "HIGH")
        ldap_radius_local_login_sudo_v6 += 1
        tc_result12 += 1
        final_result = False

    if tc_result12 > 0:
       st.report_tc_fail("FtLdapRadiusNssAuthSudov6001", "IPv6_SSH_login_LDAP_User_Auth_RADIUS_Name_Service_LDAP_sudo_Authorize_LDAP_Failed", "test_ldap_radius")
    else:
       st.report_tc_pass("FtLdapRadiusNssAuthSudov6001","IPv6_SSH_login_LDAP_User_Auth_RADIUS_Name_Service_LDAP_sudo_Authorize_LDAP_Passed", "test_ldap_radius")

    print_log("Configure  the management vrf on DUT2 ..",'MED')
    mvrf.config(dut2, no_form=False)

    print_log("Configure  the radius with vrf mgmt on DUT2 ..",'MED')
    radius.config_server(dut2, ip_address=radius_server_ipv4, key=radius_key, use_mgmt_vrf='mgmt', action="add")

    print_log("Configure  the ldap src interface as management 0 and vrf mgmt on DUT2 ..",'MED')
    ldap.config_ldap_client_srcintf_vrf(dut2, management = '0',vrf = 'mgmt')
    st.wait(15,'Added delay after configuring src interface and mgmt vrf')

    print_log("Verify the sudoer user login with ldap authorization with mgmt src interface and mgmt vrf with radius local login-method...",'MED')
    if check_login(mgmt_ipv4_add,ldap_operator_user,ldap_operator_password):
        print_log("Login to device with LDAP sudoer user with ldap authorization with mgmt src interface and mgmt vrfwith radius local verification PASSED", "HIGH")
    else:
        print_log("Login to device with LDAP sudoer user with ldap authorization with mgmt src interface and mgmt vrfwith radius local verification FAILED", "HIGH")
        ldap_radius_local_login_sudo_vrf_srcint_v4 += 1
        tc_result13 += 1
        final_result = False

    if tc_result13 > 0:
       st.report_tc_fail("FtLdapRadiusNssAuthSudoVrfSrcIntfv4001", \
        "IPv4_SSH_login_LDAP_User_Auth_RADIUS_NSS_LDAP_sudo_Authorize_LDAP_Mgmt_VRF_src_intf_Failed", "test_ldap_radius")
    else:
       st.report_tc_pass("FtLdapRadiusNssAuthSudoVrfSrcIntfv4001", \
        "IPv4_SSH_login_LDAP_User_Auth_RADIUS_NSS_LDAP_sudo_Authorize_LDAP_Mgmt_VRF_src_intf_Passed", "test_ldap_radius")

    print_log("Verify the ldap admin user login with ldap authorization with mgmt src interface and mgmt vrf with radius local login-method...",'MED')
    if check_login_v6(dut1,d2d1_ipv6,ldap_operator_user,ldap_operator_password):
        print_log("Login to device with LDAP sudoer user with ldap authorization with mgmt src interface and mgmt vrf with radius local verification PASSED", "HIGH")
    else:
        print_log("Login to device with LDAP sudoer user with ldap authorization with mgmt src interface and mgmt vrf with radius local verification FAILED", "HIGH")
        ldap_radius_local_login_sudo_vrf_srcint_v6 += 1
        tc_result14 += 1
        final_result = False

    if tc_result14 > 0:
       st.report_tc_fail("FtLdapRadiusNssAuthSudoVrfSrcIntfv6001", \
        "IPv6_SSH_login_LDAP_User_Auth_RADIUS_NSS_LDAP_sudo_Authorize_LDAP_Mgmt_VRF_src_intf_Failed", "test_ldap_radius")
    else:
       st.report_tc_pass("FtLdapRadiusNssAuthSudoVrfSrcIntfv6001", \
        "IPv6_SSH_login_LDAP_User_Auth_RADIUS_NSS_LDAP_sudo_Authorize_LDAP_Mgmt_VRF_src_intf_Passed", "test_ldap_radius")

    print_log("Enable docker routing mode and save on DUT2...", 'MED')
    bgp_api.enable_docker_routing_config_mode(dut2)
    reboot_api.config_save(dut2)

    print_log("Do Config Reload in DUT2...", 'MED')
    reboot_api.config_reload(dut2)
    st.wait(10,'Added delay after config Reload')

    print_log("Verify the v4 login after config reload with ldap sudo user,ldap auth and authorize...",'MED')
    if check_login(mgmt_ipv4_add,ldap_operator_user,ldap_operator_password):
        print_log("V4 Login to device after config reload with ldap sudo user,ldap auth and authorize radius local verification PASSED", "HIGH")
    else:
        print_log("V4 Login to device after config reload with ldap sudo user,ldap auth and authorize radius local verification FAILED", "HIGH")
        ldap_radius_local_login_sudo_vrf_srcint_config_reload_v4 += 1
        tc_result15 += 1
        final_result = False

    if tc_result15 > 0:
       st.report_tc_fail("FtLdapRadiusNssAuthSudoVrfSrcIntfConfigReloadv4001", \
        "IPv4_SSH_login_config_reload_LDAP_User_with_Auth_RADIUS_NSS_LDAP_sudo_Authorize_LDAP_Failed", "test_ldap_radius")
    else:
       st.report_tc_pass("FtLdapRadiusNssAuthSudoVrfSrcIntfConfigReloadv4001", \
        "IPv4_SSH_login_config_reload_LDAP_User_with_Auth_RADIUS_NSS_LDAP_sudo_Authorize_LDAP_Passed", "test_ldap_radius")

    print_log("Verify the v4 login after config reload with ldap sudo user,ldap auth and authorize...",'MED')
    if check_login_v6(dut1,d2d1_ipv6,ldap_operator_user,ldap_operator_password):
        print_log("V6 Login to device after config reload with ldap sudo user,ldap auth and authorize radius local verification PASSED", "HIGH")
    else:
        print_log("V6 Login to device after config reload with ldap sudo user,ldap auth and authorize radius local verification FAILED", "HIGH")
        ldap_radius_local_login_sudo_vrf_srcint_config_reload_v6 += 1
        tc_result16 += 1
        final_result = False

    if tc_result16 > 0:
       st.report_tc_fail("FtLdapRadiusNssAuthSudoVrfSrcIntfConfigReloadv6001", \
        "IPv6_SSH_login_config_reload_LDAP_User_with_Auth_RADIUS_NSS_LDAP_sudo_Authorize_LDAP_Failed", "test_ldap_radius")
    else:
       st.report_tc_pass("FtLdapRadiusNssAuthSudoVrfSrcIntfConfigReloadv6001", \
        "IPv6_SSH_login_config_reload_LDAP_User_with_Auth_RADIUS_NSS_LDAP_sudo_Authorize_LDAP_Passed", "test_ldap_radius")

    print_log("Do Cold Reboot in DUT2...", 'MED')
    st.reboot(dut2)
    st.wait(10)

    print_log("Verify the v4 login after cold reboot with ldap sudo user,ldap auth and authorize...",'MED')
    if check_login(mgmt_ipv4_add,ldap_operator_user,ldap_operator_password):
        print_log("V4 Login to device after cold reboot with ldap sudo user,ldap auth and authorize radius local verification PASSED", "HIGH")
    else:
        print_log("V4 Login to device after cold reboot with ldap sudo user,ldap auth and authorize radius local verification FAILED", "HIGH")
        ldap_radius_local_login_sudo_vrf_srcint_cold_reboot_v4 += 1
        tc_result17 += 1
        final_result = False

    if tc_result17 > 0:
       st.report_tc_fail("FtLdapRadiusNssAuthSudoVrfSrcIntfColdRebootv4001", \
        "IPv4_SSH_login_cold_reboot_LDAP_User_with_Auth_RADIUS_NSS_LDAP_sudo_Authorize_LDAP_Failed", "test_ldap_radius")
    else:
       st.report_tc_pass("FtLdapRadiusNssAuthSudoVrfSrcIntfColdRebootv4001", \
        "IPv4_SSH_login_cold_reboot_LDAP_User_with_Auth_RADIUS_NSS_LDAP_sudo_Authorize_LDAP_Passed", "test_ldap_radius")

    print_log("Verify the v6 login after cold reboot with ldap sudo user,ldap auth and authorize...",'MED')
    if check_login_v6(dut1,d2d1_ipv6,ldap_operator_user,ldap_operator_password):
        print_log("V6 Login to device after cold reboot with ldap sudo user,ldap auth and authorize radius local verification PASSED", "HIGH")
    else:
        print_log("V6 Login to device after cold reboot with ldap sudo user,ldap auth and authorize radius local verification FAILED", "HIGH")
        ldap_radius_local_login_sudo_vrf_srcint_cold_reboot_v6 += 1
        tc_result18 += 1
        final_result = False

    if tc_result18 > 0:
       st.report_tc_fail("FtLdapRadiusNssAuthSudoVrfSrcIntfColdRebootv6001", \
        "IPv6_SSH_login_cold_reboot_LDAP_User_with_Auth_RADIUS_NSS_LDAP_sudo_Authorize_LDAP_Failed", "test_ldap_radius")
    else:
       st.report_tc_pass("FtLdapRadiusNssAuthSudoVrfSrcIntfColdRebootv6001", \
        "IPv6_SSH_login_cold_reboot_LDAP_User_with_Auth_RADIUS_NSS_LDAP_sudo_Authorize_LDAP_Passed", "test_ldap_radius")

    print_log("Configure  the max LDAP servers on DUT2 ..",'MED')
    config_max_ldap_servers()

    print_log("Display  the max LDAP servers on DUT2 ..",'MED')
    display_ldap_servers()
    st.wait(10,'Added delay after configuring the 8 ldap servers')
    print_log("Verify the v4 login  with ldap scale sudo user,ldap auth and authorize...",'MED')
    if check_login(mgmt_ipv4_add,ldap_operator_user,ldap_operator_password):
        print_log("V4 Login to device  with ldap scale sudo user,ldap auth and authorize radius local verification PASSED", "HIGH")
    else:
        print_log("V4 Login to device with ldap scale sudo user,ldap auth and authorize radius local verification FAILED", "HIGH")
        ldap_scale_radius_local_login_sudo_vrf_srcint_v4 += 1
        tc_result19 += 1
        final_result = False

    if tc_result19 > 0:
       st.report_tc_fail("FtLdapScaleRadiusNssAuthSudoVrfSrcIntfv4001", \
        "LDAP_Scale_with_8_IPv4_servers_LDAP_User_with_Authentication_RADIUS_Authorize_LDAP_NSS_LDAP_Failed", "test_ldap_radius")
    else:
       st.report_tc_pass("FtLdapScaleRadiusNssAuthSudoVrfSrcIntfv4001", \
        "LDAP_Scale_with_8_IPv4_servers_LDAP_User_with_Authentication_RADIUS_Authorize_LDAP_NSS_LDAP_Passed", "test_ldap_radius")

    print_log("UnConfigure  the ldap global attribute on DUT2 ..",'MED')
    unconfig_ldap_server_attributes(dut2,'ldap_global')

    print_log("UnConfigure  the pam group dn and pam member attribute on DUT2 ..",'MED')
    unconfig_ldap_server_attributes(dut2,'pam_global')

    print_log("UnConfigure  the sudo global attribute on DUT2 ..",'MED')
    unconfig_ldap_server_attributes(dut2,'sudo_global')

    print_log("UnConfigure  the max LDAP servers on DUT2 ..",'MED')
    unconfig_max_ldap_servers()

    print_log("UnConfigure  RADIUS server on DUT2 ..",'MED')
    unconfig_radius_server()

    print_log("UnConfigure  the ldap src interface as management 0 and vrf mgmt on DUT2 ..",'MED')
    ldap.config_ldap_client_srcintf_vrf(dut2, management = '',vrf = '',config = 'no')

    print_log("Configure  RADIUS server on DUT2 ..",'MED')
    config_radius_server()

    print_log("UnConfigure  the management vrf on DUT2 ..",'MED')
    mvrf.config(dut2, no_form=True)

    print_log("Configure  the ldap as Authorization ..",'MED')
    config_aaa_login_autorization(dut2,local_only)

    print_log("Configure  the NSS ldap server ..",'MED')
    config_nss_ldap_server()

    print_log("Configure  the PAM ldap server ..",'MED')
    config_pam_ldap_server()

    print_log("Configure  the nss sudo specific ldap server attributes ..",'MED')
    config_ldap_server_attributes(dut2,'nss_sudo')

    print_log("Configure  the pam specific ldap server attributes ..",'MED')
    config_ldap_server_attributes(dut2,'pam_specific')

    print_log("Display  the NSS Sudo and PAM LDAP servers on DUT2 ..",'MED')
    display_ldap_servers()

    st.wait(50,'Added delay to apply the NSS and PAM details on device')
    print_log("Verify the nss sudoer specific user and pam group in diff ldap server with radius login-method...",'MED')
    if check_login(mgmt_ipv4_add,ldap_operator_user,ldap_operator_password):
        print_log("V4 Login to device with nss sudoer specific user and pam group in diff ldap server\
         with radius login-method verification PASSED", "HIGH")
    else:
        print_log("V4 Login to device with nss sudoer specific user and pam group in diff ldap server \
          with radius login-method verification FAILED", "HIGH")
        ldap_nss_sudo_pam_specific_radius_login_v4 += 1
        tc_result20 += 1
        final_result = False

    if tc_result20 > 0:
       st.report_tc_fail("FtLdapRadiusNssSudoLdapandPamldapv4001",\
          "IPv4_SSH_login_with_NSS_SUDO_LDAP_user_and_PAM_Authorize_LDAP_group_with_RADIUS_Auth_Failed", "test_ldap_radius")
    else:
       st.report_tc_pass("FtLdapRadiusNssSudoLdapandPamldapv4001", \
          "IPv4_SSH_login_with_NSS_SUDO_LDAP_user_and_PAM_Authorize_LDAP_group_with_RADIUS_Auth_Passed", "test_ldap_radius")
    print_log("Verify the v6 nss sudoer specific user and pam group in diff ldap server with radius login-method...",'MED')
    if check_login_v6(dut1,d2d1_ipv6,ldap_operator_user,ldap_operator_password):
        print_log("V4 Login to device with nss sudoer specific user and pam group in diff ldap server \
           with radius login-method verification PASSED", "HIGH")
    else:
        print_log("V6 Login to device with nss sudoer specific user and pam group in diff ldap server \
           with radius login-method verification FAILED", "HIGH")
        ldap_nss_sudo_pam_specific_radius_login_v6 += 1
        tc_result21 += 1
        final_result = False

#    import pdb;pdb.set_trace()
    print_log("deleting the Local user to check the failthrough with ldap and local...",'MED')
    if creating_local_user(dut2,local_user,local_user_password,role_admin,user_del):
        print_log("Local user localuser deletion verification PASSED", "HIGH")
    else:
        print_log("Local user localuser deletion verification FAILED", "HIGH")
        local_user_delete += 1
        tc_result21 += 1
        final_result = False

    if tc_result21 > 0:
        st.report_tc_fail("FtLdapRadiusNssSudoLdapandPamldapv6001",\
         "IPv6_SSH_login_with_NSS_SUDO_LDAP_user_and_PAM_Authorize_LDAP_group_with_RADIUS_Auth_Failed", "test_ldap_radius")
    else:
        st.report_tc_pass("FtLdapRadiusNssSudoLdapandPamldapv6001", \
         "IPv6_SSH_login_with_NSS_SUDO_LDAP_user_and_PAM_Authorize_LDAP_group_with_RADIUS_Auth_Passed", "test_ldap_radius")

    print_log("UnConfigure  the nss sudo specific ldap server attributes ..",'MED')
    unconfig_ldap_server_attributes(dut2,'nss_sudo')

    print_log("UnConfigure  the pam specific ldap server attributes ..",'MED')
    unconfig_ldap_server_attributes(dut2,'pam_specific')


    print_log("UnConfigure  the NSS ldap server ..",'MED')
    unconfig_nss_ldap_server()

    print_log("UnConfigure  the PAM ldap server ..",'MED')
    unconfig_pam_ldap_server()

    print_log("Disable the sshv6 on DUT2...",'MED')
    ssh_api.disable_sshv6(dut2)

    print_log("UnConfigure  RADIUS server on DUT2 ..",'MED')
    unconfig_radius_server()



    if not final_result:
        fail_msg = ''
        if ldap_server_global > 0:
            fail_msg += 'LDAP server global details for ldap only Failed:'
        if ldap_login_v4_1 > 0:
            fail_msg += 'IPv4:LDAP user login with ldapuser user Failed:'
        if ldap_login_v4_2 > 0:
            fail_msg += 'IPv4:LDAP user login with ldapuser user and invalid passwd Failed:'
        if ldap_login_v6 > 0:
            fail_msg += 'IPv6:LDAP user login with ldapuser user Failed:'
        if aaa_login_ldap_local > 0:
            fail_msg += 'AAA Login details for ldap local Failed:'
        if ldap_local_login_v4_1 > 0:
            fail_msg += 'IPv4:LDAP user login-method ldap local with ldapuser user Failed:'
        if local_user_create > 0:
            fail_msg += 'IPv4:LDAP user login-method ldap local local user creation Failed:'
        if ldap_local_login_v4_2 > 0:
            fail_msg += 'IPv4:LDAP user login-method ldap local with local user after failthrough Failed:'
        if ldap_local_login_v6 > 0:
            fail_msg += 'IPv6:LDAP user login-method ldap local with ldapuser user Failed:'
        if aaa_login_radius_only > 0:
            fail_msg += 'AAA Login details for radius only Failed:'
        if aaa_login_radius_nss_only > 0:
            fail_msg += 'AAA Login NSS details for radius only Failed:'
        if ldap_radius_login_v4 > 0:
            fail_msg += 'IPv4:LDAP user login with ldapuser user and radius auth Failed:'
        if ldap_radius_login_v6 > 0:
            fail_msg += 'IPv6:LDAP user login with ldapuser user and radius auth Failed:'
        if aaa_login_radius_local > 0:
            fail_msg += 'AAA Login details for radius local Failed:'
        if ldap_radius_local_login_v4_1 > 0:
            fail_msg += 'IPv4:LDAP user login-method radius local with ldapuser user Failed:'
        if ldap_radius_local_login_v4_2 > 0:
            fail_msg += 'IPv4:LDAP user login-method radius local with local user after failthrough Failed:'
        if ldap_radius_local_login_v6 > 0:
            fail_msg += 'IPv6:LDAP user login-method radius local with ldapuser user Failed:'
        if aaa_login_authorize_radius_local_nss > 0:
            fail_msg += 'IPv4:LDAP user login Authorization radius local with ldapuser user Failed:'
        if ldap_server_global_pam > 0:
            fail_msg += 'AAA pam group and attributes details for radius local Failed:'
        if ldap_radius_local_login_pam_v4 > 0:
            fail_msg += 'IPv4:LDAP user login-method radius local with ldap authorization Failed:'
        if ldap_radius_local_login_pam_v6 > 0:
            fail_msg += 'IPv6:LDAP user login-method radius local with ldap authorization Failed:'
        if aaa_login_authorize_radius_local_nss_sudo  > 0:
            fail_msg += 'AAA Login sudo details for radius local Failed:'
        if ldap_server_global_sudo > 0:
            fail_msg += 'ldap global sudo details for radius local Failed:'
        if ldap_radius_local_login_sudo_v4 > 0:
            fail_msg += 'IPv4:LDAP sudo user login-method radius local with ldap authorization Failed:'
        if ldap_radius_local_login_sudo_v6 > 0:
            fail_msg += 'IPv6:LDAP sudo user login-method radius local with ldap authorization Failed:'
        if ldap_radius_local_login_sudo_vrf_srcint_v4 > 0:
            fail_msg += 'IPv4:LDAP sudo user login-method with src intf and vrf radius local with ldap authorization Failed:'
        if ldap_radius_local_login_sudo_vrf_srcint_v6 > 0:
            fail_msg += 'IPv6:LDAP sudo user login-method with src intf and vrf radius local with ldap authorization Failed:'
        if ldap_radius_local_login_sudo_vrf_srcint_config_reload_v4 > 0:
            fail_msg += 'IPv4:Config Reload LDAP sudo user login-method with src intf and vrf radius local with ldap authorization Failed:'
        if ldap_radius_local_login_sudo_vrf_srcint_config_reload_v6 > 0:
            fail_msg += 'IPv6:Config Reload LDAP sudo user login-method with src intf and vrf radius local with ldap authorization Failed:'
        if ldap_radius_local_login_sudo_vrf_srcint_cold_reboot_v4 > 0:
            fail_msg += 'IPv4:Cold Reboot LDAP sudo user login-method with src intf and vrf radius local with ldap authorization Failed:'
        if ldap_radius_local_login_sudo_vrf_srcint_cold_reboot_v6 > 0:
            fail_msg += 'IPv6:Cold Reboot LDAP sudo user login-method with src intf and vrf radius local with ldap authorization Failed:'
        if ldap_scale_radius_local_login_sudo_vrf_srcint_v4 > 0:
            fail_msg += 'IPv4:LDAP Scale sudo user login-method with src intf and vrf radius local with ldap authorization Failed:'
        if local_user_delete > 0:
            fail_msg += 'IPv4:LDAP user login-method ldap local user localuser deletion Failed:'
        if ldap_nss_sudo_pam_specific_radius_login_v4 > 0:
            fail_msg += 'IPv4:LDAP nss sudo user login-method radius passwd with ldap authorization Failed:'
        if ldap_nss_sudo_pam_specific_radius_login_v6 > 0:
            fail_msg += 'IPv6:LDAP nss sudo user login-method radius passwd with ldap authorization Failed:'
        st.report_fail("test_case_failure_message", fail_msg.strip(':'))
    else:
        st.report_pass("test_case_passed")


