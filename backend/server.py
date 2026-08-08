import os
import io
import uuid
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta

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


class CardData(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    slug: str
    templateId: str = "beige-luxury"
    accent: str = "gold"
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
