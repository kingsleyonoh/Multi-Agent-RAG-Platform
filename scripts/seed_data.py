"""Seed the knowledge base with sample documents for demo/testing.

Usage::

    python -m scripts.seed_data          # run from project root
    python scripts/seed_data.py          # direct execution

Creates sample PDF, TXT, and URL document entries in the ingestion
pipeline so the platform has realistic data for demos.
"""

from __future__ import annotations

import os
import sys

# Ensure project root is on sys.path when run directly
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


# ── Sample documents ────────────────────────────────────────────────

SAMPLE_DOCUMENTS: list[dict[str, str]] = [
    {
        "title": "RAG Architecture Overview",
        "content": (
            "Retrieval-Augmented Generation (RAG) combines a retrieval "
            "component with a generative language model.  The retriever "
            "fetches relevant passages from a knowledge base using vector "
            "similarity search, and the generator synthesises a coherent "
            "answer grounded in the retrieved context."
        ),
        "source": "sample_txt",
        "doc_type": "txt",
    },
    {
        "title": "Multi-Agent Systems",
        "content": (
            "Multi-agent systems decompose complex tasks into sub-tasks "
            "handled by specialised agents.  An orchestrator selects the "
            "best-suited agent for each query based on intent classification, "
            "enabling domain-specific reasoning with fallback to a generalist "
            "model."
        ),
        "source": "sample_txt",
        "doc_type": "txt",
    },
    {
        "title": "Semantic Caching for LLMs",
        "content": (
            "Semantic caching stores previous LLM responses keyed by the "
            "embedding of the input query.  When a new query has high cosine "
            "similarity to a cached query, the cached response is returned "
            "instantly, reducing latency and API costs."
        ),
        "source": "sample_txt",
        "doc_type": "txt",
    },
]


# ── Main ─────────────────────────────────────────────────────────────


def main() -> None:
    """Seed the knowledge base with sample documents.

    In the current phase this writes sample text files to
    ``data/samples/`` so they can be ingested via the document API.
    """
    samples_dir = os.path.join(_project_root, "data", "samples")
    os.makedirs(samples_dir, exist_ok=True)

    for doc in SAMPLE_DOCUMENTS:
        filename = doc["title"].lower().replace(" ", "_") + ".txt"
        filepath = os.path.join(samples_dir, filename)
        with open(filepath, "w", encoding="utf-8") as fh:
            fh.write(f"# {doc['title']}\n\n{doc['content']}\n")

    print(f"Seeded {len(SAMPLE_DOCUMENTS)} sample documents → {samples_dir}")


if __name__ == "__main__":
    main()
