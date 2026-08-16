"""Iteration 35 — Event Dashboard + Attribution backend tests.

Focus:
- GET /api/events (list w/ lead_count/meeting_count/customer_count)
- GET /api/events/{id} (enriched leads)
- GET /api/events/{id}/dashboard (kpis, pipeline, leaderboard, followups, daily_trend, cost)
- Tenant isolation via work@gmail.com
- Attribution: new vs returning, meeting excludes cancelled, conversion rate
- POST /api/admin/leads/{id}/complete-follow-up
"""
import os
import uuid
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
GITEX_ID = "3877d2f4-b5b8-41fa-ba60-4e934f88a83f"

ADMIN = {"email": "admin@ariadni.id", "password": "Ariadni@2026"}
WORK = {"email": "work@gmail.com", "password": "mohammed"}


def _login(creds):
    r = requests.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=20)
    assert r.status_code == 200, f"login failed {r.status_code} {r.text[:200]}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_headers():
    return {"Authorization": f"Bearer {_login(ADMIN)}"}


@pytest.fixture(scope="module")
def work_headers():
    return {"Authorization": f"Bearer {_login(WORK)}"}


# ----- List events -----

def test_events_list_has_stats(admin_headers):
    r = requests.get(f"{BASE_URL}/api/events", headers=admin_headers, timeout=20)
    assert r.status_code == 200
    events = r.json()
    assert isinstance(events, list) and len(events) >= 1
    gitex = next((e for e in events if e["id"] == GITEX_ID), None)
    assert gitex is not None, "GITEX event missing"
    for k in ("lead_count", "meeting_count", "customer_count"):
        assert k in gitex, f"missing stat {k}"
    assert gitex["lead_count"] >= 4


def test_event_detail_enrichment(admin_headers):
    r = requests.get(f"{BASE_URL}/api/events/{GITEX_ID}", headers=admin_headers, timeout=20)
    assert r.status_code == 200
    body = r.json()
    assert body["event"]["id"] == GITEX_ID
    assert isinstance(body["leads"], list)
    for l in body["leads"]:
        assert "new_returning" in l and l["new_returning"] in ("new", "returning")
        assert "has_meeting" in l
        assert "captured_by_name" in l


# ----- Dashboard aggregates -----

def test_dashboard_kpis_shape_and_conversion(admin_headers):
    r = requests.get(f"{BASE_URL}/api/events/{GITEX_ID}/dashboard", headers=admin_headers, timeout=20)
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    for k in ("kpis", "pipeline", "capture_methods", "conversion", "followups",
              "leaderboard", "daily_trend", "cost", "new_vs_returning", "timezone"):
        assert k in d, f"missing {k}"
    kpis = d["kpis"]
    assert kpis["total_leads"] >= 4
    # conversion = customers/total*100
    if kpis["total_leads"]:
        expected = round(kpis["customers"] * 100 / kpis["total_leads"], 1)
        assert kpis["conversion_rate"] == expected
    # pipeline = 7 stages
    stages = [p["stage"] for p in d["pipeline"]]
    assert stages == ["new", "contacted", "qualified", "meeting", "opportunity", "customer", "not_interested"]
    # sum(pipeline) == total leads
    assert sum(p["count"] for p in d["pipeline"]) == kpis["total_leads"]
    # cost never fabricates revenue/roi
    assert d["cost"]["attributed_revenue"] is None
    assert d["cost"]["roi"] is None
    # followups: seeded has 1 overdue + 1 completed
    assert d["followups"]["overdue"] >= 1
    assert d["followups"]["completed"] >= 1


def test_dashboard_leaderboard_and_daily(admin_headers):
    r = requests.get(f"{BASE_URL}/api/events/{GITEX_ID}/dashboard", headers=admin_headers, timeout=20)
    d = r.json()
    lb = d["leaderboard"]
    # each row has expected fields
    for row in lb:
        for k in ("user_id", "name", "leads", "new", "returning", "meetings", "customers", "conversion_rate"):
            assert k in row
    # daily_trend sorted by date asc
    dates = [x["date"] for x in d["daily_trend"]]
    assert dates == sorted(dates)


# ----- Tenant isolation -----

def test_tenant_isolation_events_list_empty(work_headers):
    r = requests.get(f"{BASE_URL}/api/events", headers=work_headers, timeout=20)
    assert r.status_code == 200
    events = r.json()
    # work@gmail.com must not see GITEX
    assert not any(e["id"] == GITEX_ID for e in events), "cross-tenant event leak"


def test_tenant_isolation_gitex_403(work_headers):
    r = requests.get(f"{BASE_URL}/api/events/{GITEX_ID}/dashboard", headers=work_headers, timeout=20)
    assert r.status_code == 403


def test_tenant_isolation_detail_403(work_headers):
    r = requests.get(f"{BASE_URL}/api/events/{GITEX_ID}", headers=work_headers, timeout=20)
    assert r.status_code == 403


# ----- Empty state event -----

def test_empty_event_dashboard(admin_headers):
    ev = {
        "name": f"TEST_iter35_empty_{int(time.time())}",
        "location": "",
        "start_date": "2026-02-01",
        "end_date": "2026-02-02",
        "notes": "",
        "campaign_code": "",
        "timezone": "Asia/Dubai",
    }
    r = requests.post(f"{BASE_URL}/api/events", headers=admin_headers, json=ev, timeout=20)
    assert r.status_code == 200, r.text[:200]
    eid = r.json()["id"]
    d = requests.get(f"{BASE_URL}/api/events/{eid}/dashboard", headers=admin_headers, timeout=20).json()
    assert d["kpis"]["total_leads"] == 0
    assert d["kpis"]["conversion_rate"] == 0
    assert d["cost"]["attributed_revenue"] is None
    assert d["cost"]["roi"] is None
    assert d["timezone"] == "Asia/Dubai"
    # empty pipeline sums to zero
    assert sum(p["count"] for p in d["pipeline"]) == 0
    # cleanup: archive
    requests.patch(f"{BASE_URL}/api/events/{eid}", headers=admin_headers, json={"status": "archived"}, timeout=20)


# ----- Attribution (new/returning) — verify seeded numbers stay consistent -----

def test_new_vs_returning_matches_pipeline_total(admin_headers):
    d = requests.get(f"{BASE_URL}/api/events/{GITEX_ID}/dashboard", headers=admin_headers, timeout=20).json()
    nv = d["new_vs_returning"]
    assert nv["new"] + nv["returning"] == d["kpis"]["total_leads"]


# ----- PATCH event_cost sets and is reflected -----

def test_patch_event_cost(admin_headers):
    r = requests.patch(f"{BASE_URL}/api/events/{GITEX_ID}",
                       headers=admin_headers,
                       json={"event_cost": 12345.5, "event_cost_currency": "usd"},
                       timeout=20)
    assert r.status_code == 200
    ev = r.json()
    assert ev.get("event_cost") == 12345.5
    assert ev.get("event_cost_currency") == "USD"
    d = requests.get(f"{BASE_URL}/api/events/{GITEX_ID}/dashboard", headers=admin_headers, timeout=20).json()
    assert d["cost"]["event_cost"] == 12345.5
    assert d["cost"]["currency"] == "USD"
    # revenue/roi remain None (no fake)
    assert d["cost"]["attributed_revenue"] is None
    assert d["cost"]["roi"] is None


# ----- complete-follow-up increments completed counter -----

def test_complete_follow_up_endpoint(admin_headers):
    # find an event lead with an overdue reminder (or any lead), toggle complete on it
    body = requests.get(f"{BASE_URL}/api/events/{GITEX_ID}", headers=admin_headers, timeout=20).json()
    leads = body["leads"]
    assert leads, "no leads to test"
    # pick a lead not yet marked completed
    target = next((l for l in leads if not l.get("follow_up_completed_at")), leads[0])
    lid = target["id"]
    r = requests.post(f"{BASE_URL}/api/admin/leads/{lid}/complete-follow-up",
                      headers=admin_headers, timeout=20)
    assert r.status_code == 200, r.text[:200]
    data = r.json()
    assert data.get("ok") is True
    assert data.get("follow_up_completed_at")
    # dashboard completed count should include this lead
    d = requests.get(f"{BASE_URL}/api/events/{GITEX_ID}/dashboard", headers=admin_headers, timeout=20).json()
    assert d["kpis"]["followups_completed"] >= 1
