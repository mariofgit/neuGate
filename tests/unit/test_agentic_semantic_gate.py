"""Unit tests — agentic semantic gate with in-memory FAISS index."""

from __future__ import annotations

import numpy as np
import pytest

from neugate.agentic.dataset import AGENTIC_ATTACK_SEED
from neugate.agentic.index_store import build_index_from_vectors
from neugate.agentic.semantic_gate import AgenticSemanticGate

pytestmark = pytest.mark.unit


def _gate_with_identical_vectors(threshold: float = 0.99) -> AgenticSemanticGate:
    dim = 8
    vectors = np.eye(len(AGENTIC_ATTACK_SEED), dim, dtype=np.float32)
    index = build_index_from_vectors(vectors, AGENTIC_ATTACK_SEED, model="test-model")
    return AgenticSemanticGate(index=index, threshold=threshold, model_name="test-model")


def test_blocks_when_query_matches_seed_vector(monkeypatch: pytest.MonkeyPatch) -> None:
    gate = _gate_with_identical_vectors(threshold=0.99)

    def fake_encode(text: str, *, model_name: str) -> np.ndarray:
        assert text == AGENTIC_ATTACK_SEED[2]["attack_prompt"]
        return np.eye(8, dtype=np.float32)[2]

    monkeypatch.setattr("neugate.agentic.semantic_gate.encode_text", fake_encode)

    match = gate.check(AGENTIC_ATTACK_SEED[2]["attack_prompt"])
    assert match.blocked is True
    assert match.category == "agentic_sql_injection"


def test_passes_when_below_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    gate = _gate_with_identical_vectors(threshold=0.99)

    def fake_encode(text: str, *, model_name: str) -> np.ndarray:
        return np.zeros(8, dtype=np.float32)

    monkeypatch.setattr("neugate.agentic.semantic_gate.encode_text", fake_encode)

    match = gate.check("What is a good pasta recipe?")
    assert match.blocked is False
    assert match.category == "safe_domain"
