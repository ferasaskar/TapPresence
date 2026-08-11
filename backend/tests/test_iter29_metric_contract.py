"""Iteration 29 — Control Center P0 data-integrity + IA fix.

Verifies the metric contract:
  - Users vs Customer Accounts separated
  - Accounts categories mutually exclusive (individual + company + enterprise == total)
  - No 'free' plan key in plan_distribution
  - No 'ARIADNI' leakage; internal workspace displays as 'TapPresence HQ'
  - Money metrics all None, money_available False
  - include_internal toggle changes numbers
  - Authorization: 403 for normal customer on all /admin/control/* endpoints
  - Subscriptions endpoint truthful (no 'free' label)
"""
import os
import pytest
import requests
from pathlib import Path

def _load_url():
    u = os.environ.get("REACT_APP_BACKEND_URL")
    if u:
        return u
    env = Path("/app/frontend/.env").read_text()
    for line in env.splitlines():
        if line.startswith("REACT_APP_BACKEND_URL="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("REACT_APP_BACKEND_URL not set")

BASE = _load_url().rstrip("/")
ADMIN = {"email": "admin@ariadni.id", "password": "Ariadni@2026"}
USER = {"email": "work@gmail.com", "password": "mohammed"}


def _login(creds):
    r = requests.post(f"{BASE}/api/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"login failed for {creds['email']}: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_token():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def user_token():
    return _login(USER)


def H(tok):
    return {"Authorization": f"Bearer {tok}"}


# ---------------- AUTHORIZATION ----------------
CONTROL_ENDPOINTS = [
    "/api/admin/control/overview",
    "/api/admin/control/subscriptions",
    "/api/admin/control/health",
    "/api/admin/control/referrals",
    "/api/admin/control/security",
    "/api/admin/control/audit",
    "/api/admin/control/flags",
    "/api/admin/control/entitlements",
]


@pytest.mark.parametrize("ep", CONTROL_ENDPOINTS)
def test_customer_forbidden(ep, user_token):
    r = requests.get(f"{BASE}{ep}", headers=H(user_token), timeout=30)
    assert r.status_code == 403, f"{ep} expected 403 for customer, got {r.status_code}"


@pytest.mark.parametrize("ep", CONTROL_ENDPOINTS)
def test_admin_ok(ep, admin_token):
    r = requests.get(f"{BASE}{ep}", headers=H(admin_token), timeout=30)
    assert r.status_code == 200, f"{ep} expected 200 for admin, got {r.status_code}"


# ---------------- OVERVIEW CONTRACT (customers-only default) ----------------
def test_overview_customers_only(admin_token):
    r = requests.get(f"{BASE}/api/admin/control/overview", headers=H(admin_token), timeout=30)
    assert r.status_code == 200
    d = r.json()
    print("OVERVIEW default:", d)

    assert d["money_available"] is False
    assert d["include_internal"] is False
    for k in ("mrr", "arr", "revenue_month", "trial_to_paid", "churn"):
        assert d["money"][k] is None, f"money.{k} should be None"

    users = d["users"]
    assert users["total"] == 8, f"users.total expected 8 got {users['total']}"
    assert users["customers"] == 2, f"users.customers expected 2 got {users['customers']}"
    assert users["internal"] == 6, f"users.internal expected 6 got {users['internal']}"

    acc = d["accounts"]
    assert acc["total"] == 2, f"accounts.total expected 2 got {acc['total']}"
    assert acc["individual"] == 2
    assert acc["company"] == 0
    assert acc["enterprise"] == 0
    # reconciliation
    assert acc["total"] == acc["individual"] + acc["company"] + acc["enterprise"]

    subs = d["subscriptions"]
    assert subs["active_trials"] == 2
    assert subs["active_paid"] == 0

    pd = d["plan_distribution"]
    assert "free" not in pd, f"plan_distribution must not contain 'free', got {pd}"
    assert pd.get("trial") == 2, f"plan_distribution expected trial=2 got {pd}"


def test_overview_include_internal(admin_token):
    r = requests.get(f"{BASE}/api/admin/control/overview?include_internal=true",
                     headers=H(admin_token), timeout=30)
    assert r.status_code == 200
    d = r.json()
    print("OVERVIEW include_internal:", d)
    assert d["include_internal"] is True
    assert d["accounts"]["total"] == 3, f"accounts.total expected 3, got {d['accounts']['total']}"
    # reconciliation
    a = d["accounts"]
    assert a["total"] == a["individual"] + a["company"] + a["enterprise"]
    assert "free" not in d["plan_distribution"]


def test_usage_differs_with_internal(admin_token):
    d1 = requests.get(f"{BASE}/api/admin/control/overview", headers=H(admin_token), timeout=30).json()
    d2 = requests.get(f"{BASE}/api/admin/control/overview?include_internal=true", headers=H(admin_token), timeout=30).json()
    print("USAGE default:", d1["usage"], "USAGE internal:", d2["usage"])
    # internal should have >= product usage (internal cards add views/leads/nfc)
    assert d2["usage"]["views"] >= d1["usage"]["views"]
    assert d2["usage"]["leads"] >= d1["usage"]["leads"]
    assert d2["usage"]["nfc_taps"] >= d1["usage"]["nfc_taps"]
    # published_cards should differ: TapPresence HQ has feras-askar / dr-leo etc.
    # (If equal, feras-askar card has workspace_id=None which is a data bug — flag it)
    if d2["usage"]["published_cards"] == d1["usage"]["published_cards"]:
        pytest.fail(
            "include_internal did not add any internal cards. feras-askar has workspace_id=None "
            "and is not attributed to TapPresence HQ — internal cards are orphaned. "
            f"default={d1['usage']} internal={d2['usage']}"
        )


# ---------------- SUBSCRIPTIONS CONTRACT ----------------
def test_subscriptions_contract(admin_token):
    r = requests.get(f"{BASE}/api/admin/control/subscriptions", headers=H(admin_token), timeout=30)
    assert r.status_code == 200
    d = r.json()
    print("SUBS default:", d["summary"], "items:", len(d["items"]))
    assert d["money_available"] is False
    assert d["summary"].get("trialing") == 2
    assert d["summary"].get("active", 0) == 0

    for item in d["items"]:
        # no free label anywhere
        assert (item.get("plan") or "").lower() != "free", f"item has free plan label: {item}"
        # no ARIADNI
        assert "ARIADNI" not in (item.get("name") or ""), f"ARIADNI leak in name: {item['name']}"

    trials = [i for i in d["items"] if i["bucket"] == "trialing"]
    assert len(trials) == 2
    # Plan label for trialing must be 'Trial' (case-insensitive contains)
    for t in trials:
        assert "trial" in (t.get("plan") or "").lower(), f"trial bucket plan label not 'Trial': {t}"


def test_subscriptions_include_internal_shows_tappresence(admin_token):
    r = requests.get(f"{BASE}/api/admin/control/subscriptions?include_internal=true",
                     headers=H(admin_token), timeout=30)
    assert r.status_code == 200
    d = r.json()
    names = [i.get("name") for i in d["items"]]
    print("SUBS names (internal):", names)
    # Should include the internal HQ workspace, renamed
    assert any("TapPresence HQ" in (n or "") for n in names), f"expected TapPresence HQ present: {names}"
    assert not any("ARIADNI" in (n or "") for n in names), f"ARIADNI leak: {names}"


# ---------------- CUSTOMER APP REGRESSION ----------------
def test_customer_login_and_isolation(user_token):
    r = requests.get(f"{BASE}/api/auth/session", headers=H(user_token), timeout=30)
    assert r.status_code == 200
    sess = r.json()
    assert sess["user"]["email"] == "work@gmail.com"
    # Customer can list own cards via /admin/cards (tenant-scoped)
    rc = requests.get(f"{BASE}/api/admin/cards", headers=H(user_token), timeout=30)
    assert rc.status_code == 200
    cards = rc.json()
    slugs = sorted(c.get("slug") for c in cards)
    print("customer cards:", slugs)
    assert slugs == ["edrina-cepele"], f"tenant leak: {slugs}"
