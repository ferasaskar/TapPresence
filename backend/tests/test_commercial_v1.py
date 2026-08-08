"""ARIADNI ID Commercial V1 — backend tests.

Covers regression + commercial auth, multi-tenant isolation, feature flags,
NFC lifecycle & redirect, CRM leads, campaigns, contact exchange, AI follow-up.
"""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@ariadni.id"
ADMIN_PASSWORD = "Ariadni@2026"
DEMO_SLUG = "feras-askar"


# ---------------- shared fixtures ----------------
@pytest.fixture(scope="session")
def admin_login():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture(scope="session")
def admin_token(admin_login):
    return admin_login["token"]


@pytest.fixture(scope="session")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="session")
def tenant_user():
    """A throwaway registered user + workspace. Deleted at end."""
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    password = "Test@1234"
    r = requests.post(f"{API}/auth/register", json={
        "email": email, "password": password, "name": "Test User",
        "workspace_name": "TEST_WS",
    }, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    yield {"email": email, "password": password, **data}
    # cleanup
    try:
        requests.delete(f"{API}/account", headers={"Authorization": f"Bearer {data['token']}"}, timeout=30)
    except Exception:
        pass


@pytest.fixture(scope="session")
def tenant_headers(tenant_user):
    return {"Authorization": f"Bearer {tenant_user['token']}"}


# ============================================================
# 1) REGRESSION — existing endpoints
# ============================================================
class TestRegression:
    def test_login_returns_commercial_payload(self, admin_login):
        d = admin_login
        assert "token" in d and "refresh_token" in d
        assert d["user"]["role"] == "SUPER_ADMIN"
        assert d.get("workspace") is not None
        assert "entitlements" in d
        assert d["entitlements"].get("plan") in ("enterprise", "team", "white_label")

    def test_admin_cards_lists_feras(self, admin_headers):
        r = requests.get(f"{API}/admin/cards", headers=admin_headers, timeout=30)
        assert r.status_code == 200
        assert any(c["slug"] == DEMO_SLUG for c in r.json())

    def test_public_feras_card(self):
        r = requests.get(f"{API}/cards/{DEMO_SLUG}", timeout=30)
        assert r.status_code == 200
        assert r.json()["slug"] == DEMO_SLUG

    def test_public_qr_png(self):
        r = requests.get(f"{API}/cards/{DEMO_SLUG}/qr", timeout=30)
        assert r.status_code == 200
        assert r.content[:8] == b"\x89PNG\r\n\x1a\n"

    def test_public_poster_png(self):
        r = requests.get(f"{API}/cards/{DEMO_SLUG}/poster", timeout=60)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("image/png")

    def test_public_lead_create(self):
        r = requests.post(f"{API}/cards/{DEMO_SLUG}/leads", json={
            "name": "TEST_reg_lead", "email": "reg@test.com", "message": "regression",
        }, timeout=30)
        assert r.status_code == 200


# ============================================================
# 2) Commercial Auth
# ============================================================
class TestCommercialAuth:
    def test_register_creates_owner(self, tenant_user):
        assert tenant_user["user"]["role"] == "WORKSPACE_OWNER"
        assert tenant_user["user"]["email_verified"] is False
        assert tenant_user["workspace"]["name"] == "TEST_WS"
        assert tenant_user["entitlements"]["plan"] == "free"

    def test_register_duplicate_email(self, tenant_user):
        r = requests.post(f"{API}/auth/register", json={
            "email": tenant_user["email"], "password": "Whatever@1",
            "name": "Dup", "workspace_name": "Dup WS",
        }, timeout=30)
        assert r.status_code == 400

    def test_refresh_rotates_and_old_invalidated(self, tenant_user):
        old = tenant_user["refresh_token"]
        r = requests.post(f"{API}/auth/refresh", json={"refresh_token": old}, timeout=30)
        assert r.status_code == 200
        new = r.json()["refresh_token"]
        assert new and new != old
        # Reusing old should now fail
        r2 = requests.post(f"{API}/auth/refresh", json={"refresh_token": old}, timeout=30)
        assert r2.status_code == 401
        # Update stored refresh so downstream logout works
        tenant_user["refresh_token"] = new

    def test_session_endpoint(self, tenant_headers, tenant_user):
        r = requests.get(f"{API}/auth/session", headers=tenant_headers, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["user"]["email"] == tenant_user["email"]
        assert "entitlements" in d
        assert d["workspace"]["id"] == tenant_user["workspace"]["id"]

    def test_forgot_password_always_ok(self):
        r = requests.post(f"{API}/auth/forgot-password", json={"email": "nope@example.com"}, timeout=30)
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_logout_revokes_refresh(self, tenant_user):
        # Login a fresh session so we can revoke without breaking the shared token
        r = requests.post(f"{API}/auth/login", json={
            "email": tenant_user["email"], "password": tenant_user["password"]
        }, timeout=30)
        assert r.status_code == 200
        refresh = r.json()["refresh_token"]
        rl = requests.post(f"{API}/auth/logout", json={"refresh_token": refresh}, timeout=30)
        assert rl.status_code == 200
        r2 = requests.post(f"{API}/auth/refresh", json={"refresh_token": refresh}, timeout=30)
        assert r2.status_code == 401


# ============================================================
# 3) Multi-tenancy (critical)
# ============================================================
class TestMultiTenancy:
    def test_new_user_sees_zero_cards(self, tenant_headers):
        r = requests.get(f"{API}/admin/cards", headers=tenant_headers, timeout=30)
        assert r.status_code == 200
        cards = r.json()
        assert isinstance(cards, list)
        assert len(cards) == 0, f"Tenant should see 0 cards; got {[c.get('slug') for c in cards]}"

    def test_tenant_cannot_read_admin_card_by_id(self, tenant_headers, admin_headers):
        # get feras-askar id via admin
        r = requests.get(f"{API}/admin/cards", headers=admin_headers, timeout=30)
        feras = next(c for c in r.json() if c["slug"] == DEMO_SLUG)
        card_id = feras["id"]
        rg = requests.get(f"{API}/admin/cards/{card_id}", headers=tenant_headers, timeout=30)
        assert rg.status_code == 403

    def test_tenant_cannot_update_admin_card(self, tenant_headers, admin_headers):
        r = requests.get(f"{API}/admin/cards", headers=admin_headers, timeout=30)
        feras = next(c for c in r.json() if c["slug"] == DEMO_SLUG)
        card_id = feras["id"]
        ru = requests.put(f"{API}/admin/cards/{card_id}", headers=tenant_headers,
                          json={"slug": DEMO_SLUG, "status": "draft"}, timeout=30)
        assert ru.status_code == 403

    def test_tenant_cannot_delete_admin_card(self, tenant_headers, admin_headers):
        r = requests.get(f"{API}/admin/cards", headers=admin_headers, timeout=30)
        feras = next(c for c in r.json() if c["slug"] == DEMO_SLUG)
        rd = requests.delete(f"{API}/admin/cards/{feras['id']}", headers=tenant_headers, timeout=30)
        assert rd.status_code == 403

    def test_super_admin_sees_all(self, admin_headers):
        r = requests.get(f"{API}/admin/cards", headers=admin_headers, timeout=30)
        assert r.status_code == 200
        assert len(r.json()) >= 1


# ============================================================
# 4) Feature flags / config
# ============================================================
class TestConfig:
    def test_config_flags(self):
        r = requests.get(f"{API}/config", timeout=30)
        assert r.status_code == 200
        integ = r.json()["integrations"]
        assert integ["ai"] is True, "EMERGENT_LLM_KEY expected configured"
        for k in ("stripe", "apple_wallet", "google_wallet", "email", "enrichment",
                  "revenuecat", "hubspot", "salesforce", "pipedrive"):
            assert integ[k] is False, f"{k} should be Not Configured"


# ============================================================
# 5) NFC
# ============================================================
class TestNFC:
    @pytest.fixture(scope="class")
    def minted_token(self, admin_headers):
        r = requests.post(f"{API}/admin/nfc/mint", headers=admin_headers,
                          json={"count": 1, "material": "standard"}, timeout=30)
        assert r.status_code == 200, r.text
        return r.json()["tokens"][0]

    def test_mint_forbidden_for_non_admin(self, tenant_headers):
        r = requests.post(f"{API}/admin/nfc/mint", headers=tenant_headers,
                          json={"count": 1}, timeout=30)
        assert r.status_code == 403

    def test_tap_before_activation_redirects_to_activate(self, minted_token):
        r = requests.get(f"{API}/t/{minted_token}", allow_redirects=False, timeout=30)
        assert r.status_code == 307
        assert "/activate?token=" in r.headers.get("location", "")

    def test_activate_wrong_ownership_forbidden(self, minted_token, tenant_headers, admin_headers):
        # get feras-askar id (owned by admin ws)
        r = requests.get(f"{API}/admin/cards", headers=admin_headers, timeout=30)
        card_id = next(c for c in r.json() if c["slug"] == DEMO_SLUG)["id"]
        ra = requests.post(f"{API}/nfc/activate", headers=tenant_headers,
                           json={"token": minted_token, "card_id": card_id}, timeout=30)
        assert ra.status_code == 403

    def test_activate_and_tap_redirects_to_profile(self, minted_token, admin_headers):
        r = requests.get(f"{API}/admin/cards", headers=admin_headers, timeout=30)
        card_id = next(c for c in r.json() if c["slug"] == DEMO_SLUG)["id"]
        ra = requests.post(f"{API}/nfc/activate", headers=admin_headers,
                           json={"token": minted_token, "card_id": card_id}, timeout=30)
        assert ra.status_code == 200
        rt = requests.get(f"{API}/t/{minted_token}", allow_redirects=False, timeout=30)
        assert rt.status_code == 307
        loc = rt.headers.get("location", "")
        assert DEMO_SLUG in loc and "src=nfc" in loc

    def test_deactivate(self, minted_token, admin_headers):
        r = requests.post(f"{API}/nfc/devices/{minted_token}/status", headers=admin_headers,
                          json={"status": "DEACTIVATED"}, timeout=30)
        assert r.status_code == 200
        # After deactivation, tap should go to /activate
        rt = requests.get(f"{API}/t/{minted_token}", allow_redirects=False, timeout=30)
        assert rt.status_code == 307
        assert "/activate?token=" in rt.headers.get("location", "")


# ============================================================
# 6) Contact exchange
# ============================================================
class TestExchange:
    def test_exchange_creates_lead(self):
        r = requests.post(f"{API}/cards/{DEMO_SLUG}/exchange", json={
            "name": "TEST_Exchange", "email": "ex@test.com", "company": "TestCo",
            "interest": "chat", "consent": True,
        }, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d.get("ok") is True
        assert d["owner"]["vcard_url"].endswith(f"/cards/{DEMO_SLUG}/vcard")

    def test_exchange_missing_name(self):
        r = requests.post(f"{API}/cards/{DEMO_SLUG}/exchange", json={
            "name": "", "email": "x@x.com",
        }, timeout=30)
        assert r.status_code == 400

    def test_exchange_missing_email_and_phone(self):
        r = requests.post(f"{API}/cards/{DEMO_SLUG}/exchange", json={
            "name": "TEST_NoContact",
        }, timeout=30)
        assert r.status_code == 400


# ============================================================
# 7) CRM
# ============================================================
class TestCRM:
    @pytest.fixture(scope="class")
    def admin_lead_id(self):
        r = requests.post(f"{API}/cards/{DEMO_SLUG}/exchange", json={
            "name": "TEST_CRM_Lead", "email": "crm@test.com", "consent": True,
        }, timeout=30)
        assert r.status_code == 200
        # fetch id via admin
        r2 = requests.post(f"{API}/auth/login", json={
            "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
        tok = r2.json()["token"]
        rl = requests.get(f"{API}/crm/leads", headers={"Authorization": f"Bearer {tok}"}, timeout=30)
        assert rl.status_code == 200
        leads = rl.json()
        lead = next(l for l in leads if l.get("name") == "TEST_CRM_Lead")
        return lead["id"]

    def test_crm_leads_list(self, admin_headers):
        r = requests.get(f"{API}/crm/leads", headers=admin_headers, timeout=30)
        assert r.status_code == 200
        leads = r.json()
        assert isinstance(leads, list)
        # At least the exchange-created leads must carry status
        exchanged = [l for l in leads if l.get("source") == "profile_exchange"]
        assert exchanged, "No profile_exchange leads found"
        assert all("status" in l for l in exchanged)

    def test_crm_patch_status_valid(self, admin_headers, admin_lead_id):
        r = requests.patch(f"{API}/crm/leads/{admin_lead_id}", headers=admin_headers,
                           json={"status": "CONTACTED"}, timeout=30)
        assert r.status_code == 200
        assert r.json()["status"] == "CONTACTED"

    def test_crm_patch_status_invalid(self, admin_headers, admin_lead_id):
        r = requests.patch(f"{API}/crm/leads/{admin_lead_id}", headers=admin_headers,
                           json={"status": "INVALID_XYZ"}, timeout=30)
        assert r.status_code == 400

    def test_crm_activities_records_change(self, admin_headers, admin_lead_id):
        r = requests.get(f"{API}/crm/leads/{admin_lead_id}/activities", headers=admin_headers, timeout=30)
        assert r.status_code == 200
        acts = r.json()
        assert any("status" in a.get("change", {}) for a in acts)

    def test_crm_csv_export(self, admin_headers):
        r = requests.get(f"{API}/crm/leads.csv", headers=admin_headers, timeout=30)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("text/csv")
        assert b"name,email,phone" in r.content

    def test_tenant_cannot_patch_admin_lead(self, tenant_headers, admin_lead_id):
        r = requests.patch(f"{API}/crm/leads/{admin_lead_id}", headers=tenant_headers,
                           json={"status": "WON"}, timeout=30)
        assert r.status_code == 403


# ============================================================
# 8) Campaigns
# ============================================================
class TestCampaigns:
    def test_create_and_duplicate(self, admin_headers):
        code = f"TEST_C_{uuid.uuid4().hex[:6]}"
        r = requests.post(f"{API}/campaigns", headers=admin_headers,
                          json={"name": "TEST Camp", "code": code}, timeout=30)
        assert r.status_code == 200, r.text
        # duplicate
        r2 = requests.post(f"{API}/campaigns", headers=admin_headers,
                           json={"name": "TEST Camp 2", "code": code}, timeout=30)
        assert r2.status_code == 400
        # list
        rl = requests.get(f"{API}/campaigns", headers=admin_headers, timeout=30)
        assert rl.status_code == 200
        camp = next(c for c in rl.json() if c["code"] == code)
        # stats
        rs = requests.get(f"{API}/campaigns/{camp['id']}/stats", headers=admin_headers, timeout=30)
        assert rs.status_code == 200
        d = rs.json()
        assert "events" in d and "leads" in d


# ============================================================
# 9) AI follow-up
# ============================================================
class TestAI:
    def test_followup_returns_template_draft(self, admin_headers):
        r = requests.post(f"{API}/ai/followup", headers=admin_headers, json={
            "lead_name": "Alice Smith", "notes": "wants portfolio",
            "owner_name": "Feras", "tone": "warm", "channel": "email",
        }, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["provider"] == "template"
        assert isinstance(d.get("draft"), str) and len(d["draft"]) > 20
        assert d.get("note")

    def test_enrich_not_configured(self, admin_headers):
        r = requests.post(f"{API}/ai/enrich", headers=admin_headers, json={"email": "x@x.com"}, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["configured"] is False
        assert "Not Configured" in d.get("message", "")
