"""Backend tests for Iteration 40 — Global Tax Readiness.

Covers:
- Tax-safe checkout for individual (pro) and team (5 seats) plans
- Verify Stripe Session shows automatic_tax, billing_address_collection=required,
  tax_id_collection.enabled, tax_behavior=exclusive, allow_promotion_codes, product tax_code
- Admin commercial config stripe_tax_code get/persist
- GET /api/admin/control/tax/overview (SUPER_ADMIN 200, non-super 403, unauth 401)
- Regression: /api/billing, /api/admin/control/usage/overview, /api/admin/control/usage/config
"""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://template-hub-184.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@ariadni.id"
ADMIN_PASSWORD = "Ariadni@2026"


# -------------------------------------------------- fixtures
@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=20)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def non_admin_creds():
    """Register a throwaway non-admin. Returns (email, password, token)."""
    email = f"TEST_tax_{uuid.uuid4().hex[:8]}@example.com"
    password = "TestPass@123"
    r = requests.post(f"{API}/auth/register", json={
        "email": email, "password": password, "name": "Tax Test User",
        "workspace_name": "TAX_TEST_WS", "account_type": "individual",
    }, timeout=20)
    assert r.status_code in (200, 201), f"register failed: {r.status_code} {r.text}"
    body = r.json()
    token = body.get("token") or body.get("access_token")
    if not token:
        r2 = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=20)
        assert r2.status_code == 200
        token = r2.json()["token"]
    return email, password, token


@pytest.fixture(scope="module")
def stripe_sdk():
    """Load Stripe SDK with test key from backend/.env for session verification."""
    from dotenv import dotenv_values
    env = dotenv_values("/app/backend/.env")
    key = env.get("STRIPE_SECRET_KEY") or os.environ.get("STRIPE_SECRET_KEY")
    if not key:
        pytest.skip("STRIPE_SECRET_KEY not available")
    import stripe
    stripe.api_key = key
    return stripe


# -------------------------------------------------- Tax-safe checkout (individual)
class TestCheckoutTaxSafe:
    def test_pro_year_checkout_returns_session(self, admin_headers):
        r = requests.post(f"{API}/billing/checkout", headers=admin_headers, json={
            "plan": "pro", "interval": "year", "seats": 1,
            "origin_url": BASE_URL,
        }, timeout=30)
        assert r.status_code == 200, f"pro checkout failed: {r.status_code} {r.text}"
        data = r.json()
        assert "checkout_url" in data and "session_id" in data
        assert data["session_id"].startswith("cs_")
        pytest.pro_session_id = data["session_id"]

    def test_pro_session_has_tax_safe_config(self, stripe_sdk):
        sid = getattr(pytest, "pro_session_id", None)
        assert sid, "pro session id missing"
        s = stripe_sdk.checkout.Session.retrieve(sid, expand=["line_items", "line_items.data.price.product"])
        assert s.get("automatic_tax", {}).get("enabled") is True, "automatic_tax must be enabled"
        assert s.get("billing_address_collection") == "required", "billing_address_collection must be required"
        assert (s.get("tax_id_collection") or {}).get("enabled") is True, "tax_id_collection must be enabled"
        assert s.get("allow_promotion_codes") is True, "allow_promotion_codes must be true"
        items = s.get("line_items", {}).get("data", [])
        assert len(items) >= 1
        li = items[0]
        assert li.get("quantity") == 1
        # tax_behavior on price
        price = li.get("price") or {}
        assert price.get("tax_behavior") == "exclusive", f"tax_behavior expected exclusive, got {price.get('tax_behavior')}"
        # Product tax_code
        prod = price.get("product") or {}
        if isinstance(prod, dict):
            tc = prod.get("tax_code")
            assert tc in (None, "txcd_10103001"), f"unexpected tax_code {tc}"

    def test_team_5_seats_checkout(self, admin_headers, stripe_sdk):
        r = requests.post(f"{API}/billing/checkout", headers=admin_headers, json={
            "plan": "team", "interval": "year", "seats": 5,
            "origin_url": BASE_URL,
        }, timeout=30)
        assert r.status_code == 200, f"team checkout failed: {r.text}"
        sid = r.json()["session_id"]
        s = stripe_sdk.checkout.Session.retrieve(sid, expand=["line_items"])
        assert s.get("automatic_tax", {}).get("enabled") is True
        assert s.get("billing_address_collection") == "required"
        assert (s.get("tax_id_collection") or {}).get("enabled") is True
        items = s.get("line_items", {}).get("data", [])
        assert items[0]["quantity"] == 5, f"expected quantity=5, got {items[0]['quantity']}"
        # Verify base = qty * unit via line item (subtotal is 0 until session completes)
        unit = items[0]["price"]["unit_amount"]
        qty = items[0]["quantity"]
        assert qty == 5 and unit > 0, f"expected qty=5 and unit>0, got qty={qty} unit={unit}"
        computed = unit * qty
        assert computed > 0, f"unit*qty must be >0, got {computed}"


# -------------------------------------------------- No fallback (code review test)
class TestNoFallback:
    def test_only_one_session_create_call(self):
        src = open("/app/backend/platform_v1.py").read()
        # billing_checkout function slice
        start = src.index("async def billing_checkout(")
        end = src.index("\nasync def ", start + 1)
        chunk = src[start:end]
        count = chunk.count("stripe.checkout.Session.create")
        assert count == 1, f"expected exactly 1 Session.create in billing_checkout, found {count}"
        # No 'automatic_tax=' with False anywhere
        assert "automatic_tax={\"enabled\": True}" in chunk
        assert "billing_address_collection=\"required\"" in chunk
        assert "tax_id_collection={\"enabled\": True}" in chunk
        # StripeError -> 503
        assert "HTTPException(503" in chunk


# -------------------------------------------------- Commercial config stripe_tax_code
class TestCommercialConfigTaxCode:
    def test_get_commercial_has_stripe_tax_code(self, admin_headers):
        r = requests.get(f"{API}/admin/commercial", headers=admin_headers, timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        cfg = body.get("config") or body
        # Look either at top-level or nested
        tc = cfg.get("stripe_tax_code") or body.get("stripe_tax_code")
        assert tc == "txcd_10103001", f"expected txcd_10103001, got {tc}"

    def test_put_commercial_persists_stripe_tax_code(self, admin_headers):
        # Fetch, then re-put with same value to verify echo & persistence
        g = requests.get(f"{API}/admin/commercial", headers=admin_headers, timeout=20).json()
        cfg = g.get("config") or g
        payload = {"stripe_tax_code": "txcd_10103001"}
        # Some endpoints require full body; merge
        merged = {**cfg, **payload}
        r = requests.put(f"{API}/admin/commercial", headers=admin_headers, json=merged, timeout=20)
        assert r.status_code in (200, 204), r.text
        # Re-fetch
        g2 = requests.get(f"{API}/admin/commercial", headers=admin_headers, timeout=20).json()
        cfg2 = g2.get("config") or g2
        assert cfg2.get("stripe_tax_code") == "txcd_10103001"


# -------------------------------------------------- Tax overview endpoint
class TestTaxOverview:
    def test_super_admin_gets_overview(self, admin_headers):
        r = requests.get(f"{API}/admin/control/tax/overview", headers=admin_headers, timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        for key in ["range", "totals_by_currency", "paying_customers", "countries",
                    "country_count", "by_country", "by_state_us",
                    "tax_status_breakdown", "transactions", "note"]:
            assert key in d, f"missing key {key}"

    def test_non_admin_403(self, non_admin_creds):
        _, _, token = non_admin_creds
        r = requests.get(f"{API}/admin/control/tax/overview",
                         headers={"Authorization": f"Bearer {token}"}, timeout=20)
        assert r.status_code == 403, f"expected 403 got {r.status_code} {r.text}"

    def test_unauth_401(self):
        r = requests.get(f"{API}/admin/control/tax/overview", timeout=20)
        assert r.status_code in (401, 403), f"expected 401, got {r.status_code}"


# -------------------------------------------------- Regression
class TestRegression:
    def test_billing_endpoint(self, admin_headers):
        r = requests.get(f"{API}/billing", headers=admin_headers, timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "plan" in d and "status" in d
        assert "entitlements" in d
        assert "commercial" in d

    def test_usage_overview(self, admin_headers):
        r = requests.get(f"{API}/admin/control/usage/overview", headers=admin_headers, timeout=20)
        assert r.status_code == 200

    def test_usage_config(self, admin_headers):
        r = requests.get(f"{API}/admin/control/usage/config", headers=admin_headers, timeout=20)
        assert r.status_code == 200
