"""Router for fund / financial data endpoints."""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models.fund import Fund, FundCategory, FundCreate, FundRead, FundStatus, FundUpdate
from app.models.organization import Organization

router = APIRouter(prefix="/funds", tags=["Funds"])


def _get_fund_or_404(fund_id: int, db: Session) -> Fund:
    fund = db.get(Fund, fund_id)
    if not fund:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fund not found.")
    return fund


@router.get("/", response_model=list[FundRead], summary="List fund records")
def list_funds(
    organization_id: int | None = Query(None, description="Filter by organization ID"),
    category: FundCategory | None = Query(None),
    status_filter: FundStatus | None = Query(None, alias="status"),
    reference_year: int | None = Query(None, ge=1900, le=2100),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[Fund]:
    """Return a paginated list of fund records with optional filters."""
    stmt = select(Fund)
    if organization_id is not None:
        stmt = stmt.where(Fund.organization_id == organization_id)
    if category:
        stmt = stmt.where(Fund.category == category)
    if status_filter:
        stmt = stmt.where(Fund.status == status_filter)
    if reference_year is not None:
        stmt = stmt.where(Fund.reference_year == reference_year)
    stmt = stmt.offset(skip).limit(limit)
    return list(db.execute(stmt).scalars().all())


@router.post(
    "/",
    response_model=FundRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a fund record",
)
def create_fund(payload: FundCreate, db: Session = Depends(get_db)) -> Fund:
    """Create a new fund/allocation record linked to an organization."""
    org = db.get(Organization, payload.organization_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization with ID {payload.organization_id} not found.",
        )
    fund = Fund(**payload.model_dump())
    db.add(fund)
    db.commit()
    db.refresh(fund)
    return fund


@router.get("/{fund_id}", response_model=FundRead, summary="Get a fund record")
def get_fund(fund_id: int, db: Session = Depends(get_db)) -> Fund:
    return _get_fund_or_404(fund_id, db)


@router.patch("/{fund_id}", response_model=FundRead, summary="Update a fund record")
def update_fund(
    fund_id: int,
    payload: FundUpdate,
    db: Session = Depends(get_db),
) -> Fund:
    """Partially update a fund record."""
    fund = _get_fund_or_404(fund_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(fund, field, value)
    db.commit()
    db.refresh(fund)
    return fund


@router.delete(
    "/{fund_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a fund record",
)
def delete_fund(fund_id: int, db: Session = Depends(get_db)) -> None:
    fund = _get_fund_or_404(fund_id, db)
    db.delete(fund)
    db.commit()


# ---------------------------------------------------------------------------
# Bulk import from external data source
# ---------------------------------------------------------------------------

@router.post(
    "/import/external",
    response_model=list[FundRead],
    status_code=status.HTTP_201_CREATED,
    summary="Import fund records from an external public-data source",
)
async def import_external_funds(
    organization_id: int = Query(..., description="Target organization ID"),
    year: int | None = Query(None, ge=1900, le=2100, description="Reference year to import"),
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
) -> list[Fund]:
    """Fetch fund/agreement data from Portal da Transparência for the given
    organization and persist any new records (de-duplicated by external_id).
    """
    from app.services.data_fetcher import DataFetcherError, data_fetcher

    org = db.get(Organization, organization_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization with ID {organization_id} not found.",
        )

    try:
        raw_records = await data_fetcher.fetch_convenios(cnpj=org.cnpj, year=year, page=page)
    except DataFetcherError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    created: list[Fund] = []
    for record in raw_records:
        fund_data = data_fetcher.convenio_to_fund_data(record)
        external_id = fund_data.get("external_id")

        # Skip if already imported
        if external_id:
            existing = db.execute(
                select(Fund).where(
                    Fund.organization_id == organization_id,
                    Fund.external_id == external_id,
                )
            ).scalar_one_or_none()
            if existing:
                continue

        fund = Fund(organization_id=organization_id, **fund_data)
        db.add(fund)
        created.append(fund)

    if created:
        db.commit()
        for f in created:
            db.refresh(f)

    return created
