
from spytest import st,utils, tgapi
from spytest.utils import filter_and_select

from vrrpv3_scale_vars import *
from vrrpv3_scale_vars import data
import apis.switching.portchannel as pc
import apis.system.port as port_api
import apis.switching.vlan as vlan_api
import apis.routing.ip as ip_api
from apis.routing import arp
import apis.routing.bgp as bgp_api
import apis.routing.ip_bgp as ip_bgp
from apis.routing import vrrp
import apis.switching.mac as mac_api

from utilities import parallel

def vrrpv3_scalebase_config():
    ###################################################
    hdrMsg("########## Base Config for vrrpv3 scale test Starts ########")
    ###################################################
    config_lag()
    result,err = verify_lag()
    if not result:
        st.error(err)
        #config_lag(config='no')
        return False
    config_vlan()
    config_scale_ip()
    config_bgp()
    result = verify_bgp()
    if not result:
        #config_bgp(config='no')
        #config_scale_ip(config='no')
        #config_vlan(config='no')
        #config_lag(config='no')
        return False
    config_vrrp()
    config_scale_tgen()
    ###################################################
    hdrMsg("########## Base Config for vrrpv3 scale test Ends ########")
    ###################################################
    return True

def vrrpv3_scalebase_deconfig():
    ###################################################
    hdrMsg("########## Base De-Config for vrrpv3 scale test Starts ########")
    ###################################################
    config_scale_tgen(config='no')
    #config_vrrp(config='no')
    #config_bgp(config='no')
    #config_scale_ip(config='no')
    #config_vlan(config='no')
    #config_lag(config='no')
    ###################################################
    hdrMsg("########## Base De-Config for vrrpv3 scale test End ########")
    ###################################################


def config_lag(config='yes'):
    if config == 'yes':
        member_flag = 'add'
        ##################################################################
        hdrMsg("LAG-Config1:  Dut1 {} >>> {} <<<< {} Dut3".format(data.d1d3_ports, lag_intf_list[0], data.d3d1_ports))
        hdrMsg("LAG-Config2:  Dut2 {} >>> {} <<<< {} Dut3".format(data.d2d3_ports, lag_intf_list[1], data.d3d2_ports))
        hdrMsg("LAG-Config3:  Dut1 {} >>> {} <<<< {} Dut4".format(data.d1d4_ports[0:2], lag_intf_list[2],data.d4d1_ports[0:2]))
        hdrMsg("LAG-Config4:  Dut2 {} >>> {} <<<< {} Dut4".format(data.d2d4_ports[0:2], lag_intf_list[3],data.d4d2_ports[0:2]))
        ##################################################################
        utils.exec_all(True, [[pc.create_portchannel, data.dut1, [lag_intf_list[0], lag_intf_list[2]], False],
                              [pc.create_portchannel, data.dut2, [lag_intf_list[1], lag_intf_list[3]], False],
                              [pc.create_portchannel, data.dut3, [lag_intf_list[0], lag_intf_list[1]], False],
                              [pc.create_portchannel, data.dut4, [lag_intf_list[2], lag_intf_list[3]], False]])
    else:
        member_flag = 'del'

    ###################################################################
    hdrMsg("LAG-Config: {} member ports to portchannels".format(member_flag))
    ###################################################################
    utils.exec_all(True, [[pc.add_del_portchannel_member, data.dut1, lag_intf_list[0],data.d1d3_ports,member_flag],
                          [pc.add_del_portchannel_member, data.dut3, lag_intf_list[0],data.d3d1_ports,member_flag],
                          [pc.add_del_portchannel_member, data.dut4, lag_intf_list[2],data.d4d1_ports[0:2],member_flag]])
    utils.exec_all(True, [[pc.add_del_portchannel_member, data.dut1, lag_intf_list[2], data.d1d4_ports[0:2],member_flag]])


    utils.exec_all(True, [[pc.add_del_portchannel_member, data.dut2, lag_intf_list[1], data.d2d3_ports,member_flag],
                          [pc.add_del_portchannel_member, data.dut3, lag_intf_list[1], data.d3d2_ports,member_flag],
                          [pc.add_del_portchannel_member, data.dut4, lag_intf_list[3], data.d4d2_ports[0:2],member_flag]])
    utils.exec_all(True, [[pc.add_del_portchannel_member, data.dut2, lag_intf_list[3], data.d2d4_ports[0:2],member_flag]])

    if config == 'no':
        ###################################################################
        hdrMsg("{} Port-channels from all duts".format(member_flag))
        ###################################################################
        utils.exec_all(True, [[pc.delete_portchannel, data.dut1, [lag_intf_list[0], lag_intf_list[2]]],
                              [pc.delete_portchannel, data.dut2, [lag_intf_list[1], lag_intf_list[3]]],
                              [pc.delete_portchannel, data.dut3, [lag_intf_list[0], lag_intf_list[1]]],
                              [pc.delete_portchannel, data.dut4, [lag_intf_list[2], lag_intf_list[3]]]])




def verify_lag():
    ###################################################################
    hdrMsg("Verify Port-Channels are UP on DUT1 and DUT2")
    ###################################################################
    ret_val = True;err_list=[]
    result = retry_api(pc.verify_portchannel_state,data.dut1,portchannel=lag_intf_list[0])
    if result is False:
        err_list.append("{} did not come up on dut1".format(lag_intf_list[0]))
        ret_val= False
    result = retry_api(pc.verify_portchannel_state,data.dut1, portchannel=lag_intf_list[2])
    if result is False:
        err_list.append("{} did not come up on dut1".format(lag_intf_list[2]))
        ret_val=False
    result = retry_api(pc.verify_portchannel_state,data.dut2, portchannel=lag_intf_list[1])
    if result is False:
        err_list.append("{} did not come up on dut2".format(lag_intf_list[1]))
        ret_val=False
    result = retry_api(pc.verify_portchannel_state,data.dut2, portchannel=lag_intf_list[3])
    if result is False:
        err_list.append("{} did not come up on dut2".format(lag_intf_list[3]))
        ret_val=False
    if len(err_list) == 0:
        err_list.append('')
    return ret_val,err_list[0]



def config_vlan(config='yes'):
    if config == 'yes' :
        ##################################################################
        hdrMsg("Vlan-Config: Configure Vlans {} on dut1 ,{} on dut2 ,{} on dut3(Switch) "
               "and {} on dut4(TOR)".format(dut1_vlans,dut2_vlans,dut3_vlans,dut4_vlans))
        ##################################################################
        utils.exec_all(True,[[vlan_api.config_vlan_range,data.dut1,'{} {}'.format(dut1_vlans[0],dut1_vlans[-1])],
                             [vlan_api.config_vlan_range,data.dut2,'{} {}'.format(dut2_vlans[0],dut2_vlans[vrrp_sessions-1])],
                             [vlan_api.config_vlan_range,data.dut3,'{} {}'.format(dut3_vlans[0],dut3_vlans[-1])],
                             [vlan_api.config_vlan_range,data.dut4,'{} {}'.format(dut4_vlans[0],dut4_vlans[-1])]])
        vlan_api.config_vlan_range(data.dut2, '{} {}'.format(dut2_vlans[vrrp_sessions], dut2_vlans[-1]))

        ##################################################################
        hdrMsg("Vlan-Config:Configure {} member of vlans {} on dut1,{} member of vlans {} on dut2 "
               "and {} member of vlans {}"
               " on dut3".format(vrrp_vlans,lag_intf_list[0],vrrp_vlans,lag_intf_list[1],vrrp_vlans,[lag_intf_list[0],lag_intf_list[1]]))
        ##################################################################

        utils.exec_all(True,[[vlan_api.config_vlan_range_members,data.dut1,'{} {}'.format(vrrp_vlans[0],vrrp_vlans[-1]), lag_intf_list[0]],
                         [vlan_api.config_vlan_range_members,data.dut2,'{} {}'.format(vrrp_vlans[0],vrrp_vlans[-1]), lag_intf_list[1]],
                         [vlan_api.config_vlan_range_members,data.dut3,'{} {}'.format(vrrp_vlans[0],vrrp_vlans[-1]), lag_intf_list[0]]])
        vlan_api.config_vlan_range_members(data.dut3, '{} {}'.format(vrrp_vlans[0],vrrp_vlans[-1]),lag_intf_list[1])


        ##################################################################
        hdrMsg("Vlan-Config:Configure Uplink {} member of vlans {} on dut1,{} member of vlans {} on dut2 "
               "and {} {} member of vlans {} "
               "on dut4".format(dut1_uplink_vlans[0],lag_intf_list[2],dut2_uplink_vlans[0],lag_intf_list[3],dut4_vlans[0],dut4_vlans[2],[lag_intf_list[2],lag_intf_list[3]]))
        ##################################################################

        utils.exec_all(True,[[vlan_api.add_vlan_member,data.dut1,'{}'.format(dut1_uplink_vlans[0]),[lag_intf_list[2]],True],
                             [vlan_api.add_vlan_member,data.dut4,'{}'.format(dut4_vlans[0]),[lag_intf_list[2]],True]])

        utils.exec_all(True,[[vlan_api.add_vlan_member,data.dut2,'{}'.format(dut2_uplink_vlans[0]),[lag_intf_list[3]],True],
                             [vlan_api.add_vlan_member,data.dut4,'{}'.format(dut4_vlans[2]),[lag_intf_list[3]],True]])

        ######################################################################
        hdrMsg("Vlan-Config: Configure Uplink dut1 <--> dut4 and dut2 <--> dut4 as access port on vlans  {} and {}"
               " respectively".format(dut1_uplink_vlans[1],dut2_uplink_vlans[1]))
        ######################################################################

        utils.exec_all(True,[[vlan_api.add_vlan_member,data.dut1,'{}'.format(dut1_uplink_vlans[1]),data.d1d4_ports[2]],
                             [vlan_api.add_vlan_member,data.dut4,'{}'.format(dut4_vlans[1]),data.d4d1_ports[2]]])

        utils.exec_all(True,[[vlan_api.add_vlan_member,data.dut2,'{}'.format(dut2_uplink_vlans[1]),data.d2d4_ports[2]],
                             [vlan_api.add_vlan_member,data.dut4,'{}'.format(dut4_vlans[3]),data.d4d2_ports[2]]])

        ######################################################################
        hdrMsg("Vlan-Config: Configure on TOR dut4_tg_port as trunk port with member vlans {}".format(dut4_vlans[4:]))
        ######################################################################

        vlan_api.config_vlan_range_members(data.dut4,'{} {}'.format(dut4_vlans[4],dut4_vlans[-1]),data.d4tg_ports)

        ######################################################################
        hdrMsg("Vlan-Config: Configure on dut3 dut3_tg_port as trunk port with member vlans {}".format(vrrp_vlans))
        ######################################################################

        vlan_api.config_vlan_range_members(data.dut3,'{} {}'.format(vrrp_vlans[0],vrrp_vlans[-1]),data.d3tg_ports)

    else:
        ##########################################################################
        hdrMsg("Vlan-Deconfig: Remove Vlan members  on all DUTs")
        ##########################################################################
        utils.exec_all(True,[[vlan_api.config_vlan_range_members,data.dut1,'{} {}'.format(vrrp_vlans[0],vrrp_vlans[-1]), lag_intf_list[0],'del'],
                         [vlan_api.config_vlan_range_members,data.dut2,'{} {}'.format(vrrp_vlans[0],vrrp_vlans[-1]), lag_intf_list[1],'del'],
                         [vlan_api.config_vlan_range_members,data.dut3,'{} {}'.format(vrrp_vlans[0],vrrp_vlans[-1]), lag_intf_list[0],'del']])
        vlan_api.config_vlan_range_members(data.dut3, '{} {}'.format(vrrp_vlans[0],vrrp_vlans[-1]),lag_intf_list[1],'del')

        utils.exec_all(True,[[vlan_api.delete_vlan_member,data.dut1,'{}'.format(dut1_uplink_vlans[0]),[lag_intf_list[2]],'True'],
                             [vlan_api.delete_vlan_member,data.dut4,'{}'.format(dut4_vlans[0]),[lag_intf_list[2]],'True']])

        utils.exec_all(True,[[vlan_api.delete_vlan_member,data.dut2,'{}'.format(dut2_uplink_vlans[0]),[lag_intf_list[3]],'True'],
                             [vlan_api.delete_vlan_member,data.dut4,'{}'.format(dut4_vlans[2]),[lag_intf_list[3]],'True']])
        utils.exec_all(True,[[vlan_api.delete_vlan_member,data.dut1,'{}'.format(dut1_uplink_vlans[1]),data.d1d4_ports[2]],
                             [vlan_api.delete_vlan_member,data.dut4,'{}'.format(dut4_vlans[1]),data.d4d1_ports[2]]])

        utils.exec_all(True,[[vlan_api.delete_vlan_member,data.dut2,'{}'.format(dut2_uplink_vlans[1]),data.d2d4_ports[2]],
                             [vlan_api.delete_vlan_member,data.dut4,'{}'.format(dut4_vlans[3]),data.d4d2_ports[2]]])

        vlan_api.config_vlan_range_members(data.dut4, '{} {}'.format(dut4_vlans[4], dut4_vlans[-1]), data.d4tg_ports,'del')
        vlan_api.config_vlan_range_members(data.dut3, '{} {}'.format(vrrp_vlans[0], vrrp_vlans[-1]), data.d3tg_ports,'del')
        ##########################################################################
        hdrMsg("Vlan-Deconfig: Remove Vlans on all DUTs")
        ##########################################################################

        utils.exec_all(True,[[vlan_api.config_vlan_range,data.dut1,'{} {}'.format(dut1_vlans[0],dut1_vlans[-1]),'del'],
                             [vlan_api.config_vlan_range,data.dut2,'{} {}'.format(dut2_vlans[0],dut2_vlans[vrrp_sessions-1]),'del'],
                             [vlan_api.config_vlan_range,data.dut3,'{} {}'.format(dut3_vlans[0],dut3_vlans[-1]),'del'],
                             [vlan_api.config_vlan_range,data.dut4,'{} {}'.format(dut4_vlans[0],dut4_vlans[-1]),'del']])
        vlan_api.config_vlan_range(data.dut2, '{} {}'.format(dut2_vlans[vrrp_sessions], dut2_vlans[-1]),'del')

def config_scale_ip(config='yes'):
    if config == 'yes':
        api_name = ip_api.config_ip_addr_interface
        config_str = "Configure"
    else:
        api_name = ip_api.delete_ip_interface
        config_str = "Delete"

    for vlan,ip,secondary_ip in zip(vrrp_vlan_intf,vrrp_ip_list,vrrp_secondary_ip):
        ##########################################################################
        hdrMsg("IP-config: {} IP address for VRRP vlan {} : {}/24 on dut1 and {}/24 on "
                "dut2".format(config_str,vlan,ip[0],ip[1]))
        ##########################################################################
        dict1 = {'interface_name':vlan,'ip_address':ip[0],'subnet':mask,'is_secondary_ip':secondary_ip}
        dict2 = {'interface_name':vlan,'ip_address':ip[1],'subnet':mask,'is_secondary_ip':secondary_ip}
        parallel.exec_parallel(True, [data.dut1, data.dut2], api_name, [dict1, dict2])
        
    ##########################################################################
    hdrMsg("IP-config: {} IP address for uplink vlan over lag {} : {}/24 on dut1 and {}/24 on "
           "dut4".format(config_str,dut1_uplink_vlan_intf[0],dut1_4_ip_list[0],dut4_1_ip_list[0]))
    ##########################################################################
    utils.exec_all(True, [[api_name, data.dut1,dut1_uplink_vlan_intf[0] ,dut1_4_ip_list[0], mask],
                          [api_name, data.dut4,dut1_uplink_vlan_intf[0], dut4_1_ip_list[0], mask]])

    ##########################################################################
    hdrMsg("IP-config: {} IP address for uplink access vlan {} : {}/24 on dut1 and {}/24 on "
           "dut4".format(config_str,dut1_uplink_vlan_intf[1],dut1_4_ip_list[1],dut4_1_ip_list[1]))
    ##########################################################################
    utils.exec_all(True, [[api_name, data.dut1,dut1_uplink_vlan_intf[1] ,dut1_4_ip_list[1], mask],
                          [api_name, data.dut4,dut1_uplink_vlan_intf[1], dut4_1_ip_list[1], mask]])

    ##########################################################################
    hdrMsg("IP-config: {} IP address for uplink vlan over lag {} : {}/24 on dut2 and {}/24 on "
           "dut4".format(config_str,dut2_uplink_vlan_intf[0],dut2_4_ip_list[0],dut4_2_ip_list[0]))
    ##########################################################################
    utils.exec_all(True, [[api_name, data.dut2,dut2_uplink_vlan_intf[0] ,dut2_4_ip_list[0], mask],
                          [api_name, data.dut4,dut2_uplink_vlan_intf[0], dut4_2_ip_list[0], mask]])

    ##########################################################################
    hdrMsg("IP-config: {} IP address for uplink access vlan {} : {}/24 on dut2 and {}/24 on "
           "dut4".format(config_str,dut2_uplink_vlan_intf[1],dut2_4_ip_list[1],dut4_2_ip_list[1]))
    ##########################################################################
    utils.exec_all(True, [[api_name, data.dut2,dut2_uplink_vlan_intf[1] ,dut2_4_ip_list[1], mask],
                          [api_name, data.dut4,dut2_uplink_vlan_intf[1], dut4_2_ip_list[1], mask]])

    ##########################################################################
    hdrMsg("IP-config: On DUT4 (TOR) {} connected routes on vlans {} with addresses {} "
           "respectively ".format(config_str,dut4_vlan_intf[vrrp_sessions:],dut4_tg_ip_list))
    ##########################################################################
    for vlan,ip in zip(dut4_vlan_intf[vrrp_sessions:],dut4_tg_ip_list):
        api_name(data.dut4,vlan,ip,mask)

    ##########################################################################
    hdrMsg("IP-config: {} Static arp on DUT4 for destination IPs to verify traffic".format(config_str))
    ##########################################################################
    if config == 'yes':
        ip_api.config_ip_addr_interface(data.dut4,dut4_vlan_intf[-1],dut4_tg_ip_list[-1],mask)
        arp.add_static_arp(data.dut4, tg_dest_ip_list[-1],tg_dest_mac_list[-1], interface="Vlan{}".format(dut4_vlans[-1]))
        mac_api.config_mac(data.dut4,tg_dest_mac_list[-1],dut4_vlans[-1],data.d4tg_ports)
    else:
        ip_api.delete_ip_interface(data.dut4,dut4_vlan_intf[-1],dut4_tg_ip_list[-1],mask)
        arp.delete_static_arp(data.dut4,tg_dest_ip_list[-1])
        mac_api.delete_mac(data.dut4,tg_dest_mac_list[-1],dut4_vlans[-1])


def config_bgp(config='yes'):
    if config == 'yes':
        ##########################################################################
        hdrMsg("BGP-config: Configure BGP routers on dut1,dut2 and dut4")
        ##########################################################################
        dict1 = {'local_as':dut1_as,'router_id':dut1_router_id,'config_type_list':['router_id']}
        dict2 = {'local_as':dut2_as,'router_id':dut2_router_id,'config_type_list':['router_id']}
        dict3 = {'local_as': dut4_as, 'router_id': dut4_router_id, 'config_type_list': ['router_id']}
        parallel.exec_parallel(True, [data.dut1, data.dut2,data.dut4], bgp_api.config_bgp, [dict1, dict2,dict3])

        ##########################################################################
        hdrMsg("BGP-config: Configure 2  EBGP sessions each  between dut1 <--> dut4 and dut2 <--> dut4 using peer-group ")
        ##########################################################################
        for nbr_1,nbr_3 in zip(dut4_1_ip_list,dut1_4_ip_list):
           dict1 = {'local_as':dut1_as,'peergroup':peer_v4_1,'config_type_list':['peergroup'],'remote_as':dut4_as,'neighbor':nbr_1}
           dict2 = {'local_as':dut4_as,'peergroup': peer_v4_1, 'config_type_list': ['peergroup'], 'remote_as': dut1_as,'neighbor': nbr_3}
           parallel.exec_parallel(True, [data.dut1, data.dut4], bgp_api.config_bgp, [dict1, dict2])

        for nbr_1,nbr_3 in zip(dut4_2_ip_list,dut2_4_ip_list):
           dict1 = {'local_as':dut2_as,'peergroup':peer_v4_2,'config_type_list':['peergroup'],'remote_as':dut4_as,'neighbor':nbr_1}
           dict2 = {'local_as':dut4_as,'peergroup': peer_v4_2, 'config_type_list': ['peergroup'], 'remote_as': dut2_as,'neighbor': nbr_3}
           parallel.exec_parallel(True, [data.dut2, data.dut4], bgp_api.config_bgp, [dict1, dict2])


        ##########################################################################
        hdrMsg("BGP-config: Advertise routes from dut4 to VRRP duts dut1 and dut2 using netowrk command ")
        ##########################################################################
        bgp_api.config_bgp(data.dut4,local_as=dut4_as,config_type_list=['network'],network='{}/{}'.format(dut4_route_list[-1],mask))
    else:
        ##########################################################################
        hdrMsg("BGP-Deconfig: Delete BGP routers globally from all DUTs")
        ##########################################################################
        dict1 = {'config_type_list': ["removeBGP"], 'removeBGP': 'yes', 'config': 'no'}
        parallel.exec_parallel(True, [data.dut1, data.dut2,data.dut4], bgp_api.config_bgp, [dict1, dict1,dict1])

def config_scale_tgen(config='yes'):
    if data.delay_factor != 1:
        vrid_list1 = [x for x in vrid_list if vrid_list.index(x) % 16 == 0]
        vlan_list1 = []
        for a in vrid_list1:
            vlan_list1.append(vlan_list[a-1])
        #vlan_list1 = [i+1 for i in range(len(vrid_list1))]
        tg_src_mac_list1 = [x for x in tg_src_mac_list if tg_src_mac_list.index(x) % 16 == 0]
        vmac_list1 = [x for x in vmac_list if vmac_list.index(x) % 16 == 0]
        tg_src_ip_list1 = [x for x in tg_src_ip_list if tg_src_ip_list.index(x) % 16 == 0]
        tg_dest_ip_list1 = [x for x in tg_dest_ip_list if tg_dest_ip_list.index(x) % 16 == 0]
        vip_list1 = [x for x in vip_list if vip_list.index(x) % 16 == 0]
    else:
        vrid_list1 = [x for x in vrid_list if vrid_list.index(x) % 4 == 0]
        vlan_list1 = []
        for a in vrid_list1:
            vlan_list1.append(vlan_list[a-1])
        #vlan_list1 = [i+1 for i in range(len(vrid_list1))]
        tg_src_mac_list1 = [x for x in tg_src_mac_list if tg_src_mac_list.index(x) % 4 == 0]
        vmac_list1 = [x for x in vmac_list if vmac_list.index(x) % 4 == 0]
        tg_src_ip_list1 = [x for x in tg_src_ip_list if tg_src_ip_list.index(x) % 4 == 0]
        tg_dest_ip_list1 = [x for x in tg_dest_ip_list if tg_dest_ip_list.index(x) % 4 == 0]
        vip_list1 = [x for x in vip_list if vip_list.index(x) % 4 == 0]

    if config == 'yes':
        data.tg1.tg_traffic_control(action='reset', port_handle=data.tg_handles)
        data.stream_handles = {}
        data.host_handles ={}
        data.stream_details = {}

        for vrid,vlan,src_mac,dest_mac,src_ip,dest_ip,vip in zip(vrid_list1,vlan_list1,tg_src_mac_list1,vmac_list1,tg_src_ip_list1,tg_dest_ip_list1,vip_list1):
            ##########################################################################
            hdrMsg("TGEN-Config: DUT3-TG : Configure IPv4 traffic for VRRP session {} "
                   " SRC-MAC: {} DEST-MAC :{} SRC-IP:{}  DEST IP :{}"
                   "".format(vrid,src_mac,dest_mac,src_ip,dest_ip))
            ##########################################################################

            vrrp_stream = data.tg1.tg_traffic_config(mac_src=src_mac, mac_dst=dest_mac,l2_encap='ethernet_ii_vlan', vlan="enable", vlan_id=vlan,
                                                rate_pps=traffic_rate, high_speed_result_analysis=0, \
                                              mode='create', port_handle=data.tg_handles[0], transmit_mode='continuous',
                                              l3_protocol='ipv4', ip_src_addr=src_ip \
                                              , ip_dst_addr=tg_dest_ip_list[-1], mac_discovery_gw=vip)
            data.stream_handles['vrrp_{}'.format(vrid)] = vrrp_stream['stream_id']
            data.stream_details[data.stream_handles['vrrp_{}'.format(vrid)]] = "IPv4 traffic for VRRP session {} SRC-MAC:{}" \
                                                                               " DEST-MAC:{} VLAN-ID:{} SRC-IP:{} " \
                                                                               " DEST IP:{} " \
                                                                               "Rate:{} fps".format(vrid,src_mac,dest_mac,vlan,src_ip,tg_dest_ip_list[-1],traffic_rate)
        '''
        ##########################################################################
        hdrMsg("TGEN-Config: DUT4-TG : Configure traffic stream for downstream TOR(dut4) to dut3")
        ##########################################################################
        down_link_stream = data.tg2.tg_traffic_config(mac_src=tg2_src_mac, mac_dst=data.D4_tg_mac, rate_pps=traffic_rate, \
                                                 mode='create', port_handle=data.tg_handles[1], high_speed_result_analysis=0,
                                                 transmit_mode='continuous',l2_encap='ethernet_ii_vlan', vlan="enable", vlan_id=dut4_vlans[-1],
                                                 l3_protocol='ipv4', ip_src_addr=tg_dest_ip_list[-1] \
                                                 , ip_dst_addr=vrrp_ip_list[0][2], mac_discovery_gw=dut4_tg_ip_list[0])

        data.stream_handles['downstream'] = down_link_stream['stream_id']
        data.stream_details[data.stream_handles['downstream']] = "Downstream IPv4 Traffic: SRC-MAC: {}" \
                                                                 "Dest-MAC: {} Vlan-ID: {} SRC-IP:{} " \
                                                                 "DEST-IP: {} ".format(tg2_src_mac,data.D4_tg_mac,dut4_vlans[-1],tg_dest_ip_list[-1],vrrp_ip_list[0][2])
        st.log(data.stream_handles)
        '''
    else:
        ##########################################################################
        hdrMsg("TGEN-DeConfig: Delete Traffic Streams/hosts on all TG ports ")
        ##########################################################################
        data.tg1.tg_traffic_control(action='reset', port_handle=data.tg_handles)

def config_vrrp(config='yes'):
    if config == 'yes':
        ##############################################################################
        hdrMsg("Configure 128-VRRPv3 sessions with dut1 Master for first 64 sessions and dut2 Master for next 64 sessions")
        ##############################################################################
        for session_no,vrid,vlan,vip,dut1_prio,dut2_prio in zip(range(1,len(vip_list)+1),vrid_list,dut1_vlan_intf[0:vrrp_sessions],
                                                                vip_list,vrrp_priority_list_dut1,vrrp_priority_list_dut2):
            if session_no == 1 or session_no == 2:
                master_dut = 'dut1' ;backup_dut = 'dut2'
            else:
                master_dut = 'dut2' ; backup_dut = 'dut1'
            ##########################################################################
            hdrMsg("VRRP-Config: Configure VRRP session {} with VRID {} on vlan {} VIP {} ,"
                   "with {} as VRRP master and {} as backup".format(session_no,vrid,vlan,vip,master_dut,backup_dut))
            ##########################################################################
            dict1 = {'vrid': vrid, 'vip': vip, 'interface': vlan, 'priority': dut1_prio,'config':'yes','enable':''}
            dict2 = {'vrid': vrid, 'vip': vip, 'interface': vlan, 'priority': dut2_prio,'config':'yes','enable':''}
            parallel.exec_parallel(True, [data.dut1, data.dut2], vrrp.configure_vrrp, [dict1, dict2])

            dict1 = {'vrid': vrid, 'interface': vlan, 'version':3,'skip_error':True}
            dict2 = {'vrid': vrid, 'interface': vlan, 'version':3,'skip_error':True}
            parallel.exec_parallel(True, [data.dut1, data.dut2], vrrp.configure_vrrp, [dict1, dict2])

    else:
        for session_no,vrid,vlan,vip,dut1_prio,dut2_prio in zip(range(1,len(vip_list)+1),vrid_list,dut1_vlan_intf[0:vrrp_sessions],
                                                                vip_list,vrrp_priority_list_dut1,vrrp_priority_list_dut2):
            ##########################################################################
            hdrMsg("VRRP-DeConfig: Delete VRRP session {} with VRID {} on vlan {} VIP {} ".format(session_no,vrid,vlan,vip))
            ##########################################################################
            dict1 = {'vrid': vrid, 'interface': vlan, 'config':'no','disable':''}
            dict2 = {'vrid': vrid, 'interface': vlan, 'config':'no','disable':''}
            parallel.exec_parallel(True, [data.dut1, data.dut2], vrrp.configure_vrrp, [dict1, dict2])


def verify_vrrp(traffic_check='no',dut_check='no',check_backup='no',summary='no',retry_count=5):
    if summary == 'no':
        for vrid,intf,vmac,vip in zip(vrid_list[0:int(vrrp_sessions/2)],dut1_vlan_intf[0:int(vrrp_sessions/2)],vmac_list_1[0:int(vrrp_sessions/2)],vip_list[0:int(vrrp_sessions/2)]):
            result = verify_master_backup(vrid,intf,vmac,vip,master_dut=data.dut1,backup_dut=data.dut2,skip_backup_check=check_backup)
            if result is False:
                st.error("VRRP Master/Backup election is incorrect for {}".format(vrid))
                return False
        if traffic_check == 'yes':
            ###########################################################
            hdrMsg("Verify for VRRP sessions {} ,Master DUT {} forwards data traffic".format(vrid_list[0:int(vrrp_sessions/2)], data.dut1))
            ############################################################
            result = verify_traffic(master_dut=data.dut1, backup_dut=data.dut2, vrid=vrid_list[0:int(vrrp_sessions/2)],dut_check=dut_check)
            if result is False:
                return False

        for vrid,intf,vmac,vip in zip(vrid_list[int(vrrp_sessions/2):],dut1_vlan_intf[int(vrrp_sessions/2):],vmac_list_1[int(vrrp_sessions/2):],vip_list[int(vrrp_sessions/2):]):
            result = verify_master_backup(vrid,intf,vmac,vip,master_dut=data.dut2,backup_dut=data.dut1,skip_backup_check=check_backup)
            if result is False:
                st.error("VRRP Master/Backup election is incorrect for {}".format(vrid))
                return False

        if traffic_check == 'yes':
            ###########################################################
            hdrMsg("Verify for VRRP sessions {} ,Master DUT {} forwards data traffic".format(vrid_list[int(vrrp_sessions/2):],data.dut2))
            ############################################################
            result = verify_traffic(master_dut=data.dut2, backup_dut=data.dut1, vrid=vrid_list[int(vrrp_sessions/2):], dut_check=dut_check)
            if result is False:
                return False
    else:
        ################################################################
        hdrMsg("Verify DUT1 is Master for VRIDs {} and Backup for VRIDs {} and vice versa on dut2".format(vrid_list[0:int(vrrp_sessions/2)],vrid_list[int(vrrp_sessions/2):]))
        ################################################################
        role_list_1 = ['Master'] * (int(vrrp_sessions/2)) + ['Backup'] * (int(vrrp_sessions/2))
        role_list_2 = ['Backup'] * (int(vrrp_sessions/2)) + ['Master'] * (int(vrrp_sessions/2))
        dict1 = {'vrid':vrid_list,'interface':vrrp_vlan_intf,'state':role_list_1,'vip':vip_list,'config_prio':vrrp_priority_list_dut1,'current_prio':vrrp_priority_list_dut1}
        dict2 = {'vrid': vrid_list, 'interface': vrrp_vlan_intf, 'state': role_list_2, 'vip': vip_list,'config_prio': vrrp_priority_list_dut2, 'current_prio': vrrp_priority_list_dut2}
        result = retry_parallel(vrrp.verify_vrrp_summary,[dict1,dict2],[data.dut1,data.dut2],retry_count=retry_count)
        if result is False:
            st.error("VRRP Master/Backup election incorrect for one or more configured VRRP sessions")
            return False
    return True

def hdrMsg(msg):
    st.log("\n######################################################################" \
    " \n %s \n######################################################################"%msg)

def retry_api(func,args,**kwargs):
    retry_count = kwargs.get("retry_count", 15)
    delay = kwargs.get("delay", 3)
    if 'retry_count' in kwargs: del kwargs['retry_count']
    if 'delay' in kwargs: del kwargs['delay']
    for i in range(retry_count):
        st.log("Attempt %s of %s" %((i+1),retry_count))
        if func(args,**kwargs):
            return True
        if retry_count != (i+1):
            st.log("waiting for %s seconds before retyring again"%delay)
            st.wait(delay)
    return False

def retry_parallel(func,dict_list=[],dut_list=[],retry_count=10,delay=3):
    for i in range(retry_count):
        st.log("Attempt %s of %s" %((i+1),retry_count))
        result = parallel.exec_parallel(True,dut_list,func,dict_list)
        if False not in result[0]:
            return True
        if retry_count != (i+1):
            st.log("waiting for %s seconds before retyring again"%delay)
            st.wait(delay)
    return False


def verify_master_backup(vrid,interface,vmac,vip,master_dut,backup_dut,traffic_check='no',skip_backup_check='no'):
    #########################################################
    hdrMsg("VRID : {} Interface : {} Verify {} is Master and {} is Backup ".format(vrid,interface,master_dut,backup_dut))
    #########################################################
    if skip_backup_check == 'no':
        dict1 = {'interface': interface, 'state': 'Master', 'vrid': vrid, 'vmac':vmac, 'vip':vip}
        dict2 = {'interface': interface, 'state': 'Backup', 'vrid': vrid, 'vmac':vmac, 'vip':vip}
        result = retry_parallel(vrrp.verify_vrrp,[dict1,dict2],[master_dut,backup_dut])
        if result is False:
            st.error("{} not elected as VRRP Master for VRID {}".format(master_dut,vrid))
            return False
    else:
        result2 = retry_api(vrrp.verify_vrrp,master_dut,state='Master',vrid=vrid,interface=interface,vmac=vmac,vip=vip)
        if result2 is False:
            st.error("{} not elected as VRRP Master for VRID {}".format(backup_dut,vrid))
            return False
    if traffic_check == 'yes':
        result = verify_traffic(master_dut,backup_dut,vrid)
        if result is False:
            st.error("Traffic check failure for VRRP session {}".format(vrid))
            return False
    return True

def verify_traffic(master_dut,backup_dut,vrid,dut_check='no',start_traffic='yes'):
    if type(vrid) is int:
        vrid = [vrid]
    stream_handle = [data.stream_handles['vrrp_{}'.format(id)] for id in vrid]
    ############################################################
    hdrMsg("Start Traffic for VRRP sessions - {} stream {} from dut3 TG to dut4 TG".format(vrid,stream_handle))
    ############################################################
    if start_traffic == 'yes':
        run_traffic(stream_handle)
        st.wait(2)
    traffic_check = verify_tg_traffic_rate(src_tg_obj=data.tg1,dest_tg_obj=data.tg2,src_port=data.tgd3_ports,dest_port=data.tgd4_ports)
    if traffic_check is False:
        if start_traffic == 'yes':
            run_traffic(stream_handle,action='stop')
        return False

    if dut_check == 'yes':
        if master_dut == data.dut1:
            master_ports = [lag_intf_list[2]]+data.d1d4_ports[2:]
            backup_ports = [lag_intf_list[3]]+data.d2d4_ports[2:]
        else:
            master_ports = [lag_intf_list[3]]+data.d2d4_ports[2:]
            backup_ports = [lag_intf_list[2]]+data.d1d4_ports[2:]
        rate_to_check = traffic_rate * len(stream_handle)
        ####################################################################
        hdrMsg("Verify Master DUT {} forwards traffic for VRRP sessions {}".format(master_dut,vrid))
        ####################################################################
        total_tx_rate = get_dut_tx_rate(master_dut,master_ports)
        ########################################################################
        hdrMsg("Verify aggregate tx_rate on Master is equal to total TG tx rate")
        ########################################################################
        st.log("Total TX rate on TGEN : {} pps ".format(rate_to_check))
        st.log("Total Tx rate on Master dut {} : {} pps".format(master_dut,total_tx_rate))

        if (float(rate_to_check) - total_tx_rate) > rate_threshold:
            st.error("Master DUT not forwading all Traffic towards TOR")
            ############################################################
            hdrMsg("Check Backup dut counters in case of failure")
            ############################################################
            total_tx_rate_backup = get_dut_tx_rate(backup_dut,backup_ports)
            st.log("Total TX rate on TGEN : {} pps ".format(rate_to_check))
            st.log("Total Tx rate on Backup dut {} : {} pps".format(backup_dut, total_tx_rate_backup))
            if start_traffic == 'yes':
                data.tg1.tg_traffic_control(action='stop', stream_handle=stream_handle)
            return False
    if start_traffic == 'yes':
        data.tg1.tg_traffic_control(action='stop', stream_handle=stream_handle)
    return True

def run_traffic(stream_handle=None,action='start'):
    if data.delay_factor != 1:
        vrid_list1 = [x for x in vrid_list if vrid_list.index(x) % 16 == 0]
    else:
        vrid_list1 = [x for x in vrid_list if vrid_list.index(x) % 4 == 0]

    if stream_handle is None:
        stream_handle = [data.stream_handles['vrrp_{}'.format(id)] for id in vrid_list1]
    else:
        if type(stream_handle) is not list : stream_handle =[stream_handle]

    if action == 'start':
        #data.tg1.tg_traffic_control(action='clear_stats',port_handle=data.tg_handles)
        data.tg1.tg_traffic_control(action='run', stream_handle=stream_handle)
    else:
        data.tg1.tg_traffic_control(action='stop', stream_handle=stream_handle)

def verify_tg_traffic_rate(src_tg_obj=None,dest_tg_obj=None,src_port=None,dest_port=None,exp_ratio=1):
    if src_tg_obj is None: src_tg_obj = data.tg1
    if dest_tg_obj is None : dest_tg_obj = data.tg2
    if src_port is None : src_port = data.tgd3_ports
    if dest_port is None: dest_port = data.tgd4_ports
    traffic_data = {
        '1': {
            'tx_ports': [src_port],
            'tx_obj': [src_tg_obj],
            'exp_ratio': [exp_ratio],
            'rx_ports': [dest_port],
            'rx_obj': [dest_tg_obj]
        }
    }
    aggregate_result = tgapi.validate_tgen_traffic(traffic_details=traffic_data, mode='aggregate',
                                             comp_type='packet_rate', delay_factor=data.delay_factor)
    if aggregate_result:
        st.log('Traffic verification passed ')
        return True
    else:
        st.error('Traffic verification failed')
        return False

def get_dut_tx_rate(dut,dut_ports):
    tx_rate = {}
    total_tx_rate = 0.0
    output = port_api.get_interface_counters_all(dut)
    for port in dut_ports:
        entries = filter_and_select(output,['tx_pps'], {'iface': port})
        if entries:
            rate = entries[0]['tx_pps'].replace("/s", "")
            tx_rate[port] = float(rate)
        else:
            tx_rate[port] = 0.0
            st.error("Interface counters for {} not available. Set to 0 B/s".format(port))
        total_tx_rate = total_tx_rate + tx_rate[port]
        st.log("Tx rate on port {} : {} /s".format(port,tx_rate[port]))
    st.log("Total Tx rate : {} /s".format(total_tx_rate))
    return total_tx_rate


def verify_bgp():
    ###########################################################
    hdrMsg("BGP verify: Verify BGP sessions are up on dut1")
    ############################################################
    result = retry_api(ip_bgp.check_bgp_session,data.dut1,nbr_list=dut4_1_ip_list,state_list=['Established']*len(dut4_1_ip_list))
    if result is False:
        st.error("one or more BGP sessions did not come up between dut1 and dut4")
        return False
    ###########################################################
    hdrMsg("BGP verify: Verify BGP sessions are up on dut2")
    ############################################################
    result = retry_api(ip_bgp.check_bgp_session,data.dut2,nbr_list=dut4_2_ip_list,state_list=['Established']*len(dut4_2_ip_list))
    if result is False:
        st.error("one or more BGP sessions did not come up between dut2 and dut4")
        return False
    return True

def verify_tg_ping(vrid,dest_ip,ping_count=3):
    host_handle = data.host_handles['vrrp_host_{}'.format(vrid)]
    st.log("#### VRID {} :Verify Ping from {} to {} ####".format(vrid,host_handle,dest_ip))
    result = tgapi.verify_ping(src_obj=data.tg1, port_handle=data.tg_handles[0],
         dev_handle=host_handle, dst_ip=dest_ip, ping_count=ping_count, exp_count=ping_count)
    return result


def check_mac(dut,vlan_list,mac_list,port_list):

    if type(vlan_list) is not list : vlan_list = [vlan_list]
    if type(mac_list) is not list: mac_list = [mac_list]
    if type(port_list) is not list: port_list = [port_list]

    for vlan,mac,port in zip(vlan_list,mac_list,port_list):
        result = mac_api.verify_mac_address_table(dut,vlan=vlan,mac_addr=mac,port=port)
        if result is False:
            err="MAC check Failed on DUT {} !!! MAC- {} VLAN-{}".format(dut,mac,vlan)
            return False,err
    return True,'mac_check_pass'

def print_topology():
    ######################################################
    hdrMsg(" #####  VRRP Topology  ######")
    ######################################################
    topology = r"""
                              TG2
                               |
                               |
                             ToR-DUT4
                         / / / / \ \ \ \
             2-port     / / / /   \ \ \ \      2-port
             Lag-{}    / / / /     \ \ \ \    Lag-{}
                      / / / /       \ \ \ \
                     / / / /         \ \ \ \
                    / / / /           \ \ \ \
                  VRRP-DUT1          VRRP-DUT2
                      \                /
            4-port     \              /  4-port
            Lag-{}      \            /   Lag-{}
                         \          /
                          \        /
                           \      /
                            DUT3(L2 switch)
                              |
                              |
                             TG1

    """.format(lag_id_list[2],lag_id_list[3],lag_id_list[0],lag_id_list[1])
    st.log(topology)

    st.log("VRRP Sessions : {}".format(vrrp_sessions))
    st.log("VRRP ID : {} ".format(vrid_list))
    st.log("VRRP VLans : {}".format(vrrp_vlan_intf))
    st.log("Virtual IPs : {}".format(vip_list))
    st.log("VMAC : {}".format(vmac_list))
    st.log("Lag-{} DUT1 ports : {} ".format(lag_id_list[0],data.d1d3_ports))
    st.log("       DUT3 ports : {} ".format(data.d3d1_ports))
    st.log("Lag-{} DUT2 ports : {} ".format(lag_id_list[1],data.d2d3_ports))
    st.log("       DUT3 ports : {} ".format(data.d3d2_ports))
    st.log("Lag-{} DUT1 ports : {} ".format(lag_id_list[2],data.d1d4_ports[0:2]))
    st.log("       DUT4 ports : {} ".format(data.d4d1_ports[0:2]))
    st.log("Lag-{} DUT2 ports : {} ".format(lag_id_list[3],data.d2d4_ports[0:2]))
    st.log("       DUT4 ports : {} ".format(data.d4d2_ports[0:2]))
    st.log("3 Uplink Intf: 2-Vlans (2-port LAG and 1 access) and 1 physical L3 port")
    st.log("D1 to D4 : UPLINK Vlans - {} ".format(dut1_uplink_vlan_intf))
    st.log("D2 to D4 : UPLINK Vlans - {}".format(dut2_uplink_vlan_intf))

def revert_vrrp():
    ######################################################
    hdrMsg(" #####  Reverting back the vrrp config to base config, ignore the errors below  ######")
    ######################################################

    for session_no,vrid,vlan,vip,dut1_prio,dut2_prio in zip(range(1,len(vip_list)+1),vrid_list,dut1_vlan_intf[0:vrrp_sessions],
                                                                vip_list,vrrp_priority_list_dut1,vrrp_priority_list_dut2):
        st.unused(session_no)
        dict1 = {'vrid': vrid, 'vip': vip, 'interface': vlan, 'priority': dut1_prio,'config':'yes','enable':'','skip_error':True}
        dict2 = {'vrid': vrid, 'vip': vip, 'interface': vlan, 'priority': dut2_prio,'config':'yes','enable':'','skip_error':True}
        parallel.exec_parallel(True, [data.dut1, data.dut2], vrrp.configure_vrrp, [dict1, dict2])


