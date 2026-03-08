"""Tests for organization endpoints."""

import pytest


@pytest.fixture()
def sample_org(client):
    resp = client.post(
        "/organizations/",
        json={
            "name": "Ministério da Saúde",
            "cnpj": "00.394.544/0001-91",
            "category": "federal",
            "state": "DF",
            "city": "Brasília",
        },
    )
    assert resp.status_code == 201
    return resp.json()


def test_health_check(client):
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


def test_create_organization(client):
    resp = client.post(
        "/organizations/",
        json={"name": "Prefeitura de São Paulo", "category": "municipal", "state": "SP"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Prefeitura de São Paulo"
    assert data["category"] == "municipal"
    assert data["id"] is not None


def test_create_organization_duplicate_cnpj(client, sample_org):
    resp = client.post(
        "/organizations/",
        json={
            "name": "Duplicate Org",
            "cnpj": sample_org["cnpj"],
            "category": "federal",
        },
    )
    assert resp.status_code == 409


def test_list_organizations(client, sample_org):
    resp = client.get("/organizations/")
    assert resp.status_code == 200
    assert any(o["id"] == sample_org["id"] for o in resp.json())


def test_list_organizations_filter_category(client, sample_org):
    resp = client.get("/organizations/?category=federal")
    assert resp.status_code == 200
    assert all(o["category"] == "federal" for o in resp.json())


def test_list_organizations_search(client, sample_org):
    resp = client.get("/organizations/?search=Saúde")
    assert resp.status_code == 200
    names = [o["name"] for o in resp.json()]
    assert any("Saúde" in n for n in names)


def test_get_organization(client, sample_org):
    resp = client.get(f"/organizations/{sample_org['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == sample_org["id"]


def test_get_organization_not_found(client):
    resp = client.get("/organizations/999999")
    assert resp.status_code == 404


def test_update_organization(client, sample_org):
    resp = client.patch(
        f"/organizations/{sample_org['id']}",
        json={"city": "Rio de Janeiro"},
    )
    assert resp.status_code == 200
    assert resp.json()["city"] == "Rio de Janeiro"


def test_update_organization_not_found(client):
    resp = client.patch("/organizations/999999", json={"city": "X"})
    assert resp.status_code == 404


def test_delete_organization(client):
    create = client.post(
        "/organizations/", json={"name": "To Delete", "category": "other"}
    )
    org_id = create.json()["id"]
    resp = client.delete(f"/organizations/{org_id}")
    assert resp.status_code == 204
    get_resp = client.get(f"/organizations/{org_id}")
    assert get_resp.status_code == 404


def test_delete_organization_not_found(client):
    resp = client.delete("/organizations/999999")
    assert resp.status_code == 404
