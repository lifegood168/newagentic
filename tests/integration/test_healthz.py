from pathlib import Path

from fastapi.testclient import TestClient


def test_healthz_and_templates(isolated_env: Path) -> None:
    demo_yaml = """
schema_version: "1.0"
code: demo
description: test
system_prompt: hello
tools: []
model:
  name: gpt-4o-mini
"""
    (isolated_env / "agents" / "demo.yaml").write_text(demo_yaml)

    from app.api.main import app

    with TestClient(app) as client:
        r = client.get("/healthz")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}

        r = client.get("/readyz")
        assert r.status_code == 200

        r = client.get("/templates")
        assert r.status_code == 200
        templates = r.json()
        assert any(t["code"] == "demo" for t in templates)
