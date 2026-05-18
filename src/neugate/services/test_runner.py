from __future__ import annotations

import asyncio
import logging
from typing import Literal

from neugate.agentic.bootstrap import get_agentic_gate
from neugate.agentic.semantic_gate import AgenticSemanticGate
from neugate.models.evaluate import ClassifierVerdict
from neugate.models.policy import ConsumerPolicy
from neugate.models.test_runner import (
    BatchRunRequest,
    BatchRunResponse,
    CaseRunResult,
    DatasetCase,
)
from neugate.services.classifier import ClassifierService, get_classifier
from neugate.settings import Settings, get_settings

logger = logging.getLogger(__name__)


class BatchRunValidationError(ValueError):
    pass


class BatchRunnerService:
    def __init__(
        self,
        classifier: ClassifierService | None = None,
        settings: Settings | None = None,
        agentic_gate: AgenticSemanticGate | None = None,
    ) -> None:
        self._classifier = classifier or get_classifier()
        self._settings = settings or get_settings()
        self._agentic_gate = agentic_gate

    def _resolve_agentic_gate(self) -> AgenticSemanticGate | None:
        if self._agentic_gate is not None:
            return self._agentic_gate
        if not self._settings.agentic_enabled:
            return None
        return get_agentic_gate()

    def _validate_dataset(self, policy: ConsumerPolicy, dataset: list[DatasetCase]) -> None:
        max_cases = self._settings.test_runner_max_cases
        if len(dataset) > max_cases:
            raise BatchRunValidationError(
                f"test_dataset exceeds maximum of {max_cases} items",
            )

        allowed = {"safe_domain", *policy.all_block_labels(), *self._agentic_categories()}
        invalid = {item.expected_category for item in dataset if item.expected_category not in allowed}
        if invalid:
            raise BatchRunValidationError(
                f"expected_category values not allowed for this policy: {sorted(invalid)}. "
                f"Allowed: {sorted(allowed)}",
            )

    def _agentic_categories(self) -> set[str]:
        gate = self._resolve_agentic_gate()
        if gate is None:
            return set()
        return {entry.category for entry in gate.index.entries}

    @staticmethod
    def _case_passed(expected_category: str, verdict: ClassifierVerdict) -> bool:
        if expected_category == "safe_domain":
            return not verdict.is_violation and verdict.category == "safe_domain"
        return verdict.is_violation and verdict.category == expected_category

    async def _classify_case(
        self,
        case: DatasetCase,
        policy: ConsumerPolicy,
        project_id: str,
        semaphore: asyncio.Semaphore,
        agentic: AgenticSemanticGate | None,
    ) -> CaseRunResult:
        async with semaphore:
            if agentic is not None:
                match = agentic.check(case.prompt)
                if match.blocked:
                    verdict = ClassifierVerdict(is_violation=True, category=match.category)
                else:
                    config = policy.to_project_config(project_id)
                    verdict = await self._classifier.classify(case.prompt, config)
            else:
                config = policy.to_project_config(project_id)
                verdict = await self._classifier.classify(case.prompt, config)

        status: Literal["PASSED", "FAILED"] = (
            "PASSED" if self._case_passed(case.expected_category, verdict) else "FAILED"
        )
        return CaseRunResult(
            prompt=case.prompt,
            expected_category=case.expected_category,
            llm_category=verdict.category,
            is_violation=verdict.is_violation,
            test_status=status,
        )

    async def run(self, request: BatchRunRequest) -> BatchRunResponse:
        project_id = request.project_id.strip()
        policy = request.policy
        self._validate_dataset(policy, request.test_dataset)

        agentic = self._resolve_agentic_gate()
        concurrency = self._settings.test_runner_concurrency
        semaphore = asyncio.Semaphore(concurrency)

        logger.info(
            "Running in-memory test batch for project=%s cases=%d concurrency=%d agentic=%s",
            project_id,
            len(request.test_dataset),
            concurrency,
            agentic is not None,
        )

        results = await asyncio.gather(
            *[
                self._classify_case(case, policy, project_id, semaphore, agentic)
                for case in request.test_dataset
            ]
        )

        passed = sum(1 for result in results if result.test_status == "PASSED")
        total = len(results)
        failed = total - passed
        accuracy = passed / total if total else 0.0

        return BatchRunResponse(
            project_id=project_id,
            total_tests=total,
            passed=passed,
            failed=failed,
            accuracy_rate=round(accuracy, 4),
            results=list(results),
        )


_batch_runner_service: BatchRunnerService | None = None


def get_batch_runner_service() -> BatchRunnerService:
    global _batch_runner_service
    if _batch_runner_service is None:
        _batch_runner_service = BatchRunnerService()
    return _batch_runner_service
