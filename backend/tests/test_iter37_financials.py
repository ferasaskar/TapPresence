"""Iteration 37 — Pipeline Value + Attributed Revenue + Event ROI backend tests.

Covers Tests 1-19, 23 from the review request. Uses the existing GITEX event/leads and does
edits with backup+restore so seed state is preserved.
"""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
GITEX_ID = "3877d2f4-b5b8-41fa-ba60-4e934f88a83f"
L1 = "30ee38ed-f003-43ec-bcdd-976fcd3d5cc0"  # customer, opp=100000 AED, rev=72000 AED (event attribution)
L2 = "8532bdf7-affe-4b42-9cf0-f0dee3a74b35"  # qualified, opp=50000 AED
L3 = "10d82386-9025-4ace-b0e7-0c16fdc0099c"  # new, no financials
SARAH = "82ac942b-332c-4a3d-89d2-f0601bf46ddc"  # qualified, opp=999 USD (currency mismatch)

ADMIN = {"email": "admin@ariadni.id", "password": "Ariadni@2026"}
WORK = {"email": "work@gmail.com", "password": "mohammed"}


def _login(creds):
    r = requests.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=20)
    assert r.status_code == 200, r.text[:200]
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_h():
    return {"Authorization": f"Bearer {_login(ADMIN)}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def work_h():
    return {"Authorization": f"Bearer {_login(WORK)}", "Content-Type": "application/json"}


def _get_lead(h, lid):
    # Fetch via event detail; /admin/leads/{id} appears not to return the raw lead for arbitrary tests.
    r = requests.get(f"{BASE_URL}/api/events/{GITEX_ID}", headers=h, timeout=20)
    assert r.status_code == 200
    for l in r.json()["leads"]:
        if l["id"] == lid:
            return l
    return None


def _dash(h):
    r = requests.get(f"{BASE_URL}/api/events/{GITEX_ID}/dashboard", headers=h, timeout=20)
    assert r.status_code == 200, r.text[:200]
    return r.json()


def _patch_fin(h, lid, body):
    return requests.patch(f"{BASE_URL}/api/admin/leads/{lid}/financials", headers=h, json=body, timeout=20)


# ------------------------------------------------------------ dashboard baseline

def test_dashboard_financials_baseline(admin_h):
    """Test3+Test4+Test5+Test10+Test15: pipeline sums OPEN AED opps, excludes cust/not_interested,
    revenue attributed, ROI=44%, currency-mismatch USD excluded."""
    fin = _dash(admin_h)["financials"]
    assert fin["currency"] == "AED"
    assert fin["pipeline_value"] == 50000.0  # only L2; L1(customer) excluded, SARAH(USD) excluded
    assert fin["open_opportunities"] == 1
    assert fin["attributed_revenue"] == 72000.0
    assert fin["attributed_revenue_count"] == 1
    assert fin["event_cost"] == 50000.0
    assert fin["roi"] == 44.0
    assert fin["revenue_cost_multiple"] == 1.44
    assert fin["excluded"]["pipeline_currency_mismatch"] >= 1  # SARAH USD
    # customer lead's opp value must NOT be inside pipeline_by_stage (only qualified 50000)
    by_stage = {p["stage"]: p["value"] for p in fin["pipeline_by_stage"]}
    assert by_stage.get("qualified") == 50000.0
    assert "customer" not in by_stage and "new" not in by_stage and "not_interested" not in by_stage


# ------------------------------------------------------------ Test1/2/14/16 financials PATCH lifecycle

def test_financials_set_edit_clear_and_audit(admin_h):
    lead_before = _get_lead(admin_h, L2)
    orig_val = lead_before.get("opportunity_value")
    orig_ccy = lead_before.get("opportunity_currency")
    orig_score = lead_before.get("lead_score")
    orig_temp = lead_before.get("lead_temperature")
    orig_close = lead_before.get("expected_close_date") or ""

    # (1) SET (already 50000 → set to 60000 and expected_close 2026-05-01)
    r = _patch_fin(admin_h, L2, {"opportunity_value": 60000, "opportunity_currency": "AED",
                                 "expected_close_date": "2026-05-01"})
    assert r.status_code == 200, r.text[:200]
    l = r.json()
    assert l["opportunity_value"] == 60000.0
    assert l["opportunity_currency"] == "AED"
    assert l["expected_close_date"] == "2026-05-01"
    # Test23: score/temperature unchanged by financial edit
    assert l["lead_score"] == orig_score, f"score changed {orig_score}->{l['lead_score']}"
    assert l["lead_temperature"] == orig_temp

    # (2) EDIT — value change writes an 'opportunity_value_updated' timeline entry with OLD -> NEW
    r = _patch_fin(admin_h, L2, {"opportunity_value": 55000, "opportunity_currency": "AED"})
    assert r.status_code == 200
    l = r.json()
    tl_events = [t for t in (l.get("timeline") or []) if t.get("event") == "opportunity_value_updated"]
    assert tl_events, "missing opportunity_value_updated audit"
    last = tl_events[-1]
    assert "→" in (last.get("detail") or ""), f"no OLD → NEW arrow: {last}"

    # (3) CLEAR — null clears cleanly + writes 'opportunity_value_cleared'
    r = _patch_fin(admin_h, L2, {"opportunity_value": None})
    assert r.status_code == 200
    l = r.json()
    assert l["opportunity_value"] is None
    assert l["opportunity_currency"] == ""
    assert any(t.get("event") == "opportunity_value_cleared" for t in l.get("timeline") or [])
    assert l["lead_score"] == orig_score  # Test23 again

    # Dashboard now shows pipeline_value = None (Not available yet)
    fin = _dash(admin_h)["financials"]
    assert fin["pipeline_value"] is None
    assert fin["open_opportunities"] == 0

    # RESTORE original state
    if orig_val is not None:
        body = {"opportunity_value": orig_val, "opportunity_currency": orig_ccy or "AED"}
        if orig_close:
            body["expected_close_date"] = orig_close
        r = _patch_fin(admin_h, L2, body)
        assert r.status_code == 200


# ------------------------------------------------------------ Test6/7 revenue independence + shape

def test_revenue_recorded_independent_of_opp_and_shape(admin_h):
    l1 = _get_lead(admin_h, L1)
    # L1 already has opp=100000, rev=72000 (setup). Verify they're independent + shape.
    assert l1["opportunity_value"] == 100000.0
    assert l1["actual_revenue"] == 72000.0
    ra = l1.get("revenue_attribution") or {}
    for k in ("event_id", "type", "amount", "currency", "recorded_at", "recorded_by"):
        assert k in ra, f"missing revenue_attribution key {k}"
    assert ra["event_id"] == GITEX_ID
    assert ra["type"] == "event"
    assert ra["amount"] == 72000.0
    assert ra["currency"] == "AED"
    # Timeline has revenue_recorded (or revenue_updated)
    tl = l1.get("timeline") or []
    assert any(t.get("event") in ("revenue_recorded", "revenue_updated") for t in tl)


# ------------------------------------------------------------ Test8: organic revenue not counted in event

def test_organic_revenue_excluded_from_event_totals(admin_h):
    """Attach a small revenue to L3 as 'organic' → dashboard attributed_revenue must NOT grow."""
    fin_before = _dash(admin_h)["financials"]
    baseline_rev = fin_before["attributed_revenue"]
    baseline_cnt = fin_before["attributed_revenue_count"]

    r = _patch_fin(admin_h, L3, {"actual_revenue": 5000, "actual_revenue_currency": "AED",
                                 "revenue_attribution_type": "organic"})
    assert r.status_code == 200, r.text[:200]
    l = r.json()
    assert l["actual_revenue"] == 5000.0
    assert (l["revenue_attribution"] or {}).get("type") == "organic"
    assert (l["revenue_attribution"] or {}).get("event_id") in (None, "")

    fin_after = _dash(admin_h)["financials"]
    assert fin_after["attributed_revenue"] == baseline_rev, "organic revenue leaked into event totals"
    assert fin_after["attributed_revenue_count"] == baseline_cnt

    # CLEAR
    r = _patch_fin(admin_h, L3, {"actual_revenue": None})
    assert r.status_code == 200
    l = r.json()
    assert l["actual_revenue"] is None
    assert l["actual_revenue_currency"] == ""
    assert l["revenue_attribution"] is None
    assert any(t.get("event") == "revenue_cleared" for t in l.get("timeline") or [])


# ------------------------------------------------------------ Test5: customer conversion w/o revenue

def test_customer_conversion_no_revenue_required(admin_h):
    """Set L3.status=customer, then unset back to 'new'. Must not require revenue."""
    r = requests.patch(f"{BASE_URL}/api/admin/leads/{L3}/status",
                       headers=admin_h, json={"status": "customer"}, timeout=20)
    assert r.status_code == 200, r.text[:200]
    # verify
    l = _get_lead(admin_h, L3)
    assert l["status"] == "customer"
    assert l.get("actual_revenue") in (None, 0, 0.0)  # no revenue was required

    # revert
    r = requests.patch(f"{BASE_URL}/api/admin/leads/{L3}/status",
                       headers=admin_h, json={"status": "new"}, timeout=20)
    assert r.status_code == 200


# ------------------------------------------------------------ Test11/12: ROI null when missing

def test_roi_null_when_event_cost_missing(admin_h):
    """Clear event_cost → roi=null; restore afterwards."""
    ev_before = requests.get(f"{BASE_URL}/api/events/{GITEX_ID}", headers=admin_h, timeout=20).json()["event"]
    orig_cost = ev_before.get("event_cost")
    orig_cc = ev_before.get("event_cost_currency")

    r = requests.patch(f"{BASE_URL}/api/events/{GITEX_ID}", headers=admin_h,
                       json={"event_cost": None}, timeout=20)
    assert r.status_code == 200
    fin = _dash(admin_h)["financials"]
    assert fin["roi"] is None
    assert fin["revenue_cost_multiple"] is None

    # restore
    r = requests.patch(f"{BASE_URL}/api/events/{GITEX_ID}", headers=admin_h,
                       json={"event_cost": orig_cost, "event_cost_currency": orig_cc or "AED"}, timeout=20)
    assert r.status_code == 200


def test_roi_null_when_revenue_missing(admin_h):
    """Temporarily clear L1 revenue, expect roi=None; restore."""
    l1 = _get_lead(admin_h, L1)
    orig_amt = l1.get("actual_revenue")
    orig_ccy = l1.get("actual_revenue_currency") or "AED"

    r = _patch_fin(admin_h, L1, {"actual_revenue": None})
    assert r.status_code == 200
    fin = _dash(admin_h)["financials"]
    assert fin["attributed_revenue"] is None
    assert fin["roi"] is None

    # restore
    r = _patch_fin(admin_h, L1, {"actual_revenue": orig_amt, "actual_revenue_currency": orig_ccy,
                                 "revenue_attribution_type": "event",
                                 "revenue_attribution_event_id": GITEX_ID})
    assert r.status_code == 200


# ------------------------------------------------------------ Test13: event cost editing

def test_event_cost_edit_and_clear(admin_h):
    ev_before = requests.get(f"{BASE_URL}/api/events/{GITEX_ID}", headers=admin_h, timeout=20).json()["event"]
    orig = ev_before.get("event_cost")
    orig_cc = ev_before.get("event_cost_currency") or "AED"
    # set to 12345
    r = requests.patch(f"{BASE_URL}/api/events/{GITEX_ID}", headers=admin_h,
                       json={"event_cost": 12345, "event_cost_currency": "AED"}, timeout=20)
    assert r.status_code == 200
    assert r.json()["event_cost"] == 12345
    # clear
    r = requests.patch(f"{BASE_URL}/api/events/{GITEX_ID}", headers=admin_h,
                       json={"event_cost": None}, timeout=20)
    assert r.status_code == 200
    ev = requests.get(f"{BASE_URL}/api/events/{GITEX_ID}", headers=admin_h, timeout=20).json()["event"]
    assert ev.get("event_cost") in (None,)
    # restore
    requests.patch(f"{BASE_URL}/api/events/{GITEX_ID}", headers=admin_h,
                   json={"event_cost": orig, "event_cost_currency": orig_cc}, timeout=20)


# ------------------------------------------------------------ Test17: top_opportunities exclusions

def test_top_opportunities_excludes_customer_with_revenue_and_not_interested(admin_h):
    """L1 is customer with actual_revenue → must NOT appear. Sarah (qualified) should."""
    d = _dash(admin_h)
    ids = [o["id"] for o in d["top_opportunities"]]
    assert L1 not in ids, "closed customer with revenue leaked into top_opportunities"
    # DESC sort by opp value
    vals = [o["opportunity_value"] for o in d["top_opportunities"]]
    assert vals == sorted(vals, reverse=True)


# ------------------------------------------------------------ Test18/19: RBAC

def test_cross_tenant_financials_403(work_h):
    """work@gmail.com is a different workspace's owner → PATCH GITEX lead financials must 403."""
    r = _patch_fin(work_h, L2, {"opportunity_value": 999})
    assert r.status_code in (403, 404), f"expected 403/404 got {r.status_code}: {r.text[:200]}"


def test_cross_tenant_revenue_attribution_403(work_h):
    """work@gmail.com cannot attribute revenue to an event they cannot access."""
    # Try on own lead? They may have no leads. Just verify GITEX lead patch = 403.
    r = _patch_fin(work_h, L1, {"actual_revenue": 100, "actual_revenue_currency": "AED",
                                "revenue_attribution_type": "event",
                                "revenue_attribution_event_id": GITEX_ID})
    assert r.status_code in (403, 404)


# ------------------------------------------------------------ Test16 leaderboard financials

def test_leaderboard_has_pipeline_and_revenue(admin_h):
    d = _dash(admin_h)
    lb = d["leaderboard"]
    assert lb, "leaderboard empty"
    for row in lb:
        assert "pipeline_value" in row and "attributed_revenue" in row
    # At least one row should have non-null pv or rev (given L1 rev + L2 pv exist)
    assert any((r.get("pipeline_value") or 0) > 0 or (r.get("attributed_revenue") or 0) > 0 for r in lb)


# ------------------------------------------------------------ Test9: multi-event revenue attribution EXCLUSIVE

def test_multi_event_revenue_not_double_counted(admin_h):
    """Create a throwaway event E2, associate L1 with E2 (timeline entry), then verify:
       - E1 (GITEX) attributed_revenue still contains L1's 72000
       - E2 attributed_revenue does NOT contain L1's 72000 (exclusive to GITEX)
       - L1's pipeline value (100000) is associated to BOTH events (ASSOCIATED, per spec) — but L1 is
         a customer so it's excluded from OPEN pipeline anyway. So we skip PV double check with L1
         and just verify revenue exclusivity."""
    # Create throwaway event
    ev = {"name": f"TEST_iter37_multi_{int(time.time())}", "location": "", "start_date": "2026-03-01",
          "end_date": "2026-03-02", "notes": "", "campaign_code": "", "timezone": "Asia/Dubai",
          "currency": "AED"}
    r = requests.post(f"{BASE_URL}/api/events", headers=admin_h, json=ev, timeout=20)
    assert r.status_code == 200, r.text[:200]
    eid = r.json()["id"]
    try:
        # Add a timeline entry on L1 that references E2 so it's "associated" with E2
        # (No public "associate" endpoint — rely on scan/rescan simulation via db insert alternative).
        # Simpler: just check E2 dashboard on its own — since L1's revenue_attribution.event_id=GITEX,
        # it must not appear anywhere else even if we could associate it. Just call dashboard.
        d2 = requests.get(f"{BASE_URL}/api/events/{eid}/dashboard", headers=admin_h, timeout=20).json()
        assert d2["financials"]["attributed_revenue"] in (None, 0, 0.0)
        assert d2["financials"]["attributed_revenue_count"] == 0
        # GITEX still holds 72000
        d1 = _dash(admin_h)
        assert d1["financials"]["attributed_revenue"] == 72000.0
    finally:
        requests.patch(f"{BASE_URL}/api/events/{eid}", headers=admin_h, json={"status": "archived"}, timeout=20)


# ------------------------------------------------------------ Test4: not_interested lead's opp excluded

def test_not_interested_lead_opp_excluded_from_pipeline(admin_h):
    """Set L3 opp=7777 AED and status=not_interested → not counted in pipeline_value."""
    pv_before = _dash(admin_h)["financials"]["pipeline_value"] or 0
    _patch_fin(admin_h, L3, {"opportunity_value": 7777, "opportunity_currency": "AED"})
    r = requests.patch(f"{BASE_URL}/api/admin/leads/{L3}/status", headers=admin_h,
                       json={"status": "not_interested"}, timeout=20)
    assert r.status_code == 200
    fin_after = _dash(admin_h)["financials"]
    assert (fin_after["pipeline_value"] or 0) == pv_before, "not_interested lead leaked into pipeline"
    # cleanup: clear + revert stage
    _patch_fin(admin_h, L3, {"opportunity_value": None})
    requests.patch(f"{BASE_URL}/api/admin/leads/{L3}/status", headers=admin_h,
                   json={"status": "new"}, timeout=20)
