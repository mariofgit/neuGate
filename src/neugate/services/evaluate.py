from __future__ import annotations

import logging

from neugate.agentic.bootstrap import get_agentic_gate
from neugate.agentic.semantic_gate import AgenticSemanticGate
from neugate.models.evaluate import EvaluateRequest, EvaluateResponse
from neugate.models.policy import ConsumerPolicy
from neugate.services.classifier import ClassifierService, get_classifier
from neugate.services.pivot_selector import PivotSelector, get_pivot_selector
from neugate.settings import Settings, get_settings

logger = logging.getLogger(__name__)


class EvaluateService:
    def __init__(
        self,
        classifier: ClassifierService | None = None,
        pivot_selector: PivotSelector | None = None,
        agentic_gate: AgenticSemanticGate | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._classifier = classifier or get_classifier()
        self._pivot_selector = pivot_selector or get_pivot_selector()
        self._agentic_gate = agentic_gate

    def _resolve_agentic_gate(self) -> AgenticSemanticGate | None:
        if self._agentic_gate is not None:
            return self._agentic_gate
        if not self._settings.agentic_enabled:
            return None
        return get_agentic_gate()

    async def evaluate(self, request: EvaluateRequest) -> EvaluateResponse:
        project_id = request.project_id.strip()
        policy = request.policy

        agentic = self._resolve_agentic_gate()
        if agentic is not None:
            match = agentic.check(request.message)
            if match.blocked:
                return self._block_response(
                    category=match.category,
                    policy=policy,
                    project_id=project_id,
                )

        config = policy.to_project_config(project_id)
        verdict = await self._classifier.classify(request.message, config)
        return self._to_response(verdict.is_violation, verdict.category, policy, project_id)

    def _block_response(
        self,
        *,
        category: str,
        policy: ConsumerPolicy,
        project_id: str,
    ) -> EvaluateResponse:
        config = policy.to_project_config(project_id)
        return EvaluateResponse(
            is_violation=True,
            category=category,
            action="short_circuit",
            cached_response=self._pivot_selector.next_template(config),
        )

    def _to_response(
        self,
        is_violation: bool,
        category: str,
        policy: ConsumerPolicy,
        project_id: str,
    ) -> EvaluateResponse:
        if not is_violation:
            return EvaluateResponse(
                is_violation=False,
                category="safe_domain",
                action="proceed",
                cached_response=None,
            )

        config = policy.to_project_config(project_id)
        return EvaluateResponse(
            is_violation=True,
            category=category,
            action="short_circuit",
            cached_response=self._pivot_selector.next_template(config),
        )


_evaluate_service: EvaluateService | None = None


def get_evaluate_service() -> EvaluateService:
    global _evaluate_service
    if _evaluate_service is None:
        _evaluate_service = EvaluateService()
    return _evaluate_service
