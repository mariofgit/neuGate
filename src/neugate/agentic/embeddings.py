"""Local sentence-transformer embeddings (no external API)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

_model: SentenceTransformer | None = None
_model_name: str | None = None


def load_embedding_model(model_name: str) -> None:
    global _model, _model_name
    if _model is not None and _model_name == model_name:
        return

    from sentence_transformers import SentenceTransformer

    logger.info("Loading embedding model %s", model_name)
    _model = SentenceTransformer(model_name)
    _model_name = model_name
    logger.info("Embedding model ready (dim=%s)", _model.get_sentence_embedding_dimension())


def encode_text(text: str, *, model_name: str) -> np.ndarray:
    load_embedding_model(model_name)
    assert _model is not None
    vector = _model.encode(
        text,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    return np.asarray(vector, dtype=np.float32)


def encode_batch(texts: list[str], *, model_name: str) -> np.ndarray:
    load_embedding_model(model_name)
    assert _model is not None
    vectors = _model.encode(
        texts,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    return np.asarray(vectors, dtype=np.float32)
