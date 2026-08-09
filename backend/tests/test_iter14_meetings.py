"""
Iteration 14 — Native ARIADNI Meetings/Calendar backend tests.

Covers:
- Public booking config
- Public slots endpoint (weekday, UTC iso)
- Public book -> creates meeting + CRM lead (source=meeting_booking) + timeline
- Slot removal after booking
- Double-booking prevention (409)
- Guest manage: GET / reschedule / cancel
- Admin meetings list (all filters) -> 200 (regression: list+tuple TypeError fix)
- Admin meeting status -> completed -> CRM timeline meeting_completed
- Owner settings: meeting-types CRUD + availability PUT
- External-only card (nativeEnabled=false) surfaces external_url
"""
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL missing"

ADMIN_EMAIL = "admin@ariadni.id"
ADMIN_PW = "Ariadni@2026"
FERAS_SLUG = "feras-askar"


# ---------------- fixtures ----------------

@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def admin_token(api):
    r = api.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PW})
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin(api, admin_token):
    api.headers.update({"Authorization": f"Bearer {admin_token}"})
    return api


@pytest.fixture(scope="module")
def feras_card_id(admin):
    r = admin.get(f"{BASE_URL}/api/admin/cards")
    assert r.status_code == 200
    for c in r.json():
        if c["slug"] == FERAS_SLUG:
            return c["id"]
    pytest.fail("feras-askar card not found")


def _next_weekday_dubai():
    """Return YYYY-MM-DD ~5 days ahead, guaranteed weekday & > min_notice."""
    d = datetime.now(timezone.utc) + timedelta(days=5)
    while d.isoweekday() > 5:
        d += timedelta(days=1)
    return d.strftime("%Y-%m-%d")


# ---------------- created-during-test tracking (for cleanup) ----------------
_created_meeting_ids = []
_created_lead_ids = []


# ---------------- 1) Booking config ----------------

def test_public_booking_config(api):
    r = api.get(f"{BASE_URL}/api/cards/{FERAS_SLUG}/booking")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["native_enabled"] is True
    assert data["owner_timezone"] == "Asia/Dubai"
    assert isinstance(data["meeting_types"], list)
    assert len(data["meeting_types"]) >= 3
    durations = sorted(mt["duration"] for mt in data["meeting_types"])
    assert 15 in durations and 30 in durations and 45 in durations


# ---------------- 2) Slots endpoint ----------------

def test_public_slots_weekday(api):
    cfg = api.get(f"{BASE_URL}/api/cards/{FERAS_SLUG}/booking").json()
    mt = next(m for m in cfg["meeting_types"] if m["duration"] == 30)
    date = _next_weekday_dubai()
    r = api.get(f"{BASE_URL}/api/cards/{FERAS_SLUG}/slots",
                params={"meeting_type_id": mt["id"], "date": date})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["owner_timezone"] == "Asia/Dubai"
    assert j["duration"] == 30
    assert isinstance(j["slots"], list) and len(j["slots"]) > 0
    # UTC ISO
    assert all(s.endswith("+00:00") or s.endswith("Z") for s in j["slots"])


# ---------------- 3) Book -> creates meeting + lead ----------------

def test_public_book_creates_meeting_and_lead(api, admin):
    cfg = api.get(f"{BASE_URL}/api/cards/{FERAS_SLUG}/booking").json()
    mt = next(m for m in cfg["meeting_types"] if m["duration"] == 30)
    date = _next_weekday_dubai()
    slots = api.get(f"{BASE_URL}/api/cards/{FERAS_SLUG}/slots",
                    params={"meeting_type_id": mt["id"], "date": date}).json()["slots"]
    assert slots, "no slots"
    start = slots[0]

    email = f"TEST_book_{uuid.uuid4().hex[:6]}@example.com"
    r = requests.post(f"{BASE_URL}/api/cards/{FERAS_SLUG}/book", json={
        "meeting_type_id": mt["id"], "start": start, "name": "TEST Booker",
        "email": email, "phone": "", "note": "TEST note", "visitor_tz": "Asia/Dubai",
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] and body["manage_token"]
    meeting = body["meeting"]
    assert meeting["status"] == "scheduled"
    assert meeting["duration"] == 30
    assert meeting["visitor_email"].lower() == email.lower()
    _created_meeting_ids.append(meeting["id"])

    # Booking creates a CRM lead
    r2 = admin.get(f"{BASE_URL}/api/admin/leads", params={"slug": FERAS_SLUG})
    assert r2.status_code == 200
    leads = r2.json()
    match = [l for l in leads if l.get("email", "").lower() == email.lower()]
    assert match, f"no CRM lead found for {email}"
    lead = match[0]
    assert lead["source"] == "meeting_booking"
    # Timeline should have meeting_booked
    events = [e.get("event") for e in (lead.get("timeline") or [])]
    assert "meeting_booked" in events
    _created_lead_ids.append(lead["id"])

    # stash for downstream tests
    pytest.shared_booking = {
        "manage_token": body["manage_token"],
        "meeting_id": meeting["id"],
        "lead_id": lead["id"],
        "meeting_type_id": mt["id"],
        "date": date,
        "start": start,
    }


# ---------------- 4) Slot removed after booking ----------------

def test_slot_removed_after_booking(api):
    ctx = pytest.shared_booking
    slots = api.get(f"{BASE_URL}/api/cards/{FERAS_SLUG}/slots",
                    params={"meeting_type_id": ctx["meeting_type_id"], "date": ctx["date"]}).json()["slots"]
    assert ctx["start"] not in slots


# ---------------- 5) Double-book -> 409 ----------------

def test_double_book_returns_409(api):
    ctx = pytest.shared_booking
    r = requests.post(f"{BASE_URL}/api/cards/{FERAS_SLUG}/book", json={
        "meeting_type_id": ctx["meeting_type_id"], "start": ctx["start"], "name": "TEST Dup",
        "email": f"TEST_dup_{uuid.uuid4().hex[:6]}@example.com", "phone": "", "visitor_tz": "UTC",
    })
    assert r.status_code == 409, r.text


# ---------------- 6) Manage GET ----------------

def test_manage_get(api):
    tok = pytest.shared_booking["manage_token"]
    r = requests.get(f"{BASE_URL}/api/meetings/manage/{tok}")
    assert r.status_code == 200
    m = r.json()
    assert m["id"] == pytest.shared_booking["meeting_id"]


# ---------------- 7) Reschedule ----------------

def test_manage_reschedule(api):
    ctx = pytest.shared_booking
    # get another slot on same day
    slots = api.get(f"{BASE_URL}/api/cards/{FERAS_SLUG}/slots",
                    params={"meeting_type_id": ctx["meeting_type_id"], "date": ctx["date"]}).json()["slots"]
    new_start = slots[0]
    assert new_start != ctx["start"]
    r = requests.post(f"{BASE_URL}/api/meetings/manage/{ctx['manage_token']}/reschedule",
                      json={"start": new_start})
    assert r.status_code == 200, r.text
    # verify
    m = requests.get(f"{BASE_URL}/api/meetings/manage/{ctx['manage_token']}").json()
    assert m["start_utc"] == new_start
    assert m["status"] == "rescheduled"
    ctx["start"] = new_start


# ---------------- 8) Admin meetings — all filters, includes rescheduled ----------------

def test_admin_meetings_all_filters(admin):
    for f in ["today", "upcoming", "past", "cancelled"]:
        r = admin.get(f"{BASE_URL}/api/admin/meetings", params={"filter": f})
        assert r.status_code == 200, f"{f}: {r.text}"
        assert isinstance(r.json(), list)
    # upcoming should include the meeting we booked (status=rescheduled)
    up = admin.get(f"{BASE_URL}/api/admin/meetings", params={"filter": "upcoming"}).json()
    mids = [m["id"] for m in up]
    assert pytest.shared_booking["meeting_id"] in mids


# ---------------- 9) Status -> completed writes timeline ----------------

def test_admin_meeting_status_completed(admin):
    mid = pytest.shared_booking["meeting_id"]
    r = admin.patch(f"{BASE_URL}/api/admin/meetings/{mid}/status", json={"status": "completed"})
    assert r.status_code == 200, r.text
    # lead timeline should have meeting_completed
    leads = admin.get(f"{BASE_URL}/api/admin/leads", params={"slug": FERAS_SLUG}).json()
    lead = next(l for l in leads if l["id"] == pytest.shared_booking["lead_id"])
    events = [e.get("event") for e in (lead.get("timeline") or [])]
    assert "meeting_completed" in events


# ---------------- 10) Cancel ----------------

def test_manage_cancel(api):
    # Book a fresh meeting to cancel
    cfg = api.get(f"{BASE_URL}/api/cards/{FERAS_SLUG}/booking").json()
    mt = next(m for m in cfg["meeting_types"] if m["duration"] == 15)
    date = _next_weekday_dubai()
    slots = api.get(f"{BASE_URL}/api/cards/{FERAS_SLUG}/slots",
                    params={"meeting_type_id": mt["id"], "date": date}).json()["slots"]
    email = f"TEST_cancel_{uuid.uuid4().hex[:6]}@example.com"
    b = requests.post(f"{BASE_URL}/api/cards/{FERAS_SLUG}/book", json={
        "meeting_type_id": mt["id"], "start": slots[-1], "name": "TEST Cancel",
        "email": email, "phone": "", "visitor_tz": "UTC",
    }).json()
    _created_meeting_ids.append(b["meeting"]["id"])
    r = requests.post(f"{BASE_URL}/api/meetings/manage/{b['manage_token']}/cancel")
    assert r.status_code == 200
    m = requests.get(f"{BASE_URL}/api/meetings/manage/{b['manage_token']}").json()
    assert m["status"] == "cancelled"

    # capture lead for cleanup
    leads = requests.get(f"{BASE_URL}/api/admin/leads",
                         params={"slug": FERAS_SLUG},
                         headers={"Authorization": api.headers["Authorization"]}).json()
    for l in leads:
        if l.get("email", "").lower() == email.lower():
            _created_lead_ids.append(l["id"])


# ---------------- 11) Owner settings: meeting-types + availability ----------------

def test_admin_meeting_types_crud(admin, feras_card_id):
    # Create
    r = admin.post(f"{BASE_URL}/api/admin/cards/{feras_card_id}/meeting-types", json={
        "title": "TEST_60min", "description": "TEST", "duration": 60,
        "location_type": "video", "location_detail": "", "enabled": True, "order": 99,
    })
    assert r.status_code == 200, r.text
    mt_id = r.json()["id"]
    # Update
    r = admin.put(f"{BASE_URL}/api/admin/cards/{feras_card_id}/meeting-types/{mt_id}", json={
        "title": "TEST_60min_v2", "description": "", "duration": 60,
        "location_type": "video", "location_detail": "", "enabled": True, "order": 99,
    })
    assert r.status_code == 200
    assert r.json()["title"] == "TEST_60min_v2"
    # Delete
    r = admin.delete(f"{BASE_URL}/api/admin/cards/{feras_card_id}/meeting-types/{mt_id}")
    assert r.status_code == 200


def test_admin_availability_put(admin, feras_card_id):
    # GET original
    orig = admin.get(f"{BASE_URL}/api/admin/cards/{feras_card_id}/availability").json()
    # PUT same values back (round-trip test)
    payload = {k: orig[k] for k in ["days", "start", "end", "buffer_before", "buffer_after",
                                     "min_notice_hours", "max_days", "slot_interval", "blocked"]}
    r = admin.put(f"{BASE_URL}/api/admin/cards/{feras_card_id}/availability", json=payload)
    assert r.status_code == 200, r.text
    assert r.json()["days"] == payload["days"]


# ---------------- 12) External-only card regression ----------------

def test_external_only_card_shows_external_url(admin):
    # Create a card with nativeEnabled=false + bookingUrl
    payload = {
        "slug": f"TEST-ext-{uuid.uuid4().hex[:6]}",
        "template_id": "executive_black_gold",
        "identity": {"fullName": "TEST Ext", "role": ""},
        "booking": {"nativeEnabled": False, "bookingUrl": "https://cal.com/test-ext",
                    "timezone": "Asia/Dubai"},
        "status": "published",
    }
    c = admin.post(f"{BASE_URL}/api/admin/cards", json=payload)
    assert c.status_code in (200, 201), c.text
    card = c.json()
    try:
        b = requests.get(f"{BASE_URL}/api/cards/{card['slug']}/booking").json()
        assert b["native_enabled"] is False
        assert b["external_url"] == "https://cal.com/test-ext"
        assert b["meeting_types"] == []
    finally:
        admin.delete(f"{BASE_URL}/api/admin/cards/{card['id']}")


# ---------------- 99) Cleanup ----------------

def test_cleanup(admin):
    # cancel any surviving test meetings (soft-delete via cancel + lead removal)
    for lid in _created_lead_ids:
        r = admin.delete(f"{BASE_URL}/api/admin/leads/{lid}")
        # 200/204/404 all OK
        assert r.status_code in (200, 204, 404)
    # Directly remove meeting docs via a management admin? No endpoint. They stay cancelled.
    # Ensure feras-askar itself is untouched.
    r = admin.get(f"{BASE_URL}/api/admin/cards")
    assert any(c["slug"] == FERAS_SLUG for c in r.json())
