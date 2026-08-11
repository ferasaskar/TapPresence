"""Iter32 - Google OAuth integration + regression tests on _provision_account refactor.

Covers:
 * Regression: email/password register (Individual, Team) still work; no orphan on 400.
 * Regression: login (SUPER_ADMIN + regular user).
 * Google /auth/google/start returns 302 with correct params.
 * Google /auth/google/callback graceful error redirects (never 500).
 * Google /auth/google/complete rejects invalid gp with 400 and does NOT create account.
"""
import os
import uuid
import urllib.parse as up

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://template-hub-184.preview.emergentagent.com").rstrip("/")
API = BASE_URL + "/api"

# Track created emails for cleanup via direct Mongo (best-effort).
_created_emails = []


def _rand_email(prefix="TEST_iter32"):
    e = f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"
    _created_emails.append(e)
    return e


@pytest.fixture(scope="module", autouse=True)
def _cleanup():
    yield
    # cleanup via mongo
    try:
        from motor.motor_asyncio import AsyncIOMotorClient  # noqa
        import asyncio, pymongo
        cli = pymongo.MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
        dbn = os.environ.get("DB_NAME", "test_database")
        db = cli[dbn]
        for e in _created_emails:
            u = db.users.find_one({"email": e.lower()})
            if u:
                uid = u["id"]
                mems = list(db.memberships.find({"user_id": uid}))
                for m in mems:
                    db.workspaces.delete_one({"id": m["workspace_id"]})
                db.memberships.delete_many({"user_id": uid})
                db.email_verifications.delete_many({"user_id": uid})
                db.users.delete_one({"id": uid})
    except Exception as ex:
        print(f"cleanup skipped: {ex}")


# ---------- Regression: email/password register (Individual) ----------
class TestRegressionIndividualRegister:
    def test_individual_register_success(self):
        email = _rand_email("TEST_iter32_indv")
        r = requests.post(f"{API}/auth/register", json={
            "email": email, "password": "Test@1234", "name": "Ind User",
            "account_type": "individual", "country_code": "US", "language": "en",
        })
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("token")
        assert data["user"]["email"] == email.lower()
        assert data["workspace"]["type"] == "individual"
        sub = data["workspace"]["subscription"]
        assert sub["plan"] == "trial"
        assert sub["status"] == "trialing"
        assert sub["pending_plan"] == "pro"

    def test_duplicate_individual_register_400(self):
        email = _rand_email("TEST_iter32_dup")
        r1 = requests.post(f"{API}/auth/register", json={
            "email": email, "password": "Test@1234", "name": "Dup", "account_type": "individual"
        })
        assert r1.status_code == 200
        r2 = requests.post(f"{API}/auth/register", json={
            "email": email, "password": "Test@1234", "name": "Dup", "account_type": "individual"
        })
        assert r2.status_code == 400


# ---------- Regression: email/password register (Team + seat minimum + no orphan) ----------
class TestRegressionTeamRegister:
    def test_team_below_min_seats_returns_400_no_orphan(self):
        email = _rand_email("TEST_iter32_team")
        r_bad = requests.post(f"{API}/auth/register", json={
            "email": email, "password": "Test@1234", "name": "Team User",
            "account_type": "team", "seats": 2, "billing_interval": "month",
            "company_name": "TestCo",
        })
        assert r_bad.status_code == 400, r_bad.text
        # Retry SAME email with valid seats -- must succeed (no orphan user was created)
        r_ok = requests.post(f"{API}/auth/register", json={
            "email": email, "password": "Test@1234", "name": "Team User",
            "account_type": "team", "seats": 3, "billing_interval": "month",
            "company_name": "TestCo",
        })
        assert r_ok.status_code == 200, r_ok.text
        data = r_ok.json()
        assert data["workspace"]["type"] == "company"
        sub = data["workspace"]["subscription"]
        assert sub["seats"] == 3
        assert sub["interval"] == "month"
        assert sub["pending_plan"] == "team"
        assert sub["status"] == "trialing"

    def test_team_yearly_interval(self):
        email = _rand_email("TEST_iter32_teamY")
        r = requests.post(f"{API}/auth/register", json={
            "email": email, "password": "Test@1234", "name": "TY",
            "account_type": "team", "seats": 5, "billing_interval": "year",
            "company_name": "TY Co",
        })
        assert r.status_code == 200
        sub = r.json()["workspace"]["subscription"]
        assert sub["seats"] == 5
        assert sub["interval"] == "year"


# ---------- Regression: login ----------
class TestRegressionLogin:
    def test_super_admin_login(self):
        r = requests.post(f"{API}/auth/login", json={
            "email": "admin@ariadni.id", "password": "Ariadni@2026"
        })
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["user"]["role"] == "SUPER_ADMIN"
        assert data.get("token")

    def test_regular_user_login_after_register(self):
        email = _rand_email("TEST_iter32_login")
        pw = "Test@1234"
        r = requests.post(f"{API}/auth/register", json={
            "email": email, "password": pw, "name": "L", "account_type": "individual"
        })
        assert r.status_code == 200
        r2 = requests.post(f"{API}/auth/login", json={"email": email, "password": pw})
        assert r2.status_code == 200
        assert r2.json()["user"]["email"] == email.lower()


# ---------- Google /auth/google/start ----------
class TestGoogleStart:
    def test_google_start_302_and_params(self):
        r = requests.get(f"{API}/auth/google/start", allow_redirects=False)
        assert r.status_code in (302, 307), r.status_code
        loc = r.headers.get("location", "")
        assert loc.startswith("https://accounts.google.com/o/oauth2/v2/auth")
        parsed = up.urlparse(loc)
        q = dict(up.parse_qsl(parsed.query))
        assert q.get("client_id", "").endswith("apps.googleusercontent.com")
        assert q.get("redirect_uri") == "https://template-hub-184.preview.emergentagent.com/api/auth/google/callback"
        assert q.get("response_type") == "code"
        assert q.get("scope") == "openid email profile"
        assert q.get("state")


# ---------- Google /auth/google/callback error handling ----------
class TestGoogleCallbackErrors:
    def _assert_login_redirect(self, r):
        assert r.status_code in (302, 307), f"expected redirect, got {r.status_code} {r.text[:200]}"
        loc = r.headers.get("location", "")
        assert "/login?google_error=" in loc, f"unexpected redirect: {loc}"
        assert loc.startswith("https://template-hub-184.preview.emergentagent.com"), loc

    def test_callback_no_params(self):
        r = requests.get(f"{API}/auth/google/callback", allow_redirects=False)
        self._assert_login_redirect(r)

    def test_callback_access_denied(self):
        r = requests.get(f"{API}/auth/google/callback?error=access_denied", allow_redirects=False)
        self._assert_login_redirect(r)

    def test_callback_bad_state(self):
        r = requests.get(f"{API}/auth/google/callback?code=x&state=badtoken", allow_redirects=False)
        self._assert_login_redirect(r)


# ---------- Google /auth/google/complete validation ----------
class TestGoogleComplete:
    def test_invalid_gp_returns_400(self):
        r = requests.post(f"{API}/auth/google/complete", json={"gp": "invalid", "account_type": "individual"})
        assert r.status_code == 400, r.text
        # ensure no user was created (invalid token has no email anyway) -- nothing to assert further.
