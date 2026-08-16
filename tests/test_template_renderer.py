import pytest

from app.core.config_loader import load_variables
from app.core.template_renderer import TemplateRenderError, render_config


def test_render_router_config_contains_hostname_and_interfaces():
    variables = load_variables("dev", "router")
    rendered = render_config("router", "edge-router-01", variables)
    assert "hostname edge-router-01" in rendered
    assert "interface GigabitEthernet0/0" in rendered
    assert "router ospf" in rendered


def test_render_switch_config_contains_vlans():
    variables = load_variables("staging", "switch")
    rendered = render_config("switch", "access-sw-01", variables)
    assert "hostname access-sw-01" in rendered
    assert "vlan 10" in rendered


def test_render_firewall_config_ends_with_deny_all():
    variables = load_variables("prod", "firewall")
    rendered = render_config("firewall", "edge-fw-01", variables)
    assert "rule deny any any" in rendered


def test_missing_template_raises():
    with pytest.raises(TemplateRenderError):
        render_config("load_balancer", "lb-01", {})


def test_missing_required_variable_raises():
    # 'interfaces' is required by router.j2 but not supplied here.
    with pytest.raises(TemplateRenderError):
        render_config(
            "router",
            "edge-router-02",
            {"routing": {"protocol": "ospf", "networks": []}},
        )
