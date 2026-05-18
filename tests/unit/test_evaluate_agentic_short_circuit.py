"""Unit tests — evaluate service agentic phase short-circuits before LLM."""

from __future__ import annotations

import pytest

from neugate.agentic.semantic_gate import AgenticMatch
from neugate.models.evaluate import ClassifierVerdict, EvaluateRequest
from neugate.services.evaluate import EvaluateService
from helpers import StubClassifier

pytestmark = pytest.mark.unit


class StubAgenticGate:
    def __init__(self, match: AgenticMatch) -> None:
        self._match = match

    def check(self, message: str) -> AgenticMatch:
        return self._match


@pytest.mark.asyncio
async def test_agentic_block_skips_classifier(consumer_policy) -> None:
    classifier = StubClassifier(ClassifierVerdict(is_violation=False, category="safe_domain"))
    gate = StubAgenticGate(
        AgenticMatch(
            blocked=True,
            score=0.95,
            category="agentic_sql_injection",
            category_group="MCP and Supabase Attacks",
            subcategory="SQL Injection",
        )
    )

    service = EvaluateService(classifier=classifier, agentic_gate=gate)
    response = await service.evaluate(
        EvaluateRequest(
            project_id="test",
            message="ignored",
            policy=consumer_policy,
        )
    )

    assert response.is_violation is True
    assert response.category == "agentic_sql_injection"
    assert response.action == "short_circuit"
    assert response.cached_response is not None
    assert classifier.call_count == 0
