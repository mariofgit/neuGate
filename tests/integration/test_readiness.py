"""Integration tests — GET /health/ready."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from neugate.services.config_loader import ConfigLoader, get_config_loader
from neugate.settings import Settings, get_settings

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_ready_when_openai_key_present(app, settings, config_loader) -> None:
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_config_loader] = lambda: config_loader

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["checks"]["openai_api_key"] is True
    assert body["checks"]["agentic_index_loaded"] is True
    assert "test-brand" in body["loadable_projects"]


@pytest.mark.asyncio
async def test_not_ready_without_openai_key(app, settings, config_loader) -> None:
    settings = settings.model_copy(update={"openai_api_key": ""})
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_config_loader] = lambda: config_loader

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready"
    assert body["checks"]["openai_api_key"] is False
    assert any("OPENAI_API_KEY" in detail for detail in body["details"])


@pytest.mark.asyncio
async def test_ready_without_legacy_project_json(app, settings, config_dir) -> None:
    empty_projects = config_dir / "projects"
    for path in empty_projects.glob("*.json"):
        path.unlink()

    settings = Settings.model_validate(
        {
            "openai_api_key": "test-key",
            "config_dir": str(empty_projects),
            "schema_path": str(config_dir / "schema" / "neugate-schema.json"),
            "NEUGATE_AGENTIC_ENABLED": False,
        }
    )
    loader = ConfigLoader(settings=settings)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_config_loader] = lambda: loader

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["loadable_projects"] == []
