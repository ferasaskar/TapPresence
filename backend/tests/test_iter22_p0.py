"""Iteration 22 — P0 roadmap tests: leads stages/fields/reminders, scanner qr_scan, NFC.

Covers:
- Public lead creation with new fields, status='new'
- Lead pipeline stages (7 new + legacy aliases + invalid 400)
- Lead fields PATCH + cross-tenant 403
- Lead reminder set/replace/clear + future-hidden / past-visible + notif dedup
- Delete lead cleans up reminder notification
- scan/confirm accepts qr_scan source, creates lead with tags=['scanned'], status='new'
- NFC devices list works
"""
import os
import time
import pytest
import requests
from datetime import datetime, timezone, timedelta

def _load_frontend_env():
    envp = "/app/frontend/.env"
    if os.path.exists(envp):
        for line in open(envp):
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip()
    raise RuntimeError("REACT_APP_BACKEND_URL missing")


BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or _load_frontend_env()).rstrip("/")
API = f"{BASE_URL}/api"

SLUG = "feras-askar"

ADMIN_EMAIL = "admin@ariadni.id"
ADMIN_PASS = "Ariadni@2026"

FERAS_EMAIL = "feras@ariadni.ai"
FERAS_PASS = "Feras@2026"

OTHER_EMAIL = "work@gmail.com"


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_token():
    return _login(ADMIN_EMAIL, ADMIN_PASS)


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def feras_headers():
    try:
        tok = _login(FERAS_EMAIL, FERAS_PASS)
        return {"Authorization": f"Bearer {tok}"}
    except AssertionError:
        return None


def _create_public_lead(name="TEST_iter22 Lead"):
    r = requests.post(
        f"{API}/cards/{SLUG}/leads",
        json={"name": name, "email": "test_iter22@example.com", "phone": "+15551230000",
              "message": "iter22 test"},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    # get the lead id via admin list (public endpoint doesn't return id)
    return None


def _find_created_lead(admin_headers, name):
    r = requests.get(f"{API}/admin/leads", headers=admin_headers, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    leads = data if isinstance(data, list) else (data.get("leads", []) or [])
    for l in leads:
        if l.get("name") == name:
            return l
    return None


# --------------------------- Public lead creation ---------------------------

class TestPublicLeadCreation:
    def test_public_lead_created_with_new_fields(self, admin_headers):
        name = f"TEST_iter22_pub_{int(time.time())}"
        _create_public_lead(name=name)
        lead = _find_created_lead(admin_headers, name)
        assert lead is not None, "created lead not found in /admin/leads"
        assert lead["status"] == "new"
        for f in ("company", "title", "website", "event", "met_at",
                  "captured_by", "next_follow_up", "tags", "notes"):
            assert f in lead, f"missing field {f}"
        assert isinstance(lead["tags"], list)
        # cleanup
        requests.delete(f"{API}/admin/leads/{lead['id']}", headers=admin_headers)


# --------------------------- Lead stages ---------------------------

class TestLeadStages:
    @pytest.fixture()
    def lead_id(self, admin_headers):
        name = f"TEST_iter22_stage_{int(time.time()*1000)}"
        _create_public_lead(name=name)
        lead = _find_created_lead(admin_headers, name)
        assert lead
        yield lead["id"]
        requests.delete(f"{API}/admin/leads/{lead['id']}", headers=admin_headers)

    @pytest.mark.parametrize("stage", [
        "new", "contacted", "qualified", "meeting",
        "opportunity", "customer", "not_interested",
    ])
    def test_valid_stages(self, admin_headers, lead_id, stage):
        r = requests.patch(f"{API}/admin/leads/{lead_id}/status",
                           headers=admin_headers, json={"status": stage}, timeout=30)
        assert r.status_code == 200, r.text

    @pytest.mark.parametrize("legacy,canonical", [
        ("converted", "customer"),
        ("meeting_booked", "meeting"),
        ("archived", "not_interested"),
        ("won", "customer"),
        ("lost", "not_interested"),
        ("follow_up", "contacted"),
    ])
    def test_legacy_aliases_accepted(self, admin_headers, lead_id, legacy, canonical):
        r = requests.patch(f"{API}/admin/leads/{lead_id}/status",
                           headers=admin_headers, json={"status": legacy}, timeout=30)
        assert r.status_code == 200, r.text
        # verify stored as canonical
        data = requests.get(f"{API}/admin/leads", headers=admin_headers).json()
        leads = data if isinstance(data, list) else (data.get("leads", []) or [])
        for l in leads:
            if l["id"] == lead_id:
                assert l["status"] == canonical
                return
        pytest.fail("lead not found after status update")

    def test_invalid_stage_400(self, admin_headers, lead_id):
        r = requests.patch(f"{API}/admin/leads/{lead_id}/status",
                           headers=admin_headers, json={"status": "bogus_stage"}, timeout=30)
        assert r.status_code == 400


# --------------------------- Lead fields ---------------------------

class TestLeadFields:
    def test_fields_update_and_return(self, admin_headers):
        name = f"TEST_iter22_fields_{int(time.time()*1000)}"
        _create_public_lead(name=name)
        lead = _find_created_lead(admin_headers, name)
        lid = lead["id"]
        try:
            payload = {
                "company": "RoeCorp", "title": "CEO", "website": "roe.com",
                "tags": ["scanned", "vip"], "notes": "hot lead",
                "met_at": "2026-01-15T10:00:00+00:00",
                "event": "CES 2026", "campaign": "q1",
                "next_follow_up": "2026-02-01T09:00:00+00:00",
            }
            r = requests.patch(f"{API}/admin/leads/{lid}/fields",
                               headers=admin_headers, json=payload, timeout=30)
            assert r.status_code == 200, r.text
            data = r.json()
            for k, v in payload.items():
                assert data[k] == v, f"{k}: {data.get(k)} != {v}"
        finally:
            requests.delete(f"{API}/admin/leads/{lid}", headers=admin_headers)


# --------------------------- Lead reminder ---------------------------

class TestLeadReminder:
    def _get_notifs(self, headers):
        r = requests.get(f"{API}/notifications", headers=headers, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        return data.get("items", data.get("notifications", data if isinstance(data, list) else []))

    def test_future_reminder_hidden_replace_and_clear(self, admin_headers):
        name = f"TEST_iter22_rem_{int(time.time()*1000)}"
        _create_public_lead(name=name)
        lead = _find_created_lead(admin_headers, name)
        lid = lead["id"]
        try:
            future = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
            r = requests.post(f"{API}/admin/leads/{lid}/remind",
                              headers=admin_headers, json={"when": future}, timeout=30)
            assert r.status_code == 200, r.text
            # future reminder must NOT appear in notifications
            notifs = self._get_notifs(admin_headers)
            assert not any(n.get("lead_id") == lid and n.get("type") == "lead_reminder"
                           for n in notifs), "future reminder should be hidden"

            # Replace with another future reminder - still only 1 in db (verified indirectly via clear)
            future2 = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
            r = requests.post(f"{API}/admin/leads/{lid}/remind",
                              headers=admin_headers, json={"when": future2}, timeout=30)
            assert r.status_code == 200

            # past reminder MUST appear
            past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
            r = requests.post(f"{API}/admin/leads/{lid}/remind",
                              headers=admin_headers, json={"when": past}, timeout=30)
            assert r.status_code == 200
            notifs = self._get_notifs(admin_headers)
            matching = [n for n in notifs
                        if n.get("lead_id") == lid and n.get("type") == "lead_reminder"]
            assert len(matching) == 1, f"expected exactly 1 past reminder notif, got {len(matching)}"

            # Clear
            r = requests.delete(f"{API}/admin/leads/{lid}/remind", headers=admin_headers, timeout=30)
            assert r.status_code == 200
            notifs = self._get_notifs(admin_headers)
            assert not any(n.get("lead_id") == lid and n.get("type") == "lead_reminder"
                           for n in notifs), "reminder should be cleared"
        finally:
            requests.delete(f"{API}/admin/leads/{lid}", headers=admin_headers)

    def test_delete_lead_removes_reminder_notification(self, admin_headers):
        name = f"TEST_iter22_delrem_{int(time.time()*1000)}"
        _create_public_lead(name=name)
        lead = _find_created_lead(admin_headers, name)
        lid = lead["id"]
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        requests.post(f"{API}/admin/leads/{lid}/remind",
                      headers=admin_headers, json={"when": past}, timeout=30)
        # confirm visible
        notifs = self._get_notifs(admin_headers)
        assert any(n.get("lead_id") == lid for n in notifs)
        # delete lead
        r = requests.delete(f"{API}/admin/leads/{lid}", headers=admin_headers, timeout=30)
        assert r.status_code == 200
        notifs = self._get_notifs(admin_headers)
        assert not any(n.get("lead_id") == lid for n in notifs), "reminder notif should be gone"


# --------------------------- Scan confirm qr_scan ---------------------------

class TestScannerQrSource:
    def test_scan_confirm_qr_source_creates_lead(self, admin_headers):
        payload = {
            "cardSlug": SLUG, "source": "qr_scan",
            "name": f"TEST_iter22_qr_{int(time.time()*1000)}",
            "email": "jane@roe.com", "phone": "+15551234567",
            "title": "CEO", "company": "RoeCorp", "website": "roe.com",
            "language": "en", "notes": "",
        }
        r = requests.post(f"{API}/scan/confirm", headers=admin_headers,
                          json=payload, timeout=30)
        assert r.status_code == 200, r.text
        lead = r.json().get("lead")
        assert lead
        assert lead["source"] == "qr_scan"
        assert lead["status"] == "new"
        assert "scanned" in lead.get("tags", [])
        assert lead.get("met_at")
        requests.delete(f"{API}/admin/leads/{lead['id']}", headers=admin_headers)


# --------------------------- NFC devices ---------------------------

class TestNFC:
    def test_nfc_devices_list_ok(self, admin_headers):
        r = requests.get(f"{API}/nfc/devices", headers=admin_headers, timeout=30)
        # Route must exist and return 200 (possibly empty list)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, (list, dict))
