import os
import io
import re
import html
import uuid
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import jwt
import bcrypt
import qrcode
import requests
from PIL import Image, ImageDraw, ImageFont
from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, UploadFile, File, Header
from fastapi.responses import Response, StreamingResponse, RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from seed_data import DEMO_CARD
from platform_v1 import platform_router, run_migration, _auth_payload, member_role, dispatch_webhooks, resolve_entitlements, effective_status, ACTIVE_STATES, rate_limit, client_ip, login_locked, record_login_fail, clear_login_fails, find_duplicate_lead

# ------------------------------------------------------------------ config
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

JWT_SECRET = os.environ['JWT_SECRET']
JWT_ALGORITHM = "HS256"
PUBLIC_APP_URL = os.environ.get('PUBLIC_APP_URL', '').rstrip('/')
APP_NAME = "ariadni-id"

STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()
api_router = APIRouter(prefix="/api")
security = HTTPBearer(auto_error=False)

# ------------------------------------------------------------------ object storage
_storage_key = None


def init_storage(force: bool = False):
    global _storage_key
    if _storage_key and not force:
        return _storage_key
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
    resp.raise_for_status()
    _storage_key = resp.json()["storage_key"]
    return _storage_key


def put_object(path: str, data: bytes, content_type: str) -> dict:
    key = init_storage()
    resp = requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data, timeout=120,
    )
    if resp.status_code == 404:
        key = init_storage(force=True)
        resp = requests.put(
            f"{STORAGE_URL}/objects/{path}",
            headers={"X-Storage-Key": key, "Content-Type": content_type},
            data=data, timeout=120,
        )
    resp.raise_for_status()
    return resp.json()


def get_object(path: str):
    key = init_storage()
    resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    if resp.status_code == 404:
        key = init_storage(force=True)
        resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")


MIME_TYPES = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
              "gif": "image/gif", "webp": "image/webp"}

# ------------------------------------------------------------------ auth helpers

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id: str, email: str) -> str:
    payload = {"sub": user_id, "email": email,
               "exp": datetime.now(timezone.utc) + timedelta(days=7), "type": "access"}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


async def get_current_user(creds: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> dict:
    if not creds or not creds.credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ------------------------------------------------------------------ models

class Identity(BaseModel):
    fullName: str = ""
    jobTitle: str = ""
    company: str = ""
    companyLogo: str = ""
    profilePhoto: str = ""
    bio: str = ""
    city: str = ""
    country: str = ""
    availabilityBadge: str = ""
    imageScale: float = 1.0
    imageOffsetX: float = 0.0
    imageOffsetY: float = 0.0


class Contact(BaseModel):
    phone: str = ""
    whatsapp: str = ""
    email: str = ""
    website: str = ""
    address: str = ""
    mapsUrl: str = ""
    addressLine1: str = ""
    addressLine2: str = ""
    city: str = ""
    adminArea: str = ""
    postalCode: str = ""
    countryCode: str = ""


class Social(BaseModel):
    linkedin: str = ""
    instagram: str = ""
    x: str = ""
    youtube: str = ""
    tiktok: str = ""


class Service(BaseModel):
    icon: str = "Sparkles"
    title: str = ""
    description: str = ""
    ctaUrl: str = ""
    order: int = 0
    enabled: bool = True


class Project(BaseModel):
    coverImage: str = ""
    name: str = ""
    category: str = ""
    description: str = ""
    url: str = ""
    order: int = 0


class Booking(BaseModel):
    bookingUrl: str = ""
    nativeEnabled: bool = False
    timezone: str = "Asia/Dubai"


class CardData(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    slug: str
    templateId: str = "beige-luxury"
    accent: str = "gold"
    custom_accent_color: str = ""
    industry: str = ""
    background_style: str = ""
    background_opacity: float = 0.14
    background_intensity: str = "medium"
    background_position: str = "center"
    custom_background: str = ""
    status: str = "draft"
    identity: Identity = Field(default_factory=Identity)
    contact: Contact = Field(default_factory=Contact)
    social: Social = Field(default_factory=Social)
    actions: List[str] = Field(default_factory=list)
    services: List[Service] = Field(default_factory=list)
    projects: List[Project] = Field(default_factory=list)
    booking: Booking = Field(default_factory=Booking)
    workspace_id: Optional[str] = None
    owner_user_id: Optional[str] = None
    created_by: Optional[str] = None
    languages: List[str] = Field(default_factory=lambda: ["en"])
    i18n: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CardUpsert(BaseModel):
    slug: str
    templateId: str = "beige-luxury"
    accent: str = "gold"
    custom_accent_color: str = ""
    industry: str = ""
    background_style: str = ""
    background_opacity: float = 0.14
    background_intensity: str = "medium"
    background_position: str = "center"
    custom_background: str = ""
    status: str = "draft"
    identity: Identity = Field(default_factory=Identity)
    contact: Contact = Field(default_factory=Contact)
    social: Social = Field(default_factory=Social)
    actions: List[str] = Field(default_factory=list)
    services: List[Service] = Field(default_factory=list)
    projects: List[Project] = Field(default_factory=list)
    booking: Booking = Field(default_factory=Booking)
    languages: List[str] = Field(default_factory=lambda: ["en"])
    i18n: Dict[str, Any] = Field(default_factory=dict)


class LoginIn(BaseModel):
    email: str
    password: str


class LeadIn(BaseModel):
    name: str
    email: str = ""
    phone: str = ""
    message: str = ""


class TrackIn(BaseModel):
    type: str  # view | scan | tap
    key: str = ""

# ------------------------------------------------------------------ auth routes

@api_router.post("/auth/login")
async def login(body: LoginIn, request: Request):
    rate_limit(request, "login", 30, 300)
    email = body.email.strip().lower()
    ip = client_ip(request)
    locked_until = await login_locked(email, ip)
    if locked_until:
        raise HTTPException(status_code=429, detail="Too many failed attempts. Please try again in a few minutes.")
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user["password_hash"]):
        await record_login_fail(email, ip)
        raise HTTPException(status_code=401, detail="Invalid email or password")
    await clear_login_fails(email, ip)
    if user.get("suspended"):
        raise HTTPException(status_code=403, detail="This account has been suspended. Please contact support.")
    return await _auth_payload(user, request)


async def _user_ws_ids(user: dict):
    if user.get("role") == "SUPER_ADMIN":
        return "ALL"
    ms = await db.memberships.find({"user_id": user["id"]}, {"_id": 0}).to_list(100)
    return [m["workspace_id"] for m in ms]


ADMIN_WS_ROLES = ("WORKSPACE_OWNER", "WORKSPACE_ADMIN", "MANAGER")


async def _card_query(user: dict):
    """Cards visible to the caller: admins see whole workspace, members see only their own."""
    if user.get("role") == "SUPER_ADMIN":
        return {}
    ms = await db.memberships.find({"user_id": user["id"]}, {"_id": 0}).to_list(100)
    ors = []
    for m in ms:
        if m.get("role") in ADMIN_WS_ROLES:
            ors.append({"workspace_id": m["workspace_id"]})
        else:
            ors.append({"workspace_id": m["workspace_id"], "owner_user_id": user["id"]})
    return {"$or": ors} if ors else {"id": "__none__"}


async def _can_access_card(user: dict, card: dict) -> bool:
    if user.get("role") == "SUPER_ADMIN":
        return True
    m = await db.memberships.find_one({"user_id": user["id"], "workspace_id": card.get("workspace_id")}, {"_id": 0})
    if not m:
        return False
    if m.get("role") in ADMIN_WS_ROLES:
        return True
    return card.get("owner_user_id") == user["id"]


@api_router.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return user

# ------------------------------------------------------------------ public card

def _public_card(card: dict) -> dict:
    card.pop("_id", None)
    return card


def _apply_lang(card: dict, lang: str) -> dict:
    """Merge localized i18n overrides for the requested language (fallback: base)."""
    i18n = card.get("i18n") or {}
    langs = card.get("languages") or ["en"]
    default_lang = langs[0] if langs else "en"
    use = lang if (lang and lang in i18n) else None
    card["_activeLang"] = lang if (lang and lang in langs) else default_lang
    card["_availableLangs"] = langs
    if not use:
        return card
    ov = i18n[use]
    idn = card.get("identity", {})
    for k in ("bio", "jobTitle", "company", "availabilityBadge"):
        if ov.get(k):
            idn[k] = ov[k]
    card["identity"] = idn
    for coll, keys in (("services", ("title", "description")), ("projects", ("name", "category", "description"))):
        items = card.get(coll, [])
        ov_items = ov.get(coll, [])
        for i, it in enumerate(items):
            if i < len(ov_items) and isinstance(ov_items[i], dict):
                for k in keys:
                    if ov_items[i].get(k):
                        it[k] = ov_items[i][k]
    return card


@api_router.get("/cards/{slug}")
async def get_public_card(slug: str, lang: str = None):
    card = await db.digital_cards.find_one({"slug": slug, "status": "published"}, {"_id": 0})
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    # Commercial Core: if the owner's subscription is inactive (trial expired / cancelled),
    # the public card is paused (data preserved; owner reactivates by subscribing).
    wsid = card.get("workspace_id")
    if wsid:
        ent = await resolve_entitlements(wsid)
        if not ent.get("active"):
            raise HTTPException(status_code=410, detail="This card is currently inactive.")
    return _apply_lang(card, lang)


def _abs_url(u: str) -> str:
    """Resolve a stored image reference to an absolute, crawler-fetchable URL."""
    if not u:
        return ""
    if u.startswith("http://") or u.startswith("https://"):
        return u
    if u.startswith("/") and PUBLIC_APP_URL:
        return f"{PUBLIC_APP_URL}{u}"
    return ""


def _clip(text: str, limit: int) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


@api_router.get("/og/{slug}")
async def card_og(slug: str, lang: str = None):
    """Crawler-visible per-card Open Graph / Twitter metadata.

    Serves a minimal HTML document (no SPA execution required) using ONLY public
    card fields. Respects publication + active-subscription rules; unknown, draft
    or paused cards return 404 so no private/unpublished data is exposed. Human
    browsers are redirected to the normal React public profile."""
    card = await db.digital_cards.find_one({"slug": slug, "status": "published"}, {"_id": 0})
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    wsid = card.get("workspace_id")
    if wsid:
        ent = await resolve_entitlements(wsid)
        if not ent.get("active"):
            raise HTTPException(status_code=404, detail="Card not found")
    card = _apply_lang(card, lang)
    idn = card.get("identity", {}) or {}

    name = (idn.get("fullName") or slug).strip()
    job = (idn.get("jobTitle") or "").strip()
    company = (idn.get("company") or "").strip()
    bio = (idn.get("bio") or "").strip()

    role_line = " · ".join([p for p in (job, company) if p])
    title = f"{name} — {role_line}" if role_line else name
    if role_line:
        desc = bio or f"Connect with {name}, {role_line}. Save the contact, book a meeting and exchange details — powered by TapPresence."
    else:
        desc = bio or f"Connect with {name}. Save the contact, book a meeting and exchange details — powered by TapPresence."
    title = _clip(title, 90)
    desc = _clip(desc, 200)

    image = _abs_url(idn.get("profilePhoto") or "")
    if not image:
        image = f"{PUBLIC_APP_URL}/logo512.png" if PUBLIC_APP_URL else "/logo512.png"
    canonical = f"{PUBLIC_APP_URL}/{slug}" if PUBLIC_APP_URL else f"/{slug}"

    active_lang = card.get("_activeLang") or "en"
    is_rtl = active_lang == "ar"
    e = html.escape
    doc = f"""<!doctype html>
<html lang="{e(active_lang)}"{' dir="rtl"' if is_rtl else ''}>
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}" />
<link rel="canonical" href="{e(canonical)}" />
<meta property="og:type" content="profile" />
<meta property="og:site_name" content="TapPresence" />
<meta property="og:title" content="{e(title)}" />
<meta property="og:description" content="{e(desc)}" />
<meta property="og:url" content="{e(canonical)}" />
<meta property="og:image" content="{e(image)}" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="{e(title)}" />
<meta name="twitter:description" content="{e(desc)}" />
<meta name="twitter:image" content="{e(image)}" />
<script>
  // Real browsers that land here go straight to the interactive card; crawlers stay for the tags.
  (function () {{
    try {{
      var ua = navigator.userAgent || "";
      var isBot = /bot|crawl|spider|facebookexternalhit|slurp|bing|preview|whatsapp|telegram|slack|discord|embed|linkedin|twitter|pinterest|applebot/i.test(ua);
      if (!isBot) window.location.replace("/{e(slug)}");
    }} catch (err) {{}}
  }})();
</script>
</head>
<body>
<h1>{e(title)}</h1>
<p>{e(desc)}</p>
<p><a href="{e(canonical)}">Open {e(name)}'s TapPresence card</a></p>
</body>
</html>"""
    return Response(content=doc, media_type="text/html; charset=utf-8",
                    headers={"Cache-Control": "public, max-age=300"})



@api_router.get("/cards/{slug}/vcard")
async def get_vcard(slug: str):
    card = await db.digital_cards.find_one({"slug": slug, "status": "published"}, {"_id": 0})
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    wsid = card.get("workspace_id")
    if wsid:
        ent = await resolve_entitlements(wsid)
        if not ent.get("active"):
            raise HTTPException(status_code=410, detail="This card is currently inactive.")
    idn = card.get("identity", {})
    ct = card.get("contact", {})
    name = idn.get("fullName", "")
    parts = name.split(" ", 1)
    last = parts[1] if len(parts) > 1 else ""
    first = parts[0] if parts else ""
    lines = [
        "BEGIN:VCARD", "VERSION:3.0",
        f"N:{last};{first};;;",
        f"FN:{name}",
    ]
    if idn.get("company"):
        lines.append(f"ORG:{idn['company']}")
    if idn.get("jobTitle"):
        lines.append(f"TITLE:{idn['jobTitle']}")
    if ct.get("phone"):
        lines.append(f"TEL;TYPE=CELL:{ct['phone']}")
    if ct.get("email"):
        lines.append(f"EMAIL;TYPE=INTERNET:{ct['email']}")
    if ct.get("website"):
        lines.append(f"URL:{ct['website']}")
    if ct.get("address"):
        lines.append(f"ADR;TYPE=WORK:;;{ct['address']};;;;")
    if idn.get("bio"):
        lines.append(f"NOTE:{idn['bio']}")
    lines.append("END:VCARD")
    vcf = "\n".join(lines)
    return Response(
        content=vcf,
        media_type="text/vcard",
        headers={"Content-Disposition": f'attachment; filename="{slug}.vcf"'},
    )


# ------------------------------------------------------------------ Phase P: idempotency (retry-safe public writes)
async def idempotency_lookup(key: str, scope: str):
    if not key:
        return None
    doc = await db.idempotency_keys.find_one({"key": key, "scope": scope}, {"_id": 0})
    return doc.get("response") if doc else None


async def idempotency_store(key: str, scope: str, response: dict):
    if not key:
        return
    try:
        await db.idempotency_keys.insert_one({
            "key": key, "scope": scope, "response": response,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception:
        pass  # duplicate key race — the first write wins, safe to ignore



@api_router.post("/cards/{slug}/leads")
async def create_lead(slug: str, body: LeadIn, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    cached = await idempotency_lookup(idempotency_key, f"lead:{slug}")
    if cached is not None:
        return cached
    card = await db.digital_cards.find_one({"slug": slug, "status": "published"}, {"_id": 0, "id": 1, "workspace_id": 1})
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    if not body.name.strip() or not (body.email.strip() or body.phone.strip()):
        raise HTTPException(status_code=400, detail="Name and an email or phone are required")
    now = datetime.now(timezone.utc).isoformat()
    # Inbound dedupe: same person re-submitting on the same card updates the existing lead, no dupes.
    dup = await find_duplicate_lead(slug, body.email, body.phone)
    if dup:
        upd = {"last_activity": now, "updated_at": now, "read": False}
        msg = body.message.strip()
        if msg:
            prev = dup.get("notes", "")
            upd["notes"] = f"{prev}\n[{now[:10]}] {msg}".strip() if prev else f"[{now[:10]}] {msg}"
        await db.leads.update_one({"id": dup["id"]}, {"$set": upd, "$inc": {"touches": 1}})
        result = {"ok": True, "merged": True}
        await idempotency_store(idempotency_key, f"lead:{slug}", result)
        return result
    lead = {
        "id": str(uuid.uuid4()), "cardSlug": slug, "workspace_id": card.get("workspace_id"),
        "name": body.name.strip(), "email": body.email.strip(), "phone": body.phone.strip(),
        "company": "", "title": "", "website": "", "message": body.message.strip(), "interest": "",
        "source": "inquiry", "campaign": "", "event": "", "met_at": now, "captured_by": "",
        "next_follow_up": "", "status": "new", "tags": [], "notes": "",
        "read": False, "created_at": now, "updated_at": now, "last_activity": now,
    }
    await db.leads.insert_one(lead)
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()), "workspace_id": card.get("workspace_id"), "type": "new_lead",
        "card_slug": slug, "scope": "card",
        "title": f"New inquiry from {body.name.strip()}", "body": f"via /{slug}",
        "read": False, "created_at": now,
    })
    await dispatch_webhooks(card.get("workspace_id"), "lead.created", {"id": lead["id"], "name": lead["name"], "cardSlug": slug, "source": lead["source"]})
    result = {"ok": True}
    await idempotency_store(idempotency_key, f"lead:{slug}", result)
    return result


@api_router.post("/cards/{slug}/track")
async def track_event(slug: str, body: TrackIn):
    if body.type not in ("view", "scan", "tap"):
        return {"ok": False}
    await db.analytics_events.insert_one({
        "id": str(uuid.uuid4()), "cardSlug": slug, "type": body.type, "key": body.key,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"ok": True}


TP_MARK_PATH = str(Path(__file__).resolve().parent.parent / "frontend" / "public" / "tp-mark.png")


def _brand_qr(url: str, fill: str = "#0B0D12", back: str = "#FFFFFF"):
    """Existing QR with the official TapPresence mark centered. Error correction bumped to H so the
    small (~20%) center logo never affects scan reliability."""
    qr = qrcode.QRCode(version=None, box_size=10, border=2,
                       error_correction=qrcode.constants.ERROR_CORRECT_H)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color=fill, back_color=back).convert("RGBA")
    try:
        logo = Image.open(TP_MARK_PATH).convert("RGBA")
        qw, qh = img.size
        lw = int(qw * 0.35)  # largest professionally-scannable size; H-level EC (30% recovery) + tight white backing keeps decode reliable (pyzbar-verified original + 300px + 3x, short & long slugs)
        logo = logo.resize((lw, lw), Image.LANCZOS)
        pad = max(3, lw // 12)
        backing = Image.new("RGBA", (lw + 2 * pad, lw + 2 * pad), (255, 255, 255, 255))
        bx, by = (qw - backing.width) // 2, (qh - backing.height) // 2
        img.paste(backing, (bx, by), backing)
        img.paste(logo, ((qw - lw) // 2, (qh - lw) // 2), logo)
    except Exception:
        pass
    return img.convert("RGB")


@api_router.get("/cards/{slug}/qr")
async def get_qr(slug: str):
    url = f"{PUBLIC_APP_URL}/{slug}?src=qr" if PUBLIC_APP_URL else f"/{slug}?src=qr"
    img = _brand_qr(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")


def _font(size, serif=True, bold=False):
    candidates = [
        f"/usr/share/fonts/truetype/dejavu/DejaVuSerif{'-Bold' if bold else ''}.ttf" if serif else None,
        f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if bold else ''}.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in [c for c in candidates if c]:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _center(draw, text, font, y, w, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text(((w - tw) / 2, y), text, font=font, fill=fill)
    return bbox[3] - bbox[1]


@api_router.get("/cards/{slug}/poster")
async def get_poster(slug: str):
    card = await db.digital_cards.find_one({"slug": slug}, {"_id": 0})
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    idn = card.get("identity", {})
    W, H = 1080, 1350
    poster = Image.new("RGB", (W, H), "#FAFAF8")
    d = ImageDraw.Draw(poster)
    # top overline
    d.rectangle([0, 0, W, 14], fill="#B89973")
    _center(d, "TapPresence", _font(30, serif=False), 70, W, "#B89973")
    _center(d, idn.get("fullName", slug), _font(96, bold=True), 150, W, "#2D2B2A")
    _center(d, idn.get("jobTitle", ""), _font(40, serif=False), 280, W, "#66615E")
    d.line([(W / 2 - 90, 360), (W / 2 + 90, 360)], fill="#B89973", width=3)
    # QR
    qr = qrcode.QRCode(box_size=10, border=1, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(f"{PUBLIC_APP_URL}/{slug}?src=qr" if PUBLIC_APP_URL else f"/{slug}?src=qr")
    qr.make(fit=True)
    qimg = qr.make_image(fill_color="#2D2B2A", back_color="#FAFAF8").convert("RGB").resize((560, 560), Image.NEAREST)
    qx = int((W - 560) / 2)
    d.rounded_rectangle([qx - 40, 440, qx + 600, 1080], radius=28, outline="#E5E1D8", width=3, fill="#F4F1EB")
    poster.paste(qimg, (qx, 480))
    _center(d, "Scan to connect", _font(46), 1120, W, "#2D2B2A")
    company = idn.get("company", "")
    if company:
        _center(d, company, _font(34, serif=False), 1200, W, "#66615E")
    _center(d, f"{PUBLIC_APP_URL}/{slug}".replace("https://", "").replace("http://", ""), _font(26, serif=False), 1270, W, "#B89973")
    buf = io.BytesIO()
    poster.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png",
                             headers={"Content-Disposition": f'attachment; filename="{slug}-poster.png"'})

# ------------------------------------------------------------------ admin cards

@api_router.get("/admin/cards")
async def list_cards(user: dict = Depends(get_current_user)):
    q = await _card_query(user)
    cards = await db.digital_cards.find(q, {"_id": 0}).to_list(1000)
    cards.sort(key=lambda c: c.get("created_at", ""))
    return cards


@api_router.get("/admin/cards/{card_id}")
async def get_card_admin(card_id: str, user: dict = Depends(get_current_user)):
    card = await db.digital_cards.find_one({"id": card_id}, {"_id": 0})
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    if not await _can_access_card(user, card):
        raise HTTPException(status_code=403, detail="Not your card")
    return card


@api_router.post("/admin/cards")
async def create_card(body: CardUpsert, user: dict = Depends(get_current_user)):
    existing = await db.digital_cards.find_one({"slug": body.slug})
    if existing:
        raise HTTPException(status_code=400, detail="Slug already exists")
    ms = await db.memberships.find_one({"user_id": user["id"]}, {"_id": 0})
    wsid = ms["workspace_id"] if ms else None
    # Commercial Core: enforce plan card limit + active subscription (SUPER_ADMIN exempt)
    if user.get("role") != "SUPER_ADMIN" and wsid:
        ent = await resolve_entitlements(wsid)
        if not ent.get("active"):
            raise HTTPException(status_code=402, detail="Your trial has ended. Subscribe to create cards.")
        owned = await db.digital_cards.count_documents({"workspace_id": wsid, "owner_user_id": user["id"]})
        if owned >= ent.get("max_cards", 1):
            raise HTTPException(status_code=402, detail=f"Your {ent['plan']} plan allows up to {ent['max_cards']} card(s). Upgrade to add more.")
    card = CardData(**body.model_dump())
    doc = card.model_dump()
    doc["workspace_id"] = wsid
    doc["owner_user_id"] = user["id"]
    doc["created_by"] = user["id"]
    await db.digital_cards.insert_one(doc)
    return await db.digital_cards.find_one({"id": card.id}, {"_id": 0})


@api_router.post("/admin/cards/{card_id}/duplicate")
async def duplicate_card(card_id: str, user: dict = Depends(get_current_user)):
    existing = await db.digital_cards.find_one({"id": card_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Card not found")
    if not await _can_access_card(user, existing):
        raise HTTPException(status_code=403, detail="Not your card")
    base = re.sub(r"-copy(-[a-z0-9]+)?$", "", existing.get("slug", "") or "card")
    new_slug = f"{base}-copy-{uuid.uuid4().hex[:5]}"
    while await db.digital_cards.find_one({"slug": new_slug}):
        new_slug = f"{base}-copy-{uuid.uuid4().hex[:5]}"
    payload = {k: existing.get(k) for k in CardUpsert.model_fields.keys() if k in existing}
    payload["slug"] = new_slug
    payload["status"] = "draft"
    card = CardData(**payload)
    doc = card.model_dump()
    ms = await db.memberships.find_one({"user_id": user["id"]}, {"_id": 0})
    doc["workspace_id"] = existing.get("workspace_id") or (ms["workspace_id"] if ms else None)
    doc["owner_user_id"] = existing.get("owner_user_id") or user["id"]
    doc["created_by"] = user["id"]
    await db.digital_cards.insert_one(doc)
    return await db.digital_cards.find_one({"id": card.id}, {"_id": 0})


@api_router.put("/admin/cards/{card_id}")
async def update_card(card_id: str, body: CardUpsert, user: dict = Depends(get_current_user)):
    existing = await db.digital_cards.find_one({"id": card_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Card not found")
    if not await _can_access_card(user, existing):
        raise HTTPException(status_code=403, detail="Not your card")
    slug_owner = await db.digital_cards.find_one({"slug": body.slug})
    if slug_owner and slug_owner["id"] != card_id:
        raise HTTPException(status_code=400, detail="Slug already used by another card")
    update = body.model_dump()
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    # Locked corporate branding: MEMBERs cannot change locked fields.
    wsid = existing.get("workspace_id")
    if user.get("role") != "SUPER_ADMIN" and wsid:
        role = await member_role(user["id"], wsid)
        if role == "MEMBER":
            wsdoc = await db.workspaces.find_one({"id": wsid}, {"_id": 0, "locked_fields": 1})
            for f in (wsdoc or {}).get("locked_fields", []):
                if f in ("templateId", "accent"):
                    update[f] = existing.get(f)
                    if f == "accent":
                        update["custom_accent_color"] = existing.get("custom_accent_color", "")
                elif f == "industry":
                    update["industry"] = existing.get("industry", "")
                elif f == "background":
                    for bf in ("background_style", "custom_background", "background_opacity", "background_intensity", "background_position"):
                        update[bf] = existing.get(bf, update.get(bf))
                elif f in ("company", "companyLogo"):
                    update.setdefault("identity", {})
                    update["identity"][f] = existing.get("identity", {}).get(f, "")
    await db.digital_cards.update_one({"id": card_id}, {"$set": update})
    return await db.digital_cards.find_one({"id": card_id}, {"_id": 0})


@api_router.delete("/admin/cards/{card_id}")
async def delete_card(card_id: str, user: dict = Depends(get_current_user)):
    existing = await db.digital_cards.find_one({"id": card_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Card not found")
    if not await _can_access_card(user, existing):
        raise HTTPException(status_code=403, detail="Not your card")
    await db.digital_cards.delete_one({"id": card_id})
    return {"ok": True}


@api_router.get("/admin/leads")
async def list_leads(slug: str = None, user: dict = Depends(get_current_user)):
    # Tenant isolation: only leads on cards the caller can access.
    q = await _card_query(user)
    cards = await db.digital_cards.find(q, {"_id": 0, "slug": 1}).to_list(5000)
    slugs = [c["slug"] for c in cards]
    if slug is not None:
        if slug not in slugs:
            raise HTTPException(status_code=403, detail="Not your card")
        lq = {"cardSlug": slug}
    else:
        lq = {"cardSlug": {"$in": slugs}}
    leads = await db.leads.find(lq, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return leads


async def _lead_or_403(lead_id: str, user: dict):
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    card = await db.digital_cards.find_one({"slug": lead.get("cardSlug")}, {"_id": 0})
    if not card or not await _can_access_card(user, card):
        raise HTTPException(status_code=403, detail="Not your lead")
    return lead


@api_router.patch("/admin/leads/{lead_id}")
async def mark_lead_read(lead_id: str, user: dict = Depends(get_current_user)):
    await _lead_or_403(lead_id, user)
    await db.leads.update_one({"id": lead_id}, {"$set": {"read": True}})
    return {"ok": True}


class LeadFieldsIn(BaseModel):
    company: Optional[str] = None
    title: Optional[str] = None
    website: Optional[str] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    interest: Optional[str] = None
    met_at: Optional[str] = None
    event: Optional[str] = None
    campaign: Optional[str] = None
    next_follow_up: Optional[str] = None


@api_router.patch("/admin/leads/{lead_id}/fields")
async def update_lead_fields(lead_id: str, body: LeadFieldsIn, user: dict = Depends(get_current_user)):
    """Edit lightweight contact-context fields on an existing lead (company/title/website/tags/notes/met_at/event/campaign/next_follow_up)."""
    await _lead_or_403(lead_id, user)
    upd = {k: v for k, v in body.model_dump().items() if v is not None}
    now = datetime.now(timezone.utc).isoformat()
    upd["updated_at"] = now
    upd["last_activity"] = now
    await db.leads.update_one({"id": lead_id}, {"$set": upd})
    return await db.leads.find_one({"id": lead_id}, {"_id": 0})


@api_router.post("/admin/leads/{lead_id}/remind")
async def set_lead_reminder(lead_id: str, body: Dict[str, Any], user: dict = Depends(get_current_user)):
    """Set/replace a follow-up reminder. Stores next_follow_up on the lead and creates ONE in-app
    notification that surfaces in the Notification Center at the chosen time. Replacing/cancelling
    removes the previous pending reminder so no duplicates accumulate."""
    lead = await _lead_or_403(lead_id, user)
    when = str(body.get("when", "")).strip()
    if not when:
        raise HTTPException(status_code=400, detail="A reminder date/time is required")
    note = str(body.get("note", "")).strip()
    now = datetime.now(timezone.utc).isoformat()
    # remove any existing pending reminder for this lead (idempotent, no duplicates)
    await db.notifications.delete_many({"type": "lead_reminder", "lead_id": lead_id})
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()), "type": "lead_reminder",
        "recipient_user_id": user["id"], "workspace_id": lead.get("workspace_id"),
        "scope": "card", "card_slug": lead.get("cardSlug"), "lead_id": lead_id,
        "remind_at": when,
        "title": f"Follow up with {lead.get('name', 'lead')}",
        "body": note or f"Scheduled follow-up · /{lead.get('cardSlug', '')}",
        "read": False, "created_at": when,
    })
    await db.leads.update_one({"id": lead_id}, {"$set": {"next_follow_up": when, "updated_at": now, "last_activity": now}})
    return {"ok": True, "next_follow_up": when}


@api_router.delete("/admin/leads/{lead_id}/remind")
async def clear_lead_reminder(lead_id: str, user: dict = Depends(get_current_user)):
    await _lead_or_403(lead_id, user)
    await db.notifications.delete_many({"type": "lead_reminder", "lead_id": lead_id})
    now = datetime.now(timezone.utc).isoformat()
    await db.leads.update_one({"id": lead_id}, {"$set": {"next_follow_up": "", "updated_at": now}})
    return {"ok": True}


@api_router.delete("/admin/leads/{lead_id}")
async def delete_lead(lead_id: str, user: dict = Depends(get_current_user)):
    await _lead_or_403(lead_id, user)
    await db.notifications.delete_many({"type": "lead_reminder", "lead_id": lead_id})
    await db.leads.delete_one({"id": lead_id})
    return {"ok": True}


# Richer pipeline: New, Contacted, Qualified, Meeting, Opportunity, Customer, Not Interested.
LEAD_STAGES = ("new", "contacted", "qualified", "meeting", "opportunity", "customer", "not_interested")
LEGACY_STAGE_ALIASES = {
    "meeting_booked": "meeting", "converted": "customer", "archived": "not_interested",
    "won": "customer", "lost": "not_interested", "follow_up": "contacted",
}


def normalize_stage(s: str) -> str:
    s = (s or "new").strip().lower()
    return LEGACY_STAGE_ALIASES.get(s, s)


@api_router.patch("/admin/leads/{lead_id}/status")
async def set_lead_status(lead_id: str, body: Dict[str, Any], user: dict = Depends(get_current_user)):
    """Move a lead through the existing pipeline. Uses the lead model's existing `status` field."""
    await _lead_or_403(lead_id, user)
    st = normalize_stage(str(body.get("status", "")))
    if st not in LEAD_STAGES:
        raise HTTPException(status_code=400, detail="Invalid status")
    now = datetime.now(timezone.utc).isoformat()
    await db.leads.update_one({"id": lead_id}, {"$set": {"status": st, "updated_at": now, "last_activity": now}})
    return {"ok": True}


@api_router.get("/admin/cards/{card_id}/analytics")
async def card_analytics(card_id: str, user: dict = Depends(get_current_user)):
    card = await db.digital_cards.find_one({"id": card_id}, {"_id": 0})
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    if not await _can_access_card(user, card):
        raise HTTPException(status_code=403, detail="Not your card")
    slug = card["slug"]
    events = await db.analytics_events.find({"cardSlug": slug}, {"_id": 0}).to_list(10000)
    views = sum(1 for e in events if e["type"] == "view")
    scans = sum(1 for e in events if e["type"] == "scan")
    taps = [e for e in events if e["type"] == "tap"]
    by_key = {}
    for e in taps:
        by_key[e["key"] or "other"] = by_key.get(e["key"] or "other", 0) + 1
    leads_count = await db.leads.count_documents({"cardSlug": slug})
    # last 7 day view timeseries
    from collections import Counter
    days = Counter()
    for e in events:
        if e["type"] in ("view", "scan"):
            days[e["created_at"][:10]] += 1
    series = sorted([{"date": k, "count": v} for k, v in days.items()], key=lambda x: x["date"])[-7:]
    return {"views": views, "scans": scans, "taps": len(taps), "tapsByKey": by_key,
            "leads": leads_count, "series": series}


@api_router.get("/admin/analytics/overview")
async def analytics_overview(days: int = 30, start: str = None, end: str = None, user: dict = Depends(get_current_user)):
    return await _compute_overview(user, days, start, end)


@api_router.get("/admin/analytics/export.csv")
async def analytics_export(days: int = 30, start: str = None, end: str = None, user: dict = Depends(get_current_user)):
    import csv
    ov = await _compute_overview(user, days, start, end)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["TapPresence Analytics Export", f"last {ov['range_days']} days"])
    w.writerow([])
    f = ov["funnel"]
    w.writerow(["Funnel"]); w.writerow(["Stage", "Count"])
    for k in ["views", "engaged", "leads", "meetings_booked", "meetings_completed"]:
        w.writerow([k, f.get(k, 0)])
    ch = ov["channels"]
    w.writerow([]); w.writerow(["Channel", "Count"])
    for k in ["direct", "qr", "nfc"]:
        w.writerow([k, ch.get(k, 0)])
    w.writerow(["scanner_leads", ov["breakdowns"].get("scanner_leads", 0)])
    for title, key, cols in [
        ("By card", "by_card", ["name", "slug", "views", "leads", "meetings"]),
        ("Leads by source", "by_source", ["key", "count"]),
        ("Leads by event", "by_event", ["key", "count"]),
        ("Leads by campaign", "by_campaign", ["key", "count"]),
        ("By team member", "by_member", ["name", "count"]),
    ]:
        rows = ov["breakdowns"].get(key, [])
        w.writerow([]); w.writerow([title]); w.writerow(cols)
        for r in rows:
            w.writerow([r.get(c, "") for c in cols])
    data = buf.getvalue()
    return StreamingResponse(iter([data]), media_type="text/csv",
                             headers={"Content-Disposition": f"attachment; filename=tappresence-analytics-{days}d.csv"})


async def _compute_overview(user: dict, days: int = 30, start: str = None, end: str = None):
    """Read-only conversion funnel + trend aggregated across all cards the caller can access.
    Reuses existing analytics_events / leads / meetings — no writes, no new event semantics.
    Accepts either a rolling `days` window or an explicit `start`/`end` ISO range (Today/Week/Month/Custom)."""
    from collections import Counter
    now = datetime.now(timezone.utc)
    if start:
        cutoff = start
        try:
            _end_dt = datetime.fromisoformat(end.replace("Z", "+00:00")) if end else now
            days = max(1, (_end_dt - datetime.fromisoformat(start.replace("Z", "+00:00"))).days + 1)
        except Exception:
            days = 30
    else:
        days = max(1, min(int(days or 30), 365))
        cutoff = (now - timedelta(days=days)).isoformat()
    upper = end

    def tw():
        q = {"$gte": cutoff}
        if upper:
            q["$lte"] = upper
        return q

    q = await _card_query(user)
    cards = await db.digital_cards.find(q, {"_id": 0, "id": 1, "slug": 1, "status": 1}).to_list(5000)
    slugs = [c["slug"] for c in cards]
    ids = [c["id"] for c in cards]
    published = sum(1 for c in cards if c.get("status") == "published")

    events = await db.analytics_events.find(
        {"cardSlug": {"$in": slugs}, "created_at": tw()}, {"_id": 0}).to_list(50000)
    views = sum(1 for e in events if e["type"] == "view")
    scans = sum(1 for e in events if e["type"] == "scan")
    nfctaps = sum(1 for e in events if e["type"] == "nfctap")
    taps = [e for e in events if e["type"] == "tap"]
    by_key = Counter((e.get("key") or "other") for e in taps)
    top_actions = [{"key": k, "count": v} for k, v in by_key.most_common(6)]

    leads_total = await db.leads.count_documents({"cardSlug": {"$in": slugs}}) if slugs else 0
    leads_window = await db.leads.count_documents(
        {"cardSlug": {"$in": slugs}, "created_at": tw()}) if slugs else 0
    meetings_booked = await db.meetings.count_documents(
        {"card_id": {"$in": ids}, "created_at": tw()}) if ids else 0
    meetings_completed = await db.meetings.count_documents(
        {"card_id": {"$in": ids}, "status": "completed", "created_at": tw()}) if ids else 0

    day_counts = Counter()
    for e in events:
        if e["type"] in ("view", "scan"):
            day_counts[e["created_at"][:10]] += 1
    series = sorted([{"date": k, "count": v} for k, v in day_counts.items()], key=lambda x: x["date"])[-min(days, 30):]

    # ---- Breakdowns (single analytics store; no new events, no writes) ----
    SCAN_SOURCES = {"business_card_scan", "badge_scan", "qr_scan"}
    lead_docs = await db.leads.find(
        {"cardSlug": {"$in": slugs}, "created_at": tw()},
        {"_id": 0, "cardSlug": 1, "source": 1, "event": 1, "campaign": 1, "captured_by": 1}).to_list(20000) if slugs else []
    meet_docs = await db.meetings.find(
        {"card_id": {"$in": ids}, "created_at": tw()}, {"_id": 0, "card_id": 1}).to_list(20000) if ids else []

    id_to_slug = {c["id"]: c["slug"] for c in cards}
    name_by_slug = {}
    for c in await db.digital_cards.find({"slug": {"$in": slugs}}, {"_id": 0, "slug": 1, "identity": 1}).to_list(5000):
        name_by_slug[c["slug"]] = (c.get("identity", {}) or {}).get("fullName", "") or c["slug"]

    views_by_slug = Counter(e["cardSlug"] for e in events if e["type"] in ("view", "scan", "nfctap"))
    leads_by_slug = Counter(l["cardSlug"] for l in lead_docs)
    meets_by_slug = Counter(id_to_slug.get(m["card_id"]) for m in meet_docs if id_to_slug.get(m["card_id"]))
    by_card = sorted(
        [{"slug": s, "name": name_by_slug.get(s, s), "views": views_by_slug.get(s, 0),
          "leads": leads_by_slug.get(s, 0), "meetings": meets_by_slug.get(s, 0)} for s in slugs],
        key=lambda x: (x["views"] + x["leads"] * 3 + x["meetings"] * 5), reverse=True)[:10]

    by_source = [{"key": k, "count": v} for k, v in Counter((l.get("source") or "inquiry") for l in lead_docs).most_common()]
    scanner_leads = sum(v for l in lead_docs for v in [1] if (l.get("source") in SCAN_SOURCES))
    by_event = [{"key": k, "count": v} for k, v in Counter((l.get("event") or "").strip() for l in lead_docs if (l.get("event") or "").strip()).most_common(10)]
    by_campaign = [{"key": k, "count": v} for k, v in Counter((l.get("campaign") or "").strip() for l in lead_docs if (l.get("campaign") or "").strip()).most_common(10)]

    member_counts = Counter((l.get("captured_by") or "").strip() for l in lead_docs if (l.get("captured_by") or "").strip())
    members = []
    if member_counts:
        users = await db.users.find({"id": {"$in": list(member_counts)}}, {"_id": 0, "id": 1, "name": 1}).to_list(200)
        uname = {u["id"]: u.get("name") or u["id"] for u in users}
        members = sorted([{"key": uid, "name": uname.get(uid, "Teammate"), "count": c} for uid, c in member_counts.items()],
                         key=lambda x: x["count"], reverse=True)[:10]

    return {
        "range_days": days,
        "cards": len(cards),
        "published": published,
        "funnel": {
            "views": views,
            "engaged": len(taps),
            "leads": leads_window,
            "meetings_booked": meetings_booked,
            "meetings_completed": meetings_completed,
        },
        "totals": {"views": views, "scans": scans, "taps": len(taps), "leads_all_time": leads_total},
        "channels": {"direct": views, "qr": scans, "nfc": nfctaps},
        "breakdowns": {
            "by_card": by_card,
            "by_source": by_source,
            "scanner_leads": scanner_leads,
            "by_event": by_event,
            "by_campaign": by_campaign,
            "by_member": members,
        },
        "top_actions": top_actions,
        "series": series,
    }



# ------------------------------------------------------------------ native meetings / calendar
DEFAULT_AVAIL = {"days": [1, 2, 3, 4, 5], "start": "09:00", "end": "18:00",
                 "buffer_before": 0, "buffer_after": 15, "min_notice_hours": 2,
                 "max_days": 60, "slot_interval": 30, "blocked": []}
DEFAULT_MTS = [
    {"title": "15 Min Introduction", "duration": 15},
    {"title": "30 Min Consultation", "duration": 30},
    {"title": "45 Min Meeting", "duration": 45},
]
ACTIVE_STATUSES = ("scheduled", "confirmed", "requested", "time_proposed")
NO_SHOW_GRACE_MIN = 15


class MeetingTypeIn(BaseModel):
    title: str = "Meeting"
    description: str = ""
    duration: int = 30
    location_type: str = "video"  # in_person | phone | video | custom
    location_detail: str = ""
    enabled: bool = True
    price: Optional[float] = None
    order: int = 0
    confirmation_mode: str = "auto"  # auto | approval


class AvailabilityIn(BaseModel):
    days: List[int] = Field(default_factory=lambda: [1, 2, 3, 4, 5])
    start: str = "09:00"
    end: str = "18:00"
    buffer_before: int = 0
    buffer_after: int = 15
    min_notice_hours: int = 2
    max_days: int = 60
    slot_interval: int = 30
    blocked: List[Dict[str, Any]] = Field(default_factory=list)


class BookIn(BaseModel):
    meeting_type_id: str
    start: str  # UTC ISO
    name: str
    email: str = ""
    phone: str = ""
    note: str = ""
    visitor_tz: str = "UTC"


async def _get_availability(card_id: str):
    doc = await db.availability.find_one({"card_id": card_id}, {"_id": 0})
    if not doc:
        doc = {"card_id": card_id, **DEFAULT_AVAIL}
        await db.availability.insert_one(dict(doc))
    return doc


async def _get_meeting_types(card_id: str, only_enabled=False, seed=True):
    mts = await db.meeting_types.find({"card_id": card_id}, {"_id": 0}).sort("order", 1).to_list(100)
    if not mts and seed:
        mts = []
        for i, d in enumerate(DEFAULT_MTS):
            mt = {"id": str(uuid.uuid4()), "card_id": card_id, "title": d["title"], "description": "",
                  "duration": d["duration"], "location_type": "video", "location_detail": "",
                  "enabled": True, "price": None, "order": i, "confirmation_mode": "auto"}
            await db.meeting_types.insert_one(dict(mt))
            mts.append(mt)
    if only_enabled:
        mts = [m for m in mts if m.get("enabled")]
    return mts


def _hhmm(s):
    h, m = s.split(":")
    return int(h), int(m)


async def _existing_intervals(card_id: str):
    ms = await db.meetings.find({"card_id": card_id, "status": {"$in": list(ACTIVE_STATUSES)}}, {"_id": 0}).to_list(2000)
    out = []
    for m in ms:
        try:
            out.append((datetime.fromisoformat(m["start_utc"]), datetime.fromisoformat(m["end_utc"])))
        except Exception:
            pass
    return out


def _day_slots(avail, tzname, duration, date_str, existing, now_utc):
    try:
        tz = ZoneInfo(tzname or "UTC")
    except Exception:
        tz = ZoneInfo("UTC")
    y, mo, d = map(int, date_str.split("-"))
    day = datetime(y, mo, d, tzinfo=tz)
    if day.isoweekday() not in avail.get("days", []):
        return []
    sh, sm = _hhmm(avail.get("start", "09:00"))
    eh, em = _hhmm(avail.get("end", "18:00"))
    cur = day.replace(hour=sh, minute=sm, second=0, microsecond=0)
    end_work = day.replace(hour=eh, minute=em, second=0, microsecond=0)
    interval = int(avail.get("slot_interval", 30)) or 30
    bb = int(avail.get("buffer_before", 0))
    ba = int(avail.get("buffer_after", 0))
    min_notice = now_utc + timedelta(hours=int(avail.get("min_notice_hours", 0)))
    max_dt = now_utc + timedelta(days=int(avail.get("max_days", 60)))
    blocked = []
    for b in avail.get("blocked", []):
        try:
            blocked.append((datetime.fromisoformat(b["start"]), datetime.fromisoformat(b["end"])))
        except Exception:
            pass
    slots = []
    while cur + timedelta(minutes=duration) <= end_work:
        s_utc = cur.astimezone(timezone.utc)
        e_utc = (cur + timedelta(minutes=duration)).astimezone(timezone.utc)
        if min_notice <= s_utc <= max_dt:
            bs = s_utc - timedelta(minutes=bb)
            be = e_utc + timedelta(minutes=ba)
            conflict = any(not (be <= ex[0] or bs >= ex[1]) for ex in existing + blocked)
            if not conflict:
                slots.append(s_utc.isoformat())
        cur += timedelta(minutes=interval)
    return slots


@api_router.get("/cards/{slug}/booking")
async def public_booking_config(slug: str):
    card = await db.digital_cards.find_one({"slug": slug, "status": "published"}, {"_id": 0})
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    b = card.get("booking", {}) or {}
    native = bool(b.get("nativeEnabled"))
    mts = await _get_meeting_types(card["id"], only_enabled=True, seed=native) if native else []
    return {
        "native_enabled": native,
        "external_url": b.get("bookingUrl", ""),
        "owner_name": card.get("identity", {}).get("fullName", ""),
        "owner_timezone": b.get("timezone", "Asia/Dubai"),
        "meeting_types": mts,
    }


@api_router.get("/cards/{slug}/slots")
async def public_slots(slug: str, meeting_type_id: str, date: str):
    card = await db.digital_cards.find_one({"slug": slug, "status": "published"}, {"_id": 0, "id": 1, "booking": 1})
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    mt = await db.meeting_types.find_one({"id": meeting_type_id, "card_id": card["id"]}, {"_id": 0})
    if not mt:
        raise HTTPException(status_code=404, detail="Meeting type not found")
    avail = await _get_availability(card["id"])
    tzname = (card.get("booking", {}) or {}).get("timezone", "Asia/Dubai")
    existing = await _existing_intervals(card["id"])
    slots = _day_slots(avail, tzname, int(mt["duration"]), date, existing, datetime.now(timezone.utc))
    return {"date": date, "owner_timezone": tzname, "duration": mt["duration"], "slots": slots}


@api_router.post("/cards/{slug}/book")
async def public_book(slug: str, body: BookIn, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    cached = await idempotency_lookup(idempotency_key, f"book:{slug}")
    if cached is not None:
        return cached
    card = await db.digital_cards.find_one({"slug": slug, "status": "published"}, {"_id": 0})
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    if not body.name.strip() or not (body.email.strip() or body.phone.strip()):
        raise HTTPException(status_code=400, detail="Name and an email or phone are required")
    mt = await db.meeting_types.find_one({"id": body.meeting_type_id, "card_id": card["id"]}, {"_id": 0})
    if not mt:
        raise HTTPException(status_code=404, detail="Meeting type not found")
    try:
        start_utc = datetime.fromisoformat(body.start.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid start time")
    avail = await _get_availability(card["id"])
    tzname = (card.get("booking", {}) or {}).get("timezone", "Asia/Dubai")
    date_str = start_utc.astimezone(ZoneInfo(tzname)).strftime("%Y-%m-%d")
    existing = await _existing_intervals(card["id"])
    valid = _day_slots(avail, tzname, int(mt["duration"]), date_str, existing, datetime.now(timezone.utc))
    if start_utc.isoformat() not in valid:
        raise HTTPException(status_code=409, detail="That time is no longer available")
    end_utc = start_utc + timedelta(minutes=int(mt["duration"]))
    now = datetime.now(timezone.utc).isoformat()

    # CRM: attach to existing lead or create one
    lead = None
    if body.email.strip():
        lead = await db.leads.find_one({"cardSlug": slug, "email": body.email.strip().lower()}, {"_id": 0})
    if lead:
        await db.leads.update_one({"id": lead["id"]}, {"$set": {"last_activity": now, "updated_at": now, "read": False}})
        lead_id = lead["id"]
    else:
        lead_id = str(uuid.uuid4())
        await db.leads.insert_one({
            "id": lead_id, "cardSlug": slug, "workspace_id": card.get("workspace_id"),
            "name": body.name.strip(), "email": body.email.strip().lower(), "phone": body.phone.strip(),
            "company": "", "title": "", "message": body.note.strip(), "interest": mt["title"],
            "source": "meeting_booking", "campaign": "", "status": "NEW", "tags": ["meeting"], "notes": "",
            "read": False, "created_at": now, "updated_at": now, "last_activity": now,
        })

    manage_token = uuid.uuid4().hex + uuid.uuid4().hex[:8]
    approval = str(mt.get("confirmation_mode", "auto")) == "approval"
    status = "requested" if approval else "scheduled"
    meeting = {
        "id": str(uuid.uuid4()), "manage_token": manage_token, "card_id": card["id"], "cardSlug": slug,
        "workspace_id": card.get("workspace_id"), "owner_user_id": card.get("owner_user_id"),
        "lead_id": lead_id, "meeting_type_id": mt["id"], "meeting_type_title": mt["title"],
        "duration": mt["duration"], "location_type": mt.get("location_type", "video"),
        "location_detail": mt.get("location_detail", ""), "owner_name": card.get("identity", {}).get("fullName", ""),
        "owner_timezone": tzname, "visitor_name": body.name.strip(), "visitor_email": body.email.strip(),
        "visitor_phone": body.phone.strip(), "visitor_tz": body.visitor_tz or "UTC", "note": body.note.strip(),
        "start_utc": start_utc.isoformat(), "end_utc": end_utc.isoformat(),
        "status": status, "confirmation_mode": "approval" if approval else "auto", "created_at": now, "updated_at": now,
        "reminders": [{"offset_hours": 24, "status": "scheduled", "provider": "NOT_CONFIGURED"},
                      {"offset_hours": 1, "status": "scheduled", "provider": "NOT_CONFIGURED"}],
        "history": [{"at": now, "event": "requested" if approval else "booked", "by": "guest"}],
    }
    await db.meetings.insert_one(dict(meeting))
    await db.leads.update_one({"id": lead_id}, {"$push": {"timeline": {"at": now, "event": "meeting_requested" if approval else "meeting_booked", "detail": mt["title"]}}})
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()), "workspace_id": card.get("workspace_id"), "type": "meeting_booked",
        "card_slug": slug, "scope": "card",
        "title": (f"Meeting request from {body.name.strip()}" if approval else f"Meeting booked by {body.name.strip()}"), "body": f"{mt['title']} · via /{slug}", "read": False, "created_at": now,
    })
    await db.analytics_events.insert_one({"id": str(uuid.uuid4()), "cardSlug": slug, "type": "tap", "key": "booking_completed", "created_at": now})
    await dispatch_webhooks(card.get("workspace_id"), "meeting.booked", {"id": meeting["id"], "guest": body.name.strip(), "type": mt["title"], "start_utc": meeting.get("start_utc"), "cardSlug": slug})
    await sync_meeting_calendar(meeting["id"])
    meeting.pop("_id", None)
    result = {"ok": True, "manage_token": manage_token, "meeting": meeting}
    await idempotency_store(idempotency_key, f"book:{slug}", result)
    return result


def _sanitize_meeting(m: dict) -> dict:
    m.pop("_id", None)
    return m


# ============================ Google Calendar integration (separate flow — does NOT touch Sign-In) ============================
import httpx as _httpx
import urllib.parse as _urlparse

GCAL_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID") or ""
GCAL_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET") or ""
GCAL_REDIRECT_URI = os.environ.get("GOOGLE_CALENDAR_REDIRECT_URI") or ""
# Minimum scope needed to create/update/delete events (+ openid/email to label the connection).
GCAL_SCOPE = "openid email https://www.googleapis.com/auth/calendar.events"
GCAL_ACTIVE_STATUSES = {"scheduled", "rescheduled", "confirmed"}


def _gcal_configured() -> bool:
    return bool(GCAL_CLIENT_ID and GCAL_CLIENT_SECRET and GCAL_REDIRECT_URI)


def _gcal_frontend_base() -> str:
    suffix = "/api/integrations/google/calendar/callback"
    if GCAL_REDIRECT_URI.endswith(suffix):
        return GCAL_REDIRECT_URI[: -len(suffix)]
    return PUBLIC_APP_URL


class _NeedsReconnect(Exception):
    pass


async def _gcal_access_token(user_id: str):
    """Valid access token for the user (refreshing if needed). None if not connected.
    Raises _NeedsReconnect if the stored grant was revoked/invalidated. Tokens never leave the server."""
    conn = await db.google_calendar_connections.find_one({"user_id": user_id}, {"_id": 0})
    if not conn or conn.get("revoked"):
        return None
    now = datetime.now(timezone.utc)
    exp = conn.get("access_expiry")
    if conn.get("access_token") and exp and datetime.fromisoformat(exp) > now + timedelta(seconds=60):
        return conn["access_token"]
    rt = conn.get("refresh_token")
    if not rt:
        return None
    async with _httpx.AsyncClient(timeout=15) as cx:
        r = await cx.post("https://oauth2.googleapis.com/token", data={
            "client_id": GCAL_CLIENT_ID, "client_secret": GCAL_CLIENT_SECRET,
            "refresh_token": rt, "grant_type": "refresh_token"})
    if r.status_code != 200:
        gerr = ""
        try:
            gerr = (r.json() or {}).get("error", "")
        except Exception:
            pass
        logging.error(f"[gcal] token refresh failed user={user_id} http={r.status_code} error={gerr}")
        if gerr in ("invalid_grant", "invalid_client"):
            await db.google_calendar_connections.update_one({"user_id": user_id}, {"$set": {"revoked": True, "updated_at": now.isoformat()}})
            raise _NeedsReconnect()
        return None
    tok = r.json()
    at = tok.get("access_token")
    new_exp = (now + timedelta(seconds=int(tok.get("expires_in", 3600)))).isoformat()
    await db.google_calendar_connections.update_one({"user_id": user_id}, {"$set": {"access_token": at, "access_expiry": new_exp, "revoked": False, "updated_at": now.isoformat()}})
    return at


def _gcal_event_body(m: dict) -> dict:
    loc = m.get("location_detail") or ("Video call" if m.get("location_type") == "video" else "")
    lines = [f"Booked via TapPresence (/{m.get('cardSlug', '')})",
             f"Guest: {m.get('visitor_name', '')}",
             f"Email: {m.get('visitor_email', '')}" if m.get("visitor_email") else "",
             f"Phone: {m.get('visitor_phone', '')}" if m.get("visitor_phone") else "",
             f"Note: {m.get('note', '')}" if m.get("note") else ""]
    body = {
        "summary": f"{m.get('meeting_type_title', 'Meeting')} with {m.get('visitor_name', 'guest')}",
        "description": "\n".join([l for l in lines if l]),
        "start": {"dateTime": m["start_utc"], "timeZone": "UTC"},
        "end": {"dateTime": m["end_utc"], "timeZone": "UTC"},
        "extendedProperties": {"private": {"tappresence_meeting_id": m["id"]}},
    }
    if loc:
        body["location"] = loc
    ve = (m.get("visitor_email") or "").strip()
    if ve:
        body["attendees"] = [{"email": ve, "displayName": m.get("visitor_name", "")}]
    return body


async def sync_meeting_calendar(meeting_id: str):
    """Create/update/delete the Google Calendar event on the OWNER's calendar for a TapPresence meeting.
    No-op if the owner hasn't connected Calendar. Only touches events this app created (stored google_event_id).
    Never raises to the caller — a Calendar hiccup must never break booking."""
    try:
        m = await db.meetings.find_one({"id": meeting_id}, {"_id": 0})
        if not m or not _gcal_configured():
            return
        owner = m.get("owner_user_id")
        if not owner:
            return
        conn = await db.google_calendar_connections.find_one({"user_id": owner}, {"_id": 0, "revoked": 1})
        if not conn or conn.get("revoked"):
            return
        try:
            at = await _gcal_access_token(owner)
        except _NeedsReconnect:
            return
        if not at:
            return
        headers = {"Authorization": f"Bearer {at}", "Content-Type": "application/json"}
        eid = m.get("google_event_id")
        base = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
        async def _flag_if_denied(resp):
            if resp.status_code in (401, 403):
                await db.google_calendar_connections.update_one({"user_id": owner}, {"$set": {"needs_reconnect": True}})
                logging.error(f"[gcal] calendar access denied http={resp.status_code} user={owner} — needs reconnect")

        async with _httpx.AsyncClient(timeout=15) as cx:
            if m.get("status") in ("cancelled", "declined"):
                if eid:
                    rd = await cx.delete(f"{base}/{eid}", headers=headers)
                    if rd.status_code in (200, 204, 404, 410):
                        await db.meetings.update_one({"id": meeting_id}, {"$set": {"google_event_id": None}})
                    else:
                        await _flag_if_denied(rd)
                        logging.error(f"[gcal] event delete failed http={rd.status_code} event={eid}")
                return
            body = _gcal_event_body(m)
            if eid:
                rp = await cx.patch(f"{base}/{eid}", headers=headers, json=body)
                if rp.status_code not in (200, 201):
                    await _flag_if_denied(rp)
                    logging.error(f"[gcal] event patch failed http={rp.status_code} event={eid}")
            elif m.get("status") in GCAL_ACTIVE_STATUSES:
                r = await cx.post(base, headers=headers, json=body)
                if r.status_code in (200, 201):
                    new_id = (r.json() or {}).get("id")
                    if new_id:
                        await db.meetings.update_one({"id": meeting_id}, {"$set": {"google_event_id": new_id}})
                else:
                    await _flag_if_denied(r)
                    logging.error(f"[gcal] event insert failed http={r.status_code}")
    except Exception as e:
        logging.error(f"[gcal] sync error meeting={meeting_id}: {type(e).__name__}: {e}")


@api_router.get("/integrations/google/calendar/status")
async def gcal_status(user: dict = Depends(get_current_user)):
    if not _gcal_configured():
        return {"configured": False, "connected": False}
    conn = await db.google_calendar_connections.find_one({"user_id": user["id"]}, {"_id": 0})
    if not conn:
        return {"configured": True, "connected": False}
    scope_ok = "calendar.events" in (conn.get("scope") or "")
    needs = bool(conn.get("revoked")) or bool(conn.get("needs_reconnect")) or not scope_ok
    reason = "calendar_permission_missing" if not scope_ok else ("reauth_required" if needs else None)
    return {"configured": True,
            "connected": (not conn.get("revoked", False)) and scope_ok and not conn.get("needs_reconnect", False),
            "needs_reconnect": needs, "reason": reason, "email": conn.get("email"),
            "connected_at": conn.get("connected_at")}


@api_router.get("/integrations/google/calendar/connect")
async def gcal_connect(user: dict = Depends(get_current_user)):
    """Returns the Google consent URL (called via XHR with the app JWT, so no token ends up in a navigable URL)."""
    if not _gcal_configured():
        raise HTTPException(status_code=503, detail="Google Calendar is not configured")
    state = jwt.encode({"sub": user["id"], "type": "gcal_state",
                        "exp": datetime.now(timezone.utc) + timedelta(minutes=10)}, JWT_SECRET, algorithm=JWT_ALGORITHM)
    params = {"client_id": GCAL_CLIENT_ID, "redirect_uri": GCAL_REDIRECT_URI, "response_type": "code",
              "scope": GCAL_SCOPE, "access_type": "offline", "prompt": "consent",
              "include_granted_scopes": "true", "state": state}
    return {"authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?" + _urlparse.urlencode(params)}


@api_router.get("/integrations/google/calendar/callback")
async def gcal_callback(code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None):
    fb = _gcal_frontend_base()
    dest = f"{fb}/settings?tab=integrations"
    if error or not code or not state:
        return RedirectResponse(f"{dest}&calendar=error&reason={error or 'missing'}")
    try:
        st = jwt.decode(state, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if st.get("type") != "gcal_state":
            raise ValueError()
        user_id = st["sub"]
    except Exception:
        return RedirectResponse(f"{dest}&calendar=error&reason=state")
    try:
        async with _httpx.AsyncClient(timeout=15) as cx:
            tok = await cx.post("https://oauth2.googleapis.com/token", data={
                "code": code, "client_id": GCAL_CLIENT_ID, "client_secret": GCAL_CLIENT_SECRET,
                "redirect_uri": GCAL_REDIRECT_URI, "grant_type": "authorization_code"})
            if tok.status_code != 200:
                gerr = ""
                try:
                    gerr = (tok.json() or {}).get("error", "")
                except Exception:
                    pass
                logging.error(f"[gcal] token exchange failed http={tok.status_code} error={gerr}")
                return RedirectResponse(f"{dest}&calendar=error&reason={gerr or 'exchange'}")
            t = tok.json()
            access_tok = t.get("access_token")
            refresh_tok = t.get("refresh_token")
            ui = await cx.get("https://www.googleapis.com/oauth2/v2/userinfo", headers={"Authorization": f"Bearer {access_tok}"})
            email = (ui.json().get("email") if ui.status_code == 200 else "") or ""
    except Exception as e:
        logging.error(f"[gcal] callback exception: {type(e).__name__}: {e}")
        return RedirectResponse(f"{dest}&calendar=error&reason=network")
    now = datetime.now(timezone.utc)
    granted_scope = t.get("scope", "") or ""
    if "calendar.events" not in granted_scope:
        logging.error(f"[gcal] calendar.events scope NOT granted user={user_id} (granted='{granted_scope}')")
        return RedirectResponse(f"{dest}&calendar=error&reason=calendar_permission_denied")
    existing = await db.google_calendar_connections.find_one({"user_id": user_id}, {"_id": 0, "refresh_token": 1})
    if not refresh_tok and not (existing and existing.get("refresh_token")):
        logging.error(f"[gcal] no refresh_token returned for user={user_id}")
        return RedirectResponse(f"{dest}&calendar=error&reason=no_refresh_token")
    setd = {"user_id": user_id, "email": email.lower(), "access_token": access_tok,
            "access_expiry": (now + timedelta(seconds=int(t.get("expires_in", 3600)))).isoformat(),
            "scope": granted_scope, "revoked": False, "needs_reconnect": False, "updated_at": now.isoformat()}
    if refresh_tok:
        setd["refresh_token"] = refresh_tok  # only present on first consent / prompt=consent
    await db.google_calendar_connections.update_one({"user_id": user_id},
        {"$set": setd, "$setOnInsert": {"connected_at": now.isoformat()}}, upsert=True)
    return RedirectResponse(f"{dest}&calendar=connected")


@api_router.post("/integrations/google/calendar/disconnect")
async def gcal_disconnect(user: dict = Depends(get_current_user)):
    conn = await db.google_calendar_connections.find_one({"user_id": user["id"]}, {"_id": 0})
    if conn:
        revoke_tok = conn.get("refresh_token") or conn.get("access_token")
        if revoke_tok:
            try:
                async with _httpx.AsyncClient(timeout=10) as cx:
                    await cx.post("https://oauth2.googleapis.com/revoke", data={"token": revoke_tok},
                                  headers={"Content-Type": "application/x-www-form-urlencoded"})
            except Exception:
                pass
        await db.google_calendar_connections.delete_one({"user_id": user["id"]})
    return {"ok": True}


@api_router.get("/meetings/manage/{token}")
async def manage_get(token: str):
    m = await db.meetings.find_one({"manage_token": token}, {"_id": 0})
    if not m:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return _sanitize_meeting(m)


@api_router.post("/meetings/manage/{token}/cancel")
async def manage_cancel(token: str):
    m = await db.meetings.find_one({"manage_token": token}, {"_id": 0})
    if not m:
        raise HTTPException(status_code=404, detail="Meeting not found")
    now = datetime.now(timezone.utc).isoformat()
    await db.meetings.update_one({"manage_token": token}, {"$set": {"status": "cancelled", "updated_at": now},
                                 "$push": {"history": {"at": now, "event": "cancelled", "by": "guest"}}})
    if m.get("lead_id"):
        await db.leads.update_one({"id": m["lead_id"]}, {"$push": {"timeline": {"at": now, "event": "meeting_cancelled", "detail": m.get("meeting_type_title", "")}}})
    await sync_meeting_calendar(m["id"])
    return {"ok": True}


@api_router.post("/meetings/manage/{token}/reschedule")
async def manage_reschedule(token: str, body: Dict[str, Any]):
    m = await db.meetings.find_one({"manage_token": token}, {"_id": 0})
    if not m:
        raise HTTPException(status_code=404, detail="Meeting not found")
    try:
        start_utc = datetime.fromisoformat(str(body.get("start", "")).replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid start time")
    avail = await _get_availability(m["card_id"])
    existing = [iv for iv in await _existing_intervals(m["card_id"])]
    date_str = start_utc.astimezone(ZoneInfo(m.get("owner_timezone", "UTC"))).strftime("%Y-%m-%d")
    valid = _day_slots(avail, m.get("owner_timezone", "UTC"), int(m["duration"]), date_str, existing, datetime.now(timezone.utc))
    if start_utc.isoformat() not in valid and start_utc.isoformat() != m["start_utc"]:
        raise HTTPException(status_code=409, detail="That time is no longer available")
    end_utc = start_utc + timedelta(minutes=int(m["duration"]))
    now = datetime.now(timezone.utc).isoformat()
    await db.meetings.update_one({"manage_token": token}, {"$set": {
        "start_utc": start_utc.isoformat(), "end_utc": end_utc.isoformat(), "status": "rescheduled", "updated_at": now,
        "reminders": [{"offset_hours": 24, "status": "scheduled", "provider": "NOT_CONFIGURED"}, {"offset_hours": 1, "status": "scheduled", "provider": "NOT_CONFIGURED"}]},
        "$push": {"history": {"at": now, "event": "rescheduled", "by": "guest"}}})
    await sync_meeting_calendar(m["id"])
    return {"ok": True}


# ---- admin: meeting types + availability + meetings
async def _own_card_or_403(card_id, user):
    card = await db.digital_cards.find_one({"id": card_id}, {"_id": 0})
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    if not await _can_access_card(user, card):
        raise HTTPException(status_code=403, detail="Not your card")
    return card


@api_router.get("/admin/cards/{card_id}/meeting-types")
async def admin_list_mts(card_id: str, user: dict = Depends(get_current_user)):
    await _own_card_or_403(card_id, user)
    return await _get_meeting_types(card_id, seed=True)


@api_router.post("/admin/cards/{card_id}/meeting-types")
async def admin_create_mt(card_id: str, body: MeetingTypeIn, user: dict = Depends(get_current_user)):
    await _own_card_or_403(card_id, user)
    mt = {"id": str(uuid.uuid4()), "card_id": card_id, **body.model_dump()}
    await db.meeting_types.insert_one(dict(mt))
    mt.pop("_id", None)
    return mt


@api_router.put("/admin/cards/{card_id}/meeting-types/{mt_id}")
async def admin_update_mt(card_id: str, mt_id: str, body: MeetingTypeIn, user: dict = Depends(get_current_user)):
    await _own_card_or_403(card_id, user)
    await db.meeting_types.update_one({"id": mt_id, "card_id": card_id}, {"$set": body.model_dump()})
    return await db.meeting_types.find_one({"id": mt_id}, {"_id": 0})


@api_router.delete("/admin/cards/{card_id}/meeting-types/{mt_id}")
async def admin_delete_mt(card_id: str, mt_id: str, user: dict = Depends(get_current_user)):
    await _own_card_or_403(card_id, user)
    await db.meeting_types.delete_one({"id": mt_id, "card_id": card_id})
    return {"ok": True}


@api_router.get("/admin/cards/{card_id}/availability")
async def admin_get_avail(card_id: str, user: dict = Depends(get_current_user)):
    await _own_card_or_403(card_id, user)
    return await _get_availability(card_id)


@api_router.put("/admin/cards/{card_id}/availability")
async def admin_put_avail(card_id: str, body: AvailabilityIn, user: dict = Depends(get_current_user)):
    await _own_card_or_403(card_id, user)
    await db.availability.update_one({"card_id": card_id}, {"$set": {"card_id": card_id, **body.model_dump()}}, upsert=True)
    return await db.availability.find_one({"card_id": card_id}, {"_id": 0})


@api_router.get("/admin/meetings")
async def admin_meetings(filter: str = "upcoming", user: dict = Depends(get_current_user)):
    q = await _card_query(user)
    cards = await db.digital_cards.find(q, {"_id": 0, "id": 1}).to_list(2000)
    ids = [c["id"] for c in cards]
    now = datetime.now(timezone.utc).isoformat()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    base = {"card_id": {"$in": ids}}
    if filter == "today":
        base["start_utc"] = {"$gte": today, "$lt": today + "T99"}
        base["status"] = {"$in": list(ACTIVE_STATUSES) + ["rescheduled"]}
    elif filter == "upcoming":
        base["start_utc"] = {"$gte": now}
        base["status"] = {"$in": list(ACTIVE_STATUSES) + ["rescheduled"]}
    elif filter == "past":
        base["$or"] = [{"start_utc": {"$lt": now}}, {"status": {"$in": ["completed", "no-show"]}}]
        base["status"] = {"$nin": ["cancelled"]}
    elif filter == "cancelled":
        base["status"] = {"$in": ["cancelled", "declined"]}
    ms = await db.meetings.find(base, {"_id": 0}).sort("start_utc", 1 if filter != "past" else -1).to_list(2000)
    return ms


@api_router.patch("/admin/meetings/{meeting_id}/status")
async def admin_meeting_status(meeting_id: str, body: Dict[str, Any], user: dict = Depends(get_current_user)):
    m = await db.meetings.find_one({"id": meeting_id}, {"_id": 0})
    if not m:
        raise HTTPException(status_code=404, detail="Meeting not found")
    card = await db.digital_cards.find_one({"id": m["card_id"]}, {"_id": 0})
    if not card or not await _can_access_card(user, card):
        raise HTTPException(status_code=403, detail="Not your meeting")
    status = str(body.get("status", "")).lower()
    if status not in ("scheduled", "confirmed", "completed", "cancelled", "no-show", "rescheduled", "requested", "declined"):
        raise HTTPException(status_code=400, detail="Invalid status")
    # Temporal eligibility (server time is the source of truth; never trust the client clock).
    now_dt = datetime.now(timezone.utc)
    if status in ("completed", "no-show"):
        try:
            start_dt = datetime.fromisoformat(m["start_utc"])
        except Exception:
            start_dt = None
        if start_dt is not None:
            end_dt = start_dt + timedelta(minutes=int(m.get("duration", 30)))
            if status == "completed" and now_dt < end_dt:
                raise HTTPException(status_code=409, detail="Meeting hasn't ended yet — can't mark completed before its scheduled end time")
            if status == "no-show" and now_dt < start_dt + timedelta(minutes=NO_SHOW_GRACE_MIN):
                raise HTTPException(status_code=409, detail="Too early to mark no-show — wait until after the meeting start + grace period")
    now = now_dt.isoformat()
    await db.meetings.update_one({"id": meeting_id}, {"$set": {"status": status, "updated_at": now},
                                 "$push": {"history": {"at": now, "event": f"status:{status}", "by": user.get("email")}}})
    if status == "completed" and m.get("lead_id"):
        await db.leads.update_one({"id": m["lead_id"]}, {"$push": {"timeline": {"at": now, "event": "meeting_completed", "detail": m.get("meeting_type_title", "")}}})
    if status == "confirmed" and m.get("lead_id"):
        await db.leads.update_one({"id": m["lead_id"]}, {"$push": {"timeline": {"at": now, "event": "meeting_confirmed", "detail": m.get("meeting_type_title", "")}}})
    if status in ("cancelled", "declined") and m.get("lead_id"):
        await db.leads.update_one({"id": m["lead_id"]}, {"$push": {"timeline": {"at": now, "event": "meeting_cancelled", "detail": m.get("meeting_type_title", "")}}})
    await sync_meeting_calendar(meeting_id)
    return {"ok": True}


class OwnerAssignIn(BaseModel):
    owner_user_id: Optional[str] = None


@api_router.put("/admin/cards/{card_id}/owner")
async def assign_card_owner(card_id: str, body: OwnerAssignIn, user: dict = Depends(get_current_user)):
    """Assign a card to a workspace member (business owner). Creator stays in created_by.
    Only SUPER_ADMIN or a workspace admin/manager may reassign."""
    card = await db.digital_cards.find_one({"id": card_id}, {"_id": 0})
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    wsid = card.get("workspace_id")
    if user.get("role") != "SUPER_ADMIN":
        role = await member_role(user["id"], wsid) if wsid else None
        if role not in ADMIN_WS_ROLES:
            raise HTTPException(status_code=403, detail="Only a workspace admin can assign card owners")
    target = (body.owner_user_id or "").strip() or None
    if target:
        mem = await db.memberships.find_one({"user_id": target, "workspace_id": wsid}, {"_id": 0})
        if not mem:
            raise HTTPException(status_code=400, detail="That user is not a member of this workspace")
    now = datetime.now(timezone.utc).isoformat()
    await db.digital_cards.update_one({"id": card_id}, {"$set": {"owner_user_id": target, "updated_at": now}})
    # keep meeting ownership pointer in sync (access is via card, this is denormalized convenience)
    await db.meetings.update_many({"card_id": card_id}, {"$set": {"owner_user_id": target}})
    return await db.digital_cards.find_one({"id": card_id}, {"_id": 0})


@api_router.get("/admin/workspaces/{workspace_id}/members")
async def list_ws_members(workspace_id: str, user: dict = Depends(get_current_user)):
    """Assignable members of a workspace (for the owner-assignment control)."""
    if user.get("role") != "SUPER_ADMIN":
        role = await member_role(user["id"], workspace_id)
        if role not in ADMIN_WS_ROLES:
            raise HTTPException(status_code=403, detail="Not allowed")
    ms = await db.memberships.find({"workspace_id": workspace_id}, {"_id": 0}).to_list(500)
    uids = [m["user_id"] for m in ms]
    users = await db.users.find({"id": {"$in": uids}}, {"_id": 0, "password_hash": 0}).to_list(500)
    role_by = {m["user_id"]: m.get("role") for m in ms}
    return [{"id": u["id"], "name": u.get("name", ""), "email": u.get("email", ""), "role": role_by.get(u["id"])} for u in users]


@api_router.post("/admin/meetings/{meeting_id}/propose")
async def admin_propose_time(meeting_id: str, body: Dict[str, Any], user: dict = Depends(get_current_user)):
    """Owner proposes a new time on a meeting (used with Requires-Approval). Guest must accept."""
    m = await db.meetings.find_one({"id": meeting_id}, {"_id": 0})
    if not m:
        raise HTTPException(status_code=404, detail="Meeting not found")
    card = await db.digital_cards.find_one({"id": m["card_id"]}, {"_id": 0})
    if not card or not await _can_access_card(user, card):
        raise HTTPException(status_code=403, detail="Not your meeting")
    try:
        start_utc = datetime.fromisoformat(str(body.get("start", "")).replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid start time")
    end_utc = start_utc + timedelta(minutes=int(m["duration"]))
    now = datetime.now(timezone.utc).isoformat()
    await db.meetings.update_one({"id": meeting_id}, {"$set": {
        "proposed_start_utc": start_utc.isoformat(), "proposed_end_utc": end_utc.isoformat(),
        "status": "time_proposed", "updated_at": now},
        "$push": {"history": {"at": now, "event": "time_proposed", "by": user.get("email")}}})
    return {"ok": True}


@api_router.post("/meetings/manage/{token}/accept-proposal")
async def manage_accept_proposal(token: str):
    m = await db.meetings.find_one({"manage_token": token}, {"_id": 0})
    if not m:
        raise HTTPException(status_code=404, detail="Meeting not found")
    ps = m.get("proposed_start_utc")
    if not ps:
        raise HTTPException(status_code=400, detail="No proposed time to accept")
    start_utc = datetime.fromisoformat(ps)
    end_utc = start_utc + timedelta(minutes=int(m["duration"]))
    now = datetime.now(timezone.utc).isoformat()
    await db.meetings.update_one({"manage_token": token}, {"$set": {
        "start_utc": start_utc.isoformat(), "end_utc": end_utc.isoformat(), "status": "confirmed",
        "proposed_start_utc": None, "proposed_end_utc": None, "updated_at": now},
        "$push": {"history": {"at": now, "event": "proposal_accepted", "by": "guest"}}})
    if m.get("lead_id"):
        await db.leads.update_one({"id": m["lead_id"]}, {"$push": {"timeline": {"at": now, "event": "meeting_confirmed", "detail": m.get("meeting_type_title", "")}}})
    await sync_meeting_calendar(m["id"])
    return {"ok": True}


@api_router.post("/admin/meetings/{meeting_id}/reschedule")
async def admin_reschedule(meeting_id: str, body: Dict[str, Any], user: dict = Depends(get_current_user)):
    """Owner directly reschedules an active meeting (reuses the same slot-validation engine)."""
    m = await db.meetings.find_one({"id": meeting_id}, {"_id": 0})
    if not m:
        raise HTTPException(status_code=404, detail="Meeting not found")
    card = await db.digital_cards.find_one({"id": m["card_id"]}, {"_id": 0})
    if not card or not await _can_access_card(user, card):
        raise HTTPException(status_code=403, detail="Not your meeting")
    try:
        start_utc = datetime.fromisoformat(str(body.get("start", "")).replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid start time")
    avail = await _get_availability(m["card_id"])
    tzname = m.get("owner_timezone", "UTC")
    date_str = start_utc.astimezone(ZoneInfo(tzname)).strftime("%Y-%m-%d")
    existing = await _existing_intervals(m["card_id"])
    valid = _day_slots(avail, tzname, int(m["duration"]), date_str, existing, datetime.now(timezone.utc))
    if start_utc.isoformat() not in valid and start_utc.isoformat() != m["start_utc"]:
        raise HTTPException(status_code=409, detail="That time is not available")
    end_utc = start_utc + timedelta(minutes=int(m["duration"]))
    now = datetime.now(timezone.utc).isoformat()
    await db.meetings.update_one({"id": meeting_id}, {"$set": {
        "start_utc": start_utc.isoformat(), "end_utc": end_utc.isoformat(), "status": "rescheduled", "updated_at": now},
        "$push": {"history": {"at": now, "event": "rescheduled", "by": user.get("email")}}})
    await sync_meeting_calendar(meeting_id)
    return {"ok": True}


# ------------------------------------------------------------------ uploads

ALLOWED_UPLOAD_EXT = {"jpg", "jpeg", "png", "gif", "webp"}
ALLOWED_UPLOAD_MIME = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB


def _sniff_image_kind(data: bytes):
    """Return the real image kind from magic bytes, or None if not a supported image."""
    if data[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


@api_router.post("/upload")
async def upload(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    ext = file.filename.split(".")[-1].lower() if file.filename and "." in file.filename else ""
    if ext not in ALLOWED_UPLOAD_EXT:
        raise HTTPException(status_code=400, detail="Unsupported file type. Allowed: JPG, PNG, GIF, WEBP.")
    declared_type = (file.content_type or "").lower()
    if declared_type and declared_type not in ALLOWED_UPLOAD_MIME:
        raise HTTPException(status_code=400, detail="Unsupported content type.")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 5 MB.")
    kind = _sniff_image_kind(data)
    if kind is None:
        raise HTTPException(status_code=400, detail="File content is not a valid image.")
    ext_norm = "jpeg" if ext == "jpg" else ext
    if kind != ext_norm:
        raise HTTPException(status_code=400, detail="File content does not match its extension.")
    file_id = str(uuid.uuid4())
    path = f"{APP_NAME}/uploads/{file_id}.{ext}"
    content_type = MIME_TYPES.get(ext, f"image/{kind}")
    result = put_object(path, data, content_type)
    await db.files.insert_one({
        "id": file_id, "storage_path": result["path"],
        "original_filename": file.filename, "content_type": content_type,
        "size": result.get("size"), "is_deleted": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"url": f"/api/files/{result['path']}", "path": result["path"]}


@api_router.get("/files/{path:path}")
async def download_file(path: str):
    record = await db.files.find_one({"storage_path": path, "is_deleted": False})
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    data, content_type = get_object(path)
    return Response(content=data, media_type=record.get("content_type", content_type),
                    headers={"Cache-Control": "public, max-age=31536000"})


@api_router.get("/")
async def root():
    return {"message": "ARIADNI ID API"}

# ------------------------------------------------------------------ startup

@app.on_event("startup")
async def startup():
    try:
        await db.users.create_index("email", unique=True)
        await db.digital_cards.create_index("slug", unique=True)
    except Exception as e:
        logger.warning(f"Index setup: {e}")

    admin_email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    admin_password = os.environ.get("ADMIN_PASSWORD", "")
    if not admin_email or not admin_password:
        logger.warning("ADMIN_EMAIL/ADMIN_PASSWORD not set — skipping admin seed (no fallback credentials).")
    else:
        existing = await db.users.find_one({"email": admin_email})
        if not existing:
            await db.users.insert_one({
                "id": str(uuid.uuid4()), "email": admin_email,
                "password_hash": hash_password(admin_password), "name": "Admin", "role": "admin",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            logger.info("Admin seeded")
        elif not verify_password(admin_password, existing["password_hash"]):
            await db.users.update_one({"email": admin_email},
                                      {"$set": {"password_hash": hash_password(admin_password)}})

    demo = await db.digital_cards.find_one({"slug": DEMO_CARD["slug"]})
    if not demo:
        card = CardData(**DEMO_CARD)
        await db.digital_cards.insert_one(card.model_dump())
        logger.info("Demo card seeded")

    try:
        await run_migration()
    except Exception as e:
        logger.error(f"Migration failed: {e}")

    try:
        init_storage()
        logger.info("Storage initialized")
    except Exception as e:
        logger.error(f"Storage init failed: {e}")


app.include_router(api_router)
app.include_router(platform_router)

_cors_origins = [o.strip() for o in os.environ.get('CORS_ORIGINS', '*').split(',') if o.strip()]
_cors_wildcard = _cors_origins == ['*']
app.add_middleware(
    CORSMiddleware,
    allow_credentials=not _cors_wildcard,
    allow_origins=_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Retry-After"],
)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
