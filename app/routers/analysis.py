"""Router for data-analysis endpoints."""

from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models.analysis import (
    CategoryReport,
    CrossReferenceReport,
    MissingFundsReport,
    OverallSummary,
)
from app.models.fund import FundCategory
from app.services.analyzer import (
    get_category_report,
    get_cross_reference_report,
    get_missing_funds_report,
    get_overall_summary,
)

router = APIRouter(prefix="/analysis", tags=["Analysis"])


@router.get(
    "/missing-funds",
    response_model=MissingFundsReport,
    summary="Report of funds where spending falls short of allocation",
)
def missing_funds(
    organization_id: int | None = Query(None, description="Restrict to one organization"),
    category: FundCategory | None = Query(None, description="Restrict to one category"),
    reference_year: int | None = Query(None, ge=1900, le=2100),
    min_missing_pct: float = Query(
        0.0, ge=0.0, le=100.0, description="Only include funds missing at least this percentage"
    ),
    db: Session = Depends(get_db),
) -> MissingFundsReport:
    """Identify fund allocations where the executed amount is less than the
    allocated amount, indicating potential misuse or underspending."""
    return get_missing_funds_report(
        db,
        organization_id=organization_id,
        category=category.value if category else None,
        reference_year=reference_year,
        min_missing_pct=min_missing_pct,
    )


@router.get(
    "/categories",
    response_model=CategoryReport,
    summary="Financial breakdown by expenditure category",
)
def categories(
    organization_id: int | None = Query(None),
    reference_year: int | None = Query(None, ge=1900, le=2100),
    db: Session = Depends(get_db),
) -> CategoryReport:
    """Summarise allocations, executed amounts, and missing amounts grouped
    by expenditure category."""
    return get_category_report(db, organization_id=organization_id, reference_year=reference_year)


@router.get(
    "/cross-reference",
    response_model=CrossReferenceReport,
    summary="Cross-reference organizations sharing irregular fund categories",
)
def cross_reference(
    min_missing_amount: Decimal = Query(
        Decimal("0"),
        description="Minimum missing amount (BRL) to include an organization in pairing",
    ),
    category: FundCategory | None = Query(None),
    reference_year: int | None = Query(None, ge=1900, le=2100),
    db: Session = Depends(get_db),
) -> CrossReferenceReport:
    """Cross-reference organizations that share expenditure categories where
    funds are missing, revealing patterns of co-occurring irregularities."""
    return get_cross_reference_report(
        db,
        min_missing_amount=min_missing_amount,
        category=category.value if category else None,
        reference_year=reference_year,
    )


@router.get(
    "/summary",
    response_model=OverallSummary,
    summary="Overall financial health summary across all organizations",
)
def summary(db: Session = Depends(get_db)) -> OverallSummary:
    """Return a top-level dashboard summary: total allocations, executed
    amounts, missing funds, and per-organization risk levels."""
    return get_overall_summary(db)
