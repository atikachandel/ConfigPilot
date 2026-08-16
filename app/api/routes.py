from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.config_loader import ConfigLoaderError, load_variables
from app.core.storage import create_deployment, get_config, get_deployment, save_config
from app.core.template_renderer import TemplateRenderError, render_config
from app.core.validator import validate_config
from app.models.schemas import (
    DeployConfigRequest,
    DeployConfigResponse,
    DeploymentStatusResponse,
    GenerateConfigRequest,
    GenerateConfigResponse,
    ValidateConfigRequest,
    ValidateConfigResponse,
)
from app.services.ansible_runner import trigger_deployment

router = APIRouter()


@router.post("/configs/generate", response_model=GenerateConfigResponse)
def generate_config(payload: GenerateConfigRequest) -> GenerateConfigResponse:
    try:
        variables = load_variables(
            payload.environment.value, payload.device_role.value, payload.overrides
        )
    except ConfigLoaderError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        rendered = render_config(
            payload.device_role.value, payload.device_name, variables
        )
    except TemplateRenderError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    config_id, file_path = save_config(
        payload.environment.value,
        payload.device_name,
        payload.device_role.value,
        rendered,
    )

    return GenerateConfigResponse(
        config_id=config_id,
        environment=payload.environment,
        device_name=payload.device_name,
        device_role=payload.device_role,
        rendered_config=rendered,
        file_path=file_path,
    )


@router.post("/configs/validate", response_model=ValidateConfigResponse)
def validate(payload: ValidateConfigRequest) -> ValidateConfigResponse:
    if payload.config_id:
        record = get_config(payload.config_id)
        if not record:
            raise HTTPException(
                status_code=404, detail=f"Unknown config_id {payload.config_id}"
            )
        raw_config = record["rendered_config"]
        device_role = record["device_role"]
    elif payload.raw_config and payload.device_role:
        raw_config = payload.raw_config
        device_role = payload.device_role.value
    else:
        raise HTTPException(
            status_code=400,
            detail="Provide either config_id, or both raw_config and device_role",
        )

    issues = validate_config(raw_config, device_role)
    has_errors = any(issue.severity == "error" for issue in issues)
    return ValidateConfigResponse(valid=not has_errors, issues=issues)


@router.post("/configs/deploy", response_model=DeployConfigResponse)
def deploy(payload: DeployConfigRequest) -> DeployConfigResponse:
    record = get_config(payload.config_id)
    if not record:
        raise HTTPException(
            status_code=404, detail=f"Unknown config_id {payload.config_id}"
        )

    if record["environment"] != payload.environment.value:
        raise HTTPException(
            status_code=400,
            detail=(
                f"config_id {payload.config_id} was generated for environment "
                f"'{record['environment']}', not '{payload.environment.value}'"
            ),
        )

    issues = validate_config(record["rendered_config"], record["device_role"])
    if any(issue.severity == "error" for issue in issues):
        raise HTTPException(
            status_code=422,
            detail="Config has validation errors; fix them before deploying. Call /configs/validate for details.",
        )

    deployment_id = create_deployment(payload.config_id, payload.dry_run)
    trigger_deployment(
        deployment_id,
        environment=payload.environment.value,
        device_name=record["device_name"],
        src_config_file=record["file_path"],
        dry_run=payload.dry_run,
    )

    return DeployConfigResponse(
        deployment_id=deployment_id,
        config_id=payload.config_id,
        status="pending",
        dry_run=payload.dry_run,
        detail="Deployment queued",
    )


@router.get("/deployments/{deployment_id}", response_model=DeploymentStatusResponse)
def deployment_status(deployment_id: str) -> DeploymentStatusResponse:
    record = get_deployment(deployment_id)
    if not record:
        raise HTTPException(
            status_code=404, detail=f"Unknown deployment_id {deployment_id}"
        )

    return DeploymentStatusResponse(
        deployment_id=deployment_id,
        status=record["status"],
        detail=record["detail"],
        log_tail=record["log_tail"],
    )
