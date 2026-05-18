"""Startup warm-up for agentic stack."""

from __future__ import annotations

import logging

from neugate.agentic.embeddings import load_embedding_model
from neugate.agentic.index_store import load_agentic_index
from neugate.agentic.semantic_gate import AgenticSemanticGate
from neugate.settings import Settings

logger = logging.getLogger(__name__)

_agentic_gate: AgenticSemanticGate | None = None


def warm_agentic_stack(settings: Settings) -> AgenticSemanticGate:
    global _agentic_gate

    load_embedding_model(settings.agentic_model)
    index = load_agentic_index(settings.agentic_index_path, settings.agentic_meta_path)
    threshold = settings.agentic_threshold
    _agentic_gate = AgenticSemanticGate(
        index=index,
        threshold=threshold,
        model_name=settings.agentic_model,
    )
    logger.info(
        "Agentic gate ready: vectors=%s threshold=%.2f model=%s",
        index.index.ntotal,
        threshold,
        settings.agentic_model,
    )
    return _agentic_gate


def get_agentic_gate() -> AgenticSemanticGate | None:
    return _agentic_gate


def set_agentic_gate(gate: AgenticSemanticGate | None) -> None:
    global _agentic_gate
    _agentic_gate = gate


def clear_agentic_gate() -> None:
    set_agentic_gate(None)
