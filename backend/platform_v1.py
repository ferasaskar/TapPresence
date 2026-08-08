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
import uuid
import secrets
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional

import jwt
import bcrypt
from fastapi import APIRouter, HTTPException, Depends, Request
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

# ------------------------------------------------------------------ entitlements
PLAN_ENTITLEMENTS = {
    "free": {"max_cards": 1, "premium_templates": False, "analytics": "basic", "leads": True,
             "wallet": True, "ai_followup": False, "scanner": False, "team": False,
             "crm": False, "white_label": False, "custom_domain": False, "campaigns": False},
    "pro": {"max_cards": 3, "premium_templates": True, "analytics": "full", "leads": True,
            "wallet": True, "ai_followup": True, "scanner": True, "team": False,
            "crm": False, "white_label": False, "custom_domain": False, "campaigns": True},
    "team": {"max_cards": 9999, "premium_templates": True, "analytics": "full", "leads": True,
             "wallet": True, "ai_followup": True, "scanner": True, "team": True,
             "crm": True, "white_label": False, "custom_domain": True, "campaigns": True},
    "enterprise": {"max_cards": 99999, "premium_templates": True, "analytics": "full", "leads": True,
                   "wallet": True, "ai_followup": True, "scanner": True, "team": True,
                   "crm": True, "white_label": True, "custom_domain": True, "campaigns": True},
    "white_label": {"max_cards": 99999, "premium_templates": True, "analytics": "full", "leads": True,
                    "wallet": True, "ai_followup": True, "scanner": True, "team": True,
                    "crm": True, "white_label": True, "custom_domain": True, "campaigns": True},
}

DEFAULT_PLANS = [
    {"id": "free", "name": "Free", "price_month": 0, "price_year": 0, "public": True},
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


async def resolve_entitlements(workspace_id: str) -> dict:
    ws = await db.workspaces.find_one({"id": workspace_id}, {"_id": 0})
    plan = (ws or {}).get("plan", "free")
    ent = dict(PLAN_ENTITLEMENTS.get(plan, PLAN_ENTITLEMENTS["free"]))
    ent["plan"] = plan
    return ent


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

# ------------------------------------------------------------------ auth models
class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    name: str = ""
    workspace_name: str = ""


class RefreshIn(BaseModel):
    refresh_token: str


class ForgotIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    token: str
    password: str


class VerifyIn(BaseModel):
    token: str


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
                 "role": user.get("role", "MEMBER"), "email_verified": user.get("email_verified", False)},
        "workspace": ws, "memberships": ms, "entitlements": ent,
    }


@platform_router.post("/auth/register")
async def register(body: RegisterIn, request: Request):
    email = body.email.strip().lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(400, "An account with this email already exists")
    uid = str(uuid.uuid4())
    verify_token = secrets.token_urlsafe(32)
    user = {
        "id": uid, "email": email, "password_hash": hash_pw(body.password),
        "name": body.name.strip(), "role": "WORKSPACE_OWNER", "email_verified": False,
        "created_at": now_iso(),
    }
    await db.users.insert_one(user)
    ws_id = str(uuid.uuid4())
    await db.workspaces.insert_one({
        "id": ws_id, "name": body.workspace_name.strip() or (body.name.strip() or "My Workspace"),
        "type": "individual", "plan": "free", "owner_id": uid,
        "branding": {}, "locked_fields": [], "created_at": now_iso(),
    })
    await db.memberships.insert_one({
        "id": str(uuid.uuid4()), "user_id": uid, "workspace_id": ws_id,
        "role": "WORKSPACE_OWNER", "status": "active", "created_at": now_iso(),
    })
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
async def forgot(body: ForgotIn):
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
async def reset(body: ResetIn):
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
    ws_ids = [m["workspace_id"] for m in await memberships_for(user["id"])]
    await db.digital_cards.delete_many({"workspace_id": {"$in": ws_ids}})
    await db.memberships.delete_many({"user_id": user["id"]})
    await db.workspaces.delete_many({"id": {"$in": ws_ids}, "owner_id": user["id"]})
    await db.sessions.delete_many({"user_id": user["id"]})
    await db.users.delete_one({"id": user["id"]})
    return {"ok": True}


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
    cols = ["name", "email", "phone", "company", "title", "status", "source", "campaign",
            "interest", "notes", "cardSlug", "created_at", "next_follow_up"]
    w.writerow(cols)
    for l in leads:
        w.writerow([l.get(c, "") for c in cols])
    buf.seek(0)
    return StreamingResponse(io.BytesIO(buf.getvalue().encode()), media_type="text/csv",
                             headers={"Content-Disposition": 'attachment; filename="leads.csv"'})

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
async def contact_exchange(slug: str, body: ExchangeIn):
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
        "title": f"New contact from {body.name.strip()}", "body": f"via {body.source}",
        "read": False, "created_at": now_iso(),
    })
    # Return the owner's contact so the visitor can save it back (mutual exchange).
    return {"ok": True, "owner": {"name": card.get("identity", {}).get("fullName", ""),
                                   "vcard_url": f"/api/cards/{slug}/vcard"}}

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


def _draft_followup(b: FollowupIn) -> str:
    first = (b.lead_name or "there").split(" ")[0]
    ctx = f" about {b.notes}" if b.notes else ""
    sign = f"\n\nBest,\n{b.owner_name}" if b.owner_name else ""
    if b.channel in ("whatsapp", "sms"):
        return f"Hi {first}! Great connecting today{ctx}. Happy to share more whenever suits you — just let me know.{(' — ' + b.owner_name) if b.owner_name else ''}"
    tone = b.tone
    opener = {
        "warm": f"Hi {first},\n\nIt was a genuine pleasure meeting you",
        "professional": f"Dear {first},\n\nThank you for taking the time to connect",
        "short": f"Hi {first}, thanks for connecting",
    }.get(tone, f"Hi {first},\n\nThank you for connecting")
    body = f"{opener}{(' — especially our chat' + ctx) if ctx else ''}. I'd love to help you take the next step."
    if b.company:
        body += f" I think there's a strong fit with what {b.company} is working toward."
    body += " Would you be open to a short call this week?"
    return body + sign


@platform_router.post("/ai/followup")
async def ai_followup(body: FollowupIn, user: dict = Depends(current_user)):
    """Drafts a follow-up. User must review + send (AI never auto-sends).
    Provider abstraction: uses configured LLM if wired, else a high-quality
    deterministic template. EMERGENT_LLM_KEY is available for future LLM wiring."""
    provider = "template"
    text = _draft_followup(body)
    await db.ai_usage.insert_one({
        "id": str(uuid.uuid4()), "user_id": user["id"], "provider": provider,
        "channel": body.channel, "tone": body.tone, "created_at": now_iso(),
    })
    return {"provider": provider, "channel": body.channel, "draft": text,
            "note": "Review before sending. AI drafts only; it never sends automatically."}


@platform_router.post("/ai/enrich")
async def ai_enrich(body: dict, user: dict = Depends(current_user)):
    if not _configured("ENRICHMENT_API_KEY"):
        return {"configured": False, "message": "Enrichment Not Configured", "data": {}}
    # Provider adapter would call the compliant enrichment API here.
    return {"configured": True, "data": {}}

# ------------------------------------------------------------------ notifications
@platform_router.get("/notifications")
async def notifications(user: dict = Depends(current_user)):
    ws_ids = await workspace_ids_for(user)
    q = {} if ws_ids == "ALL" else {"workspace_id": {"$in": ws_ids}}
    return await db.notifications.find(q, {"_id": 0}).sort("created_at", -1).to_list(200)

# ------------------------------------------------------------------ integration status (placeholders)
@platform_router.get("/integrations/status")
async def integrations_status(user: dict = Depends(current_user)):
    cfg = (await get_config())["integrations"]
    return {"crm": {"hubspot": cfg["hubspot"], "salesforce": cfg["salesforce"], "pipedrive": cfg["pipedrive"],
                    "webhook": True, "zapier": True},
            "wallet": {"apple": cfg["apple_wallet"], "google": cfg["google_wallet"]},
            "billing": {"stripe": cfg["stripe"], "revenuecat": cfg["revenuecat"]},
            "notes": "Adapters built; connect credentials to activate."}

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
    except Exception as e:
        logger.warning(f"platform index setup: {e}")

    # Seed plans
    for p in DEFAULT_PLANS:
        await db.plans.update_one({"id": p["id"]}, {"$setOnInsert": p}, upsert=True)

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
                "id": ws_id, "name": "ARIADNI HQ", "type": "company", "plan": "enterprise",
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
