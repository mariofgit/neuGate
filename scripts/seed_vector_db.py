#!/usr/bin/env python3
"""Build the agentic FAISS index from AGENTIC_ATTACK_SEED."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from neugate.agentic.dataset import AGENTIC_ATTACK_SEED  # noqa: E402
from neugate.agentic.embeddings import encode_batch  # noqa: E402
from neugate.agentic.index_store import build_index_from_vectors, write_index  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed NeuGate agentic FAISS index")
    parser.add_argument(
        "--model",
        default="paraphrase-multilingual-MiniLM-L12-v2",
        help="sentence-transformers model name",
    )
    parser.add_argument(
        "--output-index",
        type=Path,
        default=REPO_ROOT / "config/agentic/neugate_agentic.index",
    )
    parser.add_argument(
        "--output-meta",
        type=Path,
        default=REPO_ROOT / "config/agentic/neugate_agentic.meta.json",
    )
    parser.add_argument("--threshold", type=float, default=0.82)
    args = parser.parse_args()

    prompts = [row["attack_prompt"] for row in AGENTIC_ATTACK_SEED]
    vectors = encode_batch(prompts, model_name=args.model)

    agentic = build_index_from_vectors(
        vectors,
        AGENTIC_ATTACK_SEED,
        model=args.model,
        threshold_default=args.threshold,
    )
    write_index(agentic, args.output_index, args.output_meta)

    print(f"Wrote index: {args.output_index} ({agentic.index.ntotal} vectors)")
    print(f"Wrote meta:  {args.output_meta}")


if __name__ == "__main__":
    main()
