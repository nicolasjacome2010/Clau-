"""Shared helper for building an agent's user-turn input.

Every agent past Comprensión consumes structured output from earlier
agents, not raw free text — this renders that context as JSON so the
model sees exactly the same structure our code will parse back out.
"""

from __future__ import annotations

import json
from typing import Any


def format_context(**fields: Any) -> str:
    return json.dumps(fields, ensure_ascii=False)
