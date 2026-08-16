from app.core.validator import validate_config


VALID_ROUTER_CONFIG = """hostname edge-router-01
interface GigabitEthernet0/0
 ip address 10.10.1.1 255.255.255.0
router ospf
 network 10.10.0.0/16 area 0
"""

VALID_FIREWALL_CONFIG = """hostname edge-fw-01
zone inside
 interfaces eth0
rule allow 10.10.0.0/16 any https
rule deny any any
"""


def test_valid_router_config_has_no_errors():
    issues = validate_config(VALID_ROUTER_CONFIG, "router")
    assert not any(i.severity == "error" for i in issues)


def test_router_missing_routing_block_is_error():
    config = "hostname edge-router-01\ninterface Gi0/0\n ip address 10.10.1.1 255.255.255.0\n"
    issues = validate_config(config, "router")
    assert any("routing protocol" in i.message for i in issues)


def test_missing_hostname_is_error():
    config = "interface Gi0/0\n ip address 10.10.1.1 255.255.255.0\n"
    issues = validate_config(config, "router")
    messages = [i.message for i in issues]
    assert any("hostname" in m.lower() for m in messages)


def test_duplicate_interface_is_error():
    config = (
        "hostname r1\n"
        "interface Gi0/0\n ip address 10.10.1.1 255.255.255.0\n"
        "interface Gi0/0\n ip address 10.10.1.2 255.255.255.0\n"
        "router ospf\n network 10.10.0.0/16 area 0\n"
    )
    issues = validate_config(config, "router")
    assert any("Duplicate interface" in i.message for i in issues)


def test_firewall_requires_explicit_deny_all():
    config = "hostname fw1\nrule allow 10.0.0.0/8 any https\n"
    issues = validate_config(config, "firewall")
    assert any("deny any any" in i.message for i in issues)


def test_valid_firewall_config_has_no_errors():
    issues = validate_config(VALID_FIREWALL_CONFIG, "firewall")
    assert not any(i.severity == "error" for i in issues)


def test_switch_with_no_vlans_is_warning_not_error():
    config = "hostname sw1\ninterface Gi1/0/1\n switchport mode access\n"
    issues = validate_config(config, "switch")
    vlan_issues = [i for i in issues if "VLAN" in i.message]
    assert vlan_issues and vlan_issues[0].severity == "warning"


def test_empty_config_is_error():
    issues = validate_config("", "router")
    assert any("empty" in i.message.lower() for i in issues)
