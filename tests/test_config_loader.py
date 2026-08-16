import pytest

from app.core.config_loader import ConfigLoaderError, load_variables


def test_load_variables_merges_common_and_role():
    variables = load_variables("dev", "router")
    assert variables["snmp_community"] == "configpilot-ro"  # from common.yml
    assert variables["environment"] == "dev"  # from dev/common.yml
    assert variables["routing"]["protocol"] == "ospf"  # from dev/router.yml


def test_load_variables_applies_overrides():
    variables = load_variables(
        "dev", "router", overrides={"routing": {"protocol": "eigrp"}}
    )
    assert variables["routing"]["protocol"] == "eigrp"
    # unrelated nested keys must survive the deep merge
    assert variables["routing"]["networks"] == ["10.10.0.0/16 area 0"]


def test_unknown_environment_raises():
    with pytest.raises(ConfigLoaderError):
        load_variables("qa", "router")


def test_prod_uses_bgp_not_ospf():
    variables = load_variables("prod", "router")
    assert variables["routing"]["protocol"] == "bgp"
