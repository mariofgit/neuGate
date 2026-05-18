"""Phase-1 agentic semantic gate (local FAISS)."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from neugate.agentic.embeddings import encode_text
from neugate.agentic.index_store import AgenticIndex

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AgenticMatch:
    blocked: bool
    score: float
    category: str
    category_group: str
    subcategory: str


@dataclass
class AgenticSemanticGate:
    index: AgenticIndex
    threshold: float
    model_name: str

    def check(self, message: str) -> AgenticMatch:
        query = encode_text(message, model_name=self.model_name)
        score, entry = self.index.search_best(query, threshold=self.threshold)

        if entry is None:
            return AgenticMatch(
                blocked=False,
                score=score,
                category="safe_domain",
                category_group="",
                subcategory="",
            )

        logger.info(
            "Agentic semantic block category=%s score=%.4f",
            entry.category,
            score,
            extra={"gate": "agentic", "gate_category": entry.category},
        )
        return AgenticMatch(
            blocked=True,
            score=score,
            category=entry.category,
            category_group=entry.category_group,
            subcategory=entry.subcategory,
        )
