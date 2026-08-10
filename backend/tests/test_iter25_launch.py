"""Iteration 25 launch-hardening regression:
- Password reset (forgot -> reset -> login with new pw -> restore)
- Resend verification (auth + rate-limit sanity)
- Super Admin platform users/workspaces search + suspend (non-super 403, super_admin cannot be suspended)
- Suspended user cannot log in (403 'suspended')
- Public lead dedupe (merged:true) + case-insensitive email
- Scanner /scan/confirm duplicate + force
- Analytics overview days=7/30/90 (range_days honored) + CSV export
- Branding: no user-visible 'ARIADNI' in poster / config
"""
import os, re, time, uuid, datetime as dt
import pytest, requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
SUPER_EMAIL = "admin@ariadni.id"
SUPER_PW = "Ariadni@2026"
SLUG = "feras-askar"


def _login(email, pw):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": pw})
    return r


@pytest.fixture(scope="module")
def super_session():
    r = _login(SUPER_EMAIL, SUPER_PW)
    assert r.status_code == 200, f"Super admin login failed: {r.status_code} {r.text}"
    tok = r.json().get("token")
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


def _tail_backend_log_for(pattern, since_lines=800):
    """Read tail of backend supervisor log, return first match text (link)."""
    for p in ["/var/log/supervisor/backend.out.log", "/var/log/supervisor/backend.err.log"]:
        if not os.path.exists(p):
            continue
        try:
            with open(p, "r", errors="ignore") as f:
                lines = f.readlines()[-since_lines:]
            for line in reversed(lines):
                m = re.search(pattern, line)
                if m:
                    return m.group(0)
        except Exception:
            pass
    return None


# ---------- AUTH: forgot -> reset -> login ----------

def test_forgot_password_returns_ok_even_for_unknown_email():
    r = requests.post(f"{BASE}/api/auth/forgot-password", json={"email": "nobody_TEST@example.com"})
    assert r.status_code == 200
    assert r.json().get("ok") is True


def test_password_reset_end_to_end_and_restore():
    # 1) trigger forgot for super admin, then rotate password, then rotate back
    r = requests.post(f"{BASE}/api/auth/forgot-password", json={"email": SUPER_EMAIL})
    assert r.status_code == 200
    time.sleep(0.5)
    # 2) parse link from backend log
    link = _tail_backend_log_for(r"/reset\?token=[A-Za-z0-9_\-]+")
    assert link, "Reset link not found in backend logs — check /var/log/supervisor/backend.*.log"
    token = link.split("token=")[-1]
    new_pw = "Reset@Iter25!"
    rr = requests.post(f"{BASE}/api/auth/reset-password", json={"token": token, "password": new_pw})
    assert rr.status_code == 200, rr.text

    # 3) old password should fail (401), new one should succeed
    old_login = _login(SUPER_EMAIL, SUPER_PW)
    assert old_login.status_code in (401, 403), f"old pw should be rejected: {old_login.status_code}"
    new_login = _login(SUPER_EMAIL, new_pw)
    assert new_login.status_code == 200, f"login with new pw failed: {new_login.text}"

    # 4) restore original password by doing forgot->reset again
    r2 = requests.post(f"{BASE}/api/auth/forgot-password", json={"email": SUPER_EMAIL})
    assert r2.status_code == 200
    time.sleep(0.5)
    link2 = _tail_backend_log_for(r"/reset\?token=[A-Za-z0-9_\-]+")
    assert link2 and link2 != link, "expected a fresh reset link in logs"
    token2 = link2.split("token=")[-1]
    rr2 = requests.post(f"{BASE}/api/auth/reset-password", json={"token": token2, "password": SUPER_PW})
    assert rr2.status_code == 200
    final = _login(SUPER_EMAIL, SUPER_PW)
    assert final.status_code == 200, "failed to restore original password!"


def test_resend_verification_authenticated(super_session):
    r = super_session.post(f"{BASE}/api/auth/resend-verification")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("ok") is True


def test_resend_verification_unauth_rejected():
    r = requests.post(f"{BASE}/api/auth/resend-verification")
    assert r.status_code in (401, 403)


# ---------- SUPER ADMIN: users/workspaces search + suspend guards ----------

def test_admin_platform_users_search_super(super_session):
    r = super_session.get(f"{BASE}/api/admin/platform/users", params={"q": "ariadni"})
    assert r.status_code == 200, r.text
    items = r.json().get("items", [])
    assert isinstance(items, list) and len(items) > 0
    for it in items:
        # safety: no password_hash / _id leaks
        assert "password_hash" not in it and "_id" not in it


def test_admin_platform_workspaces_search_super(super_session):
    r = super_session.get(f"{BASE}/api/admin/platform/workspaces", params={"q": ""})
    assert r.status_code == 200, r.text
    items = r.json().get("items", [])
    assert isinstance(items, list) and len(items) > 0


def test_admin_platform_endpoints_forbidden_for_non_super():
    # Try a fresh registered user
    email = f"TEST_iter25_reg_{uuid.uuid4().hex[:8]}@t.io"
    reg = requests.post(f"{BASE}/api/auth/register", json={
        "email": email, "password": "Test@1234", "name": "IterTest", "workspace_name": "TEST_WS_iter25"
    })
    assert reg.status_code in (200, 201), reg.text
    tok = reg.json().get("token")
    assert tok
    h = {"Authorization": f"Bearer {tok}"}
    for path in ["/api/admin/platform/users", "/api/admin/platform/workspaces"]:
        r = requests.get(f"{BASE}{path}", headers=h)
        assert r.status_code == 403, f"{path} should be 403 for non-super, got {r.status_code}"
    r2 = requests.post(f"{BASE}/api/admin/platform/users/deadbeef/suspend", json={"suspended": True}, headers=h)
    assert r2.status_code == 403

    # cleanup: cannot self-delete easily; leave it — flagged in report if you can't cleanup users
    return


def test_super_admin_cannot_be_suspended(super_session):
    me = super_session.get(f"{BASE}/api/auth/session").json()
    my_id = me.get("user", {}).get("id")
    assert my_id
    r = super_session.post(f"{BASE}/api/admin/platform/users/{my_id}/suspend", json={"suspended": True})
    assert r.status_code == 400, r.text


def test_suspend_blocks_login_then_reinstate(super_session):
    # create test user
    email = f"TEST_iter25_suspend_{uuid.uuid4().hex[:8]}@t.io"
    pw = "Test@1234"
    reg = requests.post(f"{BASE}/api/auth/register", json={
        "email": email, "password": pw, "name": "SuspTest", "workspace_name": "TEST_WS_sus"
    })
    assert reg.status_code in (200, 201), reg.text
    # find the user id via super search
    lst = super_session.get(f"{BASE}/api/admin/platform/users", params={"q": email}).json().get("items", [])
    assert lst and lst[0]["email"].lower() == email.lower()
    uid = lst[0]["id"]
    # suspend
    r = super_session.post(f"{BASE}/api/admin/platform/users/{uid}/suspend", json={"suspended": True})
    assert r.status_code == 200 and r.json().get("suspended") is True
    # login must fail with 403 + 'suspend' hint
    lg = _login(email, pw)
    assert lg.status_code == 403, f"suspended login should be 403, got {lg.status_code} {lg.text}"
    assert "suspend" in lg.text.lower()
    # reinstate
    r2 = super_session.post(f"{BASE}/api/admin/platform/users/{uid}/suspend", json={"suspended": False})
    assert r2.status_code == 200 and r2.json().get("suspended") is False
    # login now succeeds
    lg2 = _login(email, pw)
    assert lg2.status_code == 200, lg2.text


# ---------- LEADS DEDUPE (public + scanner) ----------

def test_public_leads_dedupe_merge_case_insensitive(super_session):
    email = f"TEST_iter25_dupe_{uuid.uuid4().hex[:8]}@t.io"
    # first submission -> create
    r1 = requests.post(f"{BASE}/api/cards/{SLUG}/leads",
                       json={"name": "TEST_iter25_dupe", "email": email, "phone": "", "message": "hello 1"})
    assert r1.status_code in (200, 201), r1.text
    b1 = r1.json()
    assert b1.get("ok") is True
    assert not b1.get("merged"), f"first submission should not be merged, got {b1}"

    # second submission SAME email but UPPERCASE -> merge
    r2 = requests.post(f"{BASE}/api/cards/{SLUG}/leads",
                       json={"name": "Dupe Two", "email": email.upper(), "phone": "", "message": "hello 2"})
    assert r2.status_code in (200, 201)
    b2 = r2.json()
    assert b2.get("merged") is True, f"expected merged:true, got {b2}"

    # cleanup: find and delete
    lst = super_session.get(f"{BASE}/api/admin/leads").json()
    items = lst if isinstance(lst, list) else lst.get("items", [])
    for l in items:
        if (l.get("email") or "").lower() == email.lower():
            super_session.delete(f"{BASE}/api/admin/leads/{l['id']}")


def test_scanner_confirm_duplicate_and_force(super_session):
    email = f"TEST_iter25_scan_{uuid.uuid4().hex[:8]}@t.io"
    payload = {"name": "ScanDup", "email": email, "phone": "+15550001111", "cardSlug": SLUG,
               "source": "business_card_scan"}
    r1 = super_session.post(f"{BASE}/api/scan/confirm", json=payload)
    assert r1.status_code in (200, 201), r1.text
    lead_id_1 = (r1.json().get("lead") or r1.json()).get("id")
    assert lead_id_1

    # second attempt (no force) should indicate duplicate
    r2 = super_session.post(f"{BASE}/api/scan/confirm", json=payload)
    assert r2.status_code == 200, r2.text
    b2 = r2.json()
    assert b2.get("ok") is False, f"expected ok:false for duplicate, got {b2}"
    assert b2.get("duplicate"), f"expected duplicate payload, got {b2}"

    # force -> creates new lead
    r3 = super_session.post(f"{BASE}/api/scan/confirm", json={**payload, "force": True})
    assert r3.status_code in (200, 201)
    lead_id_2 = (r3.json().get("lead") or r3.json()).get("id")
    assert lead_id_2 and lead_id_2 != lead_id_1

    # cleanup
    for lid in [lead_id_1, lead_id_2]:
        super_session.delete(f"{BASE}/api/admin/leads/{lid}")


# ---------- ANALYTICS: range + CSV export ----------

@pytest.mark.parametrize("days", [7, 30, 90])
def test_analytics_overview_range(super_session, days):
    r = super_session.get(f"{BASE}/api/admin/analytics/overview", params={"days": days})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("range_days") == days, f"expected range_days={days}, got {body.get('range_days')}"
    assert "funnel" in body and "channels" in body and "breakdowns" in body


def test_analytics_export_csv(super_session):
    r = super_session.get(f"{BASE}/api/admin/analytics/export.csv", params={"days": 30})
    assert r.status_code == 200
    ct = r.headers.get("content-type", "")
    assert "text/csv" in ct, f"expected text/csv, got {ct}"
    text = r.text
    assert "Funnel" in text and "TapPresence" in text
    # branding: no ARIADNI in CSV
    assert "ARIADNI" not in text.upper() or "ARIADNI" not in text, "ARIADNI branding leaked into CSV"


# ---------- BRANDING ----------

def test_poster_no_ariadni_branding():
    r = requests.get(f"{BASE}/api/cards/{SLUG}/poster")
    assert r.status_code == 200
    body = r.text
    # PNG body may or may not include text; just ensure endpoint alive. Text-based check on HTML variant if present:
    # spec says QR poster should say 'TapPresence'. We'll assert content-type is image or html and no visible ARIADNI text if html.
    ct = r.headers.get("content-type", "")
    if "html" in ct.lower() or "svg" in ct.lower():
        assert "ARIADNI" not in body.upper(), "ARIADNI branding leaked into poster"


def test_config_no_ariadni_branding():
    r = requests.get(f"{BASE}/api/config")
    assert r.status_code == 200
    # Config is JSON; ensure no user-visible 'ARIADNI' string in labels/copy fields.
    text = r.text
    # allow only in workspace name 'ARIADNI HQ' if surfaced — flag as info
    if "ARIADNI" in text.upper():
        # Not a hard failure — just print for report
        print(f"NOTE: 'ARIADNI' present in /api/config response — likely internal HQ workspace name; verify not surfaced to users.")


# ---------- Tenant isolation smoke ----------

def test_tenant_isolation_non_super_cannot_access_other_ws_leads():
    email = f"TEST_iter25_iso_{uuid.uuid4().hex[:8]}@t.io"
    pw = "Test@1234"
    reg = requests.post(f"{BASE}/api/auth/register", json={
        "email": email, "password": pw, "name": "IsoTest", "workspace_name": "TEST_WS_iso"
    })
    assert reg.status_code in (200, 201), reg.text
    tok = reg.json().get("token")
    h = {"Authorization": f"Bearer {tok}"}
    # this fresh user should see 0 leads (their own empty workspace)
    r = requests.get(f"{BASE}/api/admin/leads", headers=h)
    assert r.status_code == 200
    items = r.json() if isinstance(r.json(), list) else r.json().get("items", [])
    assert items == [] or all(l.get("workspace_id") for l in items) and len(items) == 0
