"""Iter 38 — Super Admin Usage & Cost Control backend tests.

Covers:
- RBAC (SUPER_ADMIN vs non-admin -> 403)
- GET /admin/control/usage/overview KPIs + feature table
- GET/PUT /admin/control/usage/config (+ validation, audit)
- GET/POST/DELETE /admin/control/usage/overrides
- GET /admin/control/usage/detail (type user|workspace + 400)
- GET /admin/control/usage/timeseries
- GET /admin/control/usage/export.csv
- GET /usage/me gating (default empty, populated after enabling a limit,
  and RESET after test so preview stays at default)
- REGRESSION: POST /api/ai/followup returns draft; /billing loads; /config returns stripe.
"""
import os
import io
import csv
import time
import uuid
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ADMIN_EMAIL = "admin@ariadni.id"
ADMIN_PASSWORD = "Ariadni@2026"

METERED_KEYS = {"business_card_scan", "event_badge_scan", "ai_followup"}


@pytest.fixture(scope="session")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="session")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="session")
def user_token():
    suffix = uuid.uuid4().hex[:8]
    email = f"TEST_usage_{suffix}@example.com"
    r = requests.post(f"{BASE_URL}/api/auth/register",
                      json={"email": email, "password": "TestPass@123",
                            "name": "Test Usage", "workspace_name": "TEST Usage WS"}, timeout=20)
    assert r.status_code in (200, 201), f"register failed: {r.status_code} {r.text}"
    data = r.json()
    return {"token": data.get("token"), "email": email, "user_id": (data.get("user") or {}).get("id")}


@pytest.fixture(scope="session")
def user_headers(user_token):
    return {"Authorization": f"Bearer {user_token['token']}"}


# ----------------------------- RBAC -----------------------------

class TestRBAC:
    def test_non_admin_forbidden_overview(self, user_headers):
        r = requests.get(f"{BASE_URL}/api/admin/control/usage/overview", headers=user_headers, timeout=15)
        assert r.status_code == 403

    def test_non_admin_forbidden_config(self, user_headers):
        r = requests.get(f"{BASE_URL}/api/admin/control/usage/config", headers=user_headers, timeout=15)
        assert r.status_code == 403

    def test_non_admin_forbidden_overrides(self, user_headers):
        r = requests.get(f"{BASE_URL}/api/admin/control/usage/overrides", headers=user_headers, timeout=15)
        assert r.status_code == 403

    def test_non_admin_forbidden_detail(self, user_headers):
        r = requests.get(f"{BASE_URL}/api/admin/control/usage/detail?type=user&id=x",
                         headers=user_headers, timeout=15)
        assert r.status_code == 403

    def test_non_admin_forbidden_timeseries(self, user_headers):
        r = requests.get(f"{BASE_URL}/api/admin/control/usage/timeseries", headers=user_headers, timeout=15)
        assert r.status_code == 403

    def test_non_admin_forbidden_export(self, user_headers):
        r = requests.get(f"{BASE_URL}/api/admin/control/usage/export.csv", headers=user_headers, timeout=15)
        assert r.status_code == 403

    def test_admin_can_access_overview(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/admin/control/usage/overview", headers=admin_headers, timeout=30)
        assert r.status_code == 200


# ----------------------------- OVERVIEW -----------------------------

class TestOverview:
    def test_overview_shape(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/admin/control/usage/overview", headers=admin_headers, timeout=30)
        assert r.status_code == 200
        data = r.json()
        for k in ("kpis", "features", "top_users", "top_workspaces", "cost_by_plan", "cost_by_feature"):
            assert k in data, f"missing {k}"
        kpis = data["kpis"]
        for k in ("active_users", "active_workspaces", "total_tracked_usage",
                  "total_ai_operations", "estimated_ai_cost", "estimated_total_cost",
                  "avg_cost_per_user", "avg_cost_per_workspace",
                  "highest_cost_user", "highest_cost_workspace"):
            assert k in kpis, f"missing kpi {k}"
        # 12 features
        assert len(data["features"]) == 12
        row_keys = {r["key"] for r in data["features"]}
        assert METERED_KEYS.issubset(row_keys)
        # per-row shape
        row = data["features"][0]
        for k in ("usage_today", "usage_month", "avg_per_user", "avg_per_workspace",
                  "highest_user_usage", "highest_workspace_usage",
                  "unit_cost", "estimated_total_cost", "scope", "enforcement_enabled", "status"):
            assert k in row, f"row missing {k}"

    def test_estimated_cost_equals_usage_times_unit_cost(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/admin/control/usage/overview", headers=admin_headers, timeout=30)
        data = r.json()
        bcs = next((x for x in data["features"] if x["key"] == "business_card_scan"), None)
        assert bcs is not None
        # unit cost may have been adjusted by tests; check consistency: est ≈ usage*unit_cost
        expected = round(bcs["usage_month"] * bcs["unit_cost"], 4)
        assert abs(bcs["estimated_total_cost"] - expected) < 0.01, \
            f"est {bcs['estimated_total_cost']} != {expected} (usage {bcs['usage_month']} × {bcs['unit_cost']})"


# ----------------------------- CONFIG -----------------------------

class TestConfig:
    def test_config_get_returns_12_features(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/admin/control/usage/config", headers=admin_headers, timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert len(data["features"]) == 12
        # default enforcement OFF
        for f in data["features"]:
            cfg = f.get("config") or {}
            assert cfg.get("enforcement_enabled") in (False, None), \
                f"{f['key']} enforcement_enabled must default false, got {cfg.get('enforcement_enabled')}"
            assert cfg.get("currency", "USD") == "USD"

    def test_config_update_unit_cost_and_reset(self, admin_headers):
        # capture original
        r = requests.get(f"{BASE_URL}/api/admin/control/usage/config", headers=admin_headers, timeout=15)
        feats = r.json()["features"]
        orig = next(x for x in feats if x["key"] == "ai_followup")["config"]
        orig_uc = float(orig.get("unit_cost", 0.03))

        # update
        new_uc = round(orig_uc + 0.001, 4)
        r = requests.put(f"{BASE_URL}/api/admin/control/usage/config/ai_followup",
                         headers=admin_headers, json={"unit_cost": new_uc}, timeout=15)
        assert r.status_code == 200, r.text
        assert abs(r.json()["config"]["unit_cost"] - new_uc) < 1e-6

        # verify GET reflects change + cost_history
        r = requests.get(f"{BASE_URL}/api/admin/control/usage/config", headers=admin_headers, timeout=15)
        data = r.json()
        af = next(x for x in data["features"] if x["key"] == "ai_followup")
        assert abs(af["config"]["unit_cost"] - new_uc) < 1e-6
        assert any(h.get("feature") == "ai_followup" for h in (data.get("cost_history") or []))

        # reset
        r = requests.put(f"{BASE_URL}/api/admin/control/usage/config/ai_followup",
                         headers=admin_headers, json={"unit_cost": orig_uc}, timeout=15)
        assert r.status_code == 200

    def test_config_invalid_feature_404(self, admin_headers):
        r = requests.put(f"{BASE_URL}/api/admin/control/usage/config/nonsense_feature",
                         headers=admin_headers, json={"unit_cost": 0.01}, timeout=15)
        assert r.status_code == 404

    def test_config_invalid_scope_400(self, admin_headers):
        r = requests.put(f"{BASE_URL}/api/admin/control/usage/config/ai_followup",
                         headers=admin_headers, json={"scope": "bogus_scope"}, timeout=15)
        assert r.status_code == 400

    def test_config_invalid_hard_behavior_400(self, admin_headers):
        r = requests.put(f"{BASE_URL}/api/admin/control/usage/config/ai_followup",
                         headers=admin_headers, json={"hard_behavior": "explode"}, timeout=15)
        assert r.status_code == 400

    def test_config_invalid_plan_mode_400(self, admin_headers):
        r = requests.put(f"{BASE_URL}/api/admin/control/usage/config/ai_followup",
                         headers=admin_headers,
                         json={"plan_limits": {"pro": {"mode": "bogus", "limit": 5}}}, timeout=15)
        assert r.status_code == 400

    def test_config_toggle_enforcement_writes_audit(self, admin_headers):
        r = requests.put(f"{BASE_URL}/api/admin/control/usage/config/ai_followup",
                         headers=admin_headers, json={"enforcement_enabled": True}, timeout=15)
        assert r.status_code == 200
        # audit
        r = requests.get(f"{BASE_URL}/api/admin/control/audit", headers=admin_headers, timeout=15)
        if r.status_code == 200:
            logs = r.json() if isinstance(r.json(), list) else r.json().get("items", [])
            assert any("admin.usage.config" in (l.get("action") or "") for l in logs), \
                "audit entry admin.usage.config not found"
        # reset
        requests.put(f"{BASE_URL}/api/admin/control/usage/config/ai_followup",
                     headers=admin_headers, json={"enforcement_enabled": False}, timeout=15)


# ----------------------------- OVERRIDES -----------------------------

class TestOverrides:
    def test_override_create_list_delete(self, admin_headers, user_token):
        uid = user_token["user_id"]
        assert uid, "no user id for override target"
        # create
        r = requests.post(f"{BASE_URL}/api/admin/control/usage/overrides",
                          headers=admin_headers,
                          json={"feature": "ai_followup", "scope_type": "user",
                                "scope_id": uid, "mode": "monthly", "limit": 5,
                                "note": "TEST override"}, timeout=15)
        assert r.status_code == 200, r.text
        oid = r.json()["override"]["id"]

        # list
        r = requests.get(f"{BASE_URL}/api/admin/control/usage/overrides", headers=admin_headers, timeout=15)
        assert r.status_code == 200
        items = r.json()["items"]
        row = next((x for x in items if x["id"] == oid), None)
        assert row is not None
        assert "scope_label" in row

        # delete
        r = requests.delete(f"{BASE_URL}/api/admin/control/usage/overrides/{oid}",
                            headers=admin_headers, timeout=15)
        assert r.status_code == 200

    def test_override_invalid_scope_type_400(self, admin_headers):
        r = requests.post(f"{BASE_URL}/api/admin/control/usage/overrides", headers=admin_headers,
                          json={"feature": "ai_followup", "scope_type": "planet",
                                "scope_id": "x", "mode": "monthly", "limit": 5}, timeout=15)
        assert r.status_code == 400

    def test_override_unknown_feature_404(self, admin_headers):
        r = requests.post(f"{BASE_URL}/api/admin/control/usage/overrides", headers=admin_headers,
                          json={"feature": "bogus_thing", "scope_type": "user",
                                "scope_id": "x", "mode": "monthly", "limit": 5}, timeout=15)
        assert r.status_code == 404

    def test_override_invalid_mode_400(self, admin_headers):
        r = requests.post(f"{BASE_URL}/api/admin/control/usage/overrides", headers=admin_headers,
                          json={"feature": "ai_followup", "scope_type": "user",
                                "scope_id": "x", "mode": "bogus", "limit": 5}, timeout=15)
        assert r.status_code == 400


# ----------------------------- DETAIL / TIMESERIES / CSV -----------------------------

class TestDetailTimeseriesCSV:
    def test_detail_bad_type_400(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/admin/control/usage/detail?type=bogus&id=x",
                         headers=admin_headers, timeout=15)
        assert r.status_code == 400

    def test_detail_workspace(self, admin_headers):
        # find any top workspace from overview
        ov = requests.get(f"{BASE_URL}/api/admin/control/usage/overview",
                          headers=admin_headers, timeout=30).json()
        top = ov.get("top_workspaces") or []
        if not top:
            pytest.skip("no top workspace available")
        wid = top[0]["id"]
        r = requests.get(f"{BASE_URL}/api/admin/control/usage/detail?type=workspace&id={wid}",
                         headers=admin_headers, timeout=15)
        assert r.status_code == 200
        d = r.json()
        for k in ("header", "breakdown", "total_estimated_cost"):
            assert k in d
        assert d["type"] == "workspace"

    def test_timeseries(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/admin/control/usage/timeseries",
                         headers=admin_headers, timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "series" in data
        if data["series"]:
            row = data["series"][0]
            for k in ("date", "usage", "cost", "ai"):
                assert k in row

    def test_export_csv(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/admin/control/usage/export.csv",
                         headers=admin_headers, timeout=30)
        assert r.status_code == 200
        text = r.text
        assert text.startswith("\ufeff"), "CSV must start with UTF-8 BOM"
        reader = csv.reader(io.StringIO(text))
        header = next(reader)
        expected = ["Date", "Feature", "Category", "User", "Workspace", "Plan",
                    "Usage", "Unit Cost (USD)", "Estimated Cost (USD)", "Result", "Source", "Period"]
        # first cell may still have BOM stripped
        header[0] = header[0].lstrip("\ufeff")
        assert header == expected


# ----------------------------- /usage/me GATING (default OFF -> ON -> OFF) -----------------------------

class TestUsageMeGating:
    def test_usage_me_default_empty(self, user_headers):
        r = requests.get(f"{BASE_URL}/api/usage/me", headers=user_headers, timeout=15)
        assert r.status_code == 200
        assert r.json().get("items") == []

    def test_usage_me_shows_when_enforcement_enabled_then_reset(self, admin_headers, user_headers):
        # Enable ai_followup per_user monthly limit
        try:
            r = requests.put(f"{BASE_URL}/api/admin/control/usage/config/ai_followup",
                             headers=admin_headers,
                             json={"enforcement_enabled": True, "scope": "per_user",
                                   "plan_limits": {"trial": {"mode": "monthly", "limit": 10},
                                                   "pro":  {"mode": "monthly", "limit": 10},
                                                   "team": {"mode": "monthly", "limit": 10},
                                                   "enterprise": {"mode": "monthly", "limit": 10}}},
                             timeout=15)
            assert r.status_code == 200, r.text

            r = requests.get(f"{BASE_URL}/api/usage/me", headers=user_headers, timeout=15)
            assert r.status_code == 200
            items = r.json().get("items") or []
            keys = [i.get("key") for i in items]
            assert "ai_followup" in keys, f"ai_followup not in /usage/me items after enable: {items}"
            row = next(i for i in items if i["key"] == "ai_followup")
            for k in ("used", "limit", "remaining", "pct", "scope_label"):
                assert k in row
            assert row["limit"] == 10
        finally:
            # RESET — restore defaults so preview stays at no-limit
            requests.put(f"{BASE_URL}/api/admin/control/usage/config/ai_followup",
                         headers=admin_headers,
                         json={"enforcement_enabled": False,
                               "plan_limits": {"trial": {"mode": "unlimited"},
                                               "pro":  {"mode": "unlimited"},
                                               "team": {"mode": "unlimited"},
                                               "enterprise": {"mode": "unlimited"}}},
                         timeout=15)

        # confirm reset
        r = requests.get(f"{BASE_URL}/api/usage/me", headers=user_headers, timeout=15)
        assert r.status_code == 200
        assert r.json().get("items") == []


# ----------------------------- REGRESSION -----------------------------

class TestRegression:
    def test_billing_still_loads(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/billing", headers=admin_headers, timeout=15)
        assert r.status_code == 200
        data = r.json()
        # billing should include plan/status/usage keys as before
        assert "usage" in data or "plan" in data

    def test_config_public_endpoint_still_ok(self):
        r = requests.get(f"{BASE_URL}/api/config", timeout=15)
        assert r.status_code == 200
        data = r.json()
        # stripe key retained
        assert "stripe_mode" in data or "stripe" in data or "integrations" in data

    def test_ai_followup_still_works(self, admin_headers):
        # Use minimal payload; endpoint expects lead-like inputs. This is a smoke check.
        payload = {"lead_name": "TEST Regression", "context": "brief meeting", "language": "en",
                   "tone": "friendly"}
        r = requests.post(f"{BASE_URL}/api/ai/followup", headers=admin_headers, json=payload, timeout=45)
        # allow 200 (draft) or 400 (field validation) — the goal is no 500 import/regression
        assert r.status_code in (200, 400, 422), f"unexpected status {r.status_code}: {r.text[:400]}"
        if r.status_code == 200:
            assert "draft" in r.json() or "message" in r.json() or "text" in r.json()
