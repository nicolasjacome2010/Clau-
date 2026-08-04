"""SQLAlchemy ORM models for the memory bounded context.

`memory_embeddings.embedding` is stored as a plain JSON array of floats
here, not a real `vector(1536)` column — see repository.py's docstring
for the migration point to pgvector (docs/ARCHITECTURE.md §7) once volume
or latency justify it. This keeps the module portable to the SQLite test
path in the meantime, same tradeoff as every other JSON column in this
codebase.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core_api.db import Base, UTCDateTime

_JSONType = JSON().with_variant(JSONB, "postgresql")


class UserBiasProfileModel(Base):
    __tablename__ = "user_bias_profile"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    biases: Mapped[list[dict[str, Any]]] = mapped_column(_JSONType, default=list)
    calibration_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime)


class MemoryEmbeddingModel(Base):
    __tablename__ = "memory_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    decision_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("decisions.id", ondelete="SET NULL"), nullable=True
    )
    summary_text: Mapped[str] = mapped_column(String)
    embedding: Mapped[list[float]] = mapped_column(_JSONType)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
