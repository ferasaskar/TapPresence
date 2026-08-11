"""Iter30: Control Center cross-page reconciliation, entitlements, roles, workspaces."""
import os, requests, pytest
from dotenv import load_dotenv
load_dotenv("/app/frontend/.env")
BASE = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/") + "/api"
ADMIN = {"email": "admin@ariadni.id", "password": "Ariadni@2026"}
CUST = {"email": "work@gmail.com", "password": "mohammed"}


def _login(creds):
    r = requests.post(f"{BASE}/auth/login", json=creds, timeout=20)
    assert r.status_code == 200, f"login failed for {creds['email']}: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_h():
    return {"Authorization": f"Bearer {_login(ADMIN)}"}


@pytest.fixture(scope="module")
def cust_h():
    return {"Authorization": f"Bearer {_login(CUST)}"}


# ---- Cross-page reconciliation ----
class TestReconciliation:
    def test_overview_defaults(self, admin_h):
        r = requests.get(f"{BASE}/admin/control/overview", headers=admin_h, timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert d["accounts"]["total"] == 2, d["accounts"]
        assert d["accounts"]["individual"] == 2
        assert d["accounts"]["company"] == 0
        assert d["accounts"]["enterprise"] == 0
        assert d["subscriptions"]["active_trials"] == 2
        assert d["subscriptions"]["active_paid"] == 0
        assert d["plan_distribution"] == {"trial": 2}, d["plan_distribution"]
        assert "free" not in d["plan_distribution"]

    def test_customers_default_two_real(self, admin_h):
        r = requests.get(f"{BASE}/admin/control/customers", headers=admin_h, timeout=20)
        assert r.status_code == 200
        items = r.json()["items"]
        emails = sorted([i["email"] for i in items])
        assert len(items) == 2, f"expected 2, got {len(items)}: {emails}"
        # No internal leak
        for i in items:
            assert i["email"] not in ("admin@ariadni.id", "teamtest@demo.com")
            assert "ariadni.ai" not in (i.get("email") or "")
            # Human role label
            assert i.get("role_label") in ("Owner", "Admin", "Manager", "Member", "Super Admin"), i
            assert i["role_label"] != "WORKSPACE_OWNER"
            assert i["plan"] in ("Trial", "trial", "Pro", "Team", "Enterprise") or i["plan"].lower() != "free"
            assert i["plan"].lower() != "free"

    def test_workspaces_default_two_individual(self, admin_h):
        r = requests.get(f"{BASE}/admin/control/workspaces", headers=admin_h, timeout=20)
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) == 2, [i["name"] for i in items]
        for i in items:
            assert i["type"] == "individual", i
            assert "TapPresence HQ" not in (i.get("name") or "")

    def test_workspaces_type_filter(self, admin_h):
        r = requests.get(f"{BASE}/admin/control/workspaces?type=company", headers=admin_h, timeout=20)
        assert r.status_code == 200
        assert len(r.json()["items"]) == 0
        r = requests.get(f"{BASE}/admin/control/workspaces?type=individual", headers=admin_h, timeout=20)
        assert len(r.json()["items"]) == 2

    def test_subscriptions_summary(self, admin_h):
        r = requests.get(f"{BASE}/admin/control/subscriptions", headers=admin_h, timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert d["summary"].get("trialing") == 2
        assert d["summary"].get("active", 0) == 0

    def test_include_internal_adds_workspaces(self, admin_h):
        r = requests.get(f"{BASE}/admin/control/workspaces?include_internal=true", headers=admin_h, timeout=20)
        items = r.json()["items"]
        assert len(items) > 2
        # TapPresence HQ appears with include_internal
        names = [i.get("name") for i in items]
        assert any("TapPresence HQ" in (n or "") for n in names), names

    def test_include_internal_adds_customers(self, admin_h):
        r = requests.get(f"{BASE}/admin/control/customers?include_internal=true", headers=admin_h, timeout=20)
        items = r.json()["items"]
        assert len(items) > 2


# ---- Entitlements ----
class TestEntitlements:
    def test_get_shape(self, admin_h):
        r = requests.get(f"{BASE}/admin/control/entitlements", headers=admin_h, timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert d["plans"] == ["trial", "pro", "team", "enterprise"]
        assert "free" not in d["plans"]
        assert "white_label" not in d["plans"]
        assert set(d["provider_status"].keys()) == {"wallet", "ai_followup", "custom_domain", "api"}
        # ai_followup should be true (EMERGENT_LLM_KEY configured), api=True (no keys required)
        assert d["provider_status"]["ai_followup"] is True
        assert d["provider_status"]["api"] is True
        # wallet & custom_domain should be false (not configured)
        assert d["provider_status"]["wallet"] is False
        assert d["provider_status"]["custom_domain"] is False

    def test_preview(self, admin_h):
        r = requests.get(f"{BASE}/admin/control/entitlements", headers=admin_h, timeout=20)
        pro_defaults = r.json()["defaults"]["pro"]
        original = pro_defaults.get("max_cards", 5)
        body = {"plan": "pro", "overrides": {"max_cards": original + 7}}
        r = requests.post(f"{BASE}/admin/control/entitlements/preview", headers=admin_h, json=body, timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert d["plan"] == "pro"
        assert "max_cards" in d["diff"]
        assert d["diff"]["max_cards"]["after"] == original + 7
        assert "affected_customers" in d

    def test_publish_and_audit(self, admin_h):
        # Get current pro defaults
        r = requests.get(f"{BASE}/admin/control/entitlements", headers=admin_h, timeout=20)
        pro_defaults = r.json()["defaults"]["pro"]
        target = (pro_defaults.get("max_cards", 5)) + 3
        # publish
        r = requests.put(f"{BASE}/admin/control/entitlements", headers=admin_h,
                        json={"plan": "pro", "overrides": {"max_cards": target}, "reason": "iter30-test"}, timeout=20)
        assert r.status_code == 200, r.text
        # verify GET reflects override
        r = requests.get(f"{BASE}/admin/control/entitlements", headers=admin_h, timeout=20)
        assert r.json()["overrides"].get("pro", {}).get("max_cards") == target
        # verify audit log
        r = requests.get(f"{BASE}/admin/control/audit?limit=50", headers=admin_h, timeout=20)
        assert r.status_code == 200
        items = r.json().get("items", [])
        pub = [x for x in items if x.get("action") == "admin.entitlements.publish"]
        assert len(pub) > 0, "expected admin.entitlements.publish audit entry"

    def test_reject_unknown_plan(self, admin_h):
        r = requests.put(f"{BASE}/admin/control/entitlements", headers=admin_h,
                        json={"plan": "free", "overrides": {}}, timeout=20)
        assert r.status_code == 400
        r = requests.put(f"{BASE}/admin/control/entitlements", headers=admin_h,
                        json={"plan": "white_label", "overrides": {}}, timeout=20)
        assert r.status_code == 400


# ---- Authorization ----
class TestAuthz:
    @pytest.mark.parametrize("path", [
        "/admin/control/overview",
        "/admin/control/customers",
        "/admin/control/workspaces",
        "/admin/control/entitlements",
        "/admin/control/subscriptions",
    ])
    def test_customer_forbidden(self, cust_h, path):
        r = requests.get(f"{BASE}{path}", headers=cust_h, timeout=20)
        assert r.status_code == 403, f"{path} → {r.status_code}"

    def test_customer_can_hit_own_dashboard(self, cust_h):
        r = requests.get(f"{BASE}/auth/session", headers=cust_h, timeout=20)
        assert r.status_code == 200
        assert r.json().get("role") != "SUPER_ADMIN"
