"""ORM and Pydantic models for funds and transactions."""

import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.db import Base


class FundStatus(str, enum.Enum):
    """Status of a fund allocation."""

    allocated = "allocated"
    executed = "executed"
    partially_executed = "partially_executed"
    cancelled = "cancelled"
    under_investigation = "under_investigation"


class FundCategory(str, enum.Enum):
    """Category of expenditure."""

    health = "health"
    education = "education"
    infrastructure = "infrastructure"
    security = "security"
    social_assistance = "social_assistance"
    culture = "culture"
    science_technology = "science_technology"
    environment = "environment"
    administrative = "administrative"
    other = "other"


class Fund(Base):
    """Represents a financial fund allocation for an organization."""

    __tablename__ = "funds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(
        Enum(FundCategory), nullable=False, default=FundCategory.other
    )
    status: Mapped[str] = mapped_column(
        Enum(FundStatus), nullable=False, default=FundStatus.allocated
    )
    allocated_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    executed_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reference_year: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    organization: Mapped["Organization"] = relationship("Organization", back_populates="funds")  # noqa: F821


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------
from pydantic import BaseModel, ConfigDict, Field  # noqa: E402


class FundBase(BaseModel):
    """Shared fields for fund schemas."""

    title: str = Field(..., min_length=1, max_length=255)
    category: FundCategory = FundCategory.other
    status: FundStatus = FundStatus.allocated
    allocated_amount: Decimal = Field(..., gt=0)
    executed_amount: Decimal | None = Field(None, ge=0)
    source: str | None = None
    reference_year: int | None = Field(None, ge=1900, le=2100)
    start_date: date | None = None
    end_date: date | None = None
    notes: str | None = None
    external_id: str | None = None


class FundCreate(FundBase):
    """Schema for creating a fund record."""

    organization_id: int


class FundUpdate(BaseModel):
    """Schema for partially updating a fund record."""

    title: str | None = Field(None, min_length=1, max_length=255)
    category: FundCategory | None = None
    status: FundStatus | None = None
    allocated_amount: Decimal | None = Field(None, gt=0)
    executed_amount: Decimal | None = Field(None, ge=0)
    source: str | None = None
    reference_year: int | None = Field(None, ge=1900, le=2100)
    start_date: date | None = None
    end_date: date | None = None
    notes: str | None = None
    external_id: str | None = None


class FundRead(FundBase):
    """Schema for reading a fund record."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    created_at: datetime
    updated_at: datetime
