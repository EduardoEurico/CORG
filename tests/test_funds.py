"""Tests for fund endpoints."""

import pytest


@pytest.fixture()
def org(client):
    resp = client.post(
        "/organizations/",
        json={"name": "Test Org", "category": "federal", "state": "RJ"},
    )
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture()
def sample_fund(client, org):
    resp = client.post(
        "/funds/",
        json={
            "organization_id": org["id"],
            "title": "Hospital Construction",
            "category": "health",
            "status": "allocated",
            "allocated_amount": "1000000.00",
            "executed_amount": "600000.00",
            "reference_year": 2024,
        },
    )
    assert resp.status_code == 201
    return resp.json()


def test_create_fund(client, org):
    resp = client.post(
        "/funds/",
        json={
            "organization_id": org["id"],
            "title": "School Renovation",
            "category": "education",
            "status": "executed",
            "allocated_amount": "500000.00",
            "executed_amount": "500000.00",
            "reference_year": 2023,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "School Renovation"
    assert data["organization_id"] == org["id"]


def test_create_fund_org_not_found(client):
    resp = client.post(
        "/funds/",
        json={
            "organization_id": 999999,
            "title": "Ghost Fund",
            "category": "other",
            "status": "allocated",
            "allocated_amount": "100.00",
        },
    )
    assert resp.status_code == 404


def test_list_funds(client, sample_fund):
    resp = client.get("/funds/")
    assert resp.status_code == 200
    assert any(f["id"] == sample_fund["id"] for f in resp.json())


def test_list_funds_by_org(client, sample_fund, org):
    resp = client.get(f"/funds/?organization_id={org['id']}")
    assert resp.status_code == 200
    assert all(f["organization_id"] == org["id"] for f in resp.json())


def test_list_funds_by_category(client, sample_fund):
    resp = client.get("/funds/?category=health")
    assert resp.status_code == 200
    assert all(f["category"] == "health" for f in resp.json())


def test_list_funds_by_year(client, sample_fund):
    resp = client.get("/funds/?reference_year=2024")
    assert resp.status_code == 200
    assert any(f["id"] == sample_fund["id"] for f in resp.json())


def test_get_fund(client, sample_fund):
    resp = client.get(f"/funds/{sample_fund['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == sample_fund["id"]


def test_get_fund_not_found(client):
    resp = client.get("/funds/999999")
    assert resp.status_code == 404


def test_update_fund(client, sample_fund):
    resp = client.patch(
        f"/funds/{sample_fund['id']}",
        json={"executed_amount": "900000.00", "status": "partially_executed"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "partially_executed"
    assert float(data["executed_amount"]) == 900000.00


def test_update_fund_not_found(client):
    resp = client.patch("/funds/999999", json={"status": "cancelled"})
    assert resp.status_code == 404


def test_delete_fund(client, org):
    create = client.post(
        "/funds/",
        json={
            "organization_id": org["id"],
            "title": "To Delete",
            "category": "other",
            "status": "allocated",
            "allocated_amount": "100.00",
        },
    )
    fund_id = create.json()["id"]
    resp = client.delete(f"/funds/{fund_id}")
    assert resp.status_code == 204
    assert client.get(f"/funds/{fund_id}").status_code == 404


def test_delete_fund_not_found(client):
    resp = client.delete("/funds/999999")
    assert resp.status_code == 404
