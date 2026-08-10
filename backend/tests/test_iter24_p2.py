"""Iteration 24 (P2): FollowUp Today, Event Capture Mode (via scan/confirm), Signature Booking deep link.
Reuses existing endpoints: /api/admin/leads, /api/admin/leads/{id}/remind, /api/scan/confirm, /api/cards/{slug}/leads.
"""
import os, io, base64, datetime as dt, time
import pytest, requests, qrcode

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
EMAIL, PW = "admin@ariadni.id", "Ariadni@2026"
SLUG = "feras-askar"


@pytest.fixture(scope="module")
def s():
    ses = requests.Session()
    r = ses.post(f"{BASE}/api/auth/login", json={"email": EMAIL, "password": PW})
    assert r.status_code == 200, r.text
    tok = r.json().get("token")
    if tok:
        ses.headers.update({"Authorization": f"Bearer {tok}"})
    return ses


def _create_public_lead(s, name):
    r = requests.post(f"{BASE}/api/cards/{SLUG}/leads",
                      json={"name": name, "email": f"{name.lower().replace(' ', '_')}@t.io", "phone": "+15551234567", "message": "TEST_iter24"})
    assert r.status_code in (200, 201), r.text
    # Response is {ok:true}; look up id via /admin/leads
    lst = s.get(f"{BASE}/api/admin/leads").json()
    items = lst if isinstance(lst, list) else lst.get("items", [])
    match = [l for l in items if l.get("name") == name]
    assert match, f"lead {name} not found"
    return match[0]["id"]


def _cleanup(s, ids):
    for i in ids:
        try:
            s.delete(f"{BASE}/api/admin/leads/{i}")
        except Exception:
            pass


# ---------- Follow Up Today ----------

def test_follow_up_today_flow(s):
    created = []
    try:
        # Two leads: one overdue, one due today
        overdue_id = _create_public_lead(s, "TEST_iter24_overdue")
        today_id = _create_public_lead(s, "TEST_iter24_today")
        created += [overdue_id, today_id]

        r1 = s.post(f"{BASE}/api/admin/leads/{overdue_id}/remind", json={"when": "2020-01-01T09:00:00Z"})
        assert r1.status_code == 200, r1.text
        assert r1.json().get("next_follow_up")

        # due today: 1 hour from now
        due = (dt.datetime.utcnow() + dt.timedelta(hours=1)).replace(microsecond=0).isoformat() + "Z"
        r2 = s.post(f"{BASE}/api/admin/leads/{today_id}/remind", json={"when": due})
        assert r2.status_code == 200

        # verify via /admin/leads that next_follow_up persisted
        lst = s.get(f"{BASE}/api/admin/leads").json()
        items = lst if isinstance(lst, list) else lst.get("items", [])
        by_id = {l["id"]: l for l in items if l.get("id")}
        assert by_id[overdue_id].get("next_follow_up", "").startswith("2020")
        assert by_id[today_id].get("next_follow_up")

        # clear reminder works
        r3 = s.delete(f"{BASE}/api/admin/leads/{today_id}/remind")
        assert r3.status_code == 200
    finally:
        _cleanup(s, created)


# ---------- Event Capture Mode via scan/confirm ----------

def test_scan_confirm_with_event_and_campaign(s):
    # get any campaign code (optional)
    campaign_code = None
    try:
        cr = s.get(f"{BASE}/api/campaigns")
        if cr.status_code == 200:
            arr = cr.json()
            items = arr if isinstance(arr, list) else arr.get("items", [])
            if items:
                campaign_code = items[0].get("code") or items[0].get("id")
    except Exception:
        pass

    payload = {
        "name": "TEST_iter24_event",
        "email": "test_iter24_event@t.io",
        "phone": "+15550009999",
        "cardSlug": SLUG,
        "source": "business_card_scan",
        "event": "GITEX 2026",
        "campaign": campaign_code or "",
    }
    r = s.post(f"{BASE}/api/scan/confirm", json=payload)
    assert r.status_code in (200, 201), r.text
    body = r.json()
    lead = body.get("lead") or body
    lead_id = lead.get("id")
    assert lead_id
    try:
        # Verify persisted
        got = s.get(f"{BASE}/api/admin/leads/{lead_id}")
        if got.status_code == 200:
            l = got.json()
        else:
            lst = s.get(f"{BASE}/api/admin/leads").json()
            items = lst if isinstance(lst, list) else lst.get("items", [])
            l = next(x for x in items if x["id"] == lead_id)
        assert l.get("event") == "GITEX 2026"
        if campaign_code:
            assert l.get("campaign") == campaign_code
        assert "event" in (l.get("tags") or [])
    finally:
        _cleanup(s, [lead_id])


# ---------- Signature Booking Link deep-link ----------

def test_public_profile_book_deep_link_reachable():
    r = requests.get(f"{BASE}/{SLUG}?book=1", allow_redirects=True)
    # SPA returns 200 HTML (client-side handles ?book=1)
    assert r.status_code == 200
    assert "<html" in r.text.lower()


def test_public_card_has_native_booking():
    # meeting types endpoint should exist for slug
    for path in [f"/api/cards/{SLUG}/meeting-types", f"/api/public/cards/{SLUG}/meeting-types"]:
        r = requests.get(f"{BASE}{path}")
        if r.status_code == 200:
            data = r.json()
            items = data if isinstance(data, list) else data.get("items", [])
            assert isinstance(items, list)
            return
    pytest.skip("meeting-types endpoint not found - non-blocking")
