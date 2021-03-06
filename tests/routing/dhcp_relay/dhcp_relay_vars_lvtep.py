from spytest.dicts import SpyTestDict

data = SpyTestDict()

#IP params
mask = '31'
mask_1 = '20'
mask_v6 = '64'
mask_24 = '24'
dut1_2_ip_list = ['12.12.12.0']
dut2_1_ip_list = ['12.12.12.1']
dut1_3_ip_list = ['13.13.13.0']
dut3_1_ip_list = ['13.13.13.1']
dut2_4_ip_list = ['192.168.0.1','20.20.20.1','192.168.200.1','30.30.30.1']
#dut3_server_ip_list = ['172.16.0.1']
#dut3_server_ipv6_list = ['2072::1']

dut1_loopback_ip_list = ['1.1.1.1','1.1.1.5']
dut2_loopback_ip_list = ['2.2.2.1','2.2.2.5']
dut3_loopback_ip_list = ['3.3.3.1','3.3.3.5']

dut2_loopback_ip = '100.100.100.100'
dut2_loopback_ip6 = '4000::10'
dut5_loopback_ip6 = '4000::11'

## Added for IPv6 address
dut1_2_ipv6_list = ['2001::1:1', '2002::2:1', '2003::3:1']
dut2_1_ipv6_list = ['2001::1:2', '2002::2:2', '2003::3:2']
dut1_3_ipv6_list = ['3001::1:1', '3002::2:1', '3003::3:1']
dut3_1_ipv6_list = ['3001::1:2', '3002::2:2', '3003::3:2']
# Vlan100 , data.d2d4_ports[1] ,
#dut2_4_ipv6_list = ['2092::1', '2020::1', '2030::1']
dut2_4_ipv6_list = ['2092::1', '2020::1', '2200::1','2030::1']
# Lvtep params

dut1_AS ='100'
dut2_AS ='200'
dut3_AS ='300'

vrf_name ='Vrf-RED'
dut1_5_ip_list = ['12.12.11.0']
dut5_1_ip_list = ['12.12.11.1']
dut2_5_ip_list = ['25.25.11.1']
dut5_2_ip_list = ['25.25.11.2']
dut5_4_ip_list = ['192.168.0.2','20.20.20.2','192.168.200.2','30.30.30.1']

dut5_loopback_ip_list = ['5.5.5.1','2.2.2.5']
dut5_AS ='500'
dut5_4_ipv6_list = ['2092::2', '2020::2', '2200::2','2030::2']

dut1_5_ipv6_list = ['5001::1:1', '5002::2:1', '5003::3:1']
dut5_1_ipv6_list = ['5001::1:2', '5002::2:2', '5003::3:2']
route_list =  ['192.168.0.0/24','20.20.20.0/24','192.168.200.0/24','30.30.30.0/24','100.100.100.100/32','100.100.100.101/32','22.22.1.0/24']
route_list_6 = ['2092::0/64', '2020::0/64', '2200::0/64','2030::0/64','4000::10/128','4000::11/128', '1212::0/64']
mlag_domain_id = '2'
