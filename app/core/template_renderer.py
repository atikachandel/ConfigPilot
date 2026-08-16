"""Renders device configuration files from Jinja2 templates."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from jinja2 import Environment as JinjaEnvironment
from jinja2 import FileSystemLoader, StrictUndefined, TemplateError

TEMPLATES_ROOT = Path(__file__).resolve().parents[2] / "templates"

_jinja_env = JinjaEnvironment(
    loader=FileSystemLoader(str(TEMPLATES_ROOT)),
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)


class TemplateRenderError(Exception):
    """Raised when a template is missing or fails to render (e.g. undefined variable)."""


def render_config(device_role: str, device_name: str, variables: Dict[str, Any]) -> str:
    template_name = f"{device_role}.j2"
    try:
        template = _jinja_env.get_template(template_name)
    except Exception as exc:  # jinja2.TemplateNotFound etc.
        raise TemplateRenderError(
            f"No template found for role '{device_role}' ({template_name})"
        ) from exc

    context = {"device_name": device_name, **variables}
    try:
        return template.render(**context)
    except TemplateError as exc:
        raise TemplateRenderError(
            f"Failed to render template for '{device_name}': {exc}"
        ) from exc
