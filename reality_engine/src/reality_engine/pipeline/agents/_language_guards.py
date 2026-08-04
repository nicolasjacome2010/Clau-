"""Post-hoc linguistic validators enforcing docs/PRD.md §2's non-negotiable
principle: "Nunca afirmar certeza" — the system never talks about the
future in the affirmative, and never issues orders.

These are deliberately simple, curated pattern lists — a starting point,
not an exhaustive or linguistically rigorous classifier, same caveat as
the deterministic patterns in `safety_gate.py`. They can only ever trigger
a retry (ask the model to try again), never silently rewrite the model's
words into something it didn't say.
"""

from __future__ import annotations

import re

_DETERMINISTIC_FUTURE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\bserás\b",
        r"\bserán\b",
        r"\bpasará\b",
        r"\bpasarán\b",
        r"\btendrás\b",
        r"\blograrás\b",
        r"\bvas a (perder|ganar|conseguir|lograr|fallar)\b",
        r"\byou will\b",
        r"\byou'll\b",
        r"\bis going to happen\b",
    ]
]

_IMPERATIVE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\bdeberías\b",
        r"\bdebes\b",
        r"\btienes que\b",
        r"\byou should\b",
        r"\byou must\b",
    ]
]


def find_deterministic_future_language(texts: list[str]) -> list[str]:
    """docs/REALITY_ENGINE.md §2, Agente 7 error `narrative_uses_deterministic_language`."""
    return [
        pattern.pattern
        for text in texts
        for pattern in _DETERMINISTIC_FUTURE_PATTERNS
        if pattern.search(text)
    ]


def find_imperative_language(text: str) -> list[str]:
    """docs/REALITY_ENGINE.md §2, Agente 10 error `imperative_language_detected`."""
    return [pattern.pattern for pattern in _IMPERATIVE_PATTERNS if pattern.search(text)]
