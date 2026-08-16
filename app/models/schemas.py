"""Pydantic models used across the ConfigPilot API."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class Environment(str, Enum):
    dev = "dev"
    staging = "staging"
    prod = "prod"


class DeviceRole(str, Enum):
    router = "router"
    switch = "switch"
    firewall = "firewall"


class GenerateConfigRequest(BaseModel):
    environment: Environment
    device_name: str = Field(..., min_length=1, max_length=64)
    device_role: DeviceRole
    overrides: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("device_name")
    @classmethod
    def device_name_must_be_hostname_safe(cls, v: str) -> str:
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError(
                "device_name may only contain letters, digits, hyphens and underscores"
            )
        return v


class GenerateConfigResponse(BaseModel):
    config_id: str
    environment: Environment
    device_name: str
    device_role: DeviceRole
    rendered_config: str
    file_path: str


class ValidationIssue(BaseModel):
    severity: str  # "error" | "warning"
    message: str
    line: Optional[int] = None


class ValidateConfigRequest(BaseModel):
    config_id: Optional[str] = None
    raw_config: Optional[str] = None
    device_role: Optional[DeviceRole] = None

    @field_validator("raw_config")
    @classmethod
    def either_id_or_raw(cls, v, info):
        return v


class ValidateConfigResponse(BaseModel):
    valid: bool
    issues: List[ValidationIssue]


class DeployConfigRequest(BaseModel):
    config_id: str
    environment: Environment
    dry_run: bool = False


class DeploymentStatus(str, Enum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class DeployConfigResponse(BaseModel):
    deployment_id: str
    config_id: str
    status: DeploymentStatus
    dry_run: bool
    detail: Optional[str] = None


class DeploymentStatusResponse(BaseModel):
    deployment_id: str
    status: DeploymentStatus
    detail: Optional[str] = None
    log_tail: List[str] = Field(default_factory=list)
