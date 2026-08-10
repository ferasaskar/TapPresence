"""Iteration 20 — Referral Phase 2 tests.
Focus: record_paid_subscription_event idempotency, redemption ledger fields
(free_months_earned/available/redeemed), nothing marked redeemed in demo mode,
20% referred-signup discount preserved.
"""
import time, uuid, requests, pytest

BASE = open('/app/frontend/.env').read().split('REACT_APP_BACKEND_URL=')[1].split('\n')[0].strip().rstrip('/')
API = BASE + "/api"
RUN = uuid.uuid4().hex[:6]


def _reg(email, ref=None):
    body = {"email": email, "password": "Test@1234", "name": email.split('@')[0]}
    if ref:
        body["referral_code"] = ref
    return requests.post(f"{API}/auth/register", json=body)


def _tok(email, ref=None):
    r = _reg(email, ref)
    assert r.status_code == 200, f"register {r.status_code} {r.text}"
    return r.json()["token"]


def _h(t):
    return {"Authorization": f"Bearer {t}"}


def _ref(t):
    return requests.get(f"{API}/referral", headers=_h(t)).json()


def _sub(t, plan="pro"):
    return requests.post(f"{API}/billing/subscribe", headers=_h(t), json={"plan": plan, "interval": "month"})


# ---- Health ----

def test_health():
    assert requests.get(f"{API}/health").status_code == 200


# ---- Redemption ledger shape ----

@pytest.fixture(scope="module")
def referrer_and_five():
    """Build a referrer with 5 qualified paid referrals → 1 free_month_earned."""
    r_tok = _tok(f"iter20_r_{RUN}@demo.com")
    r_code = _ref(r_tok)["code"]
    referreds = []
    for i in range(5):
        t = _tok(f"iter20_c{i}_{RUN}@demo.com", ref=r_code)
        assert _sub(t).status_code == 200
        referreds.append(t)
    return {"token": r_tok, "code": r_code, "referreds": referreds}


def test_ledger_fields_present(referrer_and_five):
    d = _ref(referrer_and_five["token"])
    rw = d["reward"]
    for k in ("qualified_count", "signed_up_count", "per_reward", "reward_months",
              "free_months_earned", "free_months_available", "free_months_redeemed", "progress"):
        assert k in rw, f"missing {k} in reward ledger: {rw}"
    assert rw["free_months_earned"] == 1
    assert rw["free_months_available"] == 1
    # NOTHING must be marked redeemed in demo mode — no billing event redemption yet
    assert rw["free_months_redeemed"] == 0
    assert rw["progress"] == 0
    assert rw["qualified_count"] == 5


def test_signup_alone_does_not_qualify():
    r_tok = _tok(f"iter20_x_{RUN}@demo.com")
    code = _ref(r_tok)["code"]
    # 3 signups only
    for i in range(3):
        _tok(f"iter20_xs{i}_{RUN}@demo.com", ref=code)
    d = _ref(r_tok)
    assert d["counts"]["signed_up"] == 3
    assert d["reward"]["qualified_count"] == 0
    assert d["reward"]["free_months_earned"] == 0


def test_subscribe_idempotent_no_double_qualify(referrer_and_five):
    """Duplicate paid event for same workspace should NOT double-qualify."""
    # Re-subscribe already-qualified referred[0] many times
    t = referrer_and_five["referreds"][0]
    before = _ref(referrer_and_five["token"])["reward"]["qualified_count"]
    for _ in range(4):
        _sub(t)
    after = _ref(referrer_and_five["token"])["reward"]["qualified_count"]
    assert after == before, f"double-qualified! before={before} after={after}"


def test_referred_20pct_discount_preserved(referrer_and_five):
    b = requests.get(f"{API}/billing", headers=_h(referrer_and_five["referreds"][0])).json()
    assert b.get("discount", {}).get("referred_month_pct") == 20


def test_pricing_referred_discount_pct_20():
    p = requests.get(f"{API}/commercial/pricing").json()
    assert p["referral"]["referred_discount_month_pct"] == 20


def test_referral_qr(referrer_and_five):
    r = requests.get(f"{API}/referral/qr", params={"code": referrer_and_five["code"]})
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("image/")


def test_admin_no_referral_workspace():
    r = requests.post(f"{API}/auth/login", json={"email": "admin@ariadni.id", "password": "Ariadni@2026"})
    assert r.status_code == 200
    tok = r.json()["token"]
    r2 = requests.get(f"{API}/referral", headers=_h(tok))
    assert r2.status_code == 404


def test_public_card_feras():
    r = requests.get(f"{API}/cards/feras-askar")
    assert r.status_code == 200
    r2 = requests.get(f"{API}/cards/feras-askar/vcard")
    assert r2.status_code == 200
    assert "BEGIN:VCARD" in r2.text


def test_team_gating_402_for_trial():
    tok = _tok(f"iter20_gate_{RUN}@demo.com")
    s = requests.get(f"{API}/auth/session", headers=_h(tok)).json()
    wid = s["workspace"]["id"]
    r = requests.post(f"{API}/workspaces/{wid}/members", headers=_h(tok),
                     json={"email": f"invited_{RUN}@demo.com", "role": "member"})
    assert r.status_code == 402


def test_10_qualified_earns_2_months():
    """Fresh referrer with 10 qualified → 2 months earned, 0 redeemed, 2 available."""
    r_tok = _tok(f"iter20_r10_{RUN}@demo.com")
    code = _ref(r_tok)["code"]
    for i in range(10):
        t = _tok(f"iter20_c10_{i}_{RUN}@demo.com", ref=code)
        assert _sub(t).status_code == 200
    d = _ref(r_tok)
    rw = d["reward"]
    assert rw["qualified_count"] == 10
    assert rw["free_months_earned"] == 2
    assert rw["free_months_available"] == 2
    assert rw["free_months_redeemed"] == 0
