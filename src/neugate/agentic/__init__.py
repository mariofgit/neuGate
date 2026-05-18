"""Local agentic security phase (FAISS + embeddings)."""

from neugate.agentic.bootstrap import get_agentic_gate, warm_agentic_stack
from neugate.agentic.dataset import AGENTIC_ATTACK_SEED
from neugate.agentic.semantic_gate import AgenticMatch, AgenticSemanticGate

__all__ = [
    "AGENTIC_ATTACK_SEED",
    "AgenticMatch",
    "AgenticSemanticGate",
    "get_agentic_gate",
    "warm_agentic_stack",
]
