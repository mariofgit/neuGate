"""Unit tests — BatchRunnerService scoring logic (no HTTP)."""

from __future__ import annotations

import pytest

from neugate.models.evaluate import ClassifierVerdict
from neugate.models.policy import ConsumerPolicy
from neugate.models.test_runner import BatchRunRequest, DatasetCase
from neugate.services.test_runner import BatchRunValidationError, BatchRunnerService
from helpers import MappingStubClassifier

pytestmark = pytest.mark.unit


def test_case_passed_rules() -> None:
    assert BatchRunnerService._case_passed(
        "safe_domain",
        ClassifierVerdict(is_violation=False, category="safe_domain"),
    )
    assert BatchRunnerService._case_passed(
        "illegal",
        ClassifierVerdict(is_violation=True, category="illegal"),
    )
    assert not BatchRunnerService._case_passed(
        "safe_domain",
        ClassifierVerdict(is_violation=True, category="off_topic"),
    )


@pytest.mark.asyncio
async def test_run_batch_scores_passed_and_failed(
    settings,
    consumer_policy: ConsumerPolicy,
    test_brand_id: str,
) -> None:
    classifier = MappingStubClassifier(
        {
            "safe": ClassifierVerdict(is_violation=False, category="safe_domain"),
            "bad": ClassifierVerdict(is_violation=True, category="illegal"),
        }
    )
    service = BatchRunnerService(classifier=classifier, settings=settings, agentic_gate=None)

    response = await service.run(
        BatchRunRequest(
            project_id=test_brand_id,
            policy=consumer_policy,
            test_dataset=[
                DatasetCase(prompt="safe", expected_category="safe_domain"),
                DatasetCase(prompt="bad", expected_category="illegal"),
                DatasetCase(prompt="bad", expected_category="safe_domain"),
            ],
        )
    )

    assert response.total_tests == 3
    assert response.passed == 2
    assert response.failed == 1
    assert response.accuracy_rate == pytest.approx(2 / 3, rel=1e-4)


@pytest.mark.asyncio
async def test_rejects_dataset_larger_than_max_cases(
    settings,
    consumer_policy: ConsumerPolicy,
    test_brand_id: str,
) -> None:
    settings = settings.model_copy(update={"test_runner_max_cases": 2})
    service = BatchRunnerService(settings=settings, agentic_gate=None)

    with pytest.raises(BatchRunValidationError, match="exceeds maximum"):
        await service.run(
            BatchRunRequest(
                project_id=test_brand_id,
                policy=consumer_policy,
                test_dataset=[
                    DatasetCase(prompt="a", expected_category="safe_domain"),
                    DatasetCase(prompt="b", expected_category="safe_domain"),
                    DatasetCase(prompt="c", expected_category="safe_domain"),
                ],
            )
        )
