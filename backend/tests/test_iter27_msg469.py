"""Iteration 27 - Message-469 backlog tests.

Covers:
- Timezone: PATCH /api/account/preferences valid + invalid, persistence in session.
- Date Filter: /api/admin/analytics/overview accepts start/end and legacy days.
- Date Filter: /api/admin/analytics/export.csv accepts start/end.
"""
import os
import pytest
import requests

def _load_backend_url():
    v = os.environ.get("REACT_APP_BACKEND_URL")
    if not v:
        try:
            with open("/app/frontend/.env") as f:
                for line in f:
                    if line.startswith("REACT_APP_BACKEND_URL="):
                        v = line.split("=", 1)[1].strip()
                        break
        except Exception:
            pass
    assert v, "REACT_APP_BACKEND_URL not set"
    return v.rstrip("/")

BASE_URL = _load_backend_url()
WORK_EMAIL = "work@gmail.com"
WORK_PWD = "mohammed"


@pytest.fixture(scope="module")
def work_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": WORK_EMAIL, "password": WORK_PWD}, timeout=20)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    data = r.json()
    token = data.get("token") or data.get("access_token")
    if token:
        s.headers.update({"Authorization": f"Bearer {token}"})
    return s


# ---------- Timezone ----------
class TestTimezonePreferences:
    def test_patch_valid_timezone(self, work_session):
        r = work_session.patch(f"{BASE_URL}/api/account/preferences", json={"timezone": "Asia/Dubai"}, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("ok") is True
        assert data.get("timezone") == "Asia/Dubai"
        assert data.get("timezone_source") == "manual"

    def test_session_reflects_manual_tz(self, work_session):
        r = work_session.get(f"{BASE_URL}/api/auth/session", timeout=15)
        assert r.status_code == 200, r.text
        user = r.json().get("user", {})
        assert user.get("timezone") == "Asia/Dubai"
        assert user.get("timezone_source") == "manual"

    def test_patch_invalid_timezone(self, work_session):
        r = work_session.patch(f"{BASE_URL}/api/account/preferences", json={"timezone": "Not/AZone"}, timeout=15)
        assert r.status_code == 400, r.text

    def test_reset_timezone_to_ny(self, work_session):
        # Reset to America/New_York as requested. There is no API to unset timezone_source;
        # we set to NY (source will remain 'manual' by design of the endpoint).
        r = work_session.patch(f"{BASE_URL}/api/account/preferences", json={"timezone": "America/New_York"}, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json().get("timezone") == "America/New_York"


# ---------- Analytics date-range ----------
class TestAnalyticsDateRange:
    def test_overview_days_legacy(self, work_session):
        r = work_session.get(f"{BASE_URL}/api/admin/analytics/overview?days=30", timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        # sanity: shape includes totals
        assert isinstance(data, dict)

    def test_overview_with_start_end(self, work_session):
        r_month = work_session.get(
            f"{BASE_URL}/api/admin/analytics/overview",
            params={"start": "2026-08-01T00:00:00Z", "end": "2026-08-31T23:59:59Z"},
            timeout=20,
        )
        assert r_month.status_code == 200, r_month.text
        r_day = work_session.get(
            f"{BASE_URL}/api/admin/analytics/overview",
            params={"start": "2026-08-10T00:00:00Z", "end": "2026-08-10T23:59:59Z"},
            timeout=20,
        )
        assert r_day.status_code == 200, r_day.text
        # Sub-range should be <= full month range for views
        month = r_month.json()
        day = r_day.json()

        def views(d):
            for k in ("views", "totalViews", "total_views"):
                if k in d and isinstance(d[k], (int, float)):
                    return d[k]
            # possibly nested
            t = d.get("totals") or {}
            for k in ("views", "totalViews"):
                if k in t:
                    return t[k]
            return None

        mv, dv = views(month), views(day)
        if mv is not None and dv is not None:
            assert dv <= mv, f"day views {dv} should be <= month views {mv}"

    def test_export_csv_with_start_end(self, work_session):
        r = work_session.get(
            f"{BASE_URL}/api/admin/analytics/export.csv",
            params={"start": "2026-08-01T00:00:00Z", "end": "2026-08-31T23:59:59Z"},
            timeout=20,
        )
        assert r.status_code == 200, r.text
        ct = r.headers.get("content-type", "")
        assert "csv" in ct.lower() or r.text.count(",") > 0
