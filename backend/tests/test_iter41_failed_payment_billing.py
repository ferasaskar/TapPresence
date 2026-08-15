"""Iteration 41 — Failed Payment Recovery + Invoice History API tests.
Verifies: /billing payment_state, /billing/invoices auth+empty-state,
/billing/portal 400 with no customer, webhook bad signature 400, and admin regressions.
"""
import os
import time
import requests
import pytest

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@ariadni.id"
ADMIN_PASSWORD = "Ariadni@2026"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="module")
def throwaway_user():
    """Register a fresh non-owner (of admin's workspace) to test permission gate."""
    ts = int(time.time())
    email = f"TEST_iter41_{ts}@example.com"
    password = "TestPass@123"
    r = requests.post(f"{API}/auth/register", json={
        "email": email, "password": password, "name": "Iter41 Tester",
        "workspace_name": f"TEST_iter41_{ts}",
    }, timeout=15)
    assert r.status_code in (200, 201), f"register failed: {r.status_code} {r.text}"
    tok = r.json().get("token")
    assert tok
    return {"email": email, "token": tok}


# ---- /billing ----

class TestBillingPaymentState:
    def test_billing_returns_payment_state(self, admin_headers):
        r = requests.get(f"{API}/billing", headers=admin_headers, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "payment_state" in data, "payment_state missing from /billing"
        ps = data["payment_state"]
        for k in ("failed", "status", "amount_due", "currency",
                  "hosted_invoice_url", "next_attempt", "recovered", "has_customer"):
            assert k in ps, f"payment_state.{k} missing"
        # admin workspace has no Stripe customer -> failed False, has_customer False
        assert ps["failed"] is False, f"expected failed=False, got {ps}"
        assert ps["has_customer"] is False, f"expected has_customer=False, got {ps}"


# ---- /billing/invoices ----

class TestBillingInvoices:
    def test_unauth_returns_401(self):
        r = requests.get(f"{API}/billing/invoices", timeout=15)
        assert r.status_code in (401, 403), r.status_code

    def test_admin_no_customer_empty(self, admin_headers):
        r = requests.get(f"{API}/billing/invoices", headers=admin_headers, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("has_customer") is False
        assert data.get("invoices") == []

    def test_throwaway_owner_can_call_own(self, throwaway_user):
        """A workspace owner IS an admin of their OWN workspace — verify they get their own empty list."""
        h = {"Authorization": f"Bearer {throwaway_user['token']}"}
        r = requests.get(f"{API}/billing/invoices", headers=h, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        # own workspace: allowed, empty (no customer)
        assert data.get("has_customer") is False
        assert data.get("invoices") == []


# ---- /billing/portal ----

class TestBillingPortal:
    def test_unauth_401(self):
        r = requests.post(f"{API}/billing/portal", timeout=15)
        assert r.status_code in (401, 403)

    def test_no_customer_returns_400(self, admin_headers):
        r = requests.post(f"{API}/billing/portal", headers=admin_headers, timeout=15)
        assert r.status_code == 400, r.text
        msg = (r.json().get("detail") or "").lower()
        assert "stripe customer" in msg or "no stripe" in msg, r.json()


# ---- Webhook signature ----

class TestStripeWebhookSignature:
    def test_bad_signature_returns_400(self):
        r = requests.post(f"{API}/stripe/webhook",
                          data=b'{"id":"evt_bogus","type":"invoice.paid","data":{"object":{}}}',
                          headers={"stripe-signature": "t=1,v1=bogus", "Content-Type": "application/json"},
                          timeout=15)
        assert r.status_code == 400, f"expected 400, got {r.status_code} {r.text}"

    def test_missing_signature_returns_400(self):
        r = requests.post(f"{API}/stripe/webhook",
                          data=b'{"id":"evt_bogus","type":"invoice.paid","data":{"object":{}}}',
                          headers={"Content-Type": "application/json"}, timeout=15)
        assert r.status_code == 400


# ---- Regression: checkout still creates tax-safe session ----

class TestCheckoutRegression:
    def test_pro_year_checkout_tax_safe(self, admin_headers):
        r = requests.post(f"{API}/billing/checkout", headers=admin_headers, json={
            "plan": "pro", "interval": "year", "seats": 1, "market": "USD",
            "origin_url": BASE_URL,
        }, timeout=30)
        # Preview may return 200 with checkout_url; if Stripe misconfigured, log
        assert r.status_code == 200, f"checkout failed: {r.status_code} {r.text}"
        data = r.json()
        assert data.get("checkout_url", "").startswith("https://"), data


# ---- Regression: existing endpoints ----

class TestOtherEndpointsRegression:
    def test_usage_overview(self, admin_headers):
        r = requests.get(f"{API}/admin/control/usage/overview", headers=admin_headers, timeout=15)
        assert r.status_code == 200, r.text

    def test_ai_panels_reachable(self, admin_headers):
        # sanity — either 200 or a documented status
        r = requests.get(f"{API}/admin/control/ai/config", headers=admin_headers, timeout=15)
        assert r.status_code in (200, 404), r.status_code

    def test_trial_eligible_flag_present(self, admin_headers):
        r = requests.get(f"{API}/billing", headers=admin_headers, timeout=15)
        assert r.status_code == 200
        assert "trial_eligible" in r.json()
