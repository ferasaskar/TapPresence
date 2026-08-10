"""ARIADNI ID — Commercial V1 platform module.

Additive, multi-tenant commercial layer mounted alongside the existing API:
- Commercial auth (register / verify / refresh / forgot / reset / sessions)
- Workspaces, memberships, roles, plans + entitlements
- Feature-flag / integration config adapter ("Not Configured" states)
- NFC device token system + permanent tap redirect + lifecycle
- CRM lead upgrade (status/tags/notes/follow-up) + activities + CSV export
- Campaign attribution
- AI follow-up draft generator (provider-abstracted)
- Audit logging helper

External-credential integrations (Stripe, Apple/Google Wallet, OAuth, CRM,
enrichment, RevenueCat, email, push) are represented by config adapters that
report `configured: false` until credentials are supplied. Nothing here blocks
on a missing credential.
"""
import os
import csv
import io
import json
import re
import uuid
import secrets
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional

import jwt
import bcrypt
from fastapi import APIRouter, HTTPException, Depends, Request, Header
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr

logger = logging.getLogger("ariadni.platform")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALG = "HS256"
PUBLIC_APP_URL = os.environ.get("PUBLIC_APP_URL", "").rstrip("/")

_client = AsyncIOMotorClient(MONGO_URL)
db = _client[DB_NAME]

platform_router = APIRouter(prefix="/api")
bearer = HTTPBearer(auto_error=False)

RESERVED_SLUGS = {"admin", "login", "register", "api", "app", "dashboard", "t", "tap", "settings", "pricing", "teams"}

# ------------------------------------------------------------------ global markets / currency
SUPPORTED_CURRENCIES = ["USD", "AED", "EUR", "GBP"]
SUPPORTED_LANGUAGES = ["en", "ar", "es"]
RTL_LANGUAGES = ["ar"]

DEFAULT_MARKETS = [
    {"code": "US", "name": "United States", "currency": "USD", "default_language": "en", "timezone": "America/New_York", "active": True},
    {"code": "AE", "name": "United Arab Emirates", "currency": "AED", "default_language": "en", "timezone": "Asia/Dubai", "active": True},
    {"code": "EU", "name": "European Union", "currency": "EUR", "default_language": "es", "timezone": "Europe/Madrid", "active": True},
    {"code": "GB", "name": "United Kingdom", "currency": "GBP", "default_language": "en", "timezone": "Europe/London", "active": True},
]

# minor units; per-plan per-market {month, year}
DEFAULT_REGIONAL_PRICES = {
    "pro": {"US": {"month": 999, "year": 7999}, "AE": {"month": 3900, "year": 29900},
            "EU": {"month": 999, "year": 7999}, "GB": {"month": 899, "year": 6999}},
    "team": {"US": {"month": 699, "year": 6999}, "AE": {"month": 2600, "year": 24900},
             "EU": {"month": 699, "year": 6999}, "GB": {"month": 599, "year": 5999}},
}


def default_region(country_code="US"):
    m = next((m for m in DEFAULT_MARKETS if m["code"] == country_code), DEFAULT_MARKETS[0])
    return {"country": m["name"], "country_code": m["code"], "region": "", "timezone": m["timezone"],
            "locale": f"{m['default_language']}-{m['code']}", "default_language": m["default_language"],
            "default_currency": m["currency"], "billing_country": m["code"]}

# ------------------------------------------------------------------ entitlements
TRIAL_DAYS = 14
# Central entitlement matrix (approved). Backend is the source of truth.
# Quotas: *_limit with *_period ("month" | "total"); analytics_months (0 = unlimited).
PLAN_ENTITLEMENTS = {
    "trial": {"max_cards": 1, "premium_templates": True, "analytics": "full", "analytics_months": 1,
              "leads": True, "wallet": True, "crm": True, "campaigns": True,
              "ai_followup": True, "ai_limit": 10, "ai_period": "total",
              "scanner": True, "scanner_limit": 10, "scanner_period": "total",
              "team": False, "remove_branding": False, "white_label": False, "custom_domain": False, "api": False},
    "pro": {"max_cards": 3, "premium_templates": True, "analytics": "full", "analytics_months": 12,
            "leads": True, "wallet": True, "crm": True, "campaigns": True,
            "ai_followup": True, "ai_limit": 100, "ai_period": "month",
            "scanner": True, "scanner_limit": 50, "scanner_period": "month",
            "team": False, "remove_branding": True, "white_label": False, "custom_domain": False, "api": False},
    "team": {"max_cards": 9999, "premium_templates": True, "analytics": "full", "analytics_months": 24,
             "leads": True, "wallet": True, "crm": True, "campaigns": True,
             "ai_followup": True, "ai_limit": 100, "ai_period": "month",
             "scanner": True, "scanner_limit": 100, "scanner_period": "month",
             "team": True, "remove_branding": True, "white_label": False, "custom_domain": True, "api": True},
    "enterprise": {"max_cards": 99999, "premium_templates": True, "analytics": "full", "analytics_months": 0,
                   "leads": True, "wallet": True, "crm": True, "campaigns": True,
                   "ai_followup": True, "ai_limit": 1000000, "ai_period": "month",
                   "scanner": True, "scanner_limit": 1000000, "scanner_period": "month",
                   "team": True, "remove_branding": True, "white_label": True, "custom_domain": True, "api": True},
    # legacy — existing (grandfathered) workspaces without a subscription resolve to active
    "free": {"max_cards": 1, "premium_templates": True, "analytics": "full", "analytics_months": 12,
             "leads": True, "wallet": True, "crm": True, "campaigns": True,
             "ai_followup": True, "ai_limit": 100, "ai_period": "month",
             "scanner": True, "scanner_limit": 50, "scanner_period": "month",
             "team": False, "remove_branding": True, "white_label": False, "custom_domain": False, "api": False},
    "white_label": {"max_cards": 99999, "premium_templates": True, "analytics": "full", "analytics_months": 0,
                    "leads": True, "wallet": True, "crm": True, "campaigns": True,
                    "ai_followup": True, "ai_limit": 1000000, "ai_period": "month",
                    "scanner": True, "scanner_limit": 1000000, "scanner_period": "month",
                    "team": True, "remove_branding": True, "white_label": True, "custom_domain": True, "api": True},
}

# provider-neutral subscription states; card stays live through cancel_at_period_end
ACTIVE_STATES = {"trialing", "active", "cancel_at_period_end"}

DEFAULT_PLANS = [
    {"id": "free", "name": "Legacy", "price_month": 0, "price_year": 0, "public": False},
    {"id": "pro", "name": "Pro", "price_month": 999, "price_year": 7999, "public": True},
    {"id": "team", "name": "Team", "price_month": 699, "price_year": 6999, "public": True, "per_seat": True},
    {"id": "enterprise", "name": "Enterprise", "price_month": None, "price_year": None, "public": True, "custom": True},
    {"id": "white_label", "name": "White Label", "price_month": None, "price_year": None, "public": False, "custom": True},
]


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def hash_pw(p): return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
def check_pw(p, h):
    try:
        return bcrypt.checkpw(p.encode(), h.encode())
    except Exception:
        return False


def make_token(sub, typ, days=None, minutes=None, extra=None):
    exp = datetime.now(timezone.utc) + (timedelta(days=days) if days else timedelta(minutes=minutes or 15))
    payload = {"sub": sub, "type": typ, "exp": exp}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


async def current_user(creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer)) -> dict:
    if not creds or not creds.credentials:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")
    if payload.get("type") not in (None, "access"):
        raise HTTPException(401, "Invalid token type")
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(401, "User not found")
    return user


async def memberships_for(user_id: str):
    return await db.memberships.find({"user_id": user_id}, {"_id": 0}).to_list(100)


async def workspace_ids_for(user: dict):
    if user.get("role") == "SUPER_ADMIN":
        return "ALL"
    ms = await memberships_for(user["id"])
    return [m["workspace_id"] for m in ms]


def effective_status(ws: dict) -> str:
    """Compute provider-neutral subscription status; auto-expire trials. Existing (no sub) = active (grandfathered)."""
    sub = (ws or {}).get("subscription")
    if not sub:
        return "active"
    st = sub.get("status", "active")
    if st == "trialing" and sub.get("trial_ends_at") and now_iso() > sub["trial_ends_at"]:
        return "trial_expired"
    return st


async def resolve_entitlements(workspace_id: str) -> dict:
    ws = await db.workspaces.find_one({"id": workspace_id}, {"_id": 0})
    sub = (ws or {}).get("subscription") or {}
    plan = sub.get("plan") or (ws or {}).get("plan", "free")
    status = effective_status(ws)
    ent = dict(PLAN_ENTITLEMENTS.get(plan, PLAN_ENTITLEMENTS["free"]))
    ent["plan"] = plan
    ent["status"] = status
    ent["active"] = status in ACTIVE_STATES
    ent["trial_ends_at"] = sub.get("trial_ends_at")
    ent["current_period_end"] = sub.get("current_period_end")
    ent["seats"] = sub.get("seats")
    if not ent["active"]:
        # locked (trial_expired / past_due / cancelled): preserve all data, block premium actions & public card
        ent["ai_followup"] = False
        ent["scanner"] = False
    return ent


def _usage_period_key(period: str) -> str:
    return "total" if period == "total" else datetime.now(timezone.utc).strftime("%Y-%m")


async def get_usage(subject_id: str, metric: str, period: str) -> int:
    d = await db.usage_counters.find_one({"subject_id": subject_id, "metric": metric, "period": _usage_period_key(period)}, {"_id": 0})
    return (d or {}).get("count", 0)


async def incr_usage(subject_id: str, metric: str, period: str):
    pk = _usage_period_key(period)
    await db.usage_counters.update_one(
        {"subject_id": subject_id, "metric": metric, "period": pk},
        {"$inc": {"count": 1}, "$setOnInsert": {"subject_id": subject_id, "metric": metric, "period": pk}},
        upsert=True)


async def enforce_quota(user: dict, ws_id: str, metric: str):
    """metric: 'ai' or 'scanner'. Raises 402 if inactive, 429 if over plan limit. Returns (ent, period)."""
    if user.get("role") == "SUPER_ADMIN":
        return PLAN_ENTITLEMENTS["enterprise"], "month"
    ent = await resolve_entitlements(ws_id) if ws_id else PLAN_ENTITLEMENTS["free"]
    if not ent.get("active"):
        raise HTTPException(402, "Subscription required — your trial has ended.")
    if not ent.get(metric if metric != "ai" else "ai_followup", False):
        raise HTTPException(403, f"{metric} is not available on your plan")
    limit = ent.get(f"{metric}_limit")
    period = ent.get(f"{metric}_period", "month")
    used = await get_usage(user["id"], metric, period)
    if limit is not None and used >= limit:
        raise HTTPException(429, f"You've reached your {metric} limit ({limit}/{period}) for the {ent['plan']} plan.")
    return ent, period


# ------------------------------------------------------------------ abuse protection (rate limiting + login lockout)
_RL_BUCKETS: dict = {}


def client_ip(request) -> str:
    xff = request.headers.get("x-forwarded-for", "") if request else ""
    if xff:
        return xff.split(",")[0].strip()
    return (request.client.host if (request and request.client) else "unknown")


def rate_limit(request, bucket: str, limit: int, window_sec: int):
    """Lightweight in-memory sliding-window per-IP limiter. Raises 429 with Retry-After.
    Additive abuse protection; does not touch auth/session architecture."""
    import time
    ip = client_ip(request)
    key = f"{bucket}:{ip}"
    now = time.time()
    hits = [t for t in _RL_BUCKETS.get(key, []) if now - t < window_sec]
    if len(hits) >= limit:
        retry = int(window_sec - (now - hits[0])) + 1
        raise HTTPException(429, "Too many requests. Please slow down and try again shortly.",
                            headers={"Retry-After": str(max(1, retry))})
    hits.append(now)
    _RL_BUCKETS[key] = hits


LOGIN_MAX_FAILS = 5
LOGIN_LOCK_MIN = 15


async def login_locked(email: str, ip: str):
    rec = await db.login_attempts.find_one({"identifier": f"{ip}:{email}"}, {"_id": 0})
    if rec and rec.get("fails", 0) >= LOGIN_MAX_FAILS and (rec.get("locked_until") or "") > now_iso():
        return rec.get("locked_until")
    return None


async def record_login_fail(email: str, ip: str):
    ident = f"{ip}:{email}"
    rec = await db.login_attempts.find_one({"identifier": ident}, {"_id": 0}) or {"fails": 0}
    fails = rec.get("fails", 0) + 1
    upd = {"identifier": ident, "fails": fails, "updated_at": now_iso()}
    if fails >= LOGIN_MAX_FAILS:
        upd["locked_until"] = (datetime.now(timezone.utc) + timedelta(minutes=LOGIN_LOCK_MIN)).isoformat()
    await db.login_attempts.update_one({"identifier": ident}, {"$set": upd}, upsert=True)
    logger.warning(f"[security] failed login #{fails} for {email} from {ip}")


async def clear_login_fails(email: str, ip: str):
    await db.login_attempts.delete_one({"identifier": f"{ip}:{email}"})


# ------------------------------------------------------------------ Team-tier plan gating (uses existing entitlement engine)
async def require_team(user: dict, wid: str):
    if user.get("role") == "SUPER_ADMIN":
        return
    ent = await resolve_entitlements(wid)
    if not ent.get("team"):
        raise HTTPException(402, "Team features require a Team plan. Upgrade to add members, import, or lock company branding.")


async def enforce_seat_limit(user: dict, wid: str):
    if user.get("role") == "SUPER_ADMIN":
        return
    ent = await resolve_entitlements(wid)
    seats = ent.get("seats") or 0
    if seats:
        active = await db.memberships.count_documents({"workspace_id": wid, "status": {"$ne": "deactivated"}})
        if active >= seats:
            raise HTTPException(402, f"You've used all {seats} seat(s) on your plan. Add seats to invite more members.")



# ------------------------------------------------------------------ Commercial Core: billing (provider-neutral — NO real payment)
# Legacy static fallback (kept for safety); the authoritative source is the DB-backed commercial_config.
PRICES = {
    "pro": {"month": 9.99, "year": 99.99},
    "team": {"month": 5.0, "year": 50.0, "min_seats": 3},
}

# Demo/test activation guard. In preview this allows the internal provider-neutral endpoint to
# activate a plan WITHOUT a real payment. When a real payment provider becomes the authoritative
# activation source, set ALLOW_DEMO_BILLING=false (or connect the provider) to disable this path.
ALLOW_DEMO_BILLING = os.environ.get("ALLOW_DEMO_BILLING", "true").lower() in ("1", "true", "yes")

# Commercial pricing / trial / referral are Super-Admin configurable (DB-backed, no code changes).
COMMERCIAL_MARKETS = ["USD", "AED", "SAR", "EUR", "GBP"]
_MARKET_SYMBOL = {"USD": "$", "AED": "AED ", "SAR": "SAR ", "EUR": "€", "GBP": "£"}

DEFAULT_COMMERCIAL_CONFIG = {
    "id": "global",
    "trial": {"enabled": True, "days": 14},
    "plans": {
        "pro": {"price_month": 9.99, "price_year": 99.99, "annual_discount_pct": 17},
        "team": {"price_seat_month": 5.0, "price_seat_year": 50.0, "min_seats": 3, "annual_discount_pct": 17},
    },
    "referral": {
        "enabled": True,
        "referred_discount_month_pct": 20,
        "referred_discount_year_pct": 20,
        "referrals_per_reward": 5,
        "reward_type": "free_month",
        "reward_months": 1,
    },
    "default_market": "USD",
    "regional_pricing": {
        "USD": {"symbol": "$", "pro_month": 9.99, "pro_year": 99.99, "team_seat_month": 5.0, "team_seat_year": 50.0},
        "AED": {"symbol": "AED ", "pro_month": 36.99, "pro_year": 369.99, "team_seat_month": 18.0, "team_seat_year": 180.0},
        "SAR": {"symbol": "SAR ", "pro_month": 37.99, "pro_year": 379.99, "team_seat_month": 19.0, "team_seat_year": 190.0},
        "EUR": {"symbol": "€", "pro_month": 9.99, "pro_year": 99.99, "team_seat_month": 5.0, "team_seat_year": 50.0},
        "GBP": {"symbol": "£", "pro_month": 8.99, "pro_year": 89.99, "team_seat_month": 4.5, "team_seat_year": 45.0},
    },
}


def _deep_merge(base: dict, patch: dict) -> dict:
    out = dict(base)
    for k, v in (patch or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


async def get_commercial_config() -> dict:
    """Single source of truth for commercial config. Seeds defaults if absent; always returns a full doc."""
    doc = await db.commercial_config.find_one({"id": "global"}, {"_id": 0})
    if not doc:
        await db.commercial_config.insert_one(dict(DEFAULT_COMMERCIAL_CONFIG))
        return dict(DEFAULT_COMMERCIAL_CONFIG)
    # merge over defaults so newly added keys always resolve
    return _deep_merge(DEFAULT_COMMERCIAL_CONFIG, doc)


async def trial_days() -> int:
    cfg = await get_commercial_config()
    tr = cfg.get("trial", {})
    return int(tr.get("days", TRIAL_DAYS)) if tr.get("enabled", True) else 0


def _annual_savings_pct(monthly, yearly) -> int:
    try:
        m, y = float(monthly or 0), float(yearly or 0)
        if m > 0 and y > 0 and m * 12 > 0:
            return max(0, round((1 - (y / (m * 12))) * 100))
    except (TypeError, ValueError):
        pass
    return 0


def resolve_market_pricing(cfg: dict, market: str) -> dict:
    market = (market or cfg.get("default_market") or "USD").upper()
    rp = (cfg.get("regional_pricing") or {}).get(market)
    if not rp:
        market = cfg.get("default_market", "USD")
        rp = (cfg.get("regional_pricing") or {}).get(market, DEFAULT_COMMERCIAL_CONFIG["regional_pricing"]["USD"])
    out = {"market": market, "symbol": rp.get("symbol", _MARKET_SYMBOL.get(market, "")), **rp}
    # annual savings are DERIVED from the configured monthly vs annual prices (never hard-coded)
    out["pro_annual_savings_pct"] = _annual_savings_pct(rp.get("pro_month"), rp.get("pro_year"))
    out["team_annual_savings_pct"] = _annual_savings_pct(rp.get("team_seat_month"), rp.get("team_seat_year"))
    return out


class SubscribeIn(BaseModel):
    plan: str
    interval: str = "month"  # month | year
    seats: int = 1
    market: Optional[str] = None


async def _primary_ws_id(user: dict):
    ms = await memberships_for(user["id"])
    owned = next((m for m in ms if m.get("role") == "WORKSPACE_OWNER"), None)
    return (owned or (ms[0] if ms else {})).get("workspace_id")


@platform_router.get("/billing")
async def get_billing(user: dict = Depends(current_user), market: Optional[str] = None):
    ws_id = await _primary_ws_id(user)
    if not ws_id:
        raise HTTPException(404, "No workspace")
    ent = await resolve_entitlements(ws_id)
    ai_used = await get_usage(user["id"], "ai", ent.get("ai_period", "month"))
    sc_used = await get_usage(user["id"], "scanner", ent.get("scanner_period", "month"))
    cfg = await get_commercial_config()
    ws = await db.workspaces.find_one({"id": ws_id}, {"_id": 0, "region": 1, "subscription": 1, "referral_rewards": 1})
    mk = market or ((ws or {}).get("region") or {}).get("default_currency") or cfg.get("default_market", "USD")
    pricing = resolve_market_pricing(cfg, mk)
    cards_used = await db.digital_cards.count_documents({"workspace_id": ws_id})
    # referral discounts: referred-customer discount on their price + referrer reward on their own bill
    referred = ((ws or {}).get("subscription") or {}).get("referral") or {}
    reward = (ws or {}).get("referral_rewards") or {}
    discount = {
        "referred_month_pct": float(referred.get("discount_month_pct", 0)) if referred else 0,
        "referred_year_pct": float(referred.get("discount_year_pct", 0)) if referred else 0,
        "free_months_earned": int(reward.get("free_months_earned", 0)),
        "free_months_available": int(reward.get("free_months_available", 0)),
    }
    return {
        "plan": ent["plan"], "status": ent["status"], "active": ent["active"],
        "trial_ends_at": ent.get("trial_ends_at"), "current_period_end": ent.get("current_period_end"),
        "seats": ent.get("seats"), "entitlements": ent,
        "commercial": {"trial": cfg["trial"], "plans": cfg["plans"], "referral": cfg["referral"],
                       "pricing": pricing, "markets": COMMERCIAL_MARKETS},
        "discount": discount,
        "demo_billing": ALLOW_DEMO_BILLING,
        "usage": {"ai": {"used": ai_used, "limit": ent.get("ai_limit"), "period": ent.get("ai_period")},
                  "scanner": {"used": sc_used, "limit": ent.get("scanner_limit"), "period": ent.get("scanner_period")},
                  "cards": {"used": cards_used, "limit": ent.get("max_cards")}},
    }


@platform_router.get("/commercial/pricing")
async def commercial_pricing(market: Optional[str] = None):
    """Public resolved pricing for a market — for the billing page + marketing pricing."""
    cfg = await get_commercial_config()
    return {
        "trial": cfg["trial"], "plans": cfg["plans"], "referral": cfg["referral"],
        "pricing": resolve_market_pricing(cfg, market),
        "markets": COMMERCIAL_MARKETS,
        "all_regional": cfg["regional_pricing"],
    }


@platform_router.post("/billing/subscribe")
async def subscribe(body: SubscribeIn, user: dict = Depends(current_user)):
    """Provider-neutral activation. Does NOT connect a real payment provider (deferred).
    Reactivates the SAME card/URL/QR/NFC by flipping subscription to active.
    Demo/test path only — guarded by ALLOW_DEMO_BILLING; the future payment provider is the authoritative source."""
    if not ALLOW_DEMO_BILLING:
        raise HTTPException(402, "Payment required. Activation must be completed through the payment provider.")
    ws_id = await _primary_ws_id(user)
    await require_ws_admin(user, ws_id)
    if body.plan not in ("pro", "team", "enterprise"):
        raise HTTPException(400, "Invalid plan")
    if body.interval not in ("month", "year"):
        raise HTTPException(400, "Invalid interval")
    cfg = await get_commercial_config()
    seats = 1
    if body.plan == "team":
        min_seats = int(cfg["plans"]["team"].get("min_seats", 3))
        seats = max(int(body.seats or min_seats), min_seats)
    days = 365 if body.interval == "year" else 30
    prior = await db.workspaces.find_one({"id": ws_id}, {"_id": 0, "subscription": 1})
    sub = {"plan": body.plan, "status": "active", "interval": body.interval, "seats": seats,
           "market": (body.market or cfg.get("default_market", "USD")).upper(),
           "trial_ends_at": None,
           "current_period_end": (datetime.now(timezone.utc) + timedelta(days=days)).isoformat(),
           "activation": "demo", "updated_at": now_iso()}
    # preserve referred-customer discount linkage across activation
    _rf = ((prior or {}).get("subscription") or {}).get("referral")
    if _rf:
        sub["referral"] = _rf
    await db.workspaces.update_one({"id": ws_id}, {"$set": {"subscription": sub, "plan": body.plan}})
    # DEMO billing: activating a paid plan is treated as a verified paid-subscription event.
    # When Stripe is connected, this same hook is invoked from the verified webhook instead.
    if body.plan in ("pro", "team"):
        await record_paid_subscription_event(ws_id, source="demo")
    return {"ok": True, "subscription": sub, "entitlements": await resolve_entitlements(ws_id)}


@platform_router.get("/referral")
async def get_referral(user: dict = Depends(current_user)):
    """Internal referral program surface — my code, referred accounts, reward ledger. No real billing."""
    ws_id = await _primary_ws_id(user)
    if not ws_id:
        raise HTTPException(404, "No workspace")
    ws = await db.workspaces.find_one({"id": ws_id}, {"_id": 0})
    if not ws:
        raise HTTPException(404, "No workspace")
    code = await _ensure_referral_code(ws)
    cfg = await get_commercial_config()
    ref_cfg = cfg.get("referral", {})
    per = max(1, int(ref_cfg.get("referrals_per_reward", 5)))
    months = max(1, int(ref_cfg.get("reward_months", 1)))
    referrals = await db.referrals.find({"referrer_ws_id": ws_id}, {"_id": 0, "referred_email": 0}).to_list(1000)
    signed_up = [r for r in referrals if r.get("status") == "signed_up"]
    qualified = [r for r in referrals if r.get("status") == "qualified"]
    ledger = await _recompute_referral_rewards(ws_id)
    my_ref = ((ws.get("subscription") or {}).get("referral")) or None
    share_url = f"{PUBLIC_APP_URL}/register?ref={code}"
    return {
        "enabled": bool(ref_cfg.get("enabled")),
        "code": code, "share_url": share_url,
        "config": {"referrals_per_reward": per, "reward_months": months, "reward_type": ref_cfg.get("reward_type", "free_month"),
                   "referred_discount_month_pct": ref_cfg.get("referred_discount_month_pct", 0),
                   "referred_discount_year_pct": ref_cfg.get("referred_discount_year_pct", 0)},
        "counts": {"total": len(referrals), "signed_up": len(signed_up), "qualified": len(qualified)},
        "reward": ledger,
        "referred_as": my_ref,
    }


@platform_router.get("/referral/qr")
async def referral_qr(code: str):
    """Public QR PNG for a referral invite link (code is shareable, not secret). Reuses referral_code."""
    import qrcode
    code = (code or "").strip().upper()
    if not code or not await db.workspaces.find_one({"referral_code": code}, {"_id": 1}):
        raise HTTPException(404, "Unknown code")
    url = f"{PUBLIC_APP_URL}/register?ref={code}" if PUBLIC_APP_URL else f"/register?ref={code}"
    qr = qrcode.QRCode(version=None, box_size=10, border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0A0B0D", back_color="#FAFAF8")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")


@platform_router.post("/billing/cancel")
async def cancel_subscription(user: dict = Depends(current_user)):
    ws_id = await _primary_ws_id(user)
    await require_ws_admin(user, ws_id)
    await db.workspaces.update_one({"id": ws_id}, {"$set": {"subscription.status": "cancel_at_period_end", "subscription.updated_at": now_iso()}})
    return {"ok": True, "status": "cancel_at_period_end"}


async def audit(workspace_id, actor_id, action, meta=None):
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()), "workspace_id": workspace_id, "actor_id": actor_id,
        "action": action, "meta": meta or {}, "created_at": now_iso(),
    })

# ------------------------------------------------------------------ config / feature flags
def _configured(*keys):
    return all(bool(os.environ.get(k, "").strip()) for k in keys)


@platform_router.get("/config")
async def get_config():
    """Public config: which integrations are live vs 'Not Configured'."""
    return {
        "integrations": {
            "stripe": _configured("STRIPE_SECRET_KEY"),
            "apple_wallet": _configured("APPLE_WALLET_CERT_B64", "APPLE_WALLET_TEAM_ID"),
            "google_wallet": _configured("GOOGLE_WALLET_ISSUER_ID", "GOOGLE_WALLET_SA_JSON"),
            "apple_signin": _configured("APPLE_OAUTH_CLIENT_ID"),
            "google_signin": _configured("GOOGLE_OAUTH_CLIENT_ID"),
            "email": _configured("EMAIL_API_KEY"),
            "enrichment": _configured("ENRICHMENT_API_KEY"),
            "revenuecat": _configured("REVENUECAT_API_KEY"),
            "hubspot": _configured("HUBSPOT_CLIENT_ID"),
            "salesforce": _configured("SALESFORCE_CLIENT_ID"),
            "pipedrive": _configured("PIPEDRIVE_CLIENT_ID"),
            "ai": _configured("EMERGENT_LLM_KEY"),
            "push": _configured("PUSH_FCM_KEY"),
            "error_monitoring": _configured("SENTRY_DSN"),
        },
        "public_app_url": PUBLIC_APP_URL,
        "languages": ["en", "ar", "es"],
    }


@platform_router.get("/health")
async def health():
    """Lightweight production health probe. Never exposes secrets or connection strings."""
    db_ok = True
    try:
        await db.command("ping")
    except Exception:
        db_ok = False
    status = "ok" if db_ok else "degraded"
    return {"status": status, "db": db_ok, "time": now_iso()}

# ------------------------------------------------------------------ auth models
class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    name: str = ""
    workspace_name: str = ""
    country_code: str = "US"
    language: str = "en"
    timezone: str = ""
    currency: str = ""
    referral_code: Optional[str] = None


class RefreshIn(BaseModel):
    refresh_token: str


class ForgotIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    token: str
    password: str


class VerifyIn(BaseModel):
    token: str


async def _gen_referral_code() -> str:
    for _ in range(10):
        code = secrets.token_hex(4).upper()  # 8 hex chars
        if not await db.workspaces.find_one({"referral_code": code}, {"_id": 1}):
            return code
    return uuid.uuid4().hex[:10].upper()


async def _ensure_referral_code(ws: dict) -> str:
    if ws.get("referral_code"):
        return ws["referral_code"]
    code = await _gen_referral_code()
    await db.workspaces.update_one({"id": ws["id"]}, {"$set": {"referral_code": code}})
    return code


async def _apply_referral(code: Optional[str], referred_email: str, referred_ws_id: str, referred_uid: str):
    """Internal, provider-neutral referral ATTRIBUTION at signup.
    Stores the referred NEW-CUSTOMER discount (preserved) and records a referral in status
    'signed_up'. NO referrer reward is credited here — the referrer only earns progress when the
    referred user becomes a QUALIFIED PAID referral (see _qualify_referral, called on paid activation)."""
    if not code:
        return
    cfg = await get_commercial_config()
    ref = cfg.get("referral", {})
    if not ref.get("enabled"):
        return
    referrer_ws = await db.workspaces.find_one({"referral_code": code.strip().upper()}, {"_id": 0})
    if not referrer_ws:
        return
    # anti self-referral: not same workspace, not same account owner
    if referrer_ws["id"] == referred_ws_id:
        return
    owner = await db.users.find_one({"id": referrer_ws.get("owner_id")}, {"_id": 0, "email": 1})
    if owner and owner.get("email", "").lower() == referred_email.lower():
        return
    if await db.referrals.find_one({"referred_ws_id": referred_ws_id}):
        return  # a workspace can only be referred once
    # referred-customer signup discount stored on their subscription (PRESERVED behavior)
    dmo = float(ref.get("referred_discount_month_pct", 0))
    dyr = float(ref.get("referred_discount_year_pct", 0))
    await db.workspaces.update_one({"id": referred_ws_id}, {"$set": {
        "subscription.referral": {"referrer_code": code.strip().upper(), "referrer_ws_id": referrer_ws["id"],
                                  "discount_month_pct": dmo, "discount_year_pct": dyr}}})
    # record referral in SIGNED_UP state — does not count toward the reward yet
    await db.referrals.insert_one({
        "id": str(uuid.uuid4()), "code": code.strip().upper(),
        "referrer_ws_id": referrer_ws["id"], "referrer_user_id": referrer_ws.get("owner_id"),
        "referred_ws_id": referred_ws_id, "referred_user_id": referred_uid, "referred_email": referred_email,
        "referred_discount_month_pct": dmo, "referred_discount_year_pct": dyr,
        "status": "signed_up", "qualified_at": None, "created_at": now_iso(),
    })
    await _recompute_referral_rewards(referrer_ws["id"])


async def _recompute_referral_rewards(referrer_ws_id: str):
    """Derives the referrer reward ledger from QUALIFIED paid referrals. Idempotent:
    free months = floor(qualified / referrals_per_reward). Creates one durable grant record per
    earned free month (unique per referrer+index) so live billing can redeem them exactly once."""
    cfg = await get_commercial_config()
    ref = cfg.get("referral", {})
    per = max(1, int(ref.get("referrals_per_reward", 5)))
    months = max(1, int(ref.get("reward_months", 1)))
    qualified = await db.referrals.count_documents({"referrer_ws_id": referrer_ws_id, "status": "qualified"})
    signed_up = await db.referrals.count_documents({"referrer_ws_id": referrer_ws_id, "status": "signed_up"})
    earned = (qualified // per) * months
    # create durable, idempotent grant records for any newly earned free months (excluding voided)
    existing = await db.referral_reward_grants.count_documents({"referrer_ws_id": referrer_ws_id, "voided": {"$ne": True}})
    for i in range(existing, earned):
        try:
            await db.referral_reward_grants.insert_one({
                "id": str(uuid.uuid4()), "referrer_ws_id": referrer_ws_id, "index": i + 1,
                "months": 1, "reward_type": "free_month", "redeemed": False, "redeemed_at": None,
                "voided": False, "source": "referral", "earned_at": now_iso(),
            })
        except Exception:
            pass  # unique index guards against double insert
    redeemed = await db.referral_reward_grants.count_documents({"referrer_ws_id": referrer_ws_id, "redeemed": True, "voided": {"$ne": True}})
    ledger = {
        "qualified_count": qualified,
        "signed_up_count": signed_up,
        "per_reward": per,
        "reward_months": months,
        "free_months_earned": earned,
        "free_months_redeemed": redeemed,
        "free_months_available": max(0, earned - redeemed),
        "progress": qualified % per,
    }
    await db.workspaces.update_one({"id": referrer_ws_id}, {"$set": {"referral_rewards": ledger}})
    return ledger


async def _qualify_referral(referred_ws_id: str, source: str = "unknown", event_id: Optional[str] = None):
    """Marks a referral as a QUALIFIED PAID referral exactly once (idempotent via status guard),
    then recomputes the referrer's reward ledger. Called only from record_paid_subscription_event
    (a verified successful paid-subscription event) — never directly from checkout initiation."""
    r = await db.referrals.find_one({"referred_ws_id": referred_ws_id}, {"_id": 0})
    if not r or r.get("status") == "qualified":
        return
    res = await db.referrals.update_one(
        {"id": r["id"], "status": {"$ne": "qualified"}},
        {"$set": {"status": "qualified", "qualified_at": now_iso(),
                  "qualification_source": source, "qualification_event_id": event_id}},
    )
    if res.modified_count:
        await _recompute_referral_rewards(r["referrer_ws_id"])


async def record_paid_subscription_event(ws_id: str, source: str, event_id: Optional[str] = None):
    """SINGLE idempotent entry point for a VERIFIED successful PAID subscription.
    Pipeline stage separation (signup → trial → checkout initiation → SUCCESSFUL PAID → qualified → grant):
    a referral becomes qualified ONLY here, never on checkout initiation. Demo billing passes
    source='demo'; a future Stripe webhook passes source='stripe' + the Stripe event id.
    Deduplicated via the billing_events collection so replays/retries cannot double-count."""
    key = event_id or f"{source}:{ws_id}"
    if await db.billing_events.find_one({"key": key}):
        return False
    try:
        await db.billing_events.insert_one({
            "id": str(uuid.uuid4()), "key": key, "ws_id": ws_id, "source": source,
            "type": "paid_subscription_active", "created_at": now_iso(),
        })
    except Exception:
        return False  # unique index guards against a race
    await _qualify_referral(ws_id, source=source, event_id=event_id)
    return True


async def revoke_referral_qualification(ws_id: str, reason: str):
    """FUTURE refund/chargeback safety hook (NOT wired to any provider yet). When a paid
    subscription is later refunded/charged back within an eligibility window (policy TBD, pending
    approval), this un-qualifies the referral and voids the newest UNREDEEMED reward grant so a
    fraudulent/refunded subscription cannot yield a permanent free month. Redeemed grants are never
    silently revoked. Idempotent."""
    r = await db.referrals.find_one({"referred_ws_id": ws_id}, {"_id": 0})
    if not r or r.get("status") != "qualified":
        return False
    await db.referrals.update_one({"id": r["id"]}, {"$set": {"status": "revoked", "revoked_at": now_iso(), "revoke_reason": reason}})
    # void the highest-index unredeemed grant for the referrer (do not touch redeemed grants)
    grant = await db.referral_reward_grants.find_one({"referrer_ws_id": r["referrer_ws_id"], "redeemed": False}, sort=[("index", -1)])
    if grant:
        await db.referral_reward_grants.update_one({"id": grant["id"]}, {"$set": {"voided": True, "voided_at": now_iso(), "void_reason": reason}})
    await _recompute_referral_rewards(r["referrer_ws_id"])
    return True


async def _issue_session(user, request: Request):
    access = make_token(user["id"], "access", minutes=60 * 24 * 7, extra={"email": user["email"]})
    refresh = secrets.token_urlsafe(48)
    await db.sessions.insert_one({
        "id": str(uuid.uuid4()), "user_id": user["id"], "refresh": refresh,
        "user_agent": request.headers.get("user-agent", "")[:200], "revoked": False,
        "created_at": now_iso(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
    })
    return access, refresh


async def _auth_payload(user, request):
    access, refresh = await _issue_session(user, request)
    ms = await memberships_for(user["id"])
    ws_id = ms[0]["workspace_id"] if ms else None
    ent = await resolve_entitlements(ws_id) if ws_id else PLAN_ENTITLEMENTS["free"]
    ws = await db.workspaces.find_one({"id": ws_id}, {"_id": 0}) if ws_id else None
    return {
        "token": access, "refresh_token": refresh,
        "user": {"id": user["id"], "email": user["email"], "name": user.get("name", ""),
                 "role": user.get("role", "MEMBER"), "email_verified": user.get("email_verified", False),
                 "language": user.get("language", "en"), "locale": user.get("locale", "en-US"),
                 "timezone": user.get("timezone", "UTC")},
        "workspace": ws, "memberships": ms, "entitlements": ent,
    }


@platform_router.post("/auth/register")
async def register(body: RegisterIn, request: Request):
    rate_limit(request, "register", 40, 3600)
    email = body.email.strip().lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(400, "An account with this email already exists")
    uid = str(uuid.uuid4())
    verify_token = secrets.token_urlsafe(32)
    lang = body.language if body.language in SUPPORTED_LANGUAGES else "en"
    region = default_region(body.country_code if body.country_code else "US")
    if body.currency in SUPPORTED_CURRENCIES:
        region["default_currency"] = body.currency
    if body.timezone:
        region["timezone"] = body.timezone
    region["default_language"] = lang
    user = {
        "id": uid, "email": email, "password_hash": hash_pw(body.password),
        "name": body.name.strip(), "role": "WORKSPACE_OWNER", "email_verified": False,
        "language": lang, "locale": region["locale"], "timezone": region["timezone"],
        "created_at": now_iso(),
    }
    await db.users.insert_one(user)
    ws_id = str(uuid.uuid4())
    _tdays = await trial_days()
    if _tdays > 0:
        _sub = {"plan": "trial", "status": "trialing",
                "trial_ends_at": (datetime.now(timezone.utc) + timedelta(days=_tdays)).isoformat(),
                "current_period_end": None, "seats": 1, "interval": None}
        _plan = "trial"
    else:
        # trials disabled by Super Admin — start locked until subscribed
        _sub = {"plan": "trial", "status": "trial_expired",
                "trial_ends_at": now_iso(), "current_period_end": None, "seats": 1, "interval": None}
        _plan = "trial"
    await db.workspaces.insert_one({
        "id": ws_id, "name": body.workspace_name.strip() or (body.name.strip() or "My Workspace"),
        "type": "individual", "plan": _plan, "owner_id": uid,
        "subscription": _sub,
        "referral_code": await _gen_referral_code(),
        "region": region, "tax": {"tax_country": region["country_code"], "tax_inclusive": False,
                                   "tax_id": "", "status": "unregistered"},
        "branding": {}, "locked_fields": [], "created_at": now_iso(),
    })
    await db.memberships.insert_one({
        "id": str(uuid.uuid4()), "user_id": uid, "workspace_id": ws_id,
        "role": "WORKSPACE_OWNER", "status": "active", "created_at": now_iso(),
    })
    await _apply_referral(body.referral_code, email, ws_id, uid)
    await db.email_verifications.insert_one({
        "id": str(uuid.uuid4()), "user_id": uid, "token": verify_token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(), "used": False,
    })
    # Email adapter: send if configured, else log verification link (dev).
    link = f"{PUBLIC_APP_URL}/verify?token={verify_token}"
    if _configured("EMAIL_API_KEY"):
        logger.info(f"[email] would send verification to {email}")  # provider adapter hook
    else:
        logger.info(f"[email:NOT_CONFIGURED] verification link for {email}: {link}")
    await audit(ws_id, uid, "account.register")
    return await _auth_payload(user, request)


@platform_router.post("/auth/verify-email")
async def verify_email(body: VerifyIn):
    rec = await db.email_verifications.find_one({"token": body.token, "used": False})
    if not rec or rec["expires_at"] < now_iso():
        raise HTTPException(400, "Invalid or expired verification token")
    await db.users.update_one({"id": rec["user_id"]}, {"$set": {"email_verified": True}})
    await db.email_verifications.update_one({"id": rec["id"]}, {"$set": {"used": True}})
    return {"ok": True}


@platform_router.post("/auth/resend-verification")
async def resend_verification(request: Request, user: dict = Depends(current_user)):
    rate_limit(request, "resend_verify", 5, 3600)
    if user.get("email_verified"):
        return {"ok": True, "already_verified": True}
    token = secrets.token_urlsafe(32)
    await db.email_verifications.insert_one({
        "id": str(uuid.uuid4()), "user_id": user["id"], "token": token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(), "used": False,
    })
    link = f"{PUBLIC_APP_URL}/verify?token={token}"
    if _configured("EMAIL_API_KEY"):
        logger.info(f"[email] would resend verification to {user['email']}")
    else:
        logger.info(f"[email:NOT_CONFIGURED] verification link for {user['email']}: {link}")
    return {"ok": True}


@platform_router.post("/auth/refresh")
async def refresh(body: RefreshIn, request: Request):
    sess = await db.sessions.find_one({"refresh": body.refresh_token, "revoked": False})
    if not sess or sess["expires_at"] < now_iso():
        raise HTTPException(401, "Invalid or expired refresh token")
    user = await db.users.find_one({"id": sess["user_id"]}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(401, "User not found")
    # rotate
    await db.sessions.update_one({"id": sess["id"]}, {"$set": {"revoked": True}})
    return await _auth_payload(user, request)


@platform_router.post("/auth/forgot-password")
async def forgot(body: ForgotIn, request: Request):
    rate_limit(request, "forgot", 6, 3600)
    email = body.email.strip().lower()
    user = await db.users.find_one({"email": email})
    if user:
        token = secrets.token_urlsafe(32)
        await db.password_resets.insert_one({
            "id": str(uuid.uuid4()), "user_id": user["id"], "token": token,
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(), "used": False,
        })
        link = f"{PUBLIC_APP_URL}/reset?token={token}"
        logger.info(f"[email{'' if _configured('EMAIL_API_KEY') else ':NOT_CONFIGURED'}] reset link for {email}: {link}")
    return {"ok": True}  # do not reveal account existence


@platform_router.post("/auth/reset-password")
async def reset(body: ResetIn, request: Request):
    rate_limit(request, "reset", 10, 3600)
    rec = await db.password_resets.find_one({"token": body.token, "used": False})
    if not rec or rec["expires_at"] < now_iso():
        raise HTTPException(400, "Invalid or expired reset token")
    await db.users.update_one({"id": rec["user_id"]}, {"$set": {"password_hash": hash_pw(body.password)}})
    await db.password_resets.update_one({"id": rec["id"]}, {"$set": {"used": True}})
    await db.sessions.update_many({"user_id": rec["user_id"]}, {"$set": {"revoked": True}})
    return {"ok": True}


@platform_router.get("/auth/session")
async def session_info(user: dict = Depends(current_user)):
    ms = await memberships_for(user["id"])
    ws_id = ms[0]["workspace_id"] if ms else None
    ws = await db.workspaces.find_one({"id": ws_id}, {"_id": 0}) if ws_id else None
    ent = await resolve_entitlements(ws_id) if ws_id else PLAN_ENTITLEMENTS["free"]
    return {"user": user, "workspace": ws, "memberships": ms, "entitlements": ent}


@platform_router.get("/auth/sessions")
async def list_sessions(user: dict = Depends(current_user)):
    return await db.sessions.find({"user_id": user["id"], "revoked": False}, {"_id": 0, "refresh": 0}).to_list(100)


@platform_router.delete("/auth/sessions/{session_id}")
async def revoke_session(session_id: str, user: dict = Depends(current_user)):
    await db.sessions.update_one({"id": session_id, "user_id": user["id"]}, {"$set": {"revoked": True}})
    return {"ok": True}


@platform_router.post("/auth/logout")
async def logout(body: RefreshIn):
    await db.sessions.update_one({"refresh": body.refresh_token}, {"$set": {"revoked": True}})
    return {"ok": True}


@platform_router.delete("/account")
async def delete_account(user: dict = Depends(current_user)):
    """Irreversibly delete the account. Deletes workspaces the user OWNS and all their data
    (cards, leads, analytics, notifications, meetings, referrals, usage, api-keys, webhooks).
    For workspaces merely SHARED with the user, only their membership is removed — other
    members' data is preserved. Cross-member data is never deleted here."""
    uid = user["id"]
    all_ms = await memberships_for(uid)
    all_ws_ids = [m["workspace_id"] for m in all_ms]
    owned = await db.workspaces.find({"id": {"$in": all_ws_ids}, "owner_id": uid}, {"_id": 0, "id": 1}).to_list(1000)
    owned_ws_ids = [w["id"] for w in owned]
    if owned_ws_ids:
        owned_cards = await db.digital_cards.find({"workspace_id": {"$in": owned_ws_ids}}, {"_id": 0, "slug": 1}).to_list(5000)
        slugs = [c["slug"] for c in owned_cards if c.get("slug")]
        await db.leads.delete_many({"$or": [{"workspace_id": {"$in": owned_ws_ids}}, {"cardSlug": {"$in": slugs}}]})
        if slugs:
            await db.analytics_events.delete_many({"cardSlug": {"$in": slugs}})
        await db.notifications.delete_many({"workspace_id": {"$in": owned_ws_ids}})
        await db.meetings.delete_many({"workspace_id": {"$in": owned_ws_ids}})
        await db.digital_cards.delete_many({"workspace_id": {"$in": owned_ws_ids}})
        await db.referrals.delete_many({"$or": [{"referrer_ws_id": {"$in": owned_ws_ids}}, {"referred_ws_id": {"$in": owned_ws_ids}}]})
        await db.api_keys.delete_many({"workspace_id": {"$in": owned_ws_ids}})
        await db.webhooks.delete_many({"workspace_id": {"$in": owned_ws_ids}})
        await db.memberships.delete_many({"workspace_id": {"$in": owned_ws_ids}})
        await db.workspaces.delete_many({"id": {"$in": owned_ws_ids}})
    # remove only THIS user's membership from any shared workspaces (preserve others' data)
    await db.memberships.delete_many({"user_id": uid})
    await db.usage_counters.delete_many({"subject_id": uid})
    await db.ai_usage.delete_many({"user_id": uid})
    await db.sessions.delete_many({"user_id": uid})
    await db.email_verifications.delete_many({"user_id": uid})
    await db.password_resets.delete_many({"user_id": uid})
    await db.users.delete_one({"id": uid})
    return {"ok": True, "deleted_workspaces": len(owned_ws_ids)}


@platform_router.get("/account/export")
async def export_account(user: dict = Depends(current_user)):
    ws_ids = await workspace_ids_for(user)
    q = {} if ws_ids == "ALL" else {"workspace_id": {"$in": ws_ids}}
    cards = await db.digital_cards.find(q, {"_id": 0}).to_list(1000)
    slugs = [c["slug"] for c in cards]
    leads = await db.leads.find({"cardSlug": {"$in": slugs}}, {"_id": 0}).to_list(5000)
    return {"user": user, "cards": cards, "leads": leads, "exported_at": now_iso()}

# ------------------------------------------------------------------ plans / entitlements
@platform_router.get("/plans")
async def list_plans():
    plans = await db.plans.find({}, {"_id": 0}).to_list(50)
    return plans or DEFAULT_PLANS


@platform_router.put("/admin/plans/{plan_id}")
async def update_plan(plan_id: str, body: dict, user: dict = Depends(current_user)):
    if user.get("role") != "SUPER_ADMIN":
        raise HTTPException(403, "Super admin only")
    body.pop("_id", None)
    await db.plans.update_one({"id": plan_id}, {"$set": body}, upsert=True)
    return await db.plans.find_one({"id": plan_id}, {"_id": 0})


@platform_router.get("/workspaces/me")
async def my_workspaces(user: dict = Depends(current_user)):
    ms = await memberships_for(user["id"])
    ids = [m["workspace_id"] for m in ms]
    ws = await db.workspaces.find({"id": {"$in": ids}}, {"_id": 0}).to_list(100)
    return ws

# ------------------------------------------------------------------ NFC devices + tap redirect
class NfcActivateIn(BaseModel):
    token: str
    card_id: str


@platform_router.get("/t/{token}")
async def nfc_tap(token: str):
    """Permanent NFC redirect. Chip encodes /api/t/{token}; never rewrite the chip."""
    dev = await db.nfc_devices.find_one({"token": token})
    if not dev:
        raise HTTPException(404, "Unknown NFC token")
    await db.nfc_devices.update_one({"token": token}, {"$set": {"last_tap_at": now_iso()}})
    if dev["status"] == "ACTIVE" and dev.get("card_id"):
        card = await db.digital_cards.find_one({"id": dev["card_id"]}, {"_id": 0, "slug": 1})
        if card:
            await db.analytics_events.insert_one({
                "id": str(uuid.uuid4()), "cardSlug": card["slug"], "type": "nfctap",
                "key": token, "created_at": now_iso(),
            })
            return RedirectResponse(url=f"{PUBLIC_APP_URL}/{card['slug']}?src=nfc")
    # Not yet activated -> send to activation screen
    return RedirectResponse(url=f"{PUBLIC_APP_URL}/activate?token={token}")


@platform_router.get("/nfc/lookup/{token}")
async def nfc_lookup(token: str):
    dev = await db.nfc_devices.find_one({"token": token}, {"_id": 0})
    if not dev:
        raise HTTPException(404, "Unknown NFC token")
    return {"token": dev["token"], "status": dev["status"], "assigned": bool(dev.get("card_id"))}


@platform_router.post("/nfc/activate")
async def nfc_activate(body: NfcActivateIn, user: dict = Depends(current_user)):
    dev = await db.nfc_devices.find_one({"token": body.token})
    if not dev:
        raise HTTPException(404, "Unknown NFC token")
    if dev["status"] in ("DEACTIVATED", "LOST"):
        raise HTTPException(400, "This card is deactivated")
    card = await db.digital_cards.find_one({"id": body.card_id})
    if not card:
        raise HTTPException(404, "Card not found")
    ws_ids = await workspace_ids_for(user)
    if ws_ids != "ALL" and card.get("workspace_id") not in ws_ids:
        raise HTTPException(403, "Not your card")
    await db.nfc_devices.update_one({"token": body.token}, {"$set": {
        "status": "ACTIVE", "card_id": body.card_id, "assigned_user_id": user["id"],
        "workspace_id": card.get("workspace_id"), "activated_at": now_iso(),
    }})
    await audit(card.get("workspace_id"), user["id"], "nfc.activate", {"token": body.token})
    return {"ok": True}


@platform_router.get("/nfc/devices")
async def list_nfc(user: dict = Depends(current_user)):
    ws_ids = await workspace_ids_for(user)
    q = {} if ws_ids == "ALL" else {"workspace_id": {"$in": ws_ids}}
    return await db.nfc_devices.find(q, {"_id": 0}).to_list(1000)


@platform_router.post("/nfc/devices/{token}/status")
async def nfc_status(token: str, body: dict, user: dict = Depends(current_user)):
    status = body.get("status")
    if status not in ("ACTIVE", "DEACTIVATED", "LOST", "REPLACED", "UNASSIGNED"):
        raise HTTPException(400, "Invalid status")
    dev = await db.nfc_devices.find_one({"token": token})
    if not dev:
        raise HTTPException(404, "Unknown token")
    ws_ids = await workspace_ids_for(user)
    if ws_ids != "ALL" and dev.get("workspace_id") not in ws_ids:
        raise HTTPException(403, "Not your device")
    upd = {"status": status}
    if status in ("DEACTIVATED", "LOST", "UNASSIGNED"):
        upd["card_id"] = None
    await db.nfc_devices.update_one({"token": token}, {"$set": upd})
    await audit(dev.get("workspace_id"), user["id"], "nfc.status", {"token": token, "status": status})
    return {"ok": True}


@platform_router.post("/admin/nfc/mint")
async def mint_nfc(body: dict, user: dict = Depends(current_user)):
    """SUPER_ADMIN mints inventory (simulates manufacturing)."""
    if user.get("role") != "SUPER_ADMIN":
        raise HTTPException(403, "Super admin only")
    count = int(body.get("count", 1))
    material = body.get("material", "standard")
    tokens = []
    for _ in range(min(count, 500)):
        token = secrets.token_urlsafe(6)
        await db.nfc_devices.insert_one({
            "id": str(uuid.uuid4()), "token": token, "serial": f"ARN-{secrets.token_hex(4).upper()}",
            "status": "UNASSIGNED", "material": material, "card_id": None, "workspace_id": None,
            "assigned_user_id": None, "created_at": now_iso(), "last_tap_at": None,
        })
        tokens.append(token)
    return {"minted": len(tokens), "tokens": tokens, "tap_base": f"{PUBLIC_APP_URL}/api/t/"}

# ------------------------------------------------------------------ CRM leads upgrade
class LeadUpdateIn(BaseModel):
    status: Optional[str] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    interest: Optional[str] = None
    next_follow_up: Optional[str] = None
    owner_id: Optional[str] = None
    read: Optional[bool] = None


LEAD_STATUSES = {"NEW", "CONTACTED", "QUALIFIED", "FOLLOW_UP", "WON", "LOST"}


async def _owned_slugs(user):
    ws_ids = await workspace_ids_for(user)
    q = {} if ws_ids == "ALL" else {"workspace_id": {"$in": ws_ids}}
    cards = await db.digital_cards.find(q, {"_id": 0, "slug": 1}).to_list(1000)
    return [c["slug"] for c in cards]


@platform_router.get("/crm/leads")
async def crm_leads(status: str = None, q: str = None, user: dict = Depends(current_user)):
    slugs = await _owned_slugs(user)
    query = {"cardSlug": {"$in": slugs}}
    if status:
        query["status"] = status
    leads = await db.leads.find(query, {"_id": 0}).sort("created_at", -1).to_list(2000)
    if q:
        ql = q.lower()
        leads = [l for l in leads if ql in (l.get("name", "") + l.get("email", "") + l.get("company", "")).lower()]
    return leads


@platform_router.patch("/crm/leads/{lead_id}")
async def crm_update_lead(lead_id: str, body: LeadUpdateIn, user: dict = Depends(current_user)):
    lead = await db.leads.find_one({"id": lead_id})
    if not lead:
        raise HTTPException(404, "Lead not found")
    slugs = await _owned_slugs(user)
    if lead["cardSlug"] not in slugs and user.get("role") != "SUPER_ADMIN":
        raise HTTPException(403, "Not your lead")
    upd = {k: v for k, v in body.model_dump().items() if v is not None}
    if "status" in upd and upd["status"] not in LEAD_STATUSES:
        raise HTTPException(400, "Invalid status")
    upd["updated_at"] = now_iso()
    upd["last_activity"] = now_iso()
    await db.leads.update_one({"id": lead_id}, {"$set": upd})
    await db.lead_activities.insert_one({
        "id": str(uuid.uuid4()), "lead_id": lead_id, "actor_id": user["id"],
        "change": upd, "created_at": now_iso(),
    })
    return await db.leads.find_one({"id": lead_id}, {"_id": 0})


@platform_router.get("/crm/leads/{lead_id}/activities")
async def lead_activities(lead_id: str, user: dict = Depends(current_user)):
    return await db.lead_activities.find({"lead_id": lead_id}, {"_id": 0}).sort("created_at", -1).to_list(200)


@platform_router.get("/crm/leads.csv")
async def export_leads_csv(user: dict = Depends(current_user)):
    slugs = await _owned_slugs(user)
    leads = await db.leads.find({"cardSlug": {"$in": slugs}}, {"_id": 0}).to_list(5000)
    buf = io.StringIO()
    w = csv.writer(buf)
    cols = ["name", "email", "phone", "company", "title", "website", "status", "source", "campaign", "event",
            "interest", "notes", "tags", "cardSlug", "met_at", "created_at", "next_follow_up"]
    w.writerow(cols)
    for l in leads:
        w.writerow([",".join(l.get("tags", [])) if c == "tags" else l.get(c, "") for c in cols])
    buf.seek(0)
    return StreamingResponse(io.BytesIO(buf.getvalue().encode()), media_type="text/csv",
                             headers={"Content-Disposition": 'attachment; filename="leads.csv"'})

# ------------------------------------------------------------------ wallet passes (Phase 5, provider-abstracted)
def _wallet_capability():
    return {
        "apple": {"configured": _configured("APPLE_WALLET_CERT_B64", "APPLE_WALLET_TEAM_ID"),
                  "platform": "apple"},
        "google": {"configured": _configured("GOOGLE_WALLET_ISSUER_ID", "GOOGLE_WALLET_SA_JSON"),
                   "platform": "google"},
    }


@platform_router.get("/wallet/status")
async def wallet_status():
    """Capability/config awareness so clients can show the right (Not Configured) state."""
    return {"capabilities": _wallet_capability(),
            "note": "Wallet pass issuance activates automatically once provider credentials are supplied."}


@platform_router.get("/cards/{slug}/wallet/{platform}")
async def card_wallet_pass(slug: str, platform: str):
    """Return a wallet pass for the card's contact. Provider-abstracted:
    reports Not Configured until Apple/Google Wallet credentials are supplied."""
    if platform not in ("apple", "google"):
        raise HTTPException(400, "Unsupported wallet platform")
    card = await db.digital_cards.find_one({"slug": slug, "status": "published"}, {"_id": 0})
    if not card:
        raise HTTPException(404, "Card not found")
    cap = _wallet_capability()[platform]
    ident = card.get("identity", {})
    contact = card.get("contact", {})
    # Neutral pass payload the provider adapter would sign/issue when configured.
    pass_data = {
        "organizationName": ident.get("company") or "TapPresence",
        "description": f"{ident.get('fullName', '')} — {ident.get('jobTitle', '')}".strip(" —"),
        "name": ident.get("fullName", ""), "title": ident.get("jobTitle", ""),
        "company": ident.get("company", ""), "phone": contact.get("phone", ""),
        "email": contact.get("email", ""), "website": contact.get("website", ""),
        "profile_url": f"{PUBLIC_APP_URL}/{slug}",
    }
    if not cap["configured"]:
        return {"configured": False, "platform": platform,
                "message": f"{platform.title()} Wallet is Not Configured",
                "pass_data": pass_data}
    # When configured, the signed .pkpass (Apple) or save-to-wallet JWT link (Google)
    # would be produced by the provider adapter here.
    return {"configured": True, "platform": platform, "pass_data": pass_data,
            "pass_url": f"{PUBLIC_APP_URL}/api/cards/{slug}/wallet/{platform}/download"}


# ------------------------------------------------------------------ industry catalog (Phase 8, data-driven / admin-manageable later)
_IMG = "https://static.prod-images.emergentagent.com/jobs/b7cf9ea3-4027-4bce-9aa9-3953ffa20ee3/images/"
INDUSTRY_CATALOG = [
    {"id": "real_estate", "name": "Real Estate", "icon": "Building2", "image": _IMG + "d2c82f9a132290384b7015b8d3f12f0c7f766a1213e5f91e4eb2794e8bb247f6.jpeg",
     "recommended_accent": "gold", "default_opacity": 0.15,
     "styles": [{"id": "skyline", "label": "City Skyline", "type": "image"}, {"id": "blueprint", "label": "Blueprint", "type": "pattern", "pattern": "grid"}, {"id": "architecture", "label": "Architecture", "type": "pattern", "pattern": "lines"}]},
    {"id": "business", "name": "Business & Consulting", "icon": "Briefcase", "image": _IMG + "9b16db82a5b24fb91253e6046b321b26daa4bbab3090d35ee1a845babcf66635.jpeg",
     "recommended_accent": "platinum", "default_opacity": 0.14,
     "styles": [{"id": "glass", "label": "Glass Towers", "type": "image"}, {"id": "geometry", "label": "Geometry", "type": "pattern", "pattern": "grid"}]},
    {"id": "sales", "name": "Sales & Marketing", "icon": "TrendingUp", "image": _IMG + "782d7af414bb8a53251e87281bfe15d15ad0a94fcda7ed8c0491bd9be6c7a5db.jpeg",
     "recommended_accent": "gold", "default_opacity": 0.15,
     "styles": [{"id": "growth", "label": "Growth", "type": "image"}, {"id": "points", "label": "Data Points", "type": "pattern", "pattern": "dots"}]},
    {"id": "technology", "name": "Technology & AI", "icon": "Cpu", "image": _IMG + "447272e027a2357ae68521e30e1f5e5501d30bcdf27ede9cc9cbc06be3f47d1e.jpeg",
     "recommended_accent": "blue", "default_opacity": 0.16,
     "styles": [{"id": "neural", "label": "Neural Network", "type": "image"}, {"id": "grid", "label": "Data Grid", "type": "pattern", "pattern": "grid"}, {"id": "particles", "label": "Particles", "type": "pattern", "pattern": "dots"}]},
    {"id": "healthcare", "name": "Healthcare", "icon": "HeartPulse", "image": _IMG + "23ec91a2e4b04c3e104b208e8c055b98d69e973ed86fa385df65f283f480d466.jpeg",
     "recommended_accent": "emerald", "default_opacity": 0.12,
     "styles": [{"id": "wave", "label": "Medical Wave", "type": "image"}, {"id": "abstract", "label": "Clean Abstract", "type": "pattern", "pattern": "glow"}]},
    {"id": "legal", "name": "Legal Services", "icon": "Scale", "image": _IMG + "418c39c0a1ada4ee213ca20117211887c218ff11da800c485497e847481a4489.jpeg",
     "recommended_accent": "bronze", "default_opacity": 0.14,
     "styles": [{"id": "columns", "label": "Columns", "type": "image"}, {"id": "marble", "label": "Marble Lines", "type": "pattern", "pattern": "lines"}]},
    {"id": "education", "name": "Education & Training", "icon": "GraduationCap", "image": _IMG + "452ba54873e3fcbe3946fab9d9f17bd96505a3f60812683840ecad5806913147.jpeg",
     "recommended_accent": "gold", "default_opacity": 0.13,
     "styles": [{"id": "academic", "label": "Academic", "type": "image"}, {"id": "geometry", "label": "Geometry", "type": "pattern", "pattern": "grid"}]},
    {"id": "hospitality", "name": "Hospitality", "icon": "Hotel", "image": _IMG + "96c623ebb474f490a218d010805b8da0e5b3ff3a17743583f509367ef9e6df04.jpeg",
     "recommended_accent": "gold", "default_opacity": 0.15,
     "styles": [{"id": "interior", "label": "Luxury Interior", "type": "image"}, {"id": "warm", "label": "Warm Light", "type": "pattern", "pattern": "glow"}]},
    {"id": "automotive", "name": "Automotive", "icon": "Car", "image": _IMG + "bfa23a5b48b5e3109555190832019296ad5ef55be922dfa0abf083d40796c4bf.jpeg",
     "recommended_accent": "platinum", "default_opacity": 0.15,
     "styles": [{"id": "luxury_car", "label": "Luxury Car", "type": "image"}, {"id": "speed", "label": "Speed Lines", "type": "pattern", "pattern": "lines"}]},
    {"id": "beauty", "name": "Beauty & Wellness", "icon": "Flower2", "image": _IMG + "2ee971f749a68580d1b69c42348edcd63ffa4c8d40b64f45565920e79697a3bd.jpeg",
     "recommended_accent": "rose", "default_opacity": 0.13,
     "styles": [{"id": "editorial", "label": "Editorial", "type": "image"}, {"id": "soft", "label": "Soft Light", "type": "pattern", "pattern": "glow"}]},
    {"id": "finance", "name": "Finance", "icon": "LineChart", "image": _IMG + "782d7af414bb8a53251e87281bfe15d15ad0a94fcda7ed8c0491bd9be6c7a5db.jpeg",
     "recommended_accent": "gold", "default_opacity": 0.14,
     "styles": [{"id": "market", "label": "Market Data", "type": "image"}, {"id": "lines", "label": "Financial Lines", "type": "pattern", "pattern": "lines"}]},
    {"id": "custom", "name": "Custom Industry", "icon": "Plus", "image": "",
     "recommended_accent": "gold", "default_opacity": 0.14,
     "styles": [{"id": "custom", "label": "Custom Image", "type": "custom"}]},
]


@platform_router.get("/industries")
async def list_industries():
    """Industry personalization catalog. Overrides from DB (Super Admin managed) merge over defaults."""
    overrides = await db.industry_overrides.find({}, {"_id": 0}).to_list(200)
    by_id = {o["id"]: o for o in overrides}
    out = []
    for ind in INDUSTRY_CATALOG:
        merged = {**ind, **by_id.get(ind["id"], {})}
        if merged.get("status", "active") != "disabled":
            out.append(merged)
    return {"industries": out}


def _require_super(user: dict):
    if user.get("role") != "SUPER_ADMIN":
        raise HTTPException(403, "Super admin only")


_INDUSTRY_IDS = {i["id"] for i in INDUSTRY_CATALOG}


class IndustryOverrideIn(BaseModel):
    name: Optional[str] = None
    recommended_accent: Optional[str] = None
    default_opacity: Optional[float] = None
    image: Optional[str] = None
    status: Optional[str] = None  # active | disabled


@platform_router.get("/admin/industries")
async def admin_list_industries(user: dict = Depends(current_user)):
    """Super-admin view: default catalog + any saved overrides + effective merged values."""
    _require_super(user)
    overrides = await db.industry_overrides.find({}, {"_id": 0}).to_list(200)
    by_id = {o["id"]: o for o in overrides}
    out = []
    for ind in INDUSTRY_CATALOG:
        ov = by_id.get(ind["id"], {})
        out.append({
            "id": ind["id"], "default": ind,
            "override": {k: v for k, v in ov.items() if k != "id"},
            "effective": {**ind, **ov},
        })
    return {"industries": out}


@platform_router.put("/admin/industries/{industry_id}")
async def upsert_industry_override(industry_id: str, body: IndustryOverrideIn, user: dict = Depends(current_user)):
    _require_super(user)
    if industry_id not in _INDUSTRY_IDS:
        raise HTTPException(404, "Unknown industry")
    if body.status is not None and body.status not in ("active", "disabled"):
        raise HTTPException(400, "Invalid status")
    patch = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    if not patch:
        raise HTTPException(400, "Nothing to update")
    patch["id"] = industry_id
    await db.industry_overrides.update_one({"id": industry_id}, {"$set": patch}, upsert=True)
    return {"ok": True}


@platform_router.delete("/admin/industries/{industry_id}")
async def reset_industry_override(industry_id: str, user: dict = Depends(current_user)):
    _require_super(user)
    await db.industry_overrides.delete_one({"id": industry_id})
    return {"ok": True}


@platform_router.get("/admin/platform/overview")
async def platform_overview(user: dict = Depends(current_user)):
    """Super Admin business control tower — REAL counts only, no fabricated KPIs."""
    _require_super(user)
    from collections import Counter
    workspaces = await db.workspaces.find({}, {"_id": 0, "plan": 1, "name": 1}).to_list(5000)
    plan_dist = Counter((w.get("plan") or "free") for w in workspaces)
    cards = await db.digital_cards.find({}, {"_id": 0, "status": 1}).to_list(20000)
    published = sum(1 for c in cards if c.get("status") == "published")
    users_count = await db.users.count_documents({})
    members_count = await db.memberships.count_documents({})
    leads_count = await db.leads.count_documents({})
    meetings = await db.meetings.find({}, {"_id": 0, "status": 1}).to_list(20000)
    meet_by_status = Counter((m.get("status") or "unknown") for m in meetings)
    views_30 = await db.analytics_events.count_documents(
        {"type": "view", "created_at": {"$gte": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()}})
    return {
        "workspaces": len(workspaces),
        "users": users_count,
        "memberships": members_count,
        "cards": len(cards),
        "cards_published": published,
        "leads": leads_count,
        "meetings": len(meetings),
        "meetings_by_status": dict(meet_by_status),
        "plan_distribution": dict(plan_dist),
        "views_30d": views_30,
    }


@platform_router.get("/admin/platform/users")
async def platform_search_users(q: str = "", user: dict = Depends(current_user)):
    """Super Admin: search users for support/ops. Returns safe fields + plan/status."""
    _require_super(user)
    query = {}
    if q.strip():
        rx = {"$regex": _re.escape(q.strip()), "$options": "i"}
        query = {"$or": [{"email": rx}, {"name": rx}]}
    users = await db.users.find(query, {"_id": 0, "password_hash": 0}).sort("created_at", -1).to_list(50)
    out = []
    for u in users:
        m = await db.memberships.find_one({"user_id": u["id"]}, {"_id": 0, "workspace_id": 1})
        ws = await db.workspaces.find_one({"id": m["workspace_id"]}, {"_id": 0, "name": 1, "plan": 1, "subscription": 1}) if m else None
        out.append({
            "id": u["id"], "name": u.get("name"), "email": u.get("email"),
            "role": u.get("role"), "email_verified": u.get("email_verified", False),
            "suspended": u.get("suspended", False), "created_at": u.get("created_at"),
            "workspace": ws.get("name") if ws else None,
            "plan": (ws or {}).get("plan"),
            "status": effective_status(ws) if ws else None,
        })
    return {"items": out}


@platform_router.get("/admin/platform/workspaces")
async def platform_search_workspaces(q: str = "", user: dict = Depends(current_user)):
    _require_super(user)
    query = {}
    if q.strip():
        query = {"name": {"$regex": _re.escape(q.strip()), "$options": "i"}}
    wss = await db.workspaces.find(query, {"_id": 0}).sort("created_at", -1).to_list(50)
    out = []
    for w in wss:
        out.append({
            "id": w["id"], "name": w.get("name"), "type": w.get("type"), "plan": w.get("plan"),
            "status": effective_status(w),
            "members": await db.memberships.count_documents({"workspace_id": w["id"]}),
            "cards": await db.digital_cards.count_documents({"workspace_id": w["id"]}),
            "leads": await db.leads.count_documents({"workspace_id": w["id"]}),
        })
    return {"items": out}


@platform_router.post("/admin/platform/users/{user_id}/suspend")
async def platform_suspend_user(user_id: str, body: dict, user: dict = Depends(current_user)):
    """Super Admin: suspend/reinstate an account. Suspended users cannot log in."""
    _require_super(user)
    target = await db.users.find_one({"id": user_id}, {"_id": 0, "role": 1})
    if not target:
        raise HTTPException(404, "User not found")
    if target.get("role") == "SUPER_ADMIN":
        raise HTTPException(400, "Cannot suspend a platform admin")
    suspended = bool(body.get("suspended", True))
    await db.users.update_one({"id": user_id}, {"$set": {"suspended": suspended}})
    if suspended:
        await db.sessions.delete_many({"user_id": user_id})
    return {"ok": True, "suspended": suspended}


# ------------------------------------------------------------------ Super Admin: Commercial / Pricing configuration
class CommercialConfigIn(BaseModel):
    trial: Optional[dict] = None
    plans: Optional[dict] = None
    referral: Optional[dict] = None
    default_market: Optional[str] = None
    regional_pricing: Optional[dict] = None


@platform_router.get("/admin/commercial")
async def get_commercial_admin(user: dict = Depends(current_user)):
    _require_super(user)
    cfg = await get_commercial_config()
    return {"config": cfg, "markets": COMMERCIAL_MARKETS, "demo_billing": ALLOW_DEMO_BILLING}


@platform_router.put("/admin/commercial")
async def update_commercial_admin(body: CommercialConfigIn, user: dict = Depends(current_user)):
    _require_super(user)
    patch = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    if not patch:
        raise HTTPException(400, "Nothing to update")
    # validation guards on core commercial rules
    if patch.get("default_market") and patch["default_market"].upper() not in COMMERCIAL_MARKETS:
        raise HTTPException(400, "Unknown market")
    if patch.get("plans", {}).get("team", {}).get("min_seats") is not None:
        try:
            if int(patch["plans"]["team"]["min_seats"]) < 1:
                raise HTTPException(400, "min_seats must be >= 1")
        except (TypeError, ValueError):
            raise HTTPException(400, "min_seats must be a number")
    ref = patch.get("referral", {})
    for k in ("referred_discount_month_pct", "referred_discount_year_pct", "referrer_reward_pct", "max_reward_discount_pct"):
        if ref.get(k) is not None:
            try:
                v = float(ref[k])
            except (TypeError, ValueError):
                raise HTTPException(400, f"{k} must be a number")
            if not (0 <= v <= 100):
                raise HTTPException(400, f"{k} must be between 0 and 100")
    current = await get_commercial_config()
    merged = _deep_merge(current, patch)
    merged["id"] = "global"
    await db.commercial_config.update_one({"id": "global"}, {"$set": merged}, upsert=True)
    await audit(None, user["id"], "commercial_config_updated", {"keys": list(patch.keys())})
    return {"ok": True, "config": merged}




# ------------------------------------------------------------------ contact exchange (unified lead)
class ExchangeIn(BaseModel):
    name: str
    email: str = ""
    phone: str = ""
    company: str = ""
    title: str = ""
    message: str = ""
    interest: str = ""
    consent: bool = False
    source: str = "profile_exchange"
    campaign: str = ""


@platform_router.post("/cards/{slug}/exchange")
async def contact_exchange(slug: str, body: ExchangeIn, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    if idempotency_key:
        prev = await db.idempotency_keys.find_one({"key": idempotency_key, "scope": f"exchange:{slug}"}, {"_id": 0})
        if prev:
            return prev["response"]
    card = await db.digital_cards.find_one({"slug": slug, "status": "published"}, {"_id": 0})
    if not card:
        raise HTTPException(404, "Card not found")
    if not body.name.strip() or not (body.email.strip() or body.phone.strip()):
        raise HTTPException(400, "Name and an email or phone are required")
    lead = {
        "id": str(uuid.uuid4()), "cardSlug": slug, "workspace_id": card.get("workspace_id"),
        "name": body.name.strip(), "email": body.email.strip(), "phone": body.phone.strip(),
        "company": body.company.strip(), "title": body.title.strip(), "message": body.message.strip(),
        "interest": body.interest.strip(), "source": body.source, "campaign": body.campaign,
        "consent": body.consent, "status": "NEW", "tags": [], "notes": "",
        "read": False, "created_at": now_iso(), "updated_at": now_iso(), "last_activity": now_iso(),
    }
    await db.leads.insert_one(lead)
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()), "workspace_id": card.get("workspace_id"), "type": "new_lead",
        "card_slug": slug, "scope": "card",
        "title": f"New contact from {body.name.strip()}", "body": f"via {body.source}",
        "read": False, "created_at": now_iso(),
    })
    await dispatch_webhooks(card.get("workspace_id"), "lead.created", {"id": lead["id"], "name": lead["name"], "email": lead["email"], "cardSlug": slug, "source": lead["source"]})
    # Return the owner's contact so the visitor can save it back (mutual exchange).
    result = {"ok": True, "owner": {"name": card.get("identity", {}).get("fullName", ""),
                                     "vcard_url": f"/api/cards/{slug}/vcard"}}
    if idempotency_key:
        try:
            await db.idempotency_keys.insert_one({"key": idempotency_key, "scope": f"exchange:{slug}", "response": result, "created_at": now_iso()})
        except Exception:
            pass
    return result

# ------------------------------------------------------------------ campaigns
class CampaignIn(BaseModel):
    name: str
    code: str
    start_date: str = ""
    end_date: str = ""
    utm_source: str = ""
    utm_medium: str = ""
    utm_campaign: str = ""


@platform_router.get("/campaigns")
async def list_campaigns(user: dict = Depends(current_user)):
    ws_ids = await workspace_ids_for(user)
    q = {} if ws_ids == "ALL" else {"workspace_id": {"$in": ws_ids}}
    return await db.campaigns.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)


@platform_router.post("/campaigns")
async def create_campaign(body: CampaignIn, user: dict = Depends(current_user)):
    ms = await memberships_for(user["id"])
    ws_id = ms[0]["workspace_id"] if ms else None
    if await db.campaigns.find_one({"workspace_id": ws_id, "code": body.code}):
        raise HTTPException(400, "Campaign code already exists")
    doc = {"id": str(uuid.uuid4()), "workspace_id": ws_id, **body.model_dump(),
           "owner_id": user["id"], "created_at": now_iso()}
    await db.campaigns.insert_one(doc)
    doc.pop("_id", None)
    return doc


@platform_router.get("/campaigns/{campaign_id}/stats")
async def campaign_stats(campaign_id: str, user: dict = Depends(current_user)):
    camp = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    if not camp:
        raise HTTPException(404, "Campaign not found")
    code = camp["code"]
    events = await db.analytics_events.count_documents({"campaign": code})
    leads = await db.leads.count_documents({"campaign": code})
    return {"campaign": camp, "events": events, "leads": leads}

# ------------------------------------------------------------------ AI follow-up (provider-abstracted)
class FollowupIn(BaseModel):
    lead_name: str
    company: str = ""
    notes: str = ""
    industry: str = ""
    owner_name: str = ""
    tone: str = "professional"
    channel: str = "email"  # email | whatsapp | sms
    language: str = "en"    # en | ar | es


def _draft_followup(b: FollowupIn) -> str:
    lang = b.language if b.language in SUPPORTED_LANGUAGES else "en"
    first = (b.lead_name or "").split(" ")[0]
    if lang == "ar":
        first = first or "حضرتك"
        ctx = f" بخصوص {b.notes}" if b.notes else ""
        msg = f"مرحباً {first}،\n\nسعدت بالتواصل معك اليوم{ctx}. يسعدني مساعدتك في الخطوة التالية"
        if b.company:
            msg += f"، وأعتقد أن هناك توافقاً ممتازاً مع ما تعمل عليه {b.company}"
        msg += ".\nهل يناسبك اتصال قصير هذا الأسبوع؟"
        if b.owner_name:
            msg += f"\n\nمع خالص التقدير،\n{b.owner_name}"
        return msg
    if lang == "es":
        first = first or "hola"
        ctx = f" sobre {b.notes}" if b.notes else ""
        msg = f"Hola {first},\n\nFue un placer conectar hoy{ctx}. Me encantaría ayudarte con el siguiente paso"
        if b.company:
            msg += f" y creo que encaja muy bien con lo que están haciendo en {b.company}"
        msg += ".\n¿Tienes disponibilidad para una llamada breve esta semana?"
        if b.owner_name:
            msg += f"\n\nUn saludo,\n{b.owner_name}"
        return msg
    first = first or "there"
    ctx = f" about {b.notes}" if b.notes else ""
    sign = f"\n\nBest,\n{b.owner_name}" if b.owner_name else ""
    if b.channel in ("whatsapp", "sms"):
        return f"Hi {first}! Great connecting today{ctx}. Happy to share more whenever suits you — just let me know.{(' — ' + b.owner_name) if b.owner_name else ''}"
    opener = {"warm": f"Hi {first},\n\nIt was a genuine pleasure meeting you",
              "professional": f"Dear {first},\n\nThank you for taking the time to connect",
              "short": f"Hi {first}, thanks for connecting"}.get(b.tone, f"Hi {first},\n\nThank you for connecting")
    body = f"{opener}{(' — especially our chat' + ctx) if ctx else ''}. I'd love to help you take the next step."
    if b.company:
        body += f" I think there's a strong fit with what {b.company} is working toward."
    return body + " Would you be open to a short call this week?" + sign


@platform_router.post("/ai/followup")
async def ai_followup(body: FollowupIn, request: Request, user: dict = Depends(current_user)):
    """Drafts a follow-up. User must review + send (AI never auto-sends).
    Uses the configured LLM (Emergent universal key) with a deterministic
    multilingual template as a guaranteed fallback."""
    rate_limit(request, "ai", 20, 60)
    _ms = await memberships_for(user["id"])
    _ws_id = _ms[0]["workspace_id"] if _ms else None
    _ent, _period = await enforce_quota(user, _ws_id, "ai")
    provider = "template"
    text = _draft_followup(body)
    key = os.environ.get("EMERGENT_LLM_KEY", "").strip()
    if key:
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            lang_name = {"ar": "Arabic", "es": "Spanish", "en": "English"}.get(body.language, "English")
            sys = (f"You are an elite networking & sales assistant writing on behalf of "
                   f"{body.owner_name or 'a professional'}. Write ONE {body.tone} follow-up "
                   f"{body.channel} message in {lang_name}. Be concise, warm and specific, "
                   f"reference the meeting context, and end with a clear next step. "
                   f"Output ONLY the message text — no preamble, no subject line, no quotes.")
            prompt = (f"Lead name: {body.lead_name}\nCompany: {body.company}\n"
                      f"Industry: {body.industry}\nMeeting notes: {body.notes}\n"
                      f"Channel: {body.channel}\nTone: {body.tone}\nLanguage: {lang_name}")
            chat = LlmChat(api_key=key, session_id=f"followup-{uuid.uuid4()}",
                           system_message=sys).with_model("openai", "gpt-5.4")
            resp = await chat.send_message(UserMessage(text=prompt))
            if resp and str(resp).strip():
                text = str(resp).strip()
                provider = "openai:gpt-5.4"
        except Exception as e:
            logger.warning(f"AI follow-up LLM fallback to template: {e}")
    await db.ai_usage.insert_one({
        "id": str(uuid.uuid4()), "user_id": user["id"], "provider": provider,
        "channel": body.channel, "tone": body.tone, "language": body.language, "created_at": now_iso(),
    })
    await incr_usage(user["id"], "ai", _period)
    _used = await get_usage(user["id"], "ai", _period)
    return {"provider": provider, "channel": body.channel, "language": body.language, "draft": text,
            "rtl": body.language in RTL_LANGUAGES, "usage": {"used": _used, "limit": _ent.get("ai_limit"), "period": _period},
            "note": "Review before sending. AI drafts only; it never sends automatically."}


# ------------------------------------------------------------------ business-card / event-badge scanner (Phase 7)
async def _user_entitlements(user: dict) -> dict:
    if user.get("role") == "SUPER_ADMIN":
        return PLAN_ENTITLEMENTS["enterprise"]
    ms = await memberships_for(user["id"])
    if not ms:
        return PLAN_ENTITLEMENTS["free"]
    return await resolve_entitlements(ms[0]["workspace_id"])


SCAN_SOURCES = {"business_card_scan", "badge_scan", "qr_scan"}


class ScanIn(BaseModel):
    image_base64: str
    source: str = "business_card_scan"


def _strip_data_url(b64: str) -> str:
    b64 = (b64 or "").strip()
    if b64.startswith("data:"):
        b64 = b64.split(",", 1)[-1]
    return b64


def _parse_scan_json(raw: str) -> dict:
    """Extract the first JSON object from an LLM response, tolerant of code fences."""
    if not raw:
        return {}
    txt = raw.strip()
    txt = re.sub(r"^```(?:json)?", "", txt).strip()
    txt = re.sub(r"```$", "", txt).strip()
    try:
        return json.loads(txt)
    except Exception:
        m = re.search(r"\{.*\}", txt, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return {}
    return {}


@platform_router.post("/scan/card")
async def scan_card(body: ScanIn, request: Request, user: dict = Depends(current_user)):
    """OCR a business card / event badge into a STRUCTURED DRAFT. Never creates a lead.
    The user must review + confirm the draft via /scan/confirm to persist a CRM lead."""
    rate_limit(request, "scan", 15, 60)
    _ms = await memberships_for(user["id"])
    _ws_id = _ms[0]["workspace_id"] if _ms else None
    _ent, _period = await enforce_quota(user, _ws_id, "scanner")
    await incr_usage(user["id"], "scanner", _period)
    source = body.source if body.source in SCAN_SOURCES else "business_card_scan"
    image_b64 = _strip_data_url(body.image_base64)
    if not image_b64:
        raise HTTPException(400, "No image provided")

    key = os.environ.get("EMERGENT_LLM_KEY", "").strip()
    if not key:
        return {"configured": False, "message": "Card scanning is Not Configured", "draft": {}}

    empty = {"name": "", "title": "", "company": "", "email": "", "phone": "",
             "website": "", "address": "", "city": "", "country": "", "language": "en", "notes": ""}
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
        sys = (
            "You are an OCR + information-extraction engine for business cards and event badges. "
            "Read ALL text in the image (any language / script, including Arabic and Latin-accented) "
            "and return ONLY a compact JSON object with these exact keys: "
            "name, title, company, email, phone, website, address, city, country, language, notes. "
            "Rules: format phone in international E.164 form when a country can be inferred (e.g. +9715...); "
            "keep the original spelling and script for name/company; "
            "'language' is the ISO-639-1 code of the card's primary language (en, ar, es, ...); "
            "'notes' may hold any extra text (tagline, second phone). "
            "Use empty strings for anything not present. Output JSON only — no prose, no code fences."
        )
        chat = LlmChat(api_key=key, session_id=f"scan-{uuid.uuid4()}",
                       system_message=sys).with_model("openai", "gpt-5.4")
        msg = UserMessage(text="Extract the contact details from this card/badge image as JSON.",
                          file_contents=[ImageContent(image_base64=image_b64)])
        resp = await chat.send_message(msg)
        data = _parse_scan_json(str(resp))
    except Exception as e:
        logger.warning(f"scan_card LLM error: {e}")
        raise HTTPException(502, "Could not read the card. Please retake the photo and try again.")

    draft = {**empty, **{k: (str(data.get(k, "")).strip() if data.get(k) is not None else "")
                          for k in empty}}
    if draft["language"] not in SUPPORTED_LANGUAGES:
        draft["language"] = "en" if not draft["language"] else draft["language"][:2].lower()
    await db.ai_usage.insert_one({
        "id": str(uuid.uuid4()), "user_id": user["id"], "provider": "openai:gpt-5.4",
        "channel": "scanner", "tone": source, "language": draft.get("language", "en"), "created_at": now_iso(),
    })
    return {"configured": True, "source": source, "draft": draft,
            "note": "Review and edit before saving. No lead is created until you confirm."}


class ScanConfirmIn(BaseModel):
    cardSlug: str
    source: str = "business_card_scan"
    name: str
    title: str = ""
    company: str = ""
    email: str = ""
    phone: str = ""
    website: str = ""
    address: str = ""
    city: str = ""
    country: str = ""
    language: str = "en"
    interest: str = ""
    notes: str = ""
    event: str = ""
    campaign: str = ""
    force: bool = False


import re as _re


def _norm_email(e):
    return (e or "").strip().lower()


def _norm_phone(p):
    d = _re.sub(r"\D", "", p or "")
    return d[-9:] if len(d) >= 7 else ""


async def find_duplicate_lead(card_slug, email, phone, exclude_id=None):
    """Lightweight dedupe within the SAME card: match by normalized email or phone (last 9 digits)."""
    ne, np = _norm_email(email), _norm_phone(phone)
    if not ne and not np:
        return None
    cands = await db.leads.find({"cardSlug": card_slug}, {"_id": 0}).to_list(3000)
    for l in cands:
        if exclude_id and l.get("id") == exclude_id:
            continue
        if ne and _norm_email(l.get("email")) == ne:
            return l
        if np and _norm_phone(l.get("phone")) == np:
            return l
    return None


@platform_router.post("/scan/confirm")
async def scan_confirm(body: ScanConfirmIn, user: dict = Depends(current_user)):
    """Persist a reviewed scan as a CRM lead scoped to one of the user's own cards."""
    ent = await _user_entitlements(user)
    if not ent.get("scanner"):
        raise HTTPException(403, "Scanner is not available on your plan")
    source = body.source if body.source in SCAN_SOURCES else "business_card_scan"
    if not body.name.strip():
        raise HTTPException(400, "A name is required")
    slugs = await _owned_slugs(user)
    if body.cardSlug not in slugs and user.get("role") != "SUPER_ADMIN":
        raise HTTPException(403, "Not your card")
    card = await db.digital_cards.find_one({"slug": body.cardSlug}, {"_id": 0})
    if not card:
        raise HTTPException(404, "Card not found")
    # Duplicate guard — let the user decide (update existing vs. save anyway) instead of silent dupes.
    if not body.force:
        dup = await find_duplicate_lead(body.cardSlug, body.email, body.phone)
        if dup:
            return {"ok": False, "duplicate": dup}
    lang = body.language if body.language in SUPPORTED_LANGUAGES else "en"
    lead = {
        "id": str(uuid.uuid4()), "cardSlug": body.cardSlug, "workspace_id": card.get("workspace_id"),
        "name": body.name.strip(), "email": body.email.strip(), "phone": body.phone.strip(),
        "company": body.company.strip(), "title": body.title.strip(),
        "website": body.website.strip(), "message": body.notes.strip(), "interest": body.interest.strip(),
        "address": body.address.strip(), "city": body.city.strip(), "country": body.country.strip(),
        "language": lang, "source": source, "campaign": body.campaign.strip(), "event": body.event.strip(), "consent": True,
        "status": "new", "tags": ["scanned"] + (["event"] if body.event.strip() else []), "notes": body.notes.strip(),
        "met_at": now_iso(), "next_follow_up": "",
        "scanned": True, "captured_by": user["id"],
        "read": False, "created_at": now_iso(), "updated_at": now_iso(), "last_activity": now_iso(),
    }
    await db.leads.insert_one(lead)
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()), "workspace_id": card.get("workspace_id"), "type": "new_lead",
        "card_slug": body.cardSlug, "scope": "card",
        "title": f"Scanned lead: {lead['name']}", "body": f"via {source}",
        "read": False, "created_at": now_iso(),
    })
    lead.pop("_id", None)
    return {"ok": True, "lead": lead}


@platform_router.post("/ai/enrich")
async def ai_enrich(body: dict, user: dict = Depends(current_user)):
    if not _configured("ENRICHMENT_API_KEY"):
        return {"configured": False, "message": "Enrichment Not Configured", "data": {}}
    # Provider adapter would call the compliant enrichment API here.
    return {"configured": True, "data": {}}

# ------------------------------------------------------------------ notifications
NOTIF_ADMIN_WS_ROLES = {"WORKSPACE_OWNER", "WORKSPACE_ADMIN", "MANAGER"}


async def _notif_visibility_query(user: dict) -> dict:
    """Ownership-aware notification visibility. Backend is the source of truth.
    - user-specific  -> only the addressed recipient
    - card-context   -> only users who can access that card (member=owner, admin=workspace)
    - workspace-wide -> members of that workspace
    - workspace_admin activity -> workspace admins only
    - legacy records (no scope/card_slug/recipient) -> workspace admins only (safe default, no leak)
    """
    if user.get("role") == "SUPER_ADMIN":
        return {}
    ms = await db.memberships.find({"user_id": user["id"]}, {"_id": 0}).to_list(200)
    member_ws = [m["workspace_id"] for m in ms]
    admin_ws = [m["workspace_id"] for m in ms if m.get("role") in NOTIF_ADMIN_WS_ROLES]
    # cards the caller can access (admins: whole workspace; members: only owned)
    ors = []
    for m in ms:
        if m.get("role") in NOTIF_ADMIN_WS_ROLES:
            ors.append({"workspace_id": m["workspace_id"]})
        else:
            ors.append({"workspace_id": m["workspace_id"], "owner_user_id": user["id"]})
    slugs = []
    if ors:
        cards = await db.digital_cards.find({"$or": ors}, {"_id": 0, "slug": 1}).to_list(5000)
        slugs = [c["slug"] for c in cards]
    conditions = [
        {"recipient_user_id": user["id"]},
        {"scope": "card", "card_slug": {"$in": slugs}},
        {"scope": "workspace", "workspace_id": {"$in": member_ws}},
        {"scope": "workspace_admin", "workspace_id": {"$in": admin_ws}},
        {"scope": {"$exists": False}, "card_slug": {"$exists": False},
         "recipient_user_id": {"$exists": False}, "workspace_id": {"$in": admin_ws}},
    ]
    return {"$or": conditions}


@platform_router.get("/notifications")
async def notifications(user: dict = Depends(current_user)):
    q = await _notif_visibility_query(user)
    # Scheduled follow-up reminders stay hidden until they are due.
    not_future = {"$or": [{"remind_at": {"$exists": False}}, {"remind_at": {"$lte": now_iso()}}]}
    items = await db.notifications.find({"$and": [q, not_future]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    unread = sum(1 for n in items if not n.get("read"))
    return {"items": items, "unread": unread}


@platform_router.patch("/notifications/{notif_id}/read")
async def mark_notification_read(notif_id: str, user: dict = Depends(current_user)):
    q = await _notif_visibility_query(user)
    n = await db.notifications.find_one({"$and": [{"id": notif_id}, q]}, {"_id": 0})
    if not n:
        raise HTTPException(404, "Notification not found")
    await db.notifications.update_one({"id": notif_id}, {"$set": {"read": True}})
    return {"ok": True}


@platform_router.post("/notifications/read-all")
async def mark_all_notifications_read(user: dict = Depends(current_user)):
    q = await _notif_visibility_query(user)
    res = await db.notifications.update_many({"$and": [q, {"read": False}]}, {"$set": {"read": True}})
    return {"ok": True, "updated": res.modified_count}

# ------------------------------------------------------------------ integration status (placeholders)
@platform_router.get("/integrations/status")
async def integrations_status(user: dict = Depends(current_user)):
    cfg = (await get_config())["integrations"]
    return {"crm": {"hubspot": cfg["hubspot"], "salesforce": cfg["salesforce"], "pipedrive": cfg["pipedrive"],
                    "webhook": True, "zapier": True},
            "wallet": {"apple": cfg["apple_wallet"], "google": cfg["google_wallet"]},
            "billing": {"stripe": cfg["stripe"], "revenuecat": cfg["revenuecat"]},
            "notes": "Adapters built; connect credentials to activate."}


# ------------------------------------------------------------------ Integration Hub (Phase O — provider-neutral internal foundation)
import hmac as _hmac, hashlib as _hashlib, secrets as _secrets, json as _json, httpx as _httpx


async def dispatch_webhooks(workspace_id: str, event: str, payload: dict):
    """Signed outbound webhook dispatch to tenant-registered endpoints. Best-effort, non-blocking to callers."""
    if not workspace_id:
        return
    hooks = await db.webhooks.find({"workspace_id": workspace_id, "active": True, "events": event}, {"_id": 0}).to_list(100)
    if not hooks:
        return
    body = _json.dumps({"event": event, "data": payload, "ts": now_iso()}, default=str)
    async with _httpx.AsyncClient(timeout=5) as client:
        for h in hooks:
            sig = _hmac.new(h["secret"].encode(), body.encode(), _hashlib.sha256).hexdigest()
            headers = {"Content-Type": "application/json", "X-TapPresence-Event": event, "X-TapPresence-Signature": f"sha256={sig}"}
            try:
                r = await client.post(h["url"], content=body, headers=headers)
                await db.webhooks.update_one({"id": h["id"]}, {"$set": {"last_delivery": now_iso(), "last_status": r.status_code}})
            except Exception:
                await db.webhooks.update_one({"id": h["id"]}, {"$set": {"last_delivery": now_iso(), "last_status": "error"}})


class ApiKeyIn(BaseModel):
    name: str = "API key"


class WebhookIn(BaseModel):
    url: str
    events: List[str] = []


WEBHOOK_EVENTS = ["lead.created", "meeting.booked", "card.published"]


@platform_router.get("/workspaces/{wid}/hub")
async def integration_hub(wid: str, user: dict = Depends(current_user)):
    await require_ws_admin(user, wid)
    keys = await db.api_keys.find({"workspace_id": wid}, {"_id": 0, "key_hash": 0}).sort("created_at", -1).to_list(200)
    hooks = await db.webhooks.find({"workspace_id": wid}, {"_id": 0, "secret": 0}).sort("created_at", -1).to_list(200)
    return {"available_events": WEBHOOK_EVENTS, "api_keys": keys, "webhooks": hooks}


@platform_router.post("/workspaces/{wid}/api-keys")
async def create_api_key(wid: str, body: ApiKeyIn, user: dict = Depends(current_user)):
    await require_ws_admin(user, wid)
    await require_team(user, wid)
    raw = "tpk_" + _secrets.token_urlsafe(32)
    prefix = raw[:12]
    doc = {"id": str(uuid.uuid4()), "workspace_id": wid, "name": body.name or "API key",
           "prefix": prefix, "key_hash": _hashlib.sha256(raw.encode()).hexdigest(),
           "created_at": now_iso(), "last_used": None, "revoked": False, "created_by": user["id"]}
    await db.api_keys.insert_one(doc)
    return {"id": doc["id"], "name": doc["name"], "prefix": prefix, "key": raw}  # full key shown ONCE


@platform_router.delete("/workspaces/{wid}/api-keys/{key_id}")
async def revoke_api_key(wid: str, key_id: str, user: dict = Depends(current_user)):
    await require_ws_admin(user, wid)
    await db.api_keys.update_one({"id": key_id, "workspace_id": wid}, {"$set": {"revoked": True}})
    return {"ok": True}


@platform_router.post("/workspaces/{wid}/webhooks")
async def create_webhook(wid: str, body: WebhookIn, user: dict = Depends(current_user)):
    await require_ws_admin(user, wid)
    await require_team(user, wid)
    if not body.url.startswith("http"):
        raise HTTPException(400, "Invalid URL")
    bad = [e for e in body.events if e not in WEBHOOK_EVENTS]
    if bad:
        raise HTTPException(400, f"Unknown events: {bad}")
    secret = "whsec_" + _secrets.token_urlsafe(24)
    doc = {"id": str(uuid.uuid4()), "workspace_id": wid, "url": body.url, "events": body.events or WEBHOOK_EVENTS,
           "secret": secret, "active": True, "created_at": now_iso(), "last_delivery": None, "last_status": None}
    await db.webhooks.insert_one(doc)
    return {"id": doc["id"], "workspace_id": wid, "url": doc["url"], "events": doc["events"],
            "active": True, "created_at": doc["created_at"], "secret": secret}  # secret shown once


@platform_router.delete("/workspaces/{wid}/webhooks/{hook_id}")
async def delete_webhook(wid: str, hook_id: str, user: dict = Depends(current_user)):
    await require_ws_admin(user, wid)
    await db.webhooks.delete_one({"id": hook_id, "workspace_id": wid})
    return {"ok": True}


@platform_router.post("/workspaces/{wid}/webhooks/{hook_id}/test")
async def test_webhook(wid: str, hook_id: str, user: dict = Depends(current_user)):
    await require_ws_admin(user, wid)
    h = await db.webhooks.find_one({"id": hook_id, "workspace_id": wid}, {"_id": 0})
    if not h:
        raise HTTPException(404, "Webhook not found")
    await dispatch_webhooks(wid, h["events"][0] if h.get("events") else "lead.created", {"test": True, "message": "TapPresence test event"})
    updated = await db.webhooks.find_one({"id": hook_id}, {"_id": 0, "secret": 0})
    return {"ok": True, "last_status": updated.get("last_status")}


async def require_ws_admin(user: dict, wid: str):
    if user.get("role") == "SUPER_ADMIN":
        return "SUPER_ADMIN"
    m = await db.memberships.find_one({"user_id": user["id"], "workspace_id": wid}, {"_id": 0})
    if not m or m.get("role") not in ("WORKSPACE_OWNER", "WORKSPACE_ADMIN"):
        raise HTTPException(403, "Workspace admin access required")
    return m["role"]


async def member_role(user_id: str, wid: str):
    m = await db.memberships.find_one({"user_id": user_id, "workspace_id": wid}, {"_id": 0})
    return m.get("role") if m else None


class MemberIn(BaseModel):
    email: EmailStr
    name: str = ""
    role: str = "MEMBER"


class BrandingIn(BaseModel):
    branding: dict = {}
    locked_fields: List[str] = []


WS_ROLES = {"WORKSPACE_OWNER", "WORKSPACE_ADMIN", "MANAGER", "MEMBER"}


@platform_router.get("/workspaces/{wid}")
async def get_workspace(wid: str, user: dict = Depends(current_user)):
    await require_ws_admin(user, wid)
    ws = await db.workspaces.find_one({"id": wid}, {"_id": 0})
    if not ws:
        raise HTTPException(404, "Workspace not found")
    ws["member_count"] = await db.memberships.count_documents({"workspace_id": wid})
    return ws


@platform_router.get("/workspaces/{wid}/members")
async def list_members(wid: str, user: dict = Depends(current_user)):
    await require_ws_admin(user, wid)
    ms = await db.memberships.find({"workspace_id": wid}, {"_id": 0}).to_list(1000)
    uids = [m["user_id"] for m in ms]
    users = {u["id"]: u for u in await db.users.find({"id": {"$in": uids}}, {"_id": 0, "password_hash": 0}).to_list(1000)}
    return [{**m, "user": users.get(m["user_id"], {})} for m in ms]


async def _create_member(wid: str, email: str, name: str, role: str):
    email = email.strip().lower()
    role = role if role in WS_ROLES else "MEMBER"
    user = await db.users.find_one({"email": email})
    if not user:
        uid = str(uuid.uuid4())
        user = {"id": uid, "email": email, "password_hash": hash_pw(secrets.token_urlsafe(16)),
                "name": name.strip(), "role": "MEMBER", "email_verified": False,
                "language": "en", "locale": "en-US", "timezone": "UTC", "created_at": now_iso()}
        await db.users.insert_one(user)
    if await db.memberships.find_one({"user_id": user["id"], "workspace_id": wid}):
        return user, False
    token = secrets.token_urlsafe(24)
    await db.memberships.insert_one({"id": str(uuid.uuid4()), "user_id": user["id"], "workspace_id": wid,
                                     "role": role, "status": "invited", "invite_token": token, "created_at": now_iso()})
    link = f"{PUBLIC_APP_URL}/register?invite={token}"
    logger.info(f"[email{'' if _configured('EMAIL_API_KEY') else ':NOT_CONFIGURED'}] team invite for {email}: {link}")
    return user, True


@platform_router.post("/workspaces/{wid}/members")
async def invite_member(wid: str, body: MemberIn, user: dict = Depends(current_user)):
    await require_ws_admin(user, wid)
    await require_team(user, wid)
    await enforce_seat_limit(user, wid)
    u, created = await _create_member(wid, body.email, body.name, body.role)
    await db.notifications.insert_one({"id": str(uuid.uuid4()), "workspace_id": wid, "type": "team_invite",
                                       "scope": "workspace_admin",
                                       "title": f"Invited {body.email}", "body": "", "read": False, "created_at": now_iso()})
    await audit(wid, user["id"], "team.invite", {"email": body.email, "created_user": created})
    return {"ok": True, "user_id": u["id"], "created": created}


@platform_router.patch("/workspaces/{wid}/members/{uid}")
async def update_member(wid: str, uid: str, body: dict, user: dict = Depends(current_user)):
    await require_ws_admin(user, wid)
    await require_team(user, wid)
    upd = {}
    if body.get("role") in WS_ROLES:
        upd["role"] = body["role"]
    if body.get("status") in ("active", "invited", "deactivated"):
        upd["status"] = body["status"]
    if not upd:
        raise HTTPException(400, "Nothing to update")
    await db.memberships.update_one({"workspace_id": wid, "user_id": uid}, {"$set": upd})
    await audit(wid, user["id"], "team.update_member", {"uid": uid, **upd})
    return {"ok": True}


@platform_router.delete("/workspaces/{wid}/members/{uid}")
async def remove_member(wid: str, uid: str, user: dict = Depends(current_user)):
    ws = await db.workspaces.find_one({"id": wid}, {"_id": 0, "owner_id": 1})
    if ws and ws.get("owner_id") == uid:
        raise HTTPException(400, "Cannot remove the workspace owner")
    await require_ws_admin(user, wid)
    await db.memberships.delete_one({"workspace_id": wid, "user_id": uid})
    await audit(wid, user["id"], "team.remove_member", {"uid": uid})
    return {"ok": True}


@platform_router.put("/workspaces/{wid}/branding")
async def set_branding(wid: str, body: BrandingIn, user: dict = Depends(current_user)):
    await require_ws_admin(user, wid)
    await require_team(user, wid)
    await db.workspaces.update_one({"id": wid}, {"$set": {"branding": body.branding, "locked_fields": body.locked_fields}})
    await audit(wid, user["id"], "team.branding", {"locked": body.locked_fields})
    return await db.workspaces.find_one({"id": wid}, {"_id": 0})


class ImportIn(BaseModel):
    csv: str
    create_cards: bool = True


@platform_router.post("/workspaces/{wid}/import")
async def import_members(wid: str, body: ImportIn, user: dict = Depends(current_user)):
    await require_ws_admin(user, wid)
    await require_team(user, wid)
    ws = await db.workspaces.find_one({"id": wid}, {"_id": 0})
    branding = (ws or {}).get("branding", {})
    reader = csv.DictReader(io.StringIO(body.csv.strip()))
    created_users, created_cards = 0, 0
    for row in reader:
        row = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
        email = row.get("email")
        if not email:
            continue
        u, is_new = await _create_member(wid, email, row.get("name", ""), row.get("role", "MEMBER"))
        if is_new:
            await enforce_seat_limit(user, wid)
            created_users += 1
        if body.create_cards:
            base = (row.get("name") or email.split("@")[0]).lower().replace(" ", "-")
            slug = base
            i = 1
            while await db.digital_cards.find_one({"slug": slug}):
                slug = f"{base}-{i}"; i += 1
            card = CardData_min(slug, wid, branding, row, u["id"])
            await db.digital_cards.insert_one(card)
            created_cards += 1
    await audit(wid, user["id"], "team.import", {"users": created_users, "cards": created_cards})
    return {"ok": True, "created_users": created_users, "created_cards": created_cards}


def CardData_min(slug, wid, branding, row, owner_user_id=None):
    return {
        "id": str(uuid.uuid4()), "slug": slug, "workspace_id": wid, "owner_user_id": owner_user_id,
        "templateId": branding.get("template", "beige-luxury"), "accent": branding.get("accent", "gold"),
        "status": "draft",
        "identity": {"fullName": row.get("name", ""), "jobTitle": row.get("title", ""),
                     "company": branding.get("company", ""), "companyLogo": branding.get("logo", ""),
                     "profilePhoto": "", "bio": "", "city": "", "country": "", "availabilityBadge": ""},
        "contact": {"phone": row.get("phone", ""), "whatsapp": "", "email": row.get("email", ""),
                    "website": branding.get("company_website", ""), "address": "", "mapsUrl": "",
                    "addressLine1": "", "addressLine2": "", "city": "", "adminArea": "", "postalCode": "", "countryCode": ""},
        "social": {}, "actions": [], "services": [], "projects": [], "booking": {"bookingUrl": ""},
        "languages": ["en"], "i18n": {},
        "created_at": now_iso(), "updated_at": now_iso(),
    }


# ------------------------------------------------------------------ global markets & pricing
@platform_router.get("/markets")
async def markets():
    ms = await db.markets.find({}, {"_id": 0}).to_list(100)
    return {"markets": ms or DEFAULT_MARKETS, "currencies": SUPPORTED_CURRENCIES,
            "languages": SUPPORTED_LANGUAGES, "rtl_languages": RTL_LANGUAGES}


def _price_for(plan: dict, market: str):
    rp = (plan.get("regional_prices") or {})
    entry = rp.get(market) or rp.get("US") or {}
    return entry


@platform_router.get("/pricing")
async def pricing(market: str = "US"):
    market = market.upper()
    all_markets = await db.markets.find({}, {"_id": 0}).to_list(100) or DEFAULT_MARKETS
    mkt = next((m for m in all_markets if m["code"] == market), None)
    if not mkt:
        raise HTTPException(400, f"Unknown market '{market}'. Supported: {[m['code'] for m in all_markets]}")
    plans = await db.plans.find({}, {"_id": 0}).to_list(50) or DEFAULT_PLANS
    out = []
    for p in plans:
        if not p.get("public"):
            continue
        pr = _price_for(p, market)
        out.append({"id": p["id"], "name": p["name"], "currency": mkt["currency"],
                    "price_month": pr.get("month", p.get("price_month")),
                    "price_year": pr.get("year", p.get("price_year")),
                    "custom": p.get("custom", False), "per_seat": p.get("per_seat", False)})
    return {"market": mkt, "plans": out}


@platform_router.get("/admin/markets")
async def admin_list_markets(user: dict = Depends(current_user)):
    if user.get("role") != "SUPER_ADMIN":
        raise HTTPException(403, "Super admin only")
    return await db.markets.find({}, {"_id": 0}).to_list(100) or DEFAULT_MARKETS


@platform_router.put("/admin/markets/{code}")
async def admin_update_market(code: str, body: dict, user: dict = Depends(current_user)):
    if user.get("role") != "SUPER_ADMIN":
        raise HTTPException(403, "Super admin only")
    body.pop("_id", None)
    body["code"] = code.upper()
    await db.markets.update_one({"code": code.upper()}, {"$set": body}, upsert=True)
    return await db.markets.find_one({"code": code.upper()}, {"_id": 0})


@platform_router.put("/admin/plans/{plan_id}/pricing/{market}")
async def admin_set_regional_price(plan_id: str, market: str, body: dict, user: dict = Depends(current_user)):
    """body: { month: <minor units>, year: <minor units> }"""
    if user.get("role") != "SUPER_ADMIN":
        raise HTTPException(403, "Super admin only")
    await db.plans.update_one({"id": plan_id},
                              {"$set": {f"regional_prices.{market.upper()}": {"month": body.get("month"), "year": body.get("year")}}},
                              upsert=True)
    return await db.plans.find_one({"id": plan_id}, {"_id": 0})


# ------------------------------------------------------------------ migration
async def run_migration():
    """Idempotent, non-destructive. Preserves existing users/cards/URLs."""
    try:
        await db.workspaces.create_index("id", unique=True)
        await db.memberships.create_index([("user_id", 1), ("workspace_id", 1)])
        await db.sessions.create_index("refresh")
        await db.nfc_devices.create_index("token", unique=True)
        await db.leads.create_index("cardSlug")
        await db.analytics_events.create_index([("cardSlug", 1), ("type", 1)])
        await db.campaigns.create_index([("workspace_id", 1), ("code", 1)])
        # Phase 5 — indexes justified by actual query patterns (audit)
        await db.referrals.create_index("referrer_ws_id")
        await db.referrals.create_index("referred_ws_id")
        await db.usage_counters.create_index([("subject_id", 1), ("metric", 1), ("period", 1)])
        await db.notifications.create_index([("workspace_id", 1), ("created_at", -1)])
        await db.idempotency_keys.create_index([("key", 1), ("scope", 1)], unique=True)
        await db.leads.create_index("workspace_id")
        await db.login_attempts.create_index("identifier", unique=True)
        await db.workspaces.create_index("referral_code")
        await db.referral_reward_grants.create_index([("referrer_ws_id", 1), ("index", 1)], unique=True)
        await db.referrals.create_index("status")
        await db.billing_events.create_index("key", unique=True)
    except Exception as e:
        logger.warning(f"platform index setup: {e}")

    # Seed plans + regional prices + markets
    for p in DEFAULT_PLANS:
        await db.plans.update_one({"id": p["id"]}, {"$setOnInsert": p}, upsert=True)
    for pid, rp in DEFAULT_REGIONAL_PRICES.items():
        await db.plans.update_one({"id": pid}, {"$set": {"regional_prices": rp}})
    for m in DEFAULT_MARKETS:
        await db.markets.update_one({"code": m["code"]}, {"$setOnInsert": m}, upsert=True)

    # Backfill global region defaults on existing workspaces (non-destructive)
    async for ws in db.workspaces.find({"region": {"$exists": False}}, {"_id": 0, "id": 1}):
        await db.workspaces.update_one({"id": ws["id"]}, {"$set": {
            "region": default_region("US"),
            "tax": {"tax_country": "US", "tax_inclusive": False, "tax_id": "", "status": "unregistered"},
        }})
    await db.users.update_many({"language": {"$exists": False}},
                               {"$set": {"language": "en", "locale": "en-US", "timezone": "America/New_York"}})

    # Promote existing admin -> SUPER_ADMIN + ensure a workspace, attach existing cards.
    admin_email = os.environ.get("ADMIN_EMAIL", "").lower()
    admin = await db.users.find_one({"email": admin_email}) if admin_email else None
    if admin:
        if admin.get("role") != "SUPER_ADMIN":
            await db.users.update_one({"id": admin["id"]}, {"$set": {"role": "SUPER_ADMIN", "email_verified": True}})
        ws = await db.workspaces.find_one({"owner_id": admin["id"]})
        if not ws:
            ws_id = str(uuid.uuid4())
            await db.workspaces.insert_one({
                "id": ws_id, "name": "TapPresence HQ", "type": "company", "plan": "enterprise",
                "owner_id": admin["id"], "branding": {}, "locked_fields": [], "created_at": now_iso(),
            })
            await db.memberships.insert_one({
                "id": str(uuid.uuid4()), "user_id": admin["id"], "workspace_id": ws_id,
                "role": "WORKSPACE_OWNER", "status": "active", "created_at": now_iso(),
            })
        else:
            ws_id = ws["id"]
        # Attach any card without workspace_id to the admin workspace (preserves feras-askar)
        await db.digital_cards.update_many({"workspace_id": {"$exists": False}}, {"$set": {"workspace_id": ws_id}})
        # Backfill CRM defaults on legacy leads
        await db.leads.update_many({"status": {"$exists": False}},
                                   {"$set": {"status": "NEW", "tags": [], "source": "inquiry"}})
    logger.info("platform migration complete")
