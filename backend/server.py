import os
import io
import uuid
import re
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
from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, UploadFile, File
from fastapi.responses import Response, StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from seed_data import DEMO_CARD
from platform_v1 import platform_router, run_migration, _auth_payload, member_role

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
    email = body.email.strip().lower()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
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
    return _apply_lang(card, lang)


@api_router.get("/cards/{slug}/vcard")
async def get_vcard(slug: str):
    card = await db.digital_cards.find_one({"slug": slug}, {"_id": 0})
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
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


@api_router.post("/cards/{slug}/leads")
async def create_lead(slug: str, body: LeadIn):
    card = await db.digital_cards.find_one({"slug": slug, "status": "published"}, {"_id": 0, "id": 1, "workspace_id": 1})
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    if not body.name.strip() or not (body.email.strip() or body.phone.strip()):
        raise HTTPException(status_code=400, detail="Name and an email or phone are required")
    now = datetime.now(timezone.utc).isoformat()
    lead = {
        "id": str(uuid.uuid4()), "cardSlug": slug, "workspace_id": card.get("workspace_id"),
        "name": body.name.strip(), "email": body.email.strip(), "phone": body.phone.strip(),
        "company": "", "title": "", "message": body.message.strip(), "interest": "",
        "source": "inquiry", "campaign": "", "status": "NEW", "tags": [], "notes": "",
        "read": False, "created_at": now, "updated_at": now, "last_activity": now,
    }
    await db.leads.insert_one(lead)
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()), "workspace_id": card.get("workspace_id"), "type": "new_lead",
        "title": f"New inquiry from {body.name.strip()}", "body": f"via /{slug}",
        "read": False, "created_at": now,
    })
    return {"ok": True}


@api_router.post("/cards/{slug}/track")
async def track_event(slug: str, body: TrackIn):
    if body.type not in ("view", "scan", "tap"):
        return {"ok": False}
    await db.analytics_events.insert_one({
        "id": str(uuid.uuid4()), "cardSlug": slug, "type": body.type, "key": body.key,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"ok": True}


@api_router.get("/cards/{slug}/qr")
async def get_qr(slug: str):
    url = f"{PUBLIC_APP_URL}/{slug}?src=qr" if PUBLIC_APP_URL else f"/{slug}?src=qr"
    qr = qrcode.QRCode(version=None, box_size=10, border=2,
                       error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#2D2B2A", back_color="#FAFAF8")
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
    _center(d, "ARIADNI ID", _font(30, serif=False), 70, W, "#B89973")
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
    card = CardData(**body.model_dump())
    doc = card.model_dump()
    doc["workspace_id"] = wsid
    doc["owner_user_id"] = user["id"]
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
    doc["owner_user_id"] = user["id"]
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
    q = {"cardSlug": slug} if slug else {}
    leads = await db.leads.find(q, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return leads


@api_router.patch("/admin/leads/{lead_id}")
async def mark_lead_read(lead_id: str, user: dict = Depends(get_current_user)):
    await db.leads.update_one({"id": lead_id}, {"$set": {"read": True}})
    return {"ok": True}


@api_router.delete("/admin/leads/{lead_id}")
async def delete_lead(lead_id: str, user: dict = Depends(get_current_user)):
    await db.leads.delete_one({"id": lead_id})
    return {"ok": True}


@api_router.get("/admin/cards/{card_id}/analytics")
async def card_analytics(card_id: str, user: dict = Depends(get_current_user)):
    card = await db.digital_cards.find_one({"id": card_id}, {"_id": 0, "slug": 1})
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
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

# ------------------------------------------------------------------ native meetings / calendar
DEFAULT_AVAIL = {"days": [1, 2, 3, 4, 5], "start": "09:00", "end": "18:00",
                 "buffer_before": 0, "buffer_after": 15, "min_notice_hours": 2,
                 "max_days": 60, "slot_interval": 30, "blocked": []}
DEFAULT_MTS = [
    {"title": "15 Min Introduction", "duration": 15},
    {"title": "30 Min Consultation", "duration": 30},
    {"title": "45 Min Meeting", "duration": 45},
]
ACTIVE_STATUSES = ("scheduled", "confirmed")


class MeetingTypeIn(BaseModel):
    title: str = "Meeting"
    description: str = ""
    duration: int = 30
    location_type: str = "video"  # in_person | phone | video | custom
    location_detail: str = ""
    enabled: bool = True
    price: Optional[float] = None
    order: int = 0


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
                  "enabled": True, "price": None, "order": i}
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
async def public_book(slug: str, body: BookIn):
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
    meeting = {
        "id": str(uuid.uuid4()), "manage_token": manage_token, "card_id": card["id"], "cardSlug": slug,
        "workspace_id": card.get("workspace_id"), "owner_user_id": card.get("owner_user_id"),
        "lead_id": lead_id, "meeting_type_id": mt["id"], "meeting_type_title": mt["title"],
        "duration": mt["duration"], "location_type": mt.get("location_type", "video"),
        "location_detail": mt.get("location_detail", ""), "owner_name": card.get("identity", {}).get("fullName", ""),
        "owner_timezone": tzname, "visitor_name": body.name.strip(), "visitor_email": body.email.strip(),
        "visitor_phone": body.phone.strip(), "visitor_tz": body.visitor_tz or "UTC", "note": body.note.strip(),
        "start_utc": start_utc.isoformat(), "end_utc": end_utc.isoformat(),
        "status": "scheduled", "created_at": now, "updated_at": now,
        "reminders": [{"offset_hours": 24, "status": "scheduled", "provider": "NOT_CONFIGURED"},
                      {"offset_hours": 1, "status": "scheduled", "provider": "NOT_CONFIGURED"}],
        "history": [{"at": now, "event": "booked", "by": "guest"}],
    }
    await db.meetings.insert_one(dict(meeting))
    await db.leads.update_one({"id": lead_id}, {"$push": {"timeline": {"at": now, "event": "meeting_booked", "detail": mt["title"]}}})
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()), "workspace_id": card.get("workspace_id"), "type": "meeting_booked",
        "title": f"Meeting booked by {body.name.strip()}", "body": f"{mt['title']} · via /{slug}", "read": False, "created_at": now,
    })
    await db.analytics_events.insert_one({"id": str(uuid.uuid4()), "cardSlug": slug, "type": "tap", "key": "booking_completed", "created_at": now})
    meeting.pop("_id", None)
    return {"ok": True, "manage_token": manage_token, "meeting": meeting}


def _sanitize_meeting(m: dict) -> dict:
    m.pop("_id", None)
    return m


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
        base["start_utc"] = {"$lt": now}
        base["status"] = {"$nin": ["cancelled"]}
    elif filter == "cancelled":
        base["status"] = "cancelled"
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
    if status not in ("scheduled", "confirmed", "completed", "cancelled", "no-show", "rescheduled"):
        raise HTTPException(status_code=400, detail="Invalid status")
    now = datetime.now(timezone.utc).isoformat()
    await db.meetings.update_one({"id": meeting_id}, {"$set": {"status": status, "updated_at": now},
                                 "$push": {"history": {"at": now, "event": f"status:{status}", "by": user.get("email")}}})
    if status == "completed" and m.get("lead_id"):
        await db.leads.update_one({"id": m["lead_id"]}, {"$push": {"timeline": {"at": now, "event": "meeting_completed", "detail": m.get("meeting_type_title", "")}}})
    return {"ok": True}


# ------------------------------------------------------------------ uploads

@api_router.post("/upload")
async def upload(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    ext = file.filename.split(".")[-1].lower() if "." in file.filename else "bin"
    file_id = str(uuid.uuid4())
    path = f"{APP_NAME}/uploads/{file_id}.{ext}"
    data = await file.read()
    content_type = MIME_TYPES.get(ext, file.content_type or "application/octet-stream")
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

    admin_email = os.environ.get("ADMIN_EMAIL", "admin@example.com").lower()
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
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

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
