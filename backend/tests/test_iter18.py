"""Iteration 18 backend tests — TapPresence P0.
Covers: /health, VCF access rules, team plan-gating for trial user, seat limits,
super admin bypass, login lockout, data export, account deletion cascade + token revocation.
"""
import os
import time
import uuid
import pytest
import requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")

ADMIN = {"email": "admin@ariadni.id", "password": "Ariadni@2026"}


def _login(email, password):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": password}, timeout=15)
    return r


def _auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


# ------------------- Health -------------------
def test_health():
    r = requests.get(f"{BASE}/api/health", timeout=10)
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "ok"
    assert d["db"] is True
    assert "time" in d
    # no secrets should leak
    body = r.text.lower()
    for bad in ["jwt_secret", "mongo_url", "password", "stripe"]:
        assert bad not in body


# ------------------- VCF access rules -------------------
def test_vcf_published_ok():
    r = requests.get(f"{BASE}/api/cards/feras-askar/vcard", timeout=10)
    assert r.status_code == 200
    assert "BEGIN:VCARD" in r.text
    assert "END:VCARD" in r.text


def test_vcf_unknown_404():
    r = requests.get(f"{BASE}/api/cards/does-not-exist-slug-xyz/vcard", timeout=10)
    assert r.status_code == 404


def test_vcf_draft_404():
    """Create a draft card as admin, then check vcard is 404."""
    la = _login(**ADMIN)
    assert la.status_code == 200, la.text
    tok = la.json()["token"]
    wsid = la.json()["workspace"]["id"]
    slug = f"qa-draft-{uuid.uuid4().hex[:8]}"
    payload = {
        "slug": slug,
        "workspace_id": wsid,
        "status": "draft",
        "identity": {"fullName": "QA Draft"},
        "contact": {"email": "qadraft@example.com"},
    }
    c = requests.post(f"{BASE}/api/admin/cards", json=payload, headers=_auth_headers(tok), timeout=15)
    if c.status_code not in (200, 201):
        pytest.skip(f"card create failed unexpectedly: {c.status_code} {c.text[:200]}")
    try:
        rv = requests.get(f"{BASE}/api/cards/{slug}/vcard", timeout=10)
        assert rv.status_code == 404
    finally:
        cid = c.json().get("id")
        if cid:
            requests.delete(f"{BASE}/api/admin/cards/{cid}", headers=_auth_headers(tok), timeout=10)


# ------------------- Team plan-gating -------------------
@pytest.fixture(scope="module")
def trial_user():
    email = f"qa_trial_{uuid.uuid4().hex[:10]}@demo.com"
    pw = "Trial@2026"
    r = requests.post(f"{BASE}/api/auth/register", json={
        "email": email, "password": pw, "name": "QA Trial", "workspace_name": "QA Trial WS"
    }, timeout=20)
    assert r.status_code == 200, r.text
    data = r.json()
    return {"email": email, "password": pw, "token": data["token"], "wsid": data["workspace"]["id"], "user": data["user"]}


@pytest.fixture(scope="module")
def admin_user():
    r = _login(**ADMIN)
    assert r.status_code == 200
    d = r.json()
    return {"token": d["token"], "wsid": d["workspace"]["id"], "user": d["user"]}


def test_team_gating_invite_402_for_trial(trial_user):
    r = requests.post(
        f"{BASE}/api/workspaces/{trial_user['wsid']}/members",
        json={"email": "someone@example.com", "role": "MEMBER"},
        headers=_auth_headers(trial_user["token"]), timeout=15,
    )
    assert r.status_code == 402, f"expected 402 got {r.status_code} {r.text}"


def test_team_gating_branding_402_for_trial(trial_user):
    r = requests.put(
        f"{BASE}/api/workspaces/{trial_user['wsid']}/branding",
        json={"primary": "#000000"},
        headers=_auth_headers(trial_user["token"]), timeout=15,
    )
    assert r.status_code == 402, r.text


def test_team_gating_import_402_for_trial(trial_user):
    r = requests.post(
        f"{BASE}/api/workspaces/{trial_user['wsid']}/import",
        json={"csv": "email,name\na@b.com,A\n", "create_cards": False},
        headers=_auth_headers(trial_user["token"]), timeout=15,
    )
    assert r.status_code == 402, r.text


def test_team_gating_apikeys_402_for_trial(trial_user):
    r = requests.post(
        f"{BASE}/api/workspaces/{trial_user['wsid']}/api-keys",
        json={"name": "test"},
        headers=_auth_headers(trial_user["token"]), timeout=15,
    )
    assert r.status_code == 402, r.text


def test_team_gating_webhooks_402_for_trial(trial_user):
    r = requests.post(
        f"{BASE}/api/workspaces/{trial_user['wsid']}/webhooks",
        json={"url": "https://example.com/hook", "events": ["lead.created"]},
        headers=_auth_headers(trial_user["token"]), timeout=15,
    )
    assert r.status_code == 402, r.text


def test_super_admin_can_invite(admin_user):
    r = requests.post(
        f"{BASE}/api/workspaces/{admin_user['wsid']}/members",
        json={"email": f"qa_invitee_{uuid.uuid4().hex[:8]}@demo.com", "role": "MEMBER", "name": "QA Invitee"},
        headers=_auth_headers(admin_user["token"]), timeout=15,
    )
    assert r.status_code in (200, 201), f"admin invite failed: {r.status_code} {r.text}"


def test_super_admin_can_branding(admin_user):
    r = requests.put(
        f"{BASE}/api/workspaces/{admin_user['wsid']}/branding",
        json={"primary": "#c9a961"},
        headers=_auth_headers(admin_user["token"]), timeout=15,
    )
    assert r.status_code == 200, r.text


def test_super_admin_can_create_apikey(admin_user):
    r = requests.post(
        f"{BASE}/api/workspaces/{admin_user['wsid']}/api-keys",
        json={"name": f"qa-key-{uuid.uuid4().hex[:6]}"},
        headers=_auth_headers(admin_user["token"]), timeout=15,
    )
    assert r.status_code in (200, 201), r.text
    kid = r.json().get("id")
    if kid:
        requests.delete(f"{BASE}/api/workspaces/{admin_user['wsid']}/api-keys/{kid}",
                        headers=_auth_headers(admin_user["token"]), timeout=10)


# ------------------- Login lockout -------------------
def test_login_lockout_throwaway():
    email = f"locktest_{uuid.uuid4().hex[:8]}@demo.com"
    for i in range(5):
        r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": "WrongPassword!"}, timeout=10)
        assert r.status_code == 401, f"attempt {i + 1}: expected 401 got {r.status_code}"
    r6 = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": "WrongPassword!"}, timeout=10)
    assert r6.status_code == 429, f"6th expected 429 got {r6.status_code} {r6.text}"
    # subsequent correct password still locked (even though user doesn't exist here, endpoint should still return 429 due to lock)
    r7 = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": "AnythingElse!"}, timeout=10)
    assert r7.status_code == 429, f"7th expected 429 got {r7.status_code}"


# ------------------- Data export + Account deletion -------------------
def test_export_shape_and_delete_cascade():
    email = f"qa_del_{uuid.uuid4().hex[:10]}@demo.com"
    pw = "Delete@2026"
    r = requests.post(f"{BASE}/api/auth/register", json={
        "email": email, "password": pw, "name": "QA Del", "workspace_name": "QA Del WS"
    }, timeout=20)
    assert r.status_code == 200, r.text
    tok = r.json()["token"]
    # export
    e = requests.get(f"{BASE}/api/account/export", headers=_auth_headers(tok), timeout=15)
    assert e.status_code == 200, e.text
    d = e.json()
    for k in ("user", "cards", "leads", "exported_at"):
        assert k in d, f"missing key {k} in export"
    assert d["user"]["email"] == email
    # delete
    dl = requests.delete(f"{BASE}/api/account", headers=_auth_headers(tok), timeout=20)
    assert dl.status_code == 200, dl.text
    body = dl.json()
    assert body.get("ok") is True
    assert "deleted_workspaces" in body
    # token invalidated
    s = requests.get(f"{BASE}/api/auth/session", headers=_auth_headers(tok), timeout=10)
    assert s.status_code == 401, f"token should be invalid after deletion, got {s.status_code}"
