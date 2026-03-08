"""ORM and Pydantic models for public organizations."""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.db import Base


class OrganizationCategory(str, enum.Enum):
    """Category of an organization."""

    federal = "federal"
    state = "state"
    municipal = "municipal"
    ngo = "ngo"
    other = "other"


class Organization(Base):
    """Represents a public organization."""

    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    cnpj: Mapped[str | None] = mapped_column(String(18), unique=True, nullable=True, index=True)
    category: Mapped[str] = mapped_column(
        Enum(OrganizationCategory), nullable=False, default=OrganizationCategory.other
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str | None] = mapped_column(String(2), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    funds: Mapped[list["Fund"]] = relationship("Fund", back_populates="organization", cascade="all, delete-orphan")  # noqa: F821


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------
from pydantic import BaseModel, ConfigDict, Field  # noqa: E402


class OrganizationBase(BaseModel):
    """Shared fields for organization schemas."""

    name: str = Field(..., min_length=1, max_length=255, examples=["Ministério da Saúde"])
    cnpj: str | None = Field(None, pattern=r"^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$", examples=["00.000.000/0000-00"])
    category: OrganizationCategory = OrganizationCategory.other
    description: str | None = None
    state: str | None = Field(None, max_length=2, examples=["SP"])
    city: str | None = Field(None, max_length=100, examples=["São Paulo"])


class OrganizationCreate(OrganizationBase):
    """Schema for creating an organization."""


class OrganizationUpdate(BaseModel):
    """Schema for partially updating an organization."""

    name: str | None = Field(None, min_length=1, max_length=255)
    cnpj: str | None = Field(None, pattern=r"^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$")
    category: OrganizationCategory | None = None
    description: str | None = None
    state: str | None = Field(None, max_length=2)
    city: str | None = Field(None, max_length=100)


class OrganizationRead(OrganizationBase):
    """Schema for reading an organization."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
