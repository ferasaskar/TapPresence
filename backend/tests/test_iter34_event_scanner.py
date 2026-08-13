"""Iteration 34 — Event Badge Scanner V1 backend tests.
Covers: /api/events CRUD, /api/scan/card (badge OCR), /api/scan/confirm
(event association, duplicate detection, update-existing), tenant isolation,
/api/admin/leads filter params, /api/admin/team-members.
"""
import base64
import os
import time

import pytest
import requests

def _load_backend_url():
    v = os.environ.get("REACT_APP_BACKEND_URL")
    if v:
        return v.rstrip("/")
    envp = "/app/frontend/.env"
    if os.path.exists(envp):
        for line in open(envp):
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip().rstrip("/")
    raise RuntimeError("REACT_APP_BACKEND_URL not set")


BASE = _load_backend_url()
ADMIN = {"email": "admin@ariadni.id", "password": "Ariadni@2026"}
WORK = {"email": "work@gmail.com", "password": "mohammed"}
TARGET_CARD = "feras-askar"
BADGE_EN = "/app/test_assets/badge_english.jpeg"
BADGE_AR = "/app/test_assets/badge_arabic.jpeg"


# ------------------------------------------------------------------ fixtures
def _login(creds):
    r = requests.post(f"{BASE}/api/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text[:200]}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_h():
    return {"Authorization": f"Bearer {_login(ADMIN)}"}


@pytest.fixture(scope="module")
def work_h():
    return {"Authorization": f"Bearer {_login(WORK)}"}


@pytest.fixture(scope="module")
def badge_en_b64():
    with open(BADGE_EN, "rb") as f:
        return base64.b64encode(f.read()).decode()


@pytest.fixture(scope="module")
def badge_ar_b64():
    with open(BADGE_AR, "rb") as f:
        return base64.b64encode(f.read()).decode()


# ------------------------------------------------------------------ Events CRUD
class TestEvents:
    def test_list_events_admin(self, admin_h):
        r = requests.get(f"{BASE}/api/events", headers=admin_h, timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_gitex_seed_present(self, admin_h):
        r = requests.get(f"{BASE}/api/events", headers=admin_h, timeout=15)
        names = [e["name"] for e in r.json()]
        assert any("GITEX" in n.upper() for n in names), f"GITEX not seeded: {names}"

    def test_create_event(self, admin_h):
        payload = {"name": "TEST_iter34_event", "location": "Dubai",
                   "start_date": "2026-01-10", "end_date": "2026-01-12",
                   "notes": "iter34", "campaign_code": "IT34"}
        r = requests.post(f"{BASE}/api/events", headers=admin_h, json=payload, timeout=15)
        assert r.status_code == 200, r.text
        ev = r.json()
        assert ev["name"] == "TEST_iter34_event"
        assert ev["status"] == "active"
        assert ev["lead_count"] == 0
        pytest.iter34_event_id = ev["id"]

    def test_get_event(self, admin_h):
        eid = pytest.iter34_event_id
        r = requests.get(f"{BASE}/api/events/{eid}", headers=admin_h, timeout=15)
        assert r.status_code == 200
        j = r.json()
        assert j["event"]["id"] == eid
        assert isinstance(j["leads"], list)

    def test_patch_event(self, admin_h):
        eid = pytest.iter34_event_id
        r = requests.patch(f"{BASE}/api/events/{eid}", headers=admin_h,
                           json={"location": "Riyadh"}, timeout=15)
        assert r.status_code == 200
        assert r.json()["location"] == "Riyadh"


# ------------------------------------------------------------------ Tenant isolation
class TestTenantIsolation:
    def test_work_user_sees_no_ariadni_events(self, work_h):
        r = requests.get(f"{BASE}/api/events", headers=work_h, timeout=15)
        assert r.status_code == 200
        # work@'s workspace has no events; ARIADNI HQ events should NOT appear
        for ev in r.json():
            assert "GITEX" not in ev["name"].upper()
            assert ev.get("name") != "TEST_iter34_event"

    def test_work_user_403_on_admin_event(self, work_h):
        eid = pytest.iter34_event_id
        r = requests.get(f"{BASE}/api/events/{eid}", headers=work_h, timeout=15)
        assert r.status_code == 403, r.text

    def test_work_user_cannot_see_admin_leads(self, admin_h, work_h):
        # Admin sees many leads on feras-askar; work@ should not.
        r_admin = requests.get(f"{BASE}/api/admin/leads?slug={TARGET_CARD}",
                               headers=admin_h, timeout=15)
        assert r_admin.status_code == 200
        r_work = requests.get(f"{BASE}/api/admin/leads?slug={TARGET_CARD}",
                              headers=work_h, timeout=15)
        # work@ doesn't own feras-askar → 403
        assert r_work.status_code == 403


# ------------------------------------------------------------------ Scan card (OCR)
class TestScanCard:
    def test_scan_badge_english(self, admin_h, badge_en_b64):
        payload = {"image_base64": badge_en_b64, "source": "event_badge_scan"}
        r = requests.post(f"{BASE}/api/scan/card", headers=admin_h, json=payload, timeout=90)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j.get("configured") is True
        d = j.get("draft", {})
        assert d.get("name"), f"no name extracted: {d}"
        pytest.badge_en_draft = d
        print(f"EN draft: name={d.get('name')} company={d.get('company')} title={d.get('title')}")

    def test_scan_badge_arabic(self, admin_h, badge_ar_b64):
        payload = {"image_base64": badge_ar_b64, "source": "event_badge_scan"}
        r = requests.post(f"{BASE}/api/scan/card", headers=admin_h, json=payload, timeout=90)
        assert r.status_code == 200, r.text
        j = r.json()
        d = j.get("draft", {})
        assert d.get("name"), f"no name extracted from arabic: {d}"
        pytest.badge_ar_draft = d
        print(f"AR draft: name={d.get('name')} company={d.get('company')} lang={d.get('language')}")


# ------------------------------------------------------------------ Scan confirm (save)
class TestScanConfirm:
    def test_confirm_requires_name(self, admin_h):
        r = requests.post(f"{BASE}/api/scan/confirm", headers=admin_h,
                          json={"cardSlug": TARGET_CARD, "name": "",
                                "scanner_type": "event_badge"}, timeout=15)
        assert r.status_code == 400

    def test_confirm_creates_badge_lead_with_event(self, admin_h):
        eid = pytest.iter34_event_id
        unique = f"TEST_iter34_{int(time.time())}"
        payload = {
            "cardSlug": TARGET_CARD, "scanner_type": "event_badge",
            "name": f"{unique} Sarah Thompson", "email": f"{unique}@novatech.test",
            "company": "NovaTech", "title": "CMO", "event_id": eid,
        }
        r = requests.post(f"{BASE}/api/scan/confirm", headers=admin_h, json=payload, timeout=20)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j.get("ok") is True, j
        lead = j["lead"]
        assert lead["source"] == "event_badge_scan"
        assert lead["scanner_type"] == "event_badge"
        assert lead["event_id"] == eid
        assert lead["captured_by"]
        assert len(lead.get("timeline") or []) == 1
        assert lead["timeline"][0]["event"] == "badge_scanned"
        pytest.badge_lead_id = lead["id"]
        pytest.badge_lead_email = payload["email"]

    def test_event_detail_shows_lead(self, admin_h):
        eid = pytest.iter34_event_id
        r = requests.get(f"{BASE}/api/events/{eid}", headers=admin_h, timeout=15)
        j = r.json()
        assert j["lead_count"] >= 1
        ids = [l["id"] for l in j["leads"]]
        assert pytest.badge_lead_id in ids

    def test_duplicate_detection_returns_existing(self, admin_h):
        eid = pytest.iter34_event_id
        payload = {
            "cardSlug": TARGET_CARD, "scanner_type": "event_badge",
            "name": "Sarah Thompson 2", "email": pytest.badge_lead_email,
            "company": "NovaTech", "event_id": eid,
        }
        r = requests.post(f"{BASE}/api/scan/confirm", headers=admin_h, json=payload, timeout=15)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j.get("ok") is False
        assert j.get("duplicate", {}).get("id") == pytest.badge_lead_id

    def test_update_existing_appends_timeline(self, admin_h):
        eid = pytest.iter34_event_id
        payload = {
            "cardSlug": TARGET_CARD, "scanner_type": "event_badge",
            "name": "Sarah Thompson", "email": pytest.badge_lead_email,
            "company": "NovaTech", "event_id": eid,
            "update_lead_id": pytest.badge_lead_id,
        }
        r = requests.post(f"{BASE}/api/scan/confirm", headers=admin_h, json=payload, timeout=15)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j.get("ok") is True
        assert j.get("updated") is True
        tl = j["lead"]["timeline"]
        assert len(tl) >= 2
        kinds = [t["event"] for t in tl]
        assert "badge_rescanned" in kinds

    def test_business_card_regression(self, admin_h, badge_en_b64):
        # scanner_type=business_card should NOT require event and source should be business_card_scan
        payload = {
            "cardSlug": TARGET_CARD, "scanner_type": "business_card",
            "name": f"TEST_iter34_bc_{int(time.time())}",
            "company": "Regression Co",
        }
        r = requests.post(f"{BASE}/api/scan/confirm", headers=admin_h, json=payload, timeout=15)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j.get("ok") is True
        assert j["lead"]["source"] == "business_card_scan"
        assert j["lead"]["scanner_type"] == "business_card"
        assert j["lead"].get("event_id") in ("", None)


# ------------------------------------------------------------------ Leads filters
class TestLeadsFilters:
    def test_filter_by_event(self, admin_h):
        eid = pytest.iter34_event_id
        r = requests.get(f"{BASE}/api/admin/leads?event_id={eid}",
                         headers=admin_h, timeout=15)
        assert r.status_code == 200
        leads = r.json()
        assert len(leads) >= 1
        assert all(l.get("event_id") == eid for l in leads)

    def test_filter_by_source(self, admin_h):
        r = requests.get(f"{BASE}/api/admin/leads?source=event_badge_scan",
                         headers=admin_h, timeout=15)
        assert r.status_code == 200
        for l in r.json():
            assert l["source"] == "event_badge_scan"

    def test_team_members(self, admin_h):
        r = requests.get(f"{BASE}/api/admin/team-members", headers=admin_h, timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert len(r.json()) >= 1
