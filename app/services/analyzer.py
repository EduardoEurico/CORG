"""Analysis service – computes missing-fund and cross-reference reports."""

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.analysis import (
    CategoryReport,
    CategorySummary,
    CrossReferenceItem,
    CrossReferenceReport,
    MissingFundItem,
    MissingFundsReport,
    OrganizationSummary,
    OverallSummary,
)
from app.models.fund import Fund, FundStatus
from app.models.organization import Organization

# Threshold above which a fund's missing percentage is considered significant
_MISSING_THRESHOLD = Decimal("0")


def _risk_level(missing_pct: float) -> str:
    """Return a risk label based on the missing percentage."""
    if missing_pct >= 50:
        return "high"
    if missing_pct >= 20:
        return "medium"
    return "low"


def get_missing_funds_report(
    db: Session,
    organization_id: int | None = None,
    category: str | None = None,
    reference_year: int | None = None,
    min_missing_pct: float = 0.0,
) -> MissingFundsReport:
    """Return a report of funds where executed < allocated."""
    stmt = (
        select(Fund, Organization.name.label("org_name"))
        .join(Organization, Fund.organization_id == Organization.id)
    )
    if organization_id is not None:
        stmt = stmt.where(Fund.organization_id == organization_id)
    if category is not None:
        stmt = stmt.where(Fund.category == category)
    if reference_year is not None:
        stmt = stmt.where(Fund.reference_year == reference_year)

    rows = db.execute(stmt).all()

    items: list[MissingFundItem] = []
    total_allocated = Decimal("0")
    total_executed = Decimal("0")

    for fund, org_name in rows:
        allocated = fund.allocated_amount or Decimal("0")
        executed = fund.executed_amount if fund.executed_amount is not None else Decimal("0")
        missing = allocated - executed

        if allocated > _MISSING_THRESHOLD:
            missing_pct = float(missing / allocated * 100)
        else:
            missing_pct = 0.0

        if missing_pct < min_missing_pct:
            continue

        total_allocated += allocated
        total_executed += executed

        items.append(
            MissingFundItem(
                fund_id=fund.id,
                organization_id=fund.organization_id,
                organization_name=org_name,
                title=fund.title,
                category=fund.category,
                allocated_amount=allocated,
                executed_amount=fund.executed_amount,
                missing_amount=missing,
                missing_percentage=round(missing_pct, 2),
                status=fund.status,
            )
        )

    total_missing = total_allocated - total_executed
    overall_pct = (
        float(total_missing / total_allocated * 100) if total_allocated > Decimal("0") else 0.0
    )

    return MissingFundsReport(
        total_allocated=total_allocated,
        total_executed=total_executed,
        total_missing=total_missing,
        missing_percentage=round(overall_pct, 2),
        items=sorted(items, key=lambda x: x.missing_amount, reverse=True),
    )


def get_category_report(
    db: Session,
    organization_id: int | None = None,
    reference_year: int | None = None,
) -> CategoryReport:
    """Return a breakdown of allocations and missing amounts by category."""
    stmt = select(Fund)
    if organization_id is not None:
        stmt = stmt.where(Fund.organization_id == organization_id)
    if reference_year is not None:
        stmt = stmt.where(Fund.reference_year == reference_year)

    funds = db.execute(stmt).scalars().all()

    category_map: dict[str, dict] = {}
    for fund in funds:
        cat = fund.category
        if cat not in category_map:
            category_map[cat] = {
                "total_allocated": Decimal("0"),
                "total_executed": Decimal("0"),
                "fund_count": 0,
            }
        allocated = fund.allocated_amount or Decimal("0")
        executed = fund.executed_amount if fund.executed_amount is not None else Decimal("0")
        category_map[cat]["total_allocated"] += allocated
        category_map[cat]["total_executed"] += executed
        category_map[cat]["fund_count"] += 1

    summaries: list[CategorySummary] = []
    for cat, data in category_map.items():
        alloc = data["total_allocated"]
        exec_ = data["total_executed"]
        missing = alloc - exec_
        summaries.append(
            CategorySummary(
                category=cat,
                total_allocated=alloc,
                total_executed=exec_,
                total_missing=missing,
                fund_count=data["fund_count"],
            )
        )

    return CategoryReport(
        categories=sorted(summaries, key=lambda x: x.total_missing, reverse=True)
    )


def get_cross_reference_report(
    db: Session,
    min_missing_amount: Decimal = Decimal("0"),
    category: str | None = None,
    reference_year: int | None = None,
) -> CrossReferenceReport:
    """Cross-reference organizations that share categories with missing funds.

    For each category, organizations that both have missing funds are paired.
    """
    stmt = (
        select(Fund, Organization.name.label("org_name"))
        .join(Organization, Fund.organization_id == Organization.id)
    )
    if category is not None:
        stmt = stmt.where(Fund.category == category)
    if reference_year is not None:
        stmt = stmt.where(Fund.reference_year == reference_year)

    rows = db.execute(stmt).all()

    # Build per-category / per-org aggregates
    cat_org: dict[str, dict[int, dict]] = {}
    for fund, org_name in rows:
        cat = fund.category
        org_id = fund.organization_id
        allocated = fund.allocated_amount or Decimal("0")
        executed = fund.executed_amount if fund.executed_amount is not None else Decimal("0")
        missing = allocated - executed

        cat_org.setdefault(cat, {})
        cat_org[cat].setdefault(org_id, {"name": org_name, "missing": Decimal("0")})
        cat_org[cat][org_id]["missing"] += missing

    items: list[CrossReferenceItem] = []
    seen: set[tuple] = set()

    for cat, orgs in cat_org.items():
        org_ids = [oid for oid, data in orgs.items() if data["missing"] > min_missing_amount]
        for i in range(len(org_ids)):
            for j in range(i + 1, len(org_ids)):
                a = org_ids[i]
                b = org_ids[j]
                pair_key = (min(a, b), max(a, b), cat)
                if pair_key in seen:
                    continue
                seen.add(pair_key)
                missing_a = orgs[a]["missing"]
                missing_b = orgs[b]["missing"]
                items.append(
                    CrossReferenceItem(
                        organization_a_id=a,
                        organization_a_name=orgs[a]["name"],
                        organization_b_id=b,
                        organization_b_name=orgs[b]["name"],
                        shared_category=cat,
                        org_a_missing_amount=missing_a,
                        org_b_missing_amount=missing_b,
                        combined_missing_amount=missing_a + missing_b,
                        note=(
                            f"Both organizations have unaccounted funds in "
                            f"the '{cat}' category."
                        ),
                    )
                )

    return CrossReferenceReport(
        total_pairs=len(items),
        items=sorted(items, key=lambda x: x.combined_missing_amount, reverse=True),
    )


def get_overall_summary(db: Session) -> OverallSummary:
    """Return a high-level summary across all organizations and funds."""
    organizations = db.execute(select(Organization)).scalars().all()
    funds = db.execute(select(Fund)).scalars().all()

    # Build per-org aggregates
    org_map: dict[int, dict] = {
        org.id: {
            "name": org.name,
            "allocated": Decimal("0"),
            "executed": Decimal("0"),
            "fund_count": 0,
            "categories": set(),
        }
        for org in organizations
    }

    grand_allocated = Decimal("0")
    grand_executed = Decimal("0")

    for fund in funds:
        org_data = org_map.get(fund.organization_id)
        if org_data is None:
            continue
        allocated = fund.allocated_amount or Decimal("0")
        executed = fund.executed_amount if fund.executed_amount is not None else Decimal("0")
        org_data["allocated"] += allocated
        org_data["executed"] += executed
        org_data["fund_count"] += 1
        org_data["categories"].add(fund.category)
        grand_allocated += allocated
        grand_executed += executed

    grand_missing = grand_allocated - grand_executed
    grand_pct = (
        float(grand_missing / grand_allocated * 100)
        if grand_allocated > Decimal("0")
        else 0.0
    )

    org_summaries: list[OrganizationSummary] = []
    high_risk = medium_risk = low_risk = 0

    for org_id, data in org_map.items():
        alloc = data["allocated"]
        exec_ = data["executed"]
        missing = alloc - exec_
        pct = float(missing / alloc * 100) if alloc > Decimal("0") else 0.0
        risk = _risk_level(pct)
        if risk == "high":
            high_risk += 1
        elif risk == "medium":
            medium_risk += 1
        else:
            low_risk += 1

        org_summaries.append(
            OrganizationSummary(
                organization_id=org_id,
                organization_name=data["name"],
                total_allocated=alloc,
                total_executed=exec_,
                total_missing=missing,
                missing_percentage=round(pct, 2),
                fund_count=data["fund_count"],
                categories=sorted(data["categories"]),
                risk_level=risk,
            )
        )

    return OverallSummary(
        total_organizations=len(organizations),
        total_funds=len(funds),
        total_allocated=grand_allocated,
        total_executed=grand_executed,
        total_missing=grand_missing,
        missing_percentage=round(grand_pct, 2),
        high_risk_organizations=high_risk,
        medium_risk_organizations=medium_risk,
        low_risk_organizations=low_risk,
        organizations=sorted(org_summaries, key=lambda x: x.total_missing, reverse=True),
    )
