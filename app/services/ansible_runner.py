"""Wraps `ansible-playbook` so the API can trigger real deployments.

Runs synchronously in a background thread per request; for a portfolio-scale
project this is simpler and more debuggable than pulling in Celery/RQ, and
the deployment record in storage.py already gives callers a status/log
endpoint to poll regardless of how the job is executed.
"""

from __future__ import annotations

import json
import subprocess
import threading
from pathlib import Path

from app.core import storage

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PLAYBOOK = PROJECT_ROOT / "ansible" / "playbooks" / "deploy_config.yml"
INVENTORY = PROJECT_ROOT / "ansible" / "inventory" / "hosts.yml"


def _run(
    deployment_id: str,
    environment: str,
    device_name: str,
    src_config_file: str,
    dry_run: bool,
) -> None:
    storage.update_deployment(deployment_id, status="running")

    # Pass extra-vars as JSON rather than space-separated key=value pairs so
    # dry_run is typed as a real boolean, not the literal string "false"
    # (which Jinja treats as truthy and silently flips every deploy into a
    # dry run).
    extra_vars = json.dumps(
        {
            "target_env": environment,
            "device_name": device_name,
            "src_config_file": src_config_file,
            "dry_run": dry_run,
        }
    )
    cmd = [
        "ansible-playbook",
        str(PLAYBOOK),
        "-i",
        str(INVENTORY),
        "--extra-vars",
        extra_vars,
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except FileNotFoundError:
        storage.update_deployment(
            deployment_id,
            status="failed",
            detail="ansible-playbook is not installed in this environment",
        )
        return
    except subprocess.TimeoutExpired:
        storage.update_deployment(
            deployment_id, status="failed", detail="Deployment timed out after 120s"
        )
        return

    log_lines = (result.stdout + result.stderr).splitlines()
    tail = log_lines[-40:]

    if result.returncode == 0:
        storage.update_deployment(
            deployment_id,
            status="succeeded",
            detail="Playbook completed",
            log_tail=tail,
        )
    else:
        storage.update_deployment(
            deployment_id,
            status="failed",
            detail=f"ansible-playbook exited with code {result.returncode}",
            log_tail=tail,
        )


def trigger_deployment(
    deployment_id: str,
    environment: str,
    device_name: str,
    src_config_file: str,
    dry_run: bool,
) -> None:
    """Kick off the playbook run in a background thread and return immediately."""
    thread = threading.Thread(
        target=_run,
        args=(deployment_id, environment, device_name, src_config_file, dry_run),
        daemon=True,
    )
    thread.start()
