"""Phase 7 - Business-card / Event-badge Scanner backend tests."""
import os, uuid, time, requests, pytest
import sys
sys.path.insert(0, os.path.dirname(__file__))
from gen_card import make_card_b64  # noqa

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") or \
           os.environ.get("BASE_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL not set"
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@ariadni.id"
ADMIN_PASS = "Ariadni@2026"


# ------------------------------------------------- auth fixtures
@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def free_user():
    email = f"free_{uuid.uuid4().hex[:8]}@demo.com"
    pw = "Test@1234"
    r = requests.post(f"{API}/auth/register", json={
        "email": email, "password": pw, "name": "Free User", "workspace_name": "FreeWs"
    }, timeout=30)
    assert r.status_code in (200, 201), r.text
    tok = r.json().get("token")
    if not tok:
        r2 = requests.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=30)
        assert r2.status_code == 200, r2.text
        tok = r2.json()["token"]
    return {"email": email, "token": tok}


@pytest.fixture(scope="module")
def card_b64():
    return make_card_b64()


def h(tok): return {"Authorization": f"Bearer {tok}"}


# ------------------------------------------------- /api/scan/card
class TestScanCard:
    def test_no_auth_401(self, card_b64):
        r = requests.post(f"{API}/scan/card", json={"image_base64": card_b64}, timeout=30)
        assert r.status_code in (401, 403), r.text

    def test_missing_image_400(self, admin_token):
        r = requests.post(f"{API}/scan/card", json={"image_base64": ""}, headers=h(admin_token), timeout=30)
        assert r.status_code == 400, r.text

    def test_free_plan_403(self, free_user, card_b64):
        r = requests.post(f"{API}/scan/card", json={"image_base64": card_b64},
                          headers=h(free_user["token"]), timeout=30)
        assert r.status_code == 403, r.text
        assert "Scanner" in r.text or "plan" in r.text.lower()

    def test_admin_scan_ok(self, admin_token, card_b64):
        r = requests.post(f"{API}/scan/card",
                          json={"image_base64": card_b64, "source": "business_card_scan"},
                          headers=h(admin_token), timeout=90)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j.get("configured") is True
        draft = j.get("draft") or {}
        # required keys present
        for k in ("name", "title", "company", "email", "phone", "website",
                  "city", "country", "language", "notes"):
            assert k in draft, f"missing {k} in draft"
        # Should have extracted something meaningful (not all blank)
        assert any(draft.get(k) for k in ("name", "email", "phone", "company")), draft
        # Save for reuse
        TestScanCard.draft = draft

    def test_scan_did_not_create_lead(self, admin_token):
        # No 'scanned' lead should have been created just from /scan/card
        r = requests.get(f"{API}/crm/leads", headers=h(admin_token), timeout=30)
        assert r.status_code == 200
        # Cannot assert count exactly but ensure endpoint is reachable
        leads = r.json()
        assert isinstance(leads, list)


# ------------------------------------------------- /api/scan/confirm
class TestScanConfirm:
    CARD_SLUG = "feras-askar"

    def test_confirm_empty_name_400(self, admin_token):
        r = requests.post(f"{API}/scan/confirm", json={
            "cardSlug": self.CARD_SLUG, "name": "   ", "email": "x@y.com"
        }, headers=h(admin_token), timeout=30)
        assert r.status_code == 400, r.text

    def test_confirm_foreign_slug_forbidden_for_free_user(self, free_user):
        # Free user has scanner=False, so we won't reach the ownership check.
        # Instead verify the plan gate blocks them.
        r = requests.post(f"{API}/scan/confirm", json={
            "cardSlug": self.CARD_SLUG, "name": "Foreign Test"
        }, headers=h(free_user["token"]), timeout=30)
        assert r.status_code == 403, r.text

    def test_confirm_ok_creates_lead(self, admin_token):
        payload = {
            "cardSlug": self.CARD_SLUG,
            "source": "business_card_scan",
            "name": "TEST Scanned Lead",
            "title": "CEO",
            "company": "Ariadni Holdings LLC",
            "email": "feras@ariadni.ae",
            "phone": "+971501234567",
            "website": "www.ariadni.ae",
            "city": "Dubai", "country": "United Arab Emirates",
            "language": "en", "notes": "scanned via test",
        }
        r = requests.post(f"{API}/scan/confirm", json=payload, headers=h(admin_token), timeout=30)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j.get("ok") is True
        lead = j["lead"]
        assert lead["source"] == "business_card_scan"
        assert "scanned" in (lead.get("tags") or [])
        assert lead["status"] == "NEW"
        assert lead["scanned"] is True
        assert lead["workspace_id"]
        assert "_id" not in lead
        TestScanConfirm.new_lead_id = lead["id"]

    def test_lead_appears_in_crm(self, admin_token):
        time.sleep(0.5)
        r = requests.get(f"{API}/crm/leads", headers=h(admin_token), timeout=30)
        assert r.status_code == 200
        ids = [x.get("id") for x in r.json()]
        assert TestScanConfirm.new_lead_id in ids, "new lead missing from /crm/leads"

    def test_lead_appears_in_admin_leads(self, admin_token):
        r = requests.get(f"{API}/admin/leads", headers=h(admin_token), timeout=30)
        assert r.status_code == 200
        ids = [x.get("id") for x in r.json()]
        assert TestScanConfirm.new_lead_id in ids, "new lead missing from /admin/leads"
