"""Pure cosine similarity — no numpy dependency, used by both the
deduplication check (application/use_cases.py) and the naive similarity
search (infrastructure/repository.py, see its docstring for why it's a
linear scan instead of a real vector index).
"""

from __future__ import annotations

import math
from collections.abc import Sequence


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b):
        raise ValueError(f"Embedding dimensions don't match: {len(a)} vs {len(b)}")

    dot_product = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot_product / (norm_a * norm_b)
