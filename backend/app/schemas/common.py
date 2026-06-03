"""Shared schema primitives."""
from __future__ import annotations

import uuid
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

T = TypeVar("T")


class ORMModel(BaseModel):
    """Base for response models read from ORM objects.

    UUID primary/foreign keys come off the ORM as ``uuid.UUID`` (or as a freshly
    generated ``uuid4`` on not-yet-refreshed instances). A wildcard before-validator
    coerces any UUID value to its string form so ``id: str`` fields validate uniformly.
    """

    model_config = ConfigDict(from_attributes=True)

    @field_validator("*", mode="before")
    @classmethod
    def _coerce_uuid_to_str(cls, v):  # noqa: ANN001
        return str(v) if isinstance(v, uuid.UUID) else v


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int = 1
    size: int = 20


class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


class Message(BaseModel):
    message: str
