"""P1 tests: extended analytics overview breakdowns + branded QR (must still decode)."""
import io
import os
import pytest
import requests
from PIL import Image
from pyzbar.pyzbar import decode as qr_decode

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
ADMIN_EMAIL = "admin@ariadni.id"
ADMIN_PASSWORD = "Ariadni@2026"
DEMO_SLUG = "feras-askar"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# ---------- Analytics overview (extended) ----------

def test_analytics_overview_top_level_keys(auth_headers):
    r = requests.get(f"{BASE_URL}/api/admin/analytics/overview?days=30",
                     headers=auth_headers, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    # existing keys (no regression)
    for k in ("funnel", "series", "top_actions"):
        assert k in data, f"missing existing key {k}"
    # new keys
    assert "channels" in data
    assert "breakdowns" in data


def test_analytics_funnel_shape(auth_headers):
    data = requests.get(f"{BASE_URL}/api/admin/analytics/overview?days=30",
                        headers=auth_headers, timeout=30).json()
    funnel = data["funnel"]
    # existing stages must exist
    for stage in ("views", "engaged", "leads", "meetings_booked", "meetings_completed"):
        assert stage in funnel, f"missing funnel stage {stage}"
        assert isinstance(funnel[stage], int)


def test_analytics_channels_shape(auth_headers):
    data = requests.get(f"{BASE_URL}/api/admin/analytics/overview?days=30",
                        headers=auth_headers, timeout=30).json()
    ch = data["channels"]
    for k in ("direct", "qr", "nfc"):
        assert k in ch, f"missing channel {k}"
        assert isinstance(ch[k], int)


def test_analytics_breakdowns_shape(auth_headers):
    data = requests.get(f"{BASE_URL}/api/admin/analytics/overview?days=30",
                        headers=auth_headers, timeout=30).json()
    bd = data["breakdowns"]
    for k in ("by_card", "by_source", "scanner_leads", "by_event", "by_campaign", "by_member"):
        assert k in bd, f"missing breakdown key {k}"
    assert isinstance(bd["by_card"], list)
    # by_card rows should have card slug + counts
    if bd["by_card"]:
        row = bd["by_card"][0]
        # accept any of typical field names
        assert any(k in row for k in ("slug", "card_slug", "card"))


def test_analytics_series_and_top_actions(auth_headers):
    data = requests.get(f"{BASE_URL}/api/admin/analytics/overview?days=30",
                        headers=auth_headers, timeout=30).json()
    assert isinstance(data["series"], (list, dict))
    assert isinstance(data["top_actions"], list)


# ---------- Branded QR ----------

def test_branded_qr_is_png_and_decodes(auth_headers):
    r = requests.get(f"{BASE_URL}/api/cards/{DEMO_SLUG}/qr", timeout=30)
    assert r.status_code == 200
    ct = r.headers.get("content-type", "")
    assert "png" in ct.lower(), f"unexpected content-type {ct}"
    img = Image.open(io.BytesIO(r.content))
    assert img.format == "PNG"
    decoded = qr_decode(img)
    assert decoded, "QR did not decode"
    payload = decoded[0].data.decode("utf-8", errors="ignore")
    assert DEMO_SLUG in payload, f"decoded payload missing slug: {payload}"
    assert "src=qr" in payload, f"decoded payload missing src=qr tracking: {payload}"


def test_poster_endpoint_still_png():
    r = requests.get(f"{BASE_URL}/api/cards/{DEMO_SLUG}/poster", timeout=45)
    assert r.status_code == 200, r.text
    ct = r.headers.get("content-type", "")
    assert "png" in ct.lower(), f"poster content-type {ct}"
    img = Image.open(io.BytesIO(r.content))
    assert img.format == "PNG"


# ---------- Public card regression ----------

def test_public_card_endpoint_ok():
    r = requests.get(f"{BASE_URL}/api/cards/{DEMO_SLUG}", timeout=30)
    assert r.status_code == 200
    body = r.json()
    assert body.get("slug") == DEMO_SLUG


def test_leads_list_still_works(auth_headers):
    r = requests.get(f"{BASE_URL}/api/admin/leads?limit=5",
                     headers=auth_headers, timeout=30)
    assert r.status_code == 200
    body = r.json()
    # accept either list or {items:[]} envelope
    assert isinstance(body, (list, dict))
