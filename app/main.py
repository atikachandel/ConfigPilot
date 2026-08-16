from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(
    title="ConfigPilot",
    description=(
        "Network configuration automation platform: validate and generate "
        "environment-specific device configs, then deploy them through Ansible."
    ),
    version="1.0.0",
)

app.include_router(router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
