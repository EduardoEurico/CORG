"""Router for organization CRUD endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models.organization import (
    Organization,
    OrganizationCategory,
    OrganizationCreate,
    OrganizationRead,
    OrganizationUpdate,
)

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.get("/", response_model=list[OrganizationRead], summary="List organizations")
def list_organizations(
    category: OrganizationCategory | None = Query(None, description="Filter by category"),
    state: str | None = Query(None, max_length=2, description="Filter by state code (e.g. SP)"),
    search: str | None = Query(None, description="Search by name"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[Organization]:
    """Return a paginated list of organizations, with optional filters."""
    stmt = select(Organization)
    if category:
        stmt = stmt.where(Organization.category == category)
    if state:
        stmt = stmt.where(Organization.state == state.upper())
    if search:
        stmt = stmt.where(Organization.name.ilike(f"%{search}%"))
    stmt = stmt.offset(skip).limit(limit)
    return list(db.execute(stmt).scalars().all())


@router.post(
    "/",
    response_model=OrganizationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an organization",
)
def create_organization(
    payload: OrganizationCreate,
    db: Session = Depends(get_db),
) -> Organization:
    """Create a new organization record."""
    if payload.cnpj:
        existing = db.execute(
            select(Organization).where(Organization.cnpj == payload.cnpj)
        ).scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Organization with CNPJ '{payload.cnpj}' already exists.",
            )

    org = Organization(**payload.model_dump())
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


@router.get("/{org_id}", response_model=OrganizationRead, summary="Get an organization")
def get_organization(org_id: int, db: Session = Depends(get_db)) -> Organization:
    """Return a single organization by ID."""
    org = db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")
    return org


@router.patch("/{org_id}", response_model=OrganizationRead, summary="Update an organization")
def update_organization(
    org_id: int,
    payload: OrganizationUpdate,
    db: Session = Depends(get_db),
) -> Organization:
    """Partially update an organization."""
    org = db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")

    data = payload.model_dump(exclude_unset=True)
    if "cnpj" in data and data["cnpj"] is not None:
        conflict = db.execute(
            select(Organization).where(
                Organization.cnpj == data["cnpj"],
                Organization.id != org_id,
            )
        ).scalar_one_or_none()
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"CNPJ '{data['cnpj']}' is already assigned to another organization.",
            )

    for field, value in data.items():
        setattr(org, field, value)
    db.commit()
    db.refresh(org)
    return org


@router.delete(
    "/{org_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an organization",
)
def delete_organization(org_id: int, db: Session = Depends(get_db)) -> None:
    """Delete an organization and all associated fund records."""
    org = db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")
    db.delete(org)
    db.commit()
