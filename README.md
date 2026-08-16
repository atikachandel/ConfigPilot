# ConfigPilot

A network configuration automation platform: generate environment-specific
device configs from templates + YAML, validate them, and deploy them through
Ansible — all behind a REST API.

Built to back up the "reduces repetitive provisioning and configuration
errors across development, staging, and production" line on a resume with
actual working code, not just a description.

## Why it exists

Manually hand-writing router/switch/firewall configs per environment is slow
and error-prone — a typo in a VLAN ID or a missing routing block doesn't
show up until something breaks in production. ConfigPilot turns that into a
pipeline: **define variables once per environment → render configs from
templates → validate structurally → deploy via Ansible**, with every step
exposed as an API call so it can be scripted, wired into CI/CD, or called
from a chatops bot.

## Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐     ┌──────────────┐
│  REST API   │────▶│  Config Loader    │────▶│ Jinja2 Renderer │────▶│  Validator   │
│  (FastAPI)  │     │ (YAML, per-env)   │     │ (device role)   │     │ (structural) │
└─────────────┘     └──────────────────┘     └─────────────────┘     └──────┬───────┘
                                                                              │
                                                                              ▼
                                                                    ┌──────────────────┐
                                                                    │  Ansible Runner   │
                                                                    │ (ansible-playbook)│
                                                                    └────────┬──────────┘
                                                                             │
                                                                             ▼
                                                                 ┌────────────────────────┐
                                                                 │  Target device / mock   │
                                                                 │  running-config store   │
                                                                 └────────────────────────┘
```

**Variable precedence** (lowest → highest): `config_vars/common.yml` →
`config_vars/<env>/common.yml` → `config_vars/<env>/<role>.yml` → per-request
overrides in the API call.

## Running it locally (VS Code)

1. Clone the repo and open the folder in VS Code.
2. Create a virtualenv and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # .venv\Scripts\activate on Windows
   pip install -r requirements-dev.txt
   ```
3. In VS Code, select the `.venv` interpreter (`Ctrl+Shift+P` → *Python: Select Interpreter*).
4. Run the API:
   ```bash
   uvicorn app.main:app --reload
   ```
5. Open `http://127.0.0.1:8000/docs` for interactive Swagger docs, or use the
   `curl` examples below.
6. Run the tests from the VS Code Testing panel (auto-discovered via
   `pytest`), or:
   ```bash
   pytest tests/ -v
   ```

### Running with Docker instead

```bash
docker compose up --build
```

## API walkthrough

**1. Generate a config**
```bash
curl -X POST http://127.0.0.1:8000/configs/generate \
  -H "Content-Type: application/json" \
  -d '{"environment": "dev", "device_name": "edge-router-01", "device_role": "router"}'
```
Returns a `config_id`, the rendered config text, and the file path it was
written to under `generated_configs/`.

**2. Validate it**
```bash
curl -X POST http://127.0.0.1:8000/configs/validate \
  -H "Content-Type: application/json" \
  -d '{"config_id": "<config_id from step 1>"}'
```
You can also validate raw config text directly (`raw_config` +
`device_role`) without generating it first — useful for checking a
hand-written config.

**3. Deploy it**
```bash
curl -X POST http://127.0.0.1:8000/configs/deploy \
  -H "Content-Type: application/json" \
  -d '{"config_id": "<config_id>", "environment": "dev", "dry_run": false}'
```
This runs the real `ansible-playbook` command against `ansible/playbooks/deploy_config.yml`
in a background thread and returns a `deployment_id` immediately.
Deployment is blocked automatically if the config has validation errors.

**4. Poll deployment status**
```bash
curl http://127.0.0.1:8000/deployments/<deployment_id>
```
Returns `pending` → `running` → `succeeded`/`failed`, plus the tail of the
Ansible run log.

## How "deployment" works without real hardware

Every environment's inventory group in `ansible/inventory/hosts.yml` targets
`localhost` with `ansible_connection: local`, and the `deploy_config` role
writes the rendered config into `mock_devices/<env>/<device>.conf` — this
file stands in for the device's running-config store. That keeps the whole
pipeline runnable in CI and on a laptop with zero lab hardware.

To point this at real devices, the only thing that changes is the
inventory: swap the `local` connection for `ansible_connection: network_cli`
(or `netconf`) with real host/credentials, and change the `deploy_config`
role's final task from a `copy` to whatever module fits the vendor (e.g.
`ios_config`, `junos_config`, or a `netmiko`/`napalm` call). The
generate → validate → deploy API contract doesn't change.

## Project layout

```
app/
  api/routes.py          REST endpoints
  core/config_loader.py  YAML variable loading + deep-merge
  core/template_renderer.py  Jinja2 rendering
  core/validator.py      structural + role-specific config validation
  core/storage.py        in-memory + on-disk config/deployment store
  services/ansible_runner.py  invokes ansible-playbook as a subprocess
  models/schemas.py      Pydantic request/response models
templates/                Jinja2 templates: router.j2, switch.j2, firewall.j2
config_vars/               per-environment YAML variables (dev/staging/prod)
ansible/
  playbooks/deploy_config.yml
  roles/deploy_config/    the actual deploy task logic
  inventory/hosts.yml
tests/                     pytest suite (26 tests: unit + API)
docker/Dockerfile
docker-compose.yml
.github/workflows/ci.yml   lint, format check, tests, Ansible syntax check, E2E smoke test, Docker build
```

## Tests

```bash
pytest tests/ -v          # 26 tests: config loading, rendering, validation, full API flows
black --check app tests   # formatting
flake8 app tests --max-line-length=120 --extend-ignore=E203
```

All of the above run in CI on every push/PR via `.github/workflows/ci.yml`,
including a real end-to-end smoke test that boots the API and exercises
generate → validate → deploy(dry-run) against it.

## Stack

Python, FastAPI, Jinja2, PyYAML, Pydantic, Ansible, Docker, pytest, GitHub Actions.
