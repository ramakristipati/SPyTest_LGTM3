"""
PDDF BMC Feature test script.
Author : Prudvi Mangadu (prudvi.mangadu@broadcom.com)
Reference Topology : D1
"""

import pytest
import pddf_lib as pddf_lib


@pytest.fixture(scope="module", autouse=True)
def pddf_bmc_module_hooks(request):
    pddf_lib.init_vars()
    pddf_lib.initialize_variables('PDDF_BMC')
    pddf_lib.pddf_module_prolog()
    yield
    pddf_lib.pddf_module_epilog()


@pytest.fixture(scope="function", autouse=True)
def pddf_bmc_func_hooks(request):
    yield


@pytest.mark.pddf_bmc
def test_ft_bmc_show_platform_syseeprom():
    """
    Verify the output of 'show platform syseeprom' command.
    """
    pddf_lib.lib_ft_show_platform_syseeprom()


@pytest.mark.pddf_bmc
def test_ft_bmc_decode_syseeprom():
    """
    Verify the output of "decode-syseeprom" command.
    """
    pddf_lib.lib_ft_decode_syseeprom()


@pytest.mark.pddf_bmc
def test_ft_pddf_bmc_fan_status_util():
    """
    Verify the output of 'show platform fanstatus' command.
    Verify the output of "pddf_fanutil" command.
    """
    pddf_lib.lib_ft_pddf_fan_status_util()


@pytest.mark.pddf_bmc
def test_ft_pddf_bmc_psu_summary_util():
    """
    Verify the output of "psuutil" command.
    Verify the output of 'show platform psusummary' command.
    Verify the output of "pddf_psuutil" command.
    """
    pddf_lib.lib_ft_pddf_psu_summary_util()


@pytest.mark.skip("Support is not yet added hence skipping this test.")
@pytest.mark.pddf_bmc
def test_ft_pddf_bmc_show_sfputil():
    """
    Verify the output of "sfputil" command.
    Verify the output of "show interface transceiver eeprom" command.
    Verify the output of "show interface transceiver presence" command.
    """
    pddf_lib.lib_ft_pddf_show_sfputil()


@pytest.mark.skip("Support is not yet added hence skipping this test.")
@pytest.mark.pddf_bmc
def test_ft_pddf_bmc_led_util():
    """
    Verify the output of "pddf_ledutil" command.
    """
    pddf_lib.lib_ft_pddf_led_util()


@pytest.mark.pddf_bmc
def test_ft_pddf_bmc_thermal_util():
    """
    Verify the output of "pddf_thermalutil" command.
    """
    pddf_lib.lib_ft_pddf_thermal_util()


@pytest.mark.pddf_bmc
def test_ft_pddf_bmc_verify_sys_environment():
    """
    Verify the output of "show environment" command.
    """
    pddf_lib.lib_ft_pddf_verify_sys_environment()


@pytest.mark.pddf_bmc
def test_ft_pddf_bmc_debug_command():
    """
    Verify that system should be stable after executing all PDDF_BMC debug commands.
    """
    pddf_lib.lib_ft_pddf_debug_command()


@pytest.mark.pddf_bmc
def test_ft_pddf_bmc_reboot_cause():
    """
    Verify the output of "show reboot-cause" command.
    """
    pddf_lib.lib_ft_pddf_reboot_cause()
