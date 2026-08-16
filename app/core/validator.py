"""Validates rendered network device configurations.

Two layers of validation are performed:
1. Structural rules that apply to every device (no blank hostname, no
   duplicated interface blocks, line length sanity, etc.)
2. Role-specific rules (e.g. routers must define at least one routing
   protocol block, firewalls must end with an explicit deny rule).

This is intentionally implemented as plain Python rather than a network
vendor's real syntax checker, since ConfigPilot is vendor-agnostic and
targets a generic, human-readable config DSL (see templates/).
"""

from __future__ import annotations

import re
from typing import List

from app.models.schemas import ValidationIssue

_HOSTNAME_RE = re.compile(r"^hostname\s+\S+", re.MULTILINE)
_INTERFACE_RE = re.compile(r"^interface\s+(\S+)", re.MULTILINE)
_MAX_LINE_LENGTH = 200


def _common_checks(rendered_config: str) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []
    lines = rendered_config.splitlines()

    if not rendered_config.strip():
        issues.append(
            ValidationIssue(severity="error", message="Rendered config is empty")
        )
        return issues

    if not _HOSTNAME_RE.search(rendered_config):
        issues.append(
            ValidationIssue(severity="error", message="Missing 'hostname' declaration")
        )

    interfaces = _INTERFACE_RE.findall(rendered_config)
    seen = set()
    for name in interfaces:
        if name in seen:
            issues.append(
                ValidationIssue(
                    severity="error", message=f"Duplicate interface block: {name}"
                )
            )
        seen.add(name)

    for i, line in enumerate(lines, start=1):
        if len(line) > _MAX_LINE_LENGTH:
            issues.append(
                ValidationIssue(
                    severity="warning",
                    message=f"Line exceeds {_MAX_LINE_LENGTH} characters",
                    line=i,
                )
            )
        if line != line.rstrip():
            issues.append(
                ValidationIssue(
                    severity="warning", message="Trailing whitespace", line=i
                )
            )

    return issues


def _role_checks(rendered_config: str, device_role: str) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []

    if device_role == "router":
        if not re.search(r"^router\s+\w+", rendered_config, re.MULTILINE):
            issues.append(
                ValidationIssue(
                    severity="error",
                    message="Router config must define a routing protocol block",
                )
            )

    elif device_role == "firewall":
        if not re.search(
            r"^rule\s+deny\s+any\s+any\s*$", rendered_config, re.MULTILINE
        ):
            issues.append(
                ValidationIssue(
                    severity="error",
                    message="Firewall config must end with an explicit 'rule deny any any'",
                )
            )

    elif device_role == "switch":
        if not re.search(r"^vlan\s+\d+", rendered_config, re.MULTILINE):
            issues.append(
                ValidationIssue(
                    severity="warning", message="Switch config defines no VLANs"
                )
            )

    return issues


def validate_config(rendered_config: str, device_role: str) -> List[ValidationIssue]:
    return _common_checks(rendered_config) + _role_checks(rendered_config, device_role)
