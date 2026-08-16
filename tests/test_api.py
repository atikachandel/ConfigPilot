from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_generate_config_success():
    resp = client.post(
        "/configs/generate",
        json={
            "environment": "dev",
            "device_name": "test-router-01",
            "device_role": "router",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["device_name"] == "test-router-01"
    assert "hostname test-router-01" in body["rendered_config"]
    assert body["config_id"]


def test_generate_config_invalid_device_name():
    resp = client.post(
        "/configs/generate",
        json={
            "environment": "dev",
            "device_name": "bad name!",
            "device_role": "router",
        },
    )
    assert resp.status_code == 422  # pydantic validation error


def test_generate_then_validate_by_id():
    gen = client.post(
        "/configs/generate",
        json={
            "environment": "dev",
            "device_name": "test-router-02",
            "device_role": "router",
        },
    )
    config_id = gen.json()["config_id"]

    resp = client.post("/configs/validate", json={"config_id": config_id})
    assert resp.status_code == 200
    assert resp.json()["valid"] is True


def test_validate_unknown_config_id_returns_404():
    resp = client.post("/configs/validate", json={"config_id": "does-not-exist"})
    assert resp.status_code == 404


def test_validate_raw_config_with_errors():
    resp = client.post(
        "/configs/validate",
        json={"raw_config": "interface Gi0/0\n", "device_role": "router"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is False
    assert len(body["issues"]) > 0


def test_deploy_requires_matching_environment():
    gen = client.post(
        "/configs/generate",
        json={
            "environment": "dev",
            "device_name": "test-router-03",
            "device_role": "router",
        },
    )
    config_id = gen.json()["config_id"]

    resp = client.post(
        "/configs/deploy",
        json={"config_id": config_id, "environment": "prod", "dry_run": True},
    )
    assert resp.status_code == 400


def test_deploy_queues_dry_run_deployment():
    gen = client.post(
        "/configs/generate",
        json={
            "environment": "dev",
            "device_name": "test-router-04",
            "device_role": "router",
        },
    )
    config_id = gen.json()["config_id"]

    resp = client.post(
        "/configs/deploy",
        json={"config_id": config_id, "environment": "dev", "dry_run": True},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["config_id"] == config_id
    assert body["dry_run"] is True

    status_resp = client.get(f"/deployments/{body['deployment_id']}")
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] in {"pending", "running", "succeeded", "failed"}


def test_deployment_status_unknown_id_returns_404():
    resp = client.get("/deployments/does-not-exist")
    assert resp.status_code == 404
