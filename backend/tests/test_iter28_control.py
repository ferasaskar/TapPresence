"""Iteration 28 — Control Center backend tests (authorization + all /admin/control/* endpoints)."""
import os
import time
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://template-hub-184.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"

ADMIN_EMAIL = "admin@ariadni.id"
ADMIN_PASS = "Ariadni@2026"
USER_EMAIL = "work@gmail.com"
USER_PASS = "mohammed"
SUSPEND_EMAIL = "teamtest@demo.com"


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login {email} -> {r.status_code} {r.text}"
    j = r.json()
    return j["token"], j.get("user", {})


@pytest.fixture(scope="session")
def admin_token():
    tok, _ = _login(ADMIN_EMAIL, ADMIN_PASS)
    return tok


@pytest.fixture(scope="session")
def user_token():
    tok, u = _login(USER_EMAIL, USER_PASS)
    assert u.get("role") != "SUPER_ADMIN"
    return tok


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


# -------- Authorization isolation --------
class TestAuthz:
    endpoints = [
        ("GET", "/admin/control/overview"),
        ("GET", "/admin/control/referrals"),
        ("GET", "/admin/control/flags"),
        ("GET", "/admin/control/audit"),
        ("GET", "/admin/control/security"),
        ("GET", "/admin/control/health"),
        ("GET", "/admin/control/entitlements"),
        ("GET", "/admin/control/pricing/versions"),
    ]

    def test_normal_user_forbidden(self, user_token):
        for method, path in self.endpoints:
            r = requests.request(method, f"{API}{path}", headers=_h(user_token), timeout=30)
            assert r.status_code == 403, f"{path} should be 403 for normal user, got {r.status_code}"

    def test_admin_allowed(self, admin_token):
        for method, path in self.endpoints:
            r = requests.request(method, f"{API}{path}", headers=_h(admin_token), timeout=30)
            assert r.status_code == 200, f"{path} admin -> {r.status_code} {r.text[:200]}"


# -------- Overview --------
class TestOverview:
    def test_kpis_and_money_masked(self, admin_token):
        r = requests.get(f"{API}/admin/control/overview", headers=_h(admin_token), timeout=30)
        assert r.status_code == 200
        j = r.json()
        for k in ("total", "individual", "team", "team_seats", "active_trials", "active_paid", "new_customers", "cancellations"):
            assert k in j["accounts"], f"missing accounts.{k}"
        for k in ("published_cards", "views", "scans", "nfc_taps", "leads", "scanner_uses", "meetings_booked", "campaigns", "paid_referrals"):
            assert k in j["usage"], f"missing usage.{k}"
        # money must be None (stripe not configured)
        assert j["money_available"] is False
        for k in ("mrr", "arr", "revenue_month", "churn", "trial_to_paid"):
            assert j["money"].get(k) is None, f"money.{k} should be None"

    def test_range_filter(self, admin_token):
        r = requests.get(f"{API}/admin/control/overview", headers=_h(admin_token),
                         params={"start": "2099-01-01", "end": "2099-01-02"}, timeout=30)
        assert r.status_code == 200
        j = r.json()
        # future window => zero counts on windowed metrics
        assert j["usage"]["views"] == 0
        assert j["usage"]["leads"] == 0


# -------- Health --------
class TestHealth:
    def test_health(self, admin_token):
        r = requests.get(f"{API}/admin/control/health", headers=_h(admin_token), timeout=30)
        assert r.status_code == 200
        j = r.json()
        assert j["api"] == "ok"
        assert j["database"] == "ok"
        assert j["billing"] in ("demo", "connected")
        assert "integrations" in j


# -------- Flags --------
class TestFlags:
    key = "iter28_test_flag"

    def test_add_and_toggle(self, admin_token):
        # create
        r = requests.put(f"{API}/admin/control/flags/{self.key}", headers=_h(admin_token),
                         json={"enabled": True, "description": "iter28 test"}, timeout=30)
        assert r.status_code == 200
        # list contains it
        lst = requests.get(f"{API}/admin/control/flags", headers=_h(admin_token), timeout=30).json()["items"]
        assert any(f["key"] == self.key and f["enabled"] is True for f in lst)
        # toggle off
        r2 = requests.put(f"{API}/admin/control/flags/{self.key}", headers=_h(admin_token),
                          json={"enabled": False}, timeout=30)
        assert r2.status_code == 200
        lst2 = requests.get(f"{API}/admin/control/flags", headers=_h(admin_token), timeout=30).json()["items"]
        assert any(f["key"] == self.key and f["enabled"] is False for f in lst2)


# -------- Entitlements --------
class TestEntitlements:
    def test_get_and_set(self, admin_token):
        r = requests.get(f"{API}/admin/control/entitlements", headers=_h(admin_token), timeout=30)
        assert r.status_code == 200
        j = r.json()
        assert "defaults" in j and "overrides" in j
        assert "pro" in j["defaults"]
        # pick a key from pro defaults to override
        pro_defaults = j["defaults"]["pro"]
        pick = next(iter(pro_defaults.keys()))
        new_val = pro_defaults[pick]
        # send trivial override (same value) to avoid disrupting anything
        r2 = requests.put(f"{API}/admin/control/entitlements", headers=_h(admin_token),
                          json={"plan": "pro", "overrides": {pick: new_val}}, timeout=30)
        assert r2.status_code == 200
        j2 = r2.json()
        assert j2["ok"] is True
        # verify persisted
        r3 = requests.get(f"{API}/admin/control/entitlements", headers=_h(admin_token), timeout=30).json()
        assert pick in r3["overrides"].get("pro", {})


# -------- Pricing preview + publish --------
class TestPricing:
    def test_preview_and_publish_and_versions(self, admin_token):
        before_versions = requests.get(f"{API}/admin/control/pricing/versions",
                                       headers=_h(admin_token), timeout=30).json()["items"]
        n_before = len(before_versions)
        patch = {"trial": {"days": 14}}
        # preview
        prv = requests.post(f"{API}/admin/control/pricing/preview", headers=_h(admin_token),
                            json={"patch": patch, "apply_to": "new_only", "reason": "iter28-preview"}, timeout=30)
        assert prv.status_code == 200
        pj = prv.json()
        assert "before" in pj and "after" in pj
        # publish
        pub = requests.post(f"{API}/admin/control/pricing/publish", headers=_h(admin_token),
                            json={"patch": patch, "apply_to": "new_only", "reason": "iter28-publish"}, timeout=30)
        assert pub.status_code == 200
        pubj = pub.json()
        assert pubj["ok"] is True
        vid = pubj["version_id"]
        # versions grew
        after = requests.get(f"{API}/admin/control/pricing/versions",
                             headers=_h(admin_token), timeout=30).json()["items"]
        assert len(after) == n_before + 1
        assert any(v["id"] == vid for v in after)
        # audit contains it
        aud = requests.get(f"{API}/admin/control/audit",
                           headers=_h(admin_token), params={"q": "admin.pricing.publish"}, timeout=30).json()["items"]
        assert any(a.get("action") == "admin.pricing.publish" for a in aud)


# -------- Customer detail & actions + suspend flow --------
class TestCustomers:
    def _find_user_id(self, admin_token, email):
        r = requests.get(f"{API}/admin/platform/users",
                         headers=_h(admin_token), params={"q": email}, timeout=30)
        assert r.status_code == 200
        for u in r.json().get("items", []):
            if u.get("email", "").lower() == email.lower():
                return u["id"]
        return None

    def test_customer_detail(self, admin_token):
        uid = self._find_user_id(admin_token, USER_EMAIL)
        assert uid, f"could not find {USER_EMAIL}"
        r = requests.get(f"{API}/admin/control/customers/{uid}", headers=_h(admin_token), timeout=30)
        assert r.status_code == 200
        j = r.json()
        assert j["user"]["email"].lower() == USER_EMAIL

    def test_resend_verification(self, admin_token):
        uid = self._find_user_id(admin_token, USER_EMAIL)
        r = requests.post(f"{API}/admin/control/customers/{uid}/action",
                          headers=_h(admin_token), json={"action": "resend_verification"}, timeout=30)
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_suspend_unsuspend_non_admin(self, admin_token):
        uid = self._find_user_id(admin_token, SUSPEND_EMAIL)
        if not uid:
            pytest.skip(f"{SUSPEND_EMAIL} not present in this env")
        # suspend
        r = requests.post(f"{API}/admin/platform/users/{uid}/suspend",
                          headers=_h(admin_token), json={"suspended": True}, timeout=30)
        assert r.status_code in (200, 204)
        det = requests.get(f"{API}/admin/control/customers/{uid}", headers=_h(admin_token), timeout=30).json()
        assert det["user"].get("suspended") is True
        # unsuspend
        r2 = requests.post(f"{API}/admin/platform/users/{uid}/suspend",
                           headers=_h(admin_token), json={"suspended": False}, timeout=30)
        assert r2.status_code in (200, 204)
        det2 = requests.get(f"{API}/admin/control/customers/{uid}", headers=_h(admin_token), timeout=30).json()
        assert not det2["user"].get("suspended")


# -------- Referrals, Audit, Security --------
class TestOthers:
    def test_referrals(self, admin_token):
        j = requests.get(f"{API}/admin/control/referrals", headers=_h(admin_token), timeout=30).json()
        assert "funnel" in j and set(["total", "signed_up", "qualified", "revoked"]).issubset(j["funnel"].keys())

    def test_audit_search(self, admin_token):
        j = requests.get(f"{API}/admin/control/audit", headers=_h(admin_token), timeout=30).json()
        assert isinstance(j.get("items"), list)

    def test_security(self, admin_token):
        j = requests.get(f"{API}/admin/control/security", headers=_h(admin_token), timeout=30).json()
        for k in ("suspended_accounts", "locked_or_throttled", "suspicious_referrals"):
            assert k in j


# -------- Workspace detail --------
class TestWorkspaces:
    def test_workspace_detail(self, admin_token):
        r = requests.get(f"{API}/admin/platform/workspaces", headers=_h(admin_token), timeout=30).json()
        items = r.get("items", [])
        assert items, "no workspaces to test"
        wid = items[0]["id"]
        det = requests.get(f"{API}/admin/control/workspaces/{wid}", headers=_h(admin_token), timeout=30)
        assert det.status_code == 200
        dj = det.json()
        assert "workspace" in dj and "members" in dj
