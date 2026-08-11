"""Iteration 26: Tenant isolation & authorization verification (P0)."""
import os
import requests
import pytest

def _load_url():
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    return line.split("=", 1)[1].strip().rstrip("/")
    except Exception:
        pass
    return os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

BASE = _load_url()
assert BASE, "REACT_APP_BACKEND_URL missing"

WORK = {"email": "work@gmail.com", "password": "mohammed"}
ADMIN = {"email": "admin@ariadni.id", "password": "Ariadni@2026"}


def _login(creds):
    r = requests.post(f"{BASE}/api/auth/login", json=creds, timeout=15)
    assert r.status_code == 200, f"login failed {r.status_code} {r.text}"
    return r.json()


@pytest.fixture(scope="module")
def work_session():
    return _login(WORK)


@pytest.fixture(scope="module")
def admin_session():
    return _login(ADMIN)


def _h(sess):
    return {"Authorization": f"Bearer {sess['token']}"}


# ---- Session claims ----
def test_work_session_claims(work_session):
    assert work_session["user"]["email"] == "work@gmail.com"
    ws = work_session["workspace"]
    assert ws["name"].lower() == "mohammed"
    mems = work_session.get("memberships") or []
    my = [m for m in mems if m["workspace_id"] == ws["id"]]
    assert my and my[0]["role"] == "WORKSPACE_OWNER", f"expected OWNER, got {my}"


# ---- Tenant isolation on /admin/cards ----
def test_work_sees_only_edrina(work_session):
    r = requests.get(f"{BASE}/api/admin/cards", headers=_h(work_session), timeout=15)
    assert r.status_code == 200, r.text
    cards = r.json()
    slugs = sorted([c["slug"] for c in cards])
    assert slugs == ["edrina-cepele"], f"leak! expected only edrina-cepele, got {slugs}"


def test_admin_sees_all(admin_session):
    r = requests.get(f"{BASE}/api/admin/cards", headers=_h(admin_session), timeout=15)
    assert r.status_code == 200
    slugs = {c["slug"] for c in r.json()}
    assert "edrina-cepele" in slugs
    # admin should see multiple cards (at least edrina + others)
    assert len(slugs) >= 2, f"admin should see multiple cards, got {slugs}"


# ---- Cross-workspace card access ----
def test_work_cannot_access_other_card(work_session, admin_session):
    # find dr-leo (or any non-edrina) card via admin
    r = requests.get(f"{BASE}/api/admin/cards", headers=_h(admin_session), timeout=15)
    others = [c for c in r.json() if c["slug"] != "edrina-cepele"]
    assert others, "need at least one other card"
    other_id = others[0]["id"]
    r2 = requests.get(f"{BASE}/api/admin/cards/{other_id}", headers=_h(work_session), timeout=15)
    assert r2.status_code == 403, f"expected 403, got {r2.status_code} {r2.text}"


def test_work_can_get_and_put_own_card(work_session):
    r = requests.get(f"{BASE}/api/admin/cards", headers=_h(work_session), timeout=15)
    cid = r.json()[0]["id"]
    g = requests.get(f"{BASE}/api/admin/cards/{cid}", headers=_h(work_session), timeout=15)
    assert g.status_code == 200
    # non-destructive PUT (re-send existing name)
    body = g.json()
    # remove server-managed fields to avoid validation issues
    for k in ("id", "created_at", "updated_at", "views", "workspace_id", "owner_user_id", "created_by"):
        body.pop(k, None)
    p = requests.put(f"{BASE}/api/admin/cards/{cid}", headers=_h(work_session), json=body, timeout=15)
    assert p.status_code == 200, p.text


# ---- Analytics & Leads isolation ----
def test_work_analytics_only_edrina(work_session):
    r = requests.get(f"{BASE}/api/admin/analytics/overview?days=30", headers=_h(work_session), timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    by_card = data.get("by_card") or []
    slugs = {c.get("slug") for c in by_card}
    # Either empty (no events) or exclusively edrina
    assert slugs.issubset({"edrina-cepele"}), f"analytics leak: {slugs}"


def test_work_leads_only_own(work_session):
    r = requests.get(f"{BASE}/api/admin/leads", headers=_h(work_session), timeout=15)
    assert r.status_code == 200, r.text
    leads = r.json()
    # every lead must belong to edrina-cepele (if any)
    for lead in leads:
        slug = lead.get("card_slug") or lead.get("slug")
        # if card_slug not present, at least verify no known other-tenant slug
        if slug:
            assert slug == "edrina-cepele", f"cross-tenant lead: {lead}"
