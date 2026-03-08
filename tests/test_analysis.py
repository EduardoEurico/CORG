"""Tests for analysis endpoints."""

import pytest


@pytest.fixture()
def org_a(client):
    resp = client.post(
        "/organizations/",
        json={"name": "Secretaria de Educação SP", "category": "state", "state": "SP"},
    )
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture()
def org_b(client):
    resp = client.post(
        "/organizations/",
        json={"name": "Secretaria de Educação RJ", "category": "state", "state": "RJ"},
    )
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture()
def funds_setup(client, org_a, org_b):
    """Create a set of funds with partial execution to drive analysis tests."""
    funds_data = [
        # org_a – education fund, 40 % missing
        {
            "organization_id": org_a["id"],
            "title": "School Build SP",
            "category": "education",
            "status": "partially_executed",
            "allocated_amount": "1000000.00",
            "executed_amount": "600000.00",
            "reference_year": 2024,
        },
        # org_a – health fund, 100 % allocated, 0 % executed
        {
            "organization_id": org_a["id"],
            "title": "Hospital Fund SP",
            "category": "health",
            "status": "allocated",
            "allocated_amount": "500000.00",
            "reference_year": 2024,
        },
        # org_b – education fund, 50 % missing
        {
            "organization_id": org_b["id"],
            "title": "School Build RJ",
            "category": "education",
            "status": "partially_executed",
            "allocated_amount": "800000.00",
            "executed_amount": "400000.00",
            "reference_year": 2024,
        },
        # org_b – fully executed
        {
            "organization_id": org_b["id"],
            "title": "Admin Budget RJ",
            "category": "administrative",
            "status": "executed",
            "allocated_amount": "200000.00",
            "executed_amount": "200000.00",
            "reference_year": 2024,
        },
    ]
    created = []
    for fd in funds_data:
        r = client.post("/funds/", json=fd)
        assert r.status_code == 201
        created.append(r.json())
    return created


def test_missing_funds_report(client, funds_setup):
    resp = client.get("/analysis/missing-funds")
    assert resp.status_code == 200
    data = resp.json()
    assert float(data["total_missing"]) > 0
    assert len(data["items"]) > 0
    # Items should be sorted descending by missing_amount
    amounts = [float(item["missing_amount"]) for item in data["items"]]
    assert amounts == sorted(amounts, reverse=True)


def test_missing_funds_filter_org(client, funds_setup, org_a):
    resp = client.get(f"/analysis/missing-funds?organization_id={org_a['id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert all(item["organization_id"] == org_a["id"] for item in data["items"])


def test_missing_funds_filter_category(client, funds_setup):
    resp = client.get("/analysis/missing-funds?category=education")
    assert resp.status_code == 200
    data = resp.json()
    assert all(item["category"] == "education" for item in data["items"])


def test_missing_funds_min_pct_filter(client, funds_setup):
    """Items below the threshold should be excluded."""
    resp = client.get("/analysis/missing-funds?min_missing_pct=90")
    assert resp.status_code == 200
    data = resp.json()
    for item in data["items"]:
        assert item["missing_percentage"] >= 90.0


def test_missing_funds_empty_database(client):
    """No funds → zero totals and empty item list."""
    resp = client.get("/analysis/missing-funds")
    assert resp.status_code == 200
    data = resp.json()
    assert float(data["total_allocated"]) == 0.0
    assert data["items"] == []


def test_categories_report(client, funds_setup):
    resp = client.get("/analysis/categories")
    assert resp.status_code == 200
    data = resp.json()
    cats = {c["category"] for c in data["categories"]}
    assert "education" in cats
    assert "health" in cats


def test_categories_report_filter_org(client, funds_setup, org_b):
    resp = client.get(f"/analysis/categories?organization_id={org_b['id']}")
    assert resp.status_code == 200
    data = resp.json()
    # org_b has education and administrative
    cats = {c["category"] for c in data["categories"]}
    assert "education" in cats
    assert "administrative" in cats


def test_cross_reference_report(client, funds_setup):
    resp = client.get("/analysis/cross-reference")
    assert resp.status_code == 200
    data = resp.json()
    # org_a and org_b both have education category with missing funds → at least 1 pair
    assert data["total_pairs"] >= 1
    # Verify structure
    for item in data["items"]:
        assert "organization_a_id" in item
        assert "organization_b_id" in item
        assert "combined_missing_amount" in item


def test_cross_reference_filter_category(client, funds_setup):
    resp = client.get("/analysis/cross-reference?category=education")
    assert resp.status_code == 200
    data = resp.json()
    assert all(item["shared_category"] == "education" for item in data["items"])


def test_cross_reference_high_threshold(client, funds_setup):
    """With a very high threshold, no pairs should be returned."""
    resp = client.get("/analysis/cross-reference?min_missing_amount=999999999")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_pairs"] == 0


def test_summary(client, funds_setup, org_a, org_b):
    resp = client.get("/analysis/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_organizations"] >= 2
    assert data["total_funds"] >= 4
    assert float(data["total_missing"]) > 0
    # Check risk level assignment
    for org_summary in data["organizations"]:
        assert org_summary["risk_level"] in ("high", "medium", "low")


def test_summary_empty_database(client):
    resp = client.get("/analysis/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_organizations"] == 0
    assert data["total_funds"] == 0
