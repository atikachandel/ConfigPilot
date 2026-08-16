"""Lightweight storage for generated configs and deployment state.

An in-memory dict is enough for a demo/portfolio-scale API (and keeps the
project dependency-free), but every generated config is also persisted to
disk under generated_configs/ so Ansible can pick it up as a real file for
the deploy step. Swap `_CONFIGS`/`_DEPLOYMENTS` for a database-backed
implementation if this is ever run beyond a single process.
"""

from __future__ import annotations

import threading
import uuid
from pathlib import Path
from typing import Dict, Optional

GENERATED_CONFIGS_DIR = Path(__file__).resolve().parents[2] / "generated_configs"
GENERATED_CONFIGS_DIR.mkdir(exist_ok=True)

_lock = threading.Lock()
_CONFIGS: Dict[str, dict] = {}
_DEPLOYMENTS: Dict[str, dict] = {}


def save_config(
    environment: str, device_name: str, device_role: str, rendered_config: str
) -> tuple[str, str]:
    config_id = str(uuid.uuid4())
    env_dir = GENERATED_CONFIGS_DIR / environment
    env_dir.mkdir(exist_ok=True)
    file_path = env_dir / f"{device_name}-{config_id[:8]}.conf"
    file_path.write_text(rendered_config, encoding="utf-8")

    with _lock:
        _CONFIGS[config_id] = {
            "environment": environment,
            "device_name": device_name,
            "device_role": device_role,
            "rendered_config": rendered_config,
            "file_path": str(file_path),
        }
    return config_id, str(file_path)


def get_config(config_id: str) -> Optional[dict]:
    with _lock:
        return _CONFIGS.get(config_id)


def create_deployment(config_id: str, dry_run: bool) -> str:
    deployment_id = str(uuid.uuid4())
    with _lock:
        _DEPLOYMENTS[deployment_id] = {
            "config_id": config_id,
            "status": "pending",
            "dry_run": dry_run,
            "detail": None,
            "log_tail": [],
        }
    return deployment_id


def update_deployment(deployment_id: str, **fields) -> None:
    with _lock:
        if deployment_id in _DEPLOYMENTS:
            _DEPLOYMENTS[deployment_id].update(fields)


def get_deployment(deployment_id: str) -> Optional[dict]:
    with _lock:
        return _DEPLOYMENTS.get(deployment_id)
