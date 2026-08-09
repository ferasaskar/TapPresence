"""Iteration 13 - duplicate, publish success, edit regression, identity crop persistence."""
import os
import requests
import pytest

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://template-hub-184.preview.emergentagent.com").rstrip("/")


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE}/api/auth/login", json={"email": "admin@ariadni.id", "password": "Ariadni@2026"})
    assert r.status_code == 200
    return r.json()["token"]


@pytest.fixture(scope="module")
def hdr(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


created_ids = []


def _mk_card(hdr, slug):
    payload = {
        "slug": slug,
        "templateId": "executive-black-gold",
        "accent": "gold",
        "industry": "sales",
        "identity": {"fullName": "QA Dup", "title": "Tester", "company": "QA Inc",
                     "profilePhoto": "", "imageScale": 1, "imageOffsetX": 0, "imageOffsetY": 0},
        "contact": {"phone": "", "email": "", "whatsapp": "", "website": "", "linkedin": "", "address": ""},
        "status": "published",
    }
    r = requests.post(f"{BASE}/api/admin/cards", json=payload, headers=hdr)
    assert r.status_code == 200, r.text
    c = r.json()
    created_ids.append(c["id"])
    return c


def test_duplicate_creates_draft_copy(hdr):
    orig = _mk_card(hdr, f"qa-iter13-orig-{os.urandom(3).hex()}")
    r = requests.post(f"{BASE}/api/admin/cards/{orig['id']}/duplicate", headers=hdr)
    assert r.status_code == 200, r.text
    copy = r.json()
    created_ids.append(copy["id"])
    assert copy["id"] != orig["id"]
    assert copy["slug"].startswith(orig["slug"] + "-copy-")
    assert copy["status"] == "draft"
    assert copy.get("identity", {}).get("fullName") == "QA Dup"
    # Verify original unchanged
    r2 = requests.get(f"{BASE}/api/admin/cards/{orig['id']}", headers=hdr)
    assert r2.status_code == 200
    assert r2.json()["status"] == "published"
    assert r2.json()["slug"] == orig["slug"]


def test_duplicate_of_copy_gets_unique_slug(hdr):
    orig = _mk_card(hdr, f"qa-iter13-dbl-{os.urandom(3).hex()}")
    r1 = requests.post(f"{BASE}/api/admin/cards/{orig['id']}/duplicate", headers=hdr)
    assert r1.status_code == 200
    c1 = r1.json(); created_ids.append(c1["id"])
    r2 = requests.post(f"{BASE}/api/admin/cards/{c1['id']}/duplicate", headers=hdr)
    assert r2.status_code == 200
    c2 = r2.json(); created_ids.append(c2["id"])
    # base should be stripped so it's not "-copy-xxx-copy-yyy"
    assert c2["slug"] != c1["slug"]
    # Should be re-based on original slug
    assert c2["slug"].startswith(orig["slug"] + "-copy-")


def test_update_card_still_works(hdr):
    """CRITICAL: verify update_card endpoint (PUT /admin/cards/{id}) still registered."""
    c = _mk_card(hdr, f"qa-iter13-upd-{os.urandom(3).hex()}")
    payload = {**c, "identity": {**c["identity"], "fullName": "QA Updated"}}
    # Remove server-added fields not in CardUpsert
    for k in ("id", "created_at", "updated_at", "workspace_id", "owner_user_id"):
        payload.pop(k, None)
    r = requests.put(f"{BASE}/api/admin/cards/{c['id']}", json=payload, headers=hdr)
    assert r.status_code == 200, f"PUT failed status={r.status_code} body={r.text[:200]}"
    assert r.json()["identity"]["fullName"] == "QA Updated"


def test_identity_crop_persists(hdr):
    slug = f"qa-iter13-crop-{os.urandom(3).hex()}"
    payload = {
        "slug": slug, "templateId": "executive-black-gold", "accent": "gold", "industry": "sales",
        "identity": {"fullName": "Crop QA", "title": "T", "company": "C",
                     "profilePhoto": "https://picsum.photos/400", "imageScale": 1.15,
                     "imageOffsetX": 3, "imageOffsetY": 6},
        "contact": {"phone": "", "email": "", "whatsapp": "", "website": "", "linkedin": "", "address": ""},
        "status": "published",
    }
    r = requests.post(f"{BASE}/api/admin/cards", json=payload, headers=hdr)
    assert r.status_code == 200
    created_ids.append(r.json()["id"])
    # public GET
    r2 = requests.get(f"{BASE}/api/cards/{slug}")
    assert r2.status_code == 200
    ident = r2.json()["identity"]
    assert ident["imageScale"] == 1.15
    assert ident["imageOffsetX"] == 3
    assert ident["imageOffsetY"] == 6


def test_qr_endpoint(hdr):
    r = requests.get(f"{BASE}/api/cards/feras-askar/qr")
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("image/")


def test_cleanup(hdr):
    for cid in created_ids:
        requests.delete(f"{BASE}/api/admin/cards/{cid}", headers=hdr)
