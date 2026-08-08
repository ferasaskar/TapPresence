"""Backend tests for iteration_2 features: leads, tracking, analytics, poster."""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@ariadni.id"
ADMIN_PASSWORD = "Ariadni@2026"
DEMO_SLUG = "feras-askar"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture
def headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="module")
def demo_card_id(admin_token):
    r = requests.get(f"{API}/admin/cards", headers={"Authorization": f"Bearer {admin_token}"}, timeout=30)
    assert r.status_code == 200
    for c in r.json():
        if c["slug"] == DEMO_SLUG:
            return c["id"]
    pytest.fail("demo card not found")


# -------------------- Leads --------------------
class TestLeads:
    def test_create_lead_ok(self):
        body = {"name": "TEST_Lead", "email": "tlead@example.com", "message": "hello"}
        r = requests.post(f"{API}/cards/{DEMO_SLUG}/leads", json=body, timeout=30)
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True

    def test_create_lead_404_for_unknown_slug(self):
        r = requests.post(f"{API}/cards/nope-{uuid.uuid4().hex[:6]}/leads",
                          json={"name": "X", "email": "a@a.com"}, timeout=30)
        assert r.status_code == 404

    def test_create_lead_400_missing_name(self):
        r = requests.post(f"{API}/cards/{DEMO_SLUG}/leads",
                          json={"name": "", "email": "x@y.com"}, timeout=30)
        assert r.status_code == 400

    def test_create_lead_400_missing_contact(self):
        r = requests.post(f"{API}/cards/{DEMO_SLUG}/leads",
                          json={"name": "NoContact", "email": "", "phone": ""}, timeout=30)
        assert r.status_code == 400

    def test_admin_leads_requires_auth(self):
        assert requests.get(f"{API}/admin/leads", timeout=30).status_code == 401

    def test_admin_leads_list_and_patch_delete(self, headers):
        # create one
        unique_name = f"TEST_{uuid.uuid4().hex[:8]}"
        cr = requests.post(f"{API}/cards/{DEMO_SLUG}/leads",
                           json={"name": unique_name, "email": "x@y.com", "message": "hi"}, timeout=30)
        assert cr.status_code == 200

        r = requests.get(f"{API}/admin/leads", headers=headers, timeout=30)
        assert r.status_code == 200
        leads = r.json()
        assert isinstance(leads, list)
        match = [l for l in leads if l["name"] == unique_name]
        assert match, "created lead not found"
        lead = match[0]
        assert lead["read"] is False

        # PATCH -> mark read
        p = requests.patch(f"{API}/admin/leads/{lead['id']}", headers=headers, timeout=30)
        assert p.status_code == 200

        # verify persisted
        r2 = requests.get(f"{API}/admin/leads", headers=headers, timeout=30)
        got = [l for l in r2.json() if l["id"] == lead["id"]][0]
        assert got["read"] is True

        # DELETE
        d = requests.delete(f"{API}/admin/leads/{lead['id']}", headers=headers, timeout=30)
        assert d.status_code == 200
        r3 = requests.get(f"{API}/admin/leads", headers=headers, timeout=30)
        assert not any(l["id"] == lead["id"] for l in r3.json())


# -------------------- Tracking / Analytics --------------------
class TestAnalytics:
    def test_track_view(self):
        r = requests.post(f"{API}/cards/{DEMO_SLUG}/track", json={"type": "view"}, timeout=30)
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_track_scan(self):
        r = requests.post(f"{API}/cards/{DEMO_SLUG}/track", json={"type": "scan"}, timeout=30)
        assert r.status_code == 200

    def test_track_tap(self):
        r = requests.post(f"{API}/cards/{DEMO_SLUG}/track", json={"type": "tap", "key": "call"}, timeout=30)
        assert r.status_code == 200

    def test_analytics_requires_auth(self, demo_card_id):
        r = requests.get(f"{API}/admin/cards/{demo_card_id}/analytics", timeout=30)
        assert r.status_code == 401

    def test_analytics_shape_and_counts_increase(self, headers, demo_card_id):
        # baseline
        r0 = requests.get(f"{API}/admin/cards/{demo_card_id}/analytics", headers=headers, timeout=30)
        assert r0.status_code == 200
        base = r0.json()
        for k in ("views", "scans", "taps", "tapsByKey", "leads"):
            assert k in base

        # fire events
        requests.post(f"{API}/cards/{DEMO_SLUG}/track", json={"type": "view"}, timeout=30)
        requests.post(f"{API}/cards/{DEMO_SLUG}/track", json={"type": "scan"}, timeout=30)
        requests.post(f"{API}/cards/{DEMO_SLUG}/track", json={"type": "tap", "key": "call"}, timeout=30)

        r1 = requests.get(f"{API}/admin/cards/{demo_card_id}/analytics", headers=headers, timeout=30)
        assert r1.status_code == 200
        now = r1.json()
        assert now["views"] >= base["views"] + 1
        assert now["scans"] >= base["scans"] + 1
        assert now["taps"] >= base["taps"] + 1
        assert now["tapsByKey"].get("call", 0) >= (base["tapsByKey"].get("call", 0) + 1)


# -------------------- QR / Poster --------------------
class TestQRPoster:
    def test_qr_png(self):
        r = requests.get(f"{API}/cards/{DEMO_SLUG}/qr", timeout=30)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("image/png")
        assert r.content[:8] == b"\x89PNG\r\n\x1a\n"

    def test_poster_png_attachment(self):
        r = requests.get(f"{API}/cards/{DEMO_SLUG}/poster", timeout=60)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("image/png")
        assert "attachment" in r.headers.get("content-disposition", "").lower()
        assert len(r.content) > 5000  # non-trivial size
        assert r.content[:8] == b"\x89PNG\r\n\x1a\n"
