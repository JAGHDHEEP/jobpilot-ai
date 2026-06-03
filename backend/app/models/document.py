"""Resume / cover-letter document model."""
from __future__ import annotations

from sqlalchemy import JSON, BigInteger, Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import GUID, Base, TimestampMixin, UUIDMixin
from app.models.enums import DocKind


class Document(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "documents"

    user_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    kind: Mapped[DocKind] = mapped_column(Enum(DocKind), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    storage_key: Mapped[str | None] = mapped_column(String(500))
    mime_type: Mapped[str | None] = mapped_column(String(120))
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    is_master: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    parsed_text: Mapped[str | None] = mapped_column(Text)
    structured: Mapped[dict | None] = mapped_column(JSON)
    job_id: Mapped[str | None] = mapped_column(GUID())
