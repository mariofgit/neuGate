"""FAISS index load and cosine search (inner product on L2-normalized vectors)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

import faiss
import numpy as np

from neugate.agentic.dataset import AgenticSeedEntry

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AgenticMetaEntry:
    id: int
    category_group: str
    subcategory: str
    category: str
    attack_prompt: str


@dataclass
class AgenticIndex:
    index: faiss.Index
    entries: list[AgenticMetaEntry]
    model: str
    dimension: int
    threshold_default: float

    def search_best(self, query_vector: np.ndarray, *, threshold: float) -> tuple[float, AgenticMetaEntry | None]:
        if query_vector.ndim == 1:
            query = query_vector.reshape(1, -1).astype(np.float32)
        else:
            query = query_vector.astype(np.float32)

        scores, indices = self.index.search(query, 1)
        score = float(scores[0][0])
        idx = int(indices[0][0])
        if idx < 0 or score < threshold:
            return score, None
        return score, self.entries[idx]


def _meta_entry_from_dict(item: dict) -> AgenticMetaEntry:
    """Load metadata entry; supports legacy Spanish field names in committed indexes."""
    return AgenticMetaEntry(
        id=int(item["id"]),
        category_group=str(item.get("category_group") or item.get("categoria", "")),
        subcategory=str(item.get("subcategory") or item.get("subcategoria", "")),
        category=str(item["category"]),
        attack_prompt=str(item.get("attack_prompt") or item.get("prompt_ataque", "")),
    )


def load_agentic_index(index_path: Path, meta_path: Path) -> AgenticIndex:
    if not index_path.is_file():
        raise FileNotFoundError(f"Agentic FAISS index not found: {index_path}")
    if not meta_path.is_file():
        raise FileNotFoundError(f"Agentic metadata not found: {meta_path}")

    payload = json.loads(meta_path.read_text(encoding="utf-8"))
    entries = [_meta_entry_from_dict(item) for item in payload["entries"]]

    index = faiss.read_index(str(index_path))
    logger.info(
        "Loaded agentic index vectors=%s model=%s path=%s",
        index.ntotal,
        payload.get("model"),
        index_path,
    )

    return AgenticIndex(
        index=index,
        entries=entries,
        model=str(payload["model"]),
        dimension=int(payload["dimension"]),
        threshold_default=float(payload.get("threshold_default", 0.82)),
    )


def build_index_from_vectors(
    vectors: np.ndarray,
    seed: list[AgenticSeedEntry],
    *,
    model: str,
    threshold_default: float = 0.82,
) -> AgenticIndex:
    dimension = vectors.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(vectors.astype(np.float32))

    entries = [
        AgenticMetaEntry(
            id=i,
            category_group=row["category_group"],
            subcategory=row["subcategory"],
            category=row["category"],
            attack_prompt=row["attack_prompt"],
        )
        for i, row in enumerate(seed)
    ]

    return AgenticIndex(
        index=index,
        entries=entries,
        model=model,
        dimension=dimension,
        threshold_default=threshold_default,
    )


def write_index(agentic: AgenticIndex, index_path: Path, meta_path: Path) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.parent.mkdir(parents=True, exist_ok=True)

    faiss.write_index(agentic.index, str(index_path))

    meta = {
        "model": agentic.model,
        "dimension": agentic.dimension,
        "threshold_default": agentic.threshold_default,
        "entries": [
            {
                "id": entry.id,
                "category_group": entry.category_group,
                "subcategory": entry.subcategory,
                "category": entry.category,
                "attack_prompt": entry.attack_prompt,
            }
            for entry in agentic.entries
        ],
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
