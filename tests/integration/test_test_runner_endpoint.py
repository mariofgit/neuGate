"""Integration tests — POST /v1/test-runner (batch metrics + concurrency, LLM mocked)."""

from __future__ import annotations

import pytest

from neugate.models.evaluate import ClassifierVerdict
from neugate.models.policy import ConsumerPolicy
from neugate.services.test_runner import BatchRunnerService, get_batch_runner_service
from helpers import ConcurrencyTrackingClassifier, MappingStubClassifier

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_test_runner_returns_accuracy_metrics(
    app,
    api_client,
    settings,
    consumer_policy: ConsumerPolicy,
    test_brand_id: str,
) -> None:
    classifier = MappingStubClassifier(
        {
            "safe question": ClassifierVerdict(is_violation=False, category="safe_domain"),
            "unsafe question": ClassifierVerdict(is_violation=True, category="illegal"),
            "misclassified": ClassifierVerdict(is_violation=True, category="off_topic"),
        }
    )
    service = BatchRunnerService(classifier=classifier, settings=settings, agentic_gate=None)
    app.dependency_overrides[get_batch_runner_service] = lambda: service

    response = await api_client.post(
        "/v1/test-runner",
        json={
            "project_id": test_brand_id,
            "policy": consumer_policy.model_dump(),
            "test_dataset": [
                {"prompt": "safe question", "expected_category": "safe_domain"},
                {"prompt": "unsafe question", "expected_category": "illegal"},
                {"prompt": "misclassified", "expected_category": "safe_domain"},
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["project_id"] == test_brand_id
    assert body["total_tests"] == 3
    assert body["passed"] == 2
    assert body["failed"] == 1
    assert body["accuracy_rate"] == pytest.approx(2 / 3, rel=1e-4)
    assert len(body["results"]) == 3
    assert body["results"][0]["test_status"] == "PASSED"
    assert body["results"][2]["test_status"] == "FAILED"
    assert classifier.call_count == 3


@pytest.mark.asyncio
async def test_test_runner_respects_concurrency_limit(
    app,
    api_client,
    settings,
    consumer_policy: ConsumerPolicy,
    test_brand_id: str,
) -> None:
    assert settings.test_runner_concurrency == 5

    classifier = ConcurrencyTrackingClassifier(delay_seconds=0.04)
    service = BatchRunnerService(classifier=classifier, settings=settings, agentic_gate=None)
    app.dependency_overrides[get_batch_runner_service] = lambda: service

    dataset = [
        {"prompt": f"prompt-{index}", "expected_category": "safe_domain"}
        for index in range(12)
    ]

    response = await api_client.post(
        "/v1/test-runner",
        json={
            "project_id": test_brand_id,
            "policy": consumer_policy.model_dump(),
            "test_dataset": dataset,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total_tests"] == 12
    assert body["passed"] == 12
    assert body["failed"] == 0
    assert body["accuracy_rate"] == 1.0
    assert classifier.call_count == 12
    assert classifier.max_in_flight <= settings.test_runner_concurrency
    assert classifier.max_in_flight > 1


@pytest.mark.asyncio
async def test_test_runner_rejects_unknown_expected_category(
    app,
    api_client,
    settings,
    consumer_policy: ConsumerPolicy,
    test_brand_id: str,
) -> None:
    service = BatchRunnerService(settings=settings, agentic_gate=None)
    app.dependency_overrides[get_batch_runner_service] = lambda: service

    response = await api_client.post(
        "/v1/test-runner",
        json={
            "project_id": test_brand_id,
            "policy": consumer_policy.model_dump(),
            "test_dataset": [
                {"prompt": "hello", "expected_category": "not_a_real_category"},
            ],
        },
    )

    assert response.status_code == 422
