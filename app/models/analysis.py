"""Pydantic schemas for analysis results (no ORM table – computed on demand)."""

from decimal import Decimal
from typing import Any

from pydantic import BaseModel


class MissingFundItem(BaseModel):
    """Represents a potential missing-fund finding for a single fund."""

    fund_id: int
    organization_id: int
    organization_name: str
    title: str
    category: str
    allocated_amount: Decimal
    executed_amount: Decimal | None
    missing_amount: Decimal
    missing_percentage: float
    status: str


class MissingFundsReport(BaseModel):
    """Aggregated report of missing/unaccounted funds."""

    total_allocated: Decimal
    total_executed: Decimal
    total_missing: Decimal
    missing_percentage: float
    items: list[MissingFundItem]


class CategorySummary(BaseModel):
    """Financial summary for a single expenditure category."""

    category: str
    total_allocated: Decimal
    total_executed: Decimal
    total_missing: Decimal
    fund_count: int


class CategoryReport(BaseModel):
    """Full report broken down by category."""

    categories: list[CategorySummary]


class CrossReferenceItem(BaseModel):
    """A pair of organizations that share financial irregularity indicators."""

    organization_a_id: int
    organization_a_name: str
    organization_b_id: int
    organization_b_name: str
    shared_category: str
    org_a_missing_amount: Decimal
    org_b_missing_amount: Decimal
    combined_missing_amount: Decimal
    note: str


class CrossReferenceReport(BaseModel):
    """Cross-reference analysis result."""

    total_pairs: int
    items: list[CrossReferenceItem]


class OrganizationSummary(BaseModel):
    """High-level financial summary for a single organization."""

    organization_id: int
    organization_name: str
    total_allocated: Decimal
    total_executed: Decimal
    total_missing: Decimal
    missing_percentage: float
    fund_count: int
    categories: list[str]
    risk_level: str


class OverallSummary(BaseModel):
    """Top-level summary across all organizations."""

    total_organizations: int
    total_funds: int
    total_allocated: Decimal
    total_executed: Decimal
    total_missing: Decimal
    missing_percentage: float
    high_risk_organizations: int
    medium_risk_organizations: int
    low_risk_organizations: int
    organizations: list[OrganizationSummary]
    extra: dict[str, Any] | None = None
