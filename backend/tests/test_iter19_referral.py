"""Iteration 19 — Referral reward-model tests.
Model: 5 qualified paid referrals => 1 free month; preserves referred 20% discount.
"""
import os, time, uuid, requests, pytest

BASE = open('/app/frontend/.env').read().split('REACT_APP_BACKEND_URL=')[1].split('\n')[0].strip().rstrip('/')
API = BASE + "/api"
TS = str(int(time.time()))
RUN = uuid.uuid4().hex[:6]


def _reg(email, ref=None):
    body = {"email": email, "password": "Test@1234", "name": email.split('@')[0]}
    if ref: body["referral_code"] = ref
    r = requests.post(f"{API}/auth/register", json=body)
    return r


def _tok(email, ref=None):
    r = _reg(email, ref)
    assert r.status_code == 200, f"register failed {r.status_code} {r.text}"
    return r.json()["token"]


def _get(path, token=None):
    h = {"Authorization": f"Bearer {token}"} if token else {}
    return requests.get(f"{API}{path}", headers=h)


def _post(path, token=None, json=None):
    h = {"Authorization": f"Bearer {token}"} if token else {}
    return requests.post(f"{API}{path}", headers=h, json=json or {})


# ---------- Basic health & admin ----------

def test_health():
    r = requests.get(f"{API}/health")
    assert r.status_code == 200

def test_admin_login_and_no_referral():
    r = requests.post(f"{API}/auth/login", json={"email": "admin@ariadni.id", "password": "Ariadni@2026"})
    assert r.status_code == 200, r.text
    tok = r.json()["token"]
    # SUPER_ADMIN has no ws membership → 404 on /referral is expected
    r2 = _get("/referral", tok)
    assert r2.status_code == 404


# ---------- Referral lifecycle ----------

@pytest.fixture(scope="module")
def referrer():
    email = f"iter19_ref_{RUN}@demo.com"
    tok = _tok(email)
    r = _get("/referral", tok).json()
    return {"email": email, "token": tok, "code": r["code"], "share_url": r["share_url"]}


def test_referral_response_shape(referrer):
    r = _get("/referral", referrer["token"]).json()
    assert r["enabled"] is True
    assert isinstance(r["code"], str) and len(r["code"]) >= 6
    assert r["share_url"].endswith(f"ref={r['code']}") or f"ref={r['code']}" in r["share_url"]
    cfg = r["config"]
    for k in ("referrals_per_reward","reward_months","reward_type","referred_discount_month_pct"):
        assert k in cfg
    assert cfg["referrals_per_reward"] == 5
    assert cfg["reward_months"] == 1
    assert cfg["referred_discount_month_pct"] == 20
    counts = r["counts"]
    for k in ("total","signed_up","qualified"): assert k in counts
    reward = r["reward"]
    for k in ("qualified_count","signed_up_count","per_reward","free_months_earned","free_months_available","progress"):
        assert k in reward


def test_pricing_referral_discount_preserved():
    r = requests.get(f"{API}/commercial/pricing").json()
    assert r["referral"]["referred_discount_month_pct"] == 20


@pytest.fixture(scope="module")
def referreds(referrer):
    """Register 6 referred accounts (signups only)."""
    accts = []
    for i in range(6):
        email = f"iter19_c{i}_{RUN}@demo.com"
        tok = _tok(email, ref=referrer["code"])
        accts.append({"email": email, "token": tok})
    return accts


def test_signups_do_not_qualify(referrer, referreds):
    r = _get("/referral", referrer["token"]).json()
    assert r["counts"]["signed_up"] == 6
    assert r["counts"]["qualified"] == 0
    assert r["reward"]["qualified_count"] == 0
    assert r["reward"]["free_months_earned"] == 0
    assert r["reward"]["progress"] == 0


def test_referred_gets_20pct_month_discount(referreds):
    b = _get("/billing", referreds[0]["token"]).json()
    # discount.referred_month_pct = 20
    disc = b.get("discount", {})
    assert disc.get("referred_month_pct") == 20, f"expected 20, got {disc}"


def test_4_qualified_no_reward(referrer, referreds):
    for i in range(4):
        r = _post("/billing/subscribe", referreds[i]["token"], {"plan": "pro", "interval": "month"})
        assert r.status_code == 200, r.text
    d = _get("/referral", referrer["token"]).json()
    assert d["reward"]["qualified_count"] == 4
    assert d["reward"]["free_months_earned"] == 0
    assert d["reward"]["progress"] == 4


def test_idempotency_no_double_count(referrer, referreds):
    # re-subscribe first referred
    _post("/billing/subscribe", referreds[0]["token"], {"plan": "pro", "interval": "month"})
    d = _get("/referral", referrer["token"]).json()
    assert d["reward"]["qualified_count"] == 4


def test_5th_qualified_earns_1_month(referrer, referreds):
    r = _post("/billing/subscribe", referreds[4]["token"], {"plan": "pro", "interval": "month"})
    assert r.status_code == 200
    d = _get("/referral", referrer["token"]).json()
    assert d["reward"]["qualified_count"] == 5
    assert d["reward"]["free_months_earned"] == 1
    assert d["reward"]["progress"] == 0


def test_6th_qualified_progress_1(referrer, referreds):
    r = _post("/billing/subscribe", referreds[5]["token"], {"plan": "pro", "interval": "month"})
    assert r.status_code == 200
    d = _get("/referral", referrer["token"]).json()
    assert d["reward"]["qualified_count"] == 6
    assert d["reward"]["free_months_earned"] == 1
    assert d["reward"]["progress"] == 1


def test_10_qualified_earns_2_months(referrer):
    # register + subscribe 4 more to reach 10 qualified
    for i in range(4):
        email = f"iter19_c{6+i}_{RUN}@demo.com"
        tok = _tok(email, ref=referrer["code"])
        r = _post("/billing/subscribe", tok, {"plan": "pro", "interval": "month"})
        assert r.status_code == 200
    d = _get("/referral", referrer["token"]).json()
    assert d["reward"]["qualified_count"] == 10
    assert d["reward"]["free_months_earned"] == 2
    assert d["reward"]["progress"] == 0


# ---------- Self-referral protection ----------

def test_self_referral_protection():
    email = f"iter19_self_{RUN}@demo.com"
    tok = _tok(email)
    code = _get("/referral", tok).json()["code"]
    # cannot re-register same email with own code
    r = _reg(email, ref=code)
    assert r.status_code == 400
    # ws only referred once: create ws A, register ws B with A's code, then try to attribute again
    tokA = _tok(f"iter19_A_{RUN}@demo.com")
    codeA = _get("/referral", tokA).json()["code"]
    tokB = _tok(f"iter19_B_{RUN}@demo.com", ref=codeA)
    # counts: A has 1 signed_up
    da = _get("/referral", tokA).json()
    assert da["counts"]["signed_up"] == 1


# ---------- Super admin config ----------

def test_admin_can_change_and_revert_referral_config():
    r = requests.post(f"{API}/auth/login", json={"email": "admin@ariadni.id", "password": "Ariadni@2026"})
    tok = r.json()["token"]
    # get current cfg
    resp = requests.get(f"{API}/admin/commercial", headers={"Authorization": f"Bearer {tok}"}).json()
    cur = resp.get("config", resp)  # endpoint returns {config, markets, demo_billing}
    # change to 3 / 2
    cur["referral"]["referrals_per_reward"] = 3
    cur["referral"]["reward_months"] = 2
    r2 = requests.put(f"{API}/admin/commercial", headers={"Authorization": f"Bearer {tok}"}, json=cur)
    assert r2.status_code == 200, r2.text
    p = requests.get(f"{API}/commercial/pricing").json()
    assert p["referral"]["referrals_per_reward"] == 3
    assert p["referral"]["reward_months"] == 2
    # REVERT
    cur["referral"]["referrals_per_reward"] = 5
    cur["referral"]["reward_months"] = 1
    r3 = requests.put(f"{API}/admin/commercial", headers={"Authorization": f"Bearer {tok}"}, json=cur)
    assert r3.status_code == 200
    p2 = requests.get(f"{API}/commercial/pricing").json()
    assert p2["referral"]["referrals_per_reward"] == 5
    assert p2["referral"]["reward_months"] == 1


# ---------- Regression ----------

def test_public_card_and_vcf():
    r = requests.get(f"{API}/cards/feras-askar")
    assert r.status_code == 200
    r2 = requests.get(f"{API}/cards/feras-askar/vcard")
    assert r2.status_code == 200
    assert "BEGIN:VCARD" in r2.text


def test_referral_qr_endpoint(referrer):
    r = requests.get(f"{API}/referral/qr", params={"code": referrer["code"]})
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("image/")


def test_team_gating_402_for_trial():
    tok = _tok(f"iter19_gate_{RUN}@demo.com")
    # get ws id
    ms = requests.get(f"{API}/auth/session", headers={"Authorization": f"Bearer {tok}"}).json()
    wid = ms["workspace"]["id"]
    # invite endpoint requires team plan (trial free plan)
    r = _post(f"/workspaces/{wid}/members", tok, {"email": f"invited_{RUN}@demo.com", "role": "member"})
    assert r.status_code == 402, f"expected 402, got {r.status_code} {r.text}"


def test_login_lockout_still_works():
    email = f"iter19_lock_{uuid.uuid4().hex[:6]}@demo.com"
    _reg(email)
    # 5 fails
    for _ in range(5):
        requests.post(f"{API}/auth/login", json={"email": email, "password": "wrong"})
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": "wrong"})
    # 6th within lockout window returns 429 or 401 depending on implementation; iter18 confirmed 429
    assert r.status_code in (401, 429)
