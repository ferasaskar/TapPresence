"""Phase 8 — Industry Template Personalization backend tests."""
import os
import pytest
import requests

def _load_base():
    url = os.environ.get("REACT_APP_BACKEND_URL", "").strip()
    if not url:
        try:
            with open("/app/frontend/.env") as f:
                for line in f:
                    if line.startswith("REACT_APP_BACKEND_URL="):
                        url = line.split("=", 1)[1].strip()
                        break
        except Exception:
            pass
    return url.rstrip("/")

BASE_URL = _load_base()
ADMIN_EMAIL = "admin@ariadni.id"
ADMIN_PASS = "Ariadni@2026"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=15)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


# --------- GET /api/industries returns 12 with required fields ---------
def test_industries_catalog():
    r = requests.get(f"{BASE_URL}/api/industries", timeout=15)
    assert r.status_code == 200
    data = r.json()
    inds = data.get("industries", [])
    ids = [i["id"] for i in inds]
    expected = ["real_estate", "business", "sales", "technology", "healthcare",
                "legal", "education", "hospitality", "automotive", "beauty",
                "finance", "custom"]
    for e in expected:
        assert e in ids, f"missing industry {e}"
    assert len(inds) == 12
    for ind in inds:
        for k in ("id", "name", "icon", "styles", "default_opacity", "recommended_accent"):
            assert k in ind, f"industry {ind.get('id')} missing key {k}"
        # 'image' key must exist (may be empty for custom)
        assert "image" in ind


# --------- Card persistence: industry + skin + accent + bg controls ---------
def _get_card_by_slug(admin_headers, slug):
    r = requests.get(f"{BASE_URL}/api/admin/cards", headers=admin_headers, timeout=15)
    assert r.status_code == 200
    cards = r.json()
    for c in cards:
        if c.get("slug") == slug:
            return c
    return None


def test_feras_askar_industry_persistence(admin_headers):
    card = _get_card_by_slug(admin_headers, "feras-askar")
    assert card is not None, "feras-askar card must exist"
    cid = card["id"]
    # Prepare PUT payload with technology/neural/blue
    payload = dict(card)
    payload.pop("_id", None)
    payload["industry"] = "technology"
    payload["background_style"] = "neural"
    payload["accent"] = "blue"
    payload["custom_accent_color"] = ""
    payload["background_opacity"] = 0.15
    payload["background_intensity"] = "medium"
    payload["background_position"] = "center"

    r = requests.put(f"{BASE_URL}/api/admin/cards/{cid}",
                     headers=admin_headers, json=payload, timeout=15)
    assert r.status_code == 200, f"PUT failed: {r.status_code} {r.text}"
    updated = r.json()
    assert updated["industry"] == "technology"
    assert updated["background_style"] == "neural"
    assert updated["accent"] == "blue"
    assert abs(updated["background_opacity"] - 0.15) < 1e-6
    assert updated["background_intensity"] == "medium"
    assert updated["background_position"] == "center"

    # Public GET must reflect
    r2 = requests.get(f"{BASE_URL}/api/cards/feras-askar", timeout=15)
    assert r2.status_code == 200
    pub = r2.json()
    assert pub["industry"] == "technology"
    assert pub["background_style"] == "neural"
    assert pub["accent"] == "blue"
    assert pub["background_position"] == "center"


def test_feras_askar_custom_accent_hex(admin_headers):
    card = _get_card_by_slug(admin_headers, "feras-askar")
    assert card is not None
    cid = card["id"]
    payload = dict(card)
    payload.pop("_id", None)
    payload["industry"] = "technology"
    payload["background_style"] = "neural"
    payload["accent"] = "custom"
    payload["custom_accent_color"] = "#22d3ee"
    payload["background_opacity"] = 0.15
    payload["background_intensity"] = "medium"
    payload["background_position"] = "center"

    r = requests.put(f"{BASE_URL}/api/admin/cards/{cid}",
                     headers=admin_headers, json=payload, timeout=15)
    assert r.status_code == 200, r.text
    up = r.json()
    assert up["accent"] == "custom"
    assert up["custom_accent_color"].lower() == "#22d3ee"

    r2 = requests.get(f"{BASE_URL}/api/cards/feras-askar", timeout=15)
    pub = r2.json()
    assert pub["accent"] == "custom"
    assert pub["custom_accent_color"].lower() == "#22d3ee"


# --------- Regression: card without industry unchanged ---------
def test_card_without_industry_regression(admin_headers):
    # Try a couple of candidate slugs; skip if none exist
    r = requests.get(f"{BASE_URL}/api/admin/cards", headers=admin_headers, timeout=15)
    assert r.status_code == 200
    cards = r.json()
    # Find a card that has no industry set
    plain = next((c for c in cards if not c.get("industry")), None)
    if not plain:
        pytest.skip("No card without industry available to regression-test")
    slug = plain["slug"]
    r2 = requests.get(f"{BASE_URL}/api/cards/{slug}", timeout=15)
    assert r2.status_code == 200
    pub = r2.json()
    assert not pub.get("industry"), f"Expected no industry, got {pub.get('industry')}"
    # background_style should be empty/absent
    assert not pub.get("background_style")


# --------- Locked branding code path (best-effort). ---------
def test_locked_branding_member_cannot_change(admin_headers):
    """Simulate a workspace with locked_fields=['industry','accent','background'] and a
    MEMBER user in that workspace attempting to update a card. Verifies the code path
    in update_card actually reverts the locked values.
    """
    import uuid as _uuid
    # Register a fresh member user via /auth/register
    mem_email = f"lockmember-{_uuid.uuid4().hex[:8]}@example.com"
    mem_pass = "Test@1234"
    r = requests.post(f"{BASE_URL}/api/auth/register",
                      json={"email": mem_email, "password": mem_pass, "name": "Lock Member"},
                      timeout=15)
    assert r.status_code == 200, r.text
    mem_token = r.json()["token"]
    mem_ws = r.json()["workspace"]["id"]
    mem_headers = {"Authorization": f"Bearer {mem_token}", "Content-Type": "application/json"}

    # Admin: set workspace locked_fields (SUPER_ADMIN can call PUT /workspaces/{wid}/branding? require_ws_admin returns SUPER_ADMIN)
    r = requests.put(f"{BASE_URL}/api/workspaces/{mem_ws}/branding",
                     headers=admin_headers,
                     json={"branding": {}, "locked_fields": ["industry", "accent", "background"]},
                     timeout=15)
    assert r.status_code == 200, r.text

    # Demote user to MEMBER role in this workspace
    # Find user id via memberships
    r = requests.get(f"{BASE_URL}/api/workspaces/{mem_ws}/members",
                     headers=admin_headers, timeout=15)
    assert r.status_code == 200
    members = r.json()
    uid = members[0]["user_id"]
    r = requests.patch(f"{BASE_URL}/api/workspaces/{mem_ws}/members/{uid}",
                       headers=admin_headers, json={"role": "MEMBER"}, timeout=15)
    assert r.status_code == 200, r.text

    # Member creates a card in their workspace
    slug = f"lock-{_uuid.uuid4().hex[:6]}"
    create_body = {
        "slug": slug,
        "templateId": "beige-luxury",
        "accent": "gold",
        "industry": "",
        "background_style": "",
        "status": "draft",
        "identity": {"fullName": "Lock Test"},
        "contact": {"email": mem_email},
        "social": {}, "actions": [], "services": [], "projects": [], "booking": {},
    }
    r = requests.post(f"{BASE_URL}/api/admin/cards", headers=mem_headers,
                      json=create_body, timeout=15)
    assert r.status_code == 200, r.text
    card = r.json()
    cid = card["id"]

    # Member attempts to change locked fields
    put_body = dict(card)
    put_body.pop("_id", None)
    put_body["industry"] = "technology"
    put_body["accent"] = "blue"
    put_body["background_style"] = "neural"
    put_body["background_opacity"] = 0.25
    put_body["background_intensity"] = "rich"

    r = requests.put(f"{BASE_URL}/api/admin/cards/{cid}",
                     headers=mem_headers, json=put_body, timeout=15)
    assert r.status_code == 200, r.text
    updated = r.json()
    # Locked reverted values
    assert updated["industry"] == "", f"industry should be locked but got {updated['industry']}"
    assert updated["accent"] == "gold", f"accent should be locked but got {updated['accent']}"
    assert updated["background_style"] == "", f"background_style should be locked but got {updated['background_style']}"

    # cleanup: delete card
    requests.delete(f"{BASE_URL}/api/admin/cards/{cid}", headers=mem_headers, timeout=10)
