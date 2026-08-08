"""Backend API tests for ARIADNI ID."""
import os
import io
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://template-hub-184.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@ariadni.id"
ADMIN_PASSWORD = "Ariadni@2026"
DEMO_SLUG = "feras-askar"


@pytest.fixture(scope="session")
def admin_token():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    data = r.json()
    assert "token" in data and "user" in data
    return data["token"]


@pytest.fixture
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# -------------------- Public card --------------------
class TestPublicCard:
    def test_get_demo_card(self):
        r = requests.get(f"{API}/cards/{DEMO_SLUG}", timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert data["slug"] == DEMO_SLUG
        for key in ("identity", "contact", "social", "services", "projects", "booking"):
            assert key in data, f"missing key: {key}"

    def test_get_nonexistent_card(self):
        r = requests.get(f"{API}/cards/nonexistent-{uuid.uuid4().hex[:6]}", timeout=30)
        assert r.status_code == 404

    def test_vcard(self):
        r = requests.get(f"{API}/cards/{DEMO_SLUG}/vcard", timeout=30)
        assert r.status_code == 200
        assert "text/vcard" in r.headers.get("content-type", "")
        body = r.text
        assert body.startswith("BEGIN:VCARD")
        assert "END:VCARD" in body
        assert "FN:" in body

    def test_qr(self):
        r = requests.get(f"{API}/cards/{DEMO_SLUG}/qr", timeout=30)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("image/png")
        assert r.content[:8] == b"\x89PNG\r\n\x1a\n"


# -------------------- Auth --------------------
class TestAuth:
    def test_login_success(self, admin_token):
        assert isinstance(admin_token, str) and len(admin_token) > 20

    def test_login_wrong_password(self):
        r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": "wrongpass"}, timeout=30)
        assert r.status_code == 401

    def test_me_with_token(self, auth_headers):
        r = requests.get(f"{API}/auth/me", headers=auth_headers, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["email"] == ADMIN_EMAIL

    def test_me_without_token(self):
        r = requests.get(f"{API}/auth/me", timeout=30)
        assert r.status_code == 401


# -------------------- Admin CRUD --------------------
class TestAdminCards:
    def test_admin_endpoints_require_auth(self):
        assert requests.get(f"{API}/admin/cards", timeout=30).status_code == 401
        assert requests.post(f"{API}/admin/cards", json={"slug": "x"}, timeout=30).status_code == 401

    def test_list_cards(self, auth_headers):
        r = requests.get(f"{API}/admin/cards", headers=auth_headers, timeout=30)
        assert r.status_code == 200
        cards = r.json()
        assert isinstance(cards, list)
        assert any(c.get("slug") == DEMO_SLUG for c in cards)

    def test_duplicate_slug_rejected(self, auth_headers):
        r = requests.post(f"{API}/admin/cards", headers=auth_headers,
                          json={"slug": DEMO_SLUG}, timeout=30)
        assert r.status_code == 400

    def test_full_crud(self, auth_headers):
        slug = f"test-{uuid.uuid4().hex[:8]}"
        payload = {
            "slug": slug, "templateId": "beige-luxury", "status": "draft",
            "identity": {"fullName": "Test User", "jobTitle": "QA", "company": "TestCo"},
            "contact": {"email": "t@t.com", "phone": "+100"},
        }
        # CREATE
        r = requests.post(f"{API}/admin/cards", headers=auth_headers, json=payload, timeout=30)
        assert r.status_code == 200, r.text
        card = r.json()
        card_id = card["id"]
        assert card["slug"] == slug
        assert card["identity"]["fullName"] == "Test User"

        try:
            # Non-published card should be 404 on public
            r2 = requests.get(f"{API}/cards/{slug}", timeout=30)
            assert r2.status_code == 404

            # UPDATE
            payload["identity"]["fullName"] = "Updated Name"
            payload["status"] = "published"
            r3 = requests.put(f"{API}/admin/cards/{card_id}", headers=auth_headers, json=payload, timeout=30)
            assert r3.status_code == 200
            assert r3.json()["identity"]["fullName"] == "Updated Name"

            # Now published -> public endpoint works
            r4 = requests.get(f"{API}/cards/{slug}", timeout=30)
            assert r4.status_code == 200
        finally:
            # DELETE
            rd = requests.delete(f"{API}/admin/cards/{card_id}", headers=auth_headers, timeout=30)
            assert rd.status_code == 200
            # verify deletion
            rg = requests.get(f"{API}/admin/cards/{card_id}", headers=auth_headers, timeout=30)
            assert rg.status_code == 404


# -------------------- Upload --------------------
class TestUpload:
    def test_upload_and_download(self, auth_headers):
        # 1x1 PNG
        png = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
               b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf"
               b"\xc0\x00\x00\x00\x03\x00\x01\x5b\x83\x0e\xb4\x00\x00\x00\x00IEND\xaeB`\x82")
        files = {"file": ("test.png", io.BytesIO(png), "image/png")}
        r = requests.post(f"{API}/upload", headers=auth_headers, files=files, timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "url" in d and d["url"].startswith("/api/files/")

        dl = requests.get(f"{BASE_URL}{d['url']}", timeout=60)
        assert dl.status_code == 200
        assert dl.headers.get("content-type", "").startswith("image/png")

    def test_upload_requires_auth(self):
        files = {"file": ("test.png", io.BytesIO(b"x"), "image/png")}
        r = requests.post(f"{API}/upload", files=files, timeout=30)
        assert r.status_code == 401
