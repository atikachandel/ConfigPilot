"""Loads and merges YAML configuration variables per environment.

Precedence (lowest -> highest): config_vars/common.yml -> config_vars/<env>/<role>.yml -> per-request overrides.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Dict

import yaml

CONFIG_VARS_ROOT = Path(__file__).resolve().parents[2] / "config_vars"


class ConfigLoaderError(Exception):
    """Raised when environment/role variable files cannot be loaded or merged."""


def _read_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except yaml.YAMLError as exc:
        raise ConfigLoaderError(f"Invalid YAML in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigLoaderError(f"Expected a mapping at top level of {path}")
    return data


def _deep_merge(base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_variables(
    environment: str, device_role: str, overrides: Dict[str, Any] | None = None
) -> Dict[str, Any]:
    """Load and merge variables for a given environment + device role.

    Raises ConfigLoaderError if the environment directory does not exist.
    """
    env_dir = CONFIG_VARS_ROOT / environment
    if not env_dir.exists():
        raise ConfigLoaderError(
            f"Unknown environment '{environment}': no directory at {env_dir}"
        )

    common = _read_yaml(CONFIG_VARS_ROOT / "common.yml")
    env_common = _read_yaml(env_dir / "common.yml")
    role_vars = _read_yaml(env_dir / f"{device_role}.yml")

    merged = _deep_merge(common, env_common)
    merged = _deep_merge(merged, role_vars)
    if overrides:
        merged = _deep_merge(merged, overrides)
    return merged
