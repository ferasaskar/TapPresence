"""ARIADNI ID Commercial V1 GLOBAL-readiness tests (iteration 4).
Covers: markets, regional pricing, i18n public profile, register region,
AI multilingual follow-up, super admin market/pricing config, intl contact fields."""
import os
import uuid
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
ADMIN_EMAIL = "admin@ariadni.id"
ADMIN_PASSWORD = "Ariadni@2026"


# ---------- fixtures ----------
@pytest.fixture(scope="session")
def s():
    return requests.Session()


@pytest.fixture(scope="session")
def admin_token(s):
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    data = r.json()
    assert data["user"]["role"] == "SUPER_ADMIN"
    return data["token"]


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


def _reg(s, **overrides):
    body = {
        "email": f"test_{uuid.uuid4().hex[:10]}@example.com",
        "password": "Test@12345",
        "name": "Test User",
    }
    body.update(overrides)
    r = s.post(f"{BASE_URL}/api/auth/register", json=body, timeout=30)
    return r, body


def _cleanup(s, token):
    try:
        s.delete(f"{BASE_URL}/api/account",
                 headers={"Authorization": f"Bearer {token}"}, timeout=15)
    except Exception:
        pass


# ---------- Regression ----------
class TestRegression:
    def test_admin_login(self, admin_token):
        assert isinstance(admin_token, str) and len(admin_token) > 20

    def test_public_card_default_english(self, s):
        r = s.get(f"{BASE_URL}/api/cards/feras-askar", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["identity"]["jobTitle"] == "Executive Real Estate Advisor"

    def test_admin_cards_list(self, s, admin_headers):
        r = s.get(f"{BASE_URL}/api/admin/cards", headers=admin_headers, timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_qr_still_png(self, s):
        r = s.get(f"{BASE_URL}/api/cards/feras-askar/qr", timeout=15)
        assert r.status_code == 200
        assert "image/png" in r.headers.get("content-type", "")

    def test_poster_still_png(self, s):
        r = s.get(f"{BASE_URL}/api/cards/feras-askar/poster", timeout=30)
        assert r.status_code == 200
        assert "image/png" in r.headers.get("content-type", "")

    def test_new_user_sees_zero_cards(self, s):
        r, body = _reg(s)
        assert r.status_code == 200
        tok = r.json()["token"]
        try:
            lr = s.get(f"{BASE_URL}/api/admin/cards",
                       headers={"Authorization": f"Bearer {tok}"}, timeout=15)
            assert lr.status_code == 200
            assert lr.json() == []
        finally:
            _cleanup(s, tok)


# ---------- Markets ----------
class TestMarkets:
    def test_markets_endpoint(self, s):
        r = s.get(f"{BASE_URL}/api/markets", timeout=15)
        assert r.status_code == 200
        d = r.json()
        codes = {m["code"] for m in d["markets"]}
        assert {"US", "AE", "EU", "GB"}.issubset(codes)
        assert set(d["currencies"]) == {"USD", "AED", "EUR", "GBP"}
        assert d["rtl_languages"] == ["ar"]


# ---------- Regional pricing ----------
class TestPricing:
    @pytest.mark.parametrize("market,cur,pro_month,team_month", [
        ("US", "USD", 999, 699),
        ("AE", "AED", 3900, 2600),
        ("GB", "GBP", 899, 599),
    ])
    def test_regional_pricing(self, s, market, cur, pro_month, team_month):
        r = s.get(f"{BASE_URL}/api/pricing?market={market}", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["market"]["code"] == market
        plans = {p["id"]: p for p in d["plans"]}
        assert plans["pro"]["currency"] == cur
        assert plans["pro"]["price_month"] == pro_month
        assert plans["team"]["currency"] == cur
        assert plans["team"]["price_month"] == team_month

    def test_entitlements_stable_by_plan_ids(self, s):
        us = {p["id"] for p in s.get(f"{BASE_URL}/api/pricing?market=US").json()["plans"]}
        ae = {p["id"] for p in s.get(f"{BASE_URL}/api/pricing?market=AE").json()["plans"]}
        assert us == ae  # same plan set across markets


# ---------- Register with region ----------
class TestRegisterRegion:
    def test_register_ae_ar_aed(self, s):
        r, body = _reg(s, country_code="AE", language="ar", currency="AED")
        assert r.status_code == 200, r.text
        d = r.json()
        tok = d["token"]
        try:
            assert d["user"]["language"] == "ar"
            assert "AE" in d["user"]["locale"]
            assert d["user"]["timezone"] == "Asia/Dubai"
            assert d["workspace"]["region"]["default_currency"] == "AED"
            assert d["workspace"]["region"]["country_code"] == "AE"
        finally:
            _cleanup(s, tok)

    def test_register_us_defaults(self, s):
        r, body = _reg(s)  # no country_code
        assert r.status_code == 200, r.text
        d = r.json()
        tok = d["token"]
        try:
            assert d["user"]["language"] == "en"
            assert d["workspace"]["region"]["default_currency"] == "USD"
            assert d["user"]["timezone"] == "America/New_York"
        finally:
            _cleanup(s, tok)


# ---------- Localized public profile ----------
class TestLocalizedProfile:
    def test_lang_ar(self, s):
        r = s.get(f"{BASE_URL}/api/cards/feras-askar?lang=ar", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["_activeLang"] == "ar"
        assert "en" in d["_availableLangs"] and "ar" in d["_availableLangs"]
        jt = d["identity"]["jobTitle"]
        # Arabic text (contains Arabic chars, not just the English string)
        assert any("\u0600" <= ch <= "\u06FF" for ch in jt), f"jobTitle not Arabic: {jt}"
        services = d.get("services", [])
        assert services, "expected at least one service"
        assert any("\u0600" <= ch <= "\u06FF" for ch in services[0].get("title", ""))

    def test_lang_ar_untranslated_service_falls_back(self, s):
        r = s.get(f"{BASE_URL}/api/cards/feras-askar?lang=ar", timeout=15)
        d = r.json()
        services = d.get("services", [])
        # If more than one service AND only the first is translated, later services keep English.
        # Just assert every service has a non-empty title (fallback preserved).
        for sv in services:
            assert sv.get("title"), "service title should never be empty (fallback expected)"

    def test_lang_unsupported_fallback(self, s):
        r = s.get(f"{BASE_URL}/api/cards/feras-askar?lang=fr", timeout=15)
        assert r.status_code == 200
        d = r.json()
        # fr is not in languages -> default (en)
        assert d["_activeLang"] == "en"
        assert d["identity"]["jobTitle"] == "Executive Real Estate Advisor"

    def test_base_no_lang_stays_english(self, s):
        r = s.get(f"{BASE_URL}/api/cards/feras-askar", timeout=15)
        d = r.json()
        assert d["identity"]["jobTitle"] == "Executive Real Estate Advisor"


# ---------- AI multilingual follow-up ----------
class TestAIMultilingual:
    @pytest.fixture(scope="class")
    def user_token(self):
        s = requests.Session()
        r, _ = _reg(s)
        assert r.status_code == 200
        tok = r.json()["token"]
        yield tok
        _cleanup(s, tok)

    def _post(self, tok, lang):
        return requests.post(
            f"{BASE_URL}/api/ai/followup",
            headers={"Authorization": f"Bearer {tok}"},
            json={"lead_name": "Ali Hassan", "notes": "villa in JBR",
                  "owner_name": "Feras", "language": lang, "channel": "email"},
            timeout=30,
        )

    def test_ar(self, user_token):
        r = self._post(user_token, "ar")
        assert r.status_code == 200
        d = r.json()
        assert d["language"] == "ar"
        assert d["rtl"] is True
        assert any("\u0600" <= ch <= "\u06FF" for ch in d["draft"])
        assert "note" in d and "never" in d["note"].lower()

    def test_es(self, user_token):
        r = self._post(user_token, "es")
        assert r.status_code == 200
        d = r.json()
        assert d["language"] == "es"
        assert d["rtl"] is False
        # Spanish greeting/keywords
        assert "Hola" in d["draft"] or "saludo" in d["draft"].lower()

    def test_en(self, user_token):
        r = self._post(user_token, "en")
        assert r.status_code == 200
        d = r.json()
        assert d["language"] == "en"
        assert d["rtl"] is False
        assert "Hi" in d["draft"] or "Dear" in d["draft"] or "Thank you" in d["draft"]


# ---------- Super admin global config ----------
class TestAdminGlobalConfig:
    def test_admin_markets_lists(self, s, admin_headers):
        r = s.get(f"{BASE_URL}/api/admin/markets", headers=admin_headers, timeout=15)
        assert r.status_code == 200
        codes = {m["code"] for m in r.json()}
        assert {"US", "AE", "EU", "GB"}.issubset(codes)

    def test_admin_markets_forbidden_for_non_admin(self, s):
        r, _ = _reg(s)
        tok = r.json()["token"]
        try:
            rr = s.get(f"{BASE_URL}/api/admin/markets",
                       headers={"Authorization": f"Bearer {tok}"}, timeout=15)
            assert rr.status_code == 403
        finally:
            _cleanup(s, tok)

    def test_admin_update_pro_ae_pricing_roundtrip(self, s, admin_headers):
        new_month, new_year = 4200, 32000
        r = s.put(f"{BASE_URL}/api/admin/plans/pro/pricing/AE",
                  headers=admin_headers,
                  json={"month": new_month, "year": new_year}, timeout=15)
        assert r.status_code == 200
        try:
            pr = s.get(f"{BASE_URL}/api/pricing?market=AE", timeout=15).json()
            pro = next(p for p in pr["plans"] if p["id"] == "pro")
            assert pro["price_month"] == new_month
            assert pro["price_year"] == new_year
        finally:
            # restore original
            s.put(f"{BASE_URL}/api/admin/plans/pro/pricing/AE",
                  headers=admin_headers,
                  json={"month": 3900, "year": 29900}, timeout=15)
            pr = s.get(f"{BASE_URL}/api/pricing?market=AE", timeout=15).json()
            pro = next(p for p in pr["plans"] if p["id"] == "pro")
            assert pro["price_month"] == 3900
            assert pro["price_year"] == 29900

    def test_admin_update_market_field(self, s, admin_headers):
        # capture original
        cur = s.get(f"{BASE_URL}/api/admin/markets", headers=admin_headers).json()
        ae = next(m for m in cur if m["code"] == "AE")
        original_name = ae.get("name", "United Arab Emirates")
        try:
            r = s.put(f"{BASE_URL}/api/admin/markets/AE", headers=admin_headers,
                      json={"name": "United Arab Emirates (UAE)"}, timeout=15)
            assert r.status_code == 200
            d = r.json()
            assert d["name"] == "United Arab Emirates (UAE)"
            assert d["code"] == "AE"
        finally:
            s.put(f"{BASE_URL}/api/admin/markets/AE", headers=admin_headers,
                  json={"name": original_name}, timeout=15)


# ---------- International contact + languages/i18n roundtrip ----------
class TestIntlContactAndI18n:
    def test_card_intl_fields_roundtrip(self, s, admin_headers):
        # Create a card via admin
        payload = {
            "slug": f"test-intl-{uuid.uuid4().hex[:6]}",
            "identity": {"fullName": "Intl Test", "jobTitle": "Advisor",
                         "company": "TestCo", "bio": "hello"},
            "contact": {
                "email": "intl@test.com", "phone": "+971500000000",
                "addressLine1": "1 Sheikh Zayed Rd",
                "city": "Dubai", "adminArea": "Dubai",
                "postalCode": "00000", "countryCode": "AE",
            },
            "languages": ["en", "ar"],
            "i18n": {"ar": {"jobTitle": "مستشار", "bio": "مرحبا"}},
            "status": "draft",
        }
        r = s.post(f"{BASE_URL}/api/admin/cards", headers=admin_headers,
                   json=payload, timeout=15)
        assert r.status_code == 200, r.text
        created = r.json()
        cid = created["id"]
        try:
            # Update via PUT to also test round-trip
            upd = dict(payload)
            upd["contact"] = dict(payload["contact"])
            upd["contact"]["city"] = "Abu Dhabi"
            pr = s.put(f"{BASE_URL}/api/admin/cards/{cid}",
                       headers=admin_headers, json=upd, timeout=15)
            assert pr.status_code == 200, pr.text
            d = pr.json()
            assert d["contact"]["addressLine1"] == "1 Sheikh Zayed Rd"
            assert d["contact"]["city"] == "Abu Dhabi"
            assert d["contact"]["countryCode"] == "AE"
            assert d["contact"]["postalCode"] == "00000"
            assert set(d["languages"]) == {"en", "ar"}
            assert d["i18n"]["ar"]["jobTitle"] == "مستشار"
        finally:
            s.delete(f"{BASE_URL}/api/admin/cards/{cid}",
                     headers=admin_headers, timeout=15)
