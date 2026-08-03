"""SQLAlchemy ORM model for the decisions bounded context.

Maps 1:1 to the `decisions` table in docs/DATABASE.md §2.4. `raw_input` is
stored as `raw_input_encrypted bytea` — encryption/decryption happens at
the repository boundary (see `repository.py`), never in the domain.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from core_api.db import Base, UTCDateTime


class DecisionModel(Base):
    __tablename__ = "decisions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String)
    vertical: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, index=True)
    raw_input_encrypted: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime)
