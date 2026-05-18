"""Integration tests — service-to-service API key on /v1/*."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from neugate.main import create_app
from neugate.models.evaluate import ClassifierVerdict
from neugate.models.policy import ConsumerPolicy
from neugate.services.evaluate import EvaluateService, get_evaluate_service
from neugate.settings import get_settings
from helpers import StubClassifier

pytestmark = pytest.mark.integration


@pytest.fixture
def secured_app(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("NEUGATE_API_KEY", "secret-test-key")
    get_settings.cache_clear()
    application = create_app()
    yield application
    application.dependency_overrides.clear()
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_v1_requires_api_key_when_configured(
    secured_app,
    consumer_policy: ConsumerPolicy,
) -> None:
    secured_app.dependency_overrides[get_evaluate_service] = lambda: EvaluateService(
        classifier=StubClassifier(ClassifierVerdict(is_violation=False, category="safe_domain")),
    )

    body = {
        "project_id": "test-brand",
        "message": "hello",
        "policy": consumer_policy.model_dump(),
    }
    transport = ASGITransport(app=secured_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        denied = await client.post("/v1/evaluate", json=body)
        allowed = await client.post(
            "/v1/evaluate",
            json=body,
            headers={"X-API-Key": "secret-test-key"},
        )

    assert denied.status_code == 401
    assert allowed.status_code == 200


@pytest.mark.asyncio
async def test_health_endpoints_skip_api_key(secured_app) -> None:
    transport = ASGITransport(app=secured_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        live = await client.get("/health")
        ready = await client.get("/health/ready")

    assert live.status_code == 200
    assert ready.status_code in {200, 503}
