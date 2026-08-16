"""
Iter 39: AI Lead Insights + AI Event Recap
Backend tests: on-demand generate, caching, stale detection, metering, per-event scope,
enforcement toggle, tenant/permission isolation. Real OpenAI calls are minimal
(a few generations + regenerations) per E1's guidance.
"""
import os
import time
import uuid
import requests
import pytest

BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API = f"{BASE}/api"

ADMIN_EMAIL = "admin@ariadni.id"
ADMIN_PASS = "Ariadni@2026"


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login {email}: {r.status_code} {r.text[:200]}"
    return r.json()["token"]


def _h(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def admin_token():
    return _login(ADMIN_EMAIL, ADMIN_PASS)


@pytest.fixture(scope="module")
def throwaway():
    email = f"TEST_throw_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "Test@12345"
    r = requests.post(f"{API}/auth/register", json={
        "email": email, "password": pwd, "name": "Throwaway",
        "workspace_name": "TEST_TAThrow"
    }, timeout=30)
    assert r.status_code in (200, 201), f"register: {r.status_code} {r.text[:200]}"
    tok = r.json().get("token") or _login(email, pwd)
    yield {"email": email, "token": tok}


@pytest.fixture(scope="module")
def a_lead(admin_token):
    # pick a lead admin can see
    r = requests.get(f"{API}/crm/leads", headers=_h(admin_token), timeout=30)
    assert r.status_code == 200, r.text[:200]
    items = r.json() if isinstance(r.json(), list) else r.json().get("items") or r.json().get("leads") or []
    assert items, "no leads seeded"
    return items[0]


@pytest.fixture(scope="module")
def an_event(admin_token):
    r = requests.get(f"{API}/events", headers=_h(admin_token), timeout=30)
    assert r.status_code == 200
    data = r.json()
    items = data if isinstance(data, list) else data.get("items") or data.get("events") or []
    assert items, "no events seeded"
    # prefer event with multiple leads if we can detect leads count
    items_sorted = sorted(items, key=lambda e: e.get("leads_count", 0), reverse=True)
    return items_sorted[0]


# ==================== USAGE CONFIG ====================

class TestUsageConfig:
    def test_config_has_both_ai_features_metered(self, admin_token):
        r = requests.get(f"{API}/admin/control/usage/config", headers=_h(admin_token), timeout=30)
        assert r.status_code == 200
        feats = {f["key"]: f for f in r.json()["features"]}
        assert "ai_lead_insight" in feats and feats["ai_lead_insight"]["metered"] is True
        assert "ai_event_recap" in feats and feats["ai_event_recap"]["metered"] is True
        assert not feats["ai_lead_insight"].get("placeholder")
        assert not feats["ai_event_recap"].get("placeholder")
        assert feats["ai_lead_insight"]["config"].get("scope") == "per_user"
        assert feats["ai_event_recap"]["config"].get("scope") == "per_event"
        # Default: enforcement OFF
        assert feats["ai_lead_insight"]["config"].get("enforcement_enabled") in (False, None)
        assert feats["ai_event_recap"]["config"].get("enforcement_enabled") in (False, None)
        # unit costs
        assert abs(float(feats["ai_lead_insight"]["config"]["unit_cost"]) - 0.03) < 1e-6
        assert abs(float(feats["ai_event_recap"]["config"]["unit_cost"]) - 0.05) < 1e-6


# ==================== LEAD INSIGHT ====================

class TestLeadInsight:
    def _count_success(self, admin_token, feature, user_id=None):
        r = requests.get(f"{API}/admin/control/usage/overview",
                         params={"feature": feature, **({"user_id": user_id} if user_id else {})},
                         headers=_h(admin_token), timeout=30)
        assert r.status_code == 200, r.text[:200]
        data = r.json()
        for row in (data.get("features") or []):
            if row.get("key") == feature:
                return int(row.get("usage_month", 0))
        return -1

    def test_full_flow(self, admin_token, a_lead):
        lead_id = a_lead["id"]
        # Clear previous ai_insight to test cache/stale/regenerate fresh
        # Use admin DB write via update endpoint if available -- otherwise leave existing
        # Get before-count
        before = self._count_success(admin_token, "ai_lead_insight", user_id=None)

        # Ensure clean baseline: if insight exists, use regenerate for one call and count deltas
        r_get = requests.get(f"{API}/crm/leads/{lead_id}/ai-insight", headers=_h(admin_token), timeout=30)
        assert r_get.status_code == 200
        had = r_get.json().get("insight") is not None

        # (single-lead GET endpoint doesn't exist; skip pre-fetch)

        # POST regenerate=false -> if had, cached; else generate
        r = requests.post(f"{API}/crm/leads/{lead_id}/ai-insight",
                          json={"regenerate": False, "language": "en"},
                          headers=_h(admin_token), timeout=120)
        assert r.status_code == 200, r.text[:400]
        body = r.json()
        assert body["insight"] is not None
        content = body["insight"]["content"]
        required_keys = {"summary", "opportunity_assessment", "why_matters", "recommended_next_action",
                         "followup_approach", "signals_risks", "priority", "timing"}
        assert required_keys.issubset(content.keys()), f"missing: {required_keys - set(content.keys())}"
        assert isinstance(content["signals_risks"], list)
        assert content["priority"] in ("High", "Medium", "Low")
        assert body["insight"]["provider"] == "openai:gpt-5.4"

        # 2nd POST regenerate=false -> cached (no new usage)
        mid = self._count_success(admin_token, "ai_lead_insight")
        r2 = requests.post(f"{API}/crm/leads/{lead_id}/ai-insight",
                           json={"regenerate": False, "language": "en"},
                           headers=_h(admin_token), timeout=30)
        assert r2.status_code == 200
        assert r2.json().get("cached") is True
        after_cached = self._count_success(admin_token, "ai_lead_insight")
        if mid >= 0 and after_cached >= 0:
            assert after_cached == mid, f"cached call should not add usage: {mid} -> {after_cached}"

        # GET returns stored, stale=false
        r3 = requests.get(f"{API}/crm/leads/{lead_id}/ai-insight", headers=_h(admin_token), timeout=30)
        assert r3.status_code == 200
        assert r3.json()["insight"] is not None
        # stale might be false since nothing changed
        # patch the lead to trigger stale
        r_patch = requests.patch(f"{API}/crm/leads/{lead_id}",
                                 json={"notes": f"TEST_stale_{uuid.uuid4().hex[:6]}"},
                                 headers=_h(admin_token), timeout=30)
        assert r_patch.status_code in (200, 204), r_patch.text[:200]
        r4 = requests.get(f"{API}/crm/leads/{lead_id}/ai-insight", headers=_h(admin_token), timeout=30)
        assert r4.status_code == 200
        assert r4.json()["stale"] is True, "should be stale after material change"
        # NOT auto-regenerated
        assert r4.json()["insight"] is not None  # returned cached-but-stale, not None

        # Rules-based score not affected by AI generation (list lookup)
        r_list = requests.get(f"{API}/crm/leads", headers=_h(admin_token), timeout=30)
        assert r_list.status_code == 200

        # regenerate=true -> +1 usage
        pre_regen = self._count_success(admin_token, "ai_lead_insight")
        r5 = requests.post(f"{API}/crm/leads/{lead_id}/ai-insight",
                           json={"regenerate": True, "language": "en"},
                           headers=_h(admin_token), timeout=120)
        assert r5.status_code == 200, r5.text[:300]
        assert r5.json().get("cached") in (False, None)
        post_regen = self._count_success(admin_token, "ai_lead_insight")
        if pre_regen >= 0 and post_regen >= 0:
            assert post_regen == pre_regen + 1, f"regenerate should add exactly 1: {pre_regen}->{post_regen}"


# ==================== EVENT RECAP ====================

class TestEventRecap:
    def _count(self, admin_token, feature):
        r = requests.get(f"{API}/admin/control/usage/overview",
                         params={"feature": feature},
                         headers=_h(admin_token), timeout=30)
        assert r.status_code == 200
        for row in (r.json().get("features") or []):
            if row.get("key") == feature:
                return int(row.get("usage_month", 0))
        return -1

    def test_recap_flow(self, admin_token, an_event):
        eid = an_event["id"]
        pre = self._count(admin_token, "ai_event_recap")
        r = requests.post(f"{API}/events/{eid}/ai-recap",
                          json={"regenerate": True, "language": "en"},
                          headers=_h(admin_token), timeout=180)
        assert r.status_code == 200, r.text[:400]
        content = r.json()["recap"]["content"]
        need = {"executive_summary", "event_performance", "lead_quality", "strongest_opportunities",
                "key_patterns", "team_highlights", "followup_priorities", "next_actions", "risks", "conclusion"}
        assert need.issubset(content.keys()), f"missing: {need - set(content.keys())}"
        assert isinstance(content["next_actions"], list)
        post = self._count(admin_token, "ai_event_recap")
        if pre >= 0 and post >= 0:
            # EXACTLY one usage regardless of #leads
            assert post == pre + 1, f"one recap = one usage: {pre}->{post}"

        # cached
        r2 = requests.post(f"{API}/events/{eid}/ai-recap",
                           json={"regenerate": False, "language": "en"},
                           headers=_h(admin_token), timeout=30)
        assert r2.status_code == 200
        assert r2.json().get("cached") is True
        post_cached = self._count(admin_token, "ai_event_recap")
        if post >= 0 and post_cached >= 0:
            assert post_cached == post, "cached should not add usage"

        # GET stored
        r3 = requests.get(f"{API}/events/{eid}/ai-recap", headers=_h(admin_token), timeout=30)
        assert r3.status_code == 200 and r3.json()["recap"] is not None


# ==================== PERMISSIONS ====================

class TestPermissions:
    def test_other_tenant_forbidden(self, throwaway, a_lead, an_event):
        tok = throwaway["token"]
        r = requests.get(f"{API}/crm/leads/{a_lead['id']}/ai-insight", headers=_h(tok), timeout=30)
        assert r.status_code in (403, 404), f"expected forbidden, got {r.status_code}"
        r2 = requests.post(f"{API}/crm/leads/{a_lead['id']}/ai-insight",
                           json={"regenerate": False}, headers=_h(tok), timeout=30)
        assert r2.status_code in (403, 404)
        r3 = requests.get(f"{API}/events/{an_event['id']}/ai-recap", headers=_h(tok), timeout=30)
        assert r3.status_code in (403, 404)
        r4 = requests.post(f"{API}/events/{an_event['id']}/ai-recap",
                           json={"regenerate": False}, headers=_h(tok), timeout=30)
        assert r4.status_code in (403, 404)


# ==================== ENFORCEMENT TOGGLE ====================

class TestEnforcementToggle:
    def test_lead_insight_enforcement_then_reset(self, admin_token, throwaway, a_lead):
        # Enable enforcement per_user with a tiny limit for pro plan (throwaway = free)
        # Use plan_limits for all plans to be safe.
        plan_limits = {p: {"mode": "monthly", "limit": 0} for p in ("trial", "pro", "team", "enterprise", "free")}
        # Only real plans are stored, but include a minimal set:
        plan_limits = {p: {"mode": "monthly", "limit": 0} for p in ("trial", "pro", "team", "enterprise")}
        r = requests.put(f"{API}/admin/control/usage/config/ai_lead_insight",
                         json={"enforcement_enabled": True, "scope": "per_user",
                               "hard_behavior": "block", "plan_limits": plan_limits},
                         headers=_h(admin_token), timeout=30)
        assert r.status_code == 200, r.text[:300]

        # GET /usage/me for throwaway (whose plan should be trial or free by default)
        r_me = requests.get(f"{API}/usage/me", headers=_h(throwaway["token"]), timeout=30)
        # It might be an empty list if plan is "free" (not in USAGE_PLANS). Not fatal.
        assert r_me.status_code == 200

        # Throwaway attempts to generate on their OWN lead? They don't have one.
        # Instead just verify admin (super_admin) is still allowed and normal user 403 on admin's lead
        # remains 403 (permission comes first, not 429). This confirms guard chain intact.
        r_gen = requests.post(f"{API}/crm/leads/{a_lead['id']}/ai-insight",
                              json={"regenerate": True}, headers=_h(throwaway["token"]), timeout=30)
        assert r_gen.status_code in (403, 404)  # permission still enforced

        # RESET: disable enforcement
        r_reset = requests.put(f"{API}/admin/control/usage/config/ai_lead_insight",
                               json={"enforcement_enabled": False},
                               headers=_h(admin_token), timeout=30)
        assert r_reset.status_code == 200

        # Verify OFF
        r_cfg = requests.get(f"{API}/admin/control/usage/config", headers=_h(admin_token), timeout=30)
        feats = {f["key"]: f for f in r_cfg.json()["features"]}
        assert feats["ai_lead_insight"]["config"].get("enforcement_enabled") is False, "must leave enforcement OFF"

    def test_event_recap_enforcement_stays_off(self, admin_token):
        r_cfg = requests.get(f"{API}/admin/control/usage/config", headers=_h(admin_token), timeout=30)
        feats = {f["key"]: f for f in r_cfg.json()["features"]}
        assert feats["ai_event_recap"]["config"].get("enforcement_enabled") in (False, None)


# ==================== REGRESSIONS ====================

class TestRegressions:
    def test_billing_endpoint(self, admin_token):
        r = requests.get(f"{API}/billing", headers=_h(admin_token), timeout=30)
        assert r.status_code == 200
        b = r.json()
        # accept either 'plan' or nested
        assert "plan" in b or "status" in b or "usage" in b or "workspace" in b

    def test_ai_followup_still_works(self, admin_token, a_lead):
        payload = {"lead_id": a_lead["id"], "lead_name": a_lead.get("name", "Test Lead"),
                   "channel": "email", "tone": "friendly", "language": "en"}
        r = requests.post(f"{API}/ai/followup", json=payload, headers=_h(admin_token), timeout=120)
        assert r.status_code in (200, 201), f"unexpected {r.status_code}: {r.text[:200]}"

    def test_event_dashboard(self, admin_token, an_event):
        r = requests.get(f"{API}/events/{an_event['id']}/dashboard", headers=_h(admin_token), timeout=30)
        assert r.status_code == 200
        assert "kpis" in r.json()
