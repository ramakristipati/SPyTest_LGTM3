from spytest import st

def init(dut):
    st.create_init_config_db(dut)

def remove_vlan_1(dut, phase):
    if not st.is_feature_supported("sai-removes-vlan-1", dut):
        st.banner("Remove VLAN-1 {}".format(phase), dut=dut)
        import apis.common.asic as asicapi
        asicapi.remove_vlan_1(dut)
        asicapi.dump_vlan(dut)

def post_reboot(dut, is_upgrade=False):
    remove_vlan_1(dut, "post reboot")

def extend(dut):
    st.log("Extend base config if needed", dut=dut)
    if not st.is_feature_supported("nat-default-enabled", dut):
        st.config(dut, "config feature state nat enabled")
    if not st.is_feature_supported("sflow-default-enabled", dut):
        st.config(dut, "config feature state sflow enabled")
    #st.config(dut, "configure lldp status disabled", type='lldp')
    remove_vlan_1(dut, "base config")

