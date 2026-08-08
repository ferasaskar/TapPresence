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
from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, UploadFile, File
from fastapi.responses import Response, StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from seed_data import DEMO_CARD

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


class LoginIn(BaseModel):
    email: str
    password: str

# ------------------------------------------------------------------ auth routes

@api_router.post("/auth/login")
async def login(body: LoginIn):
    email = body.email.strip().lower()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(user["id"], user["email"])
    return {"token": token, "user": {"id": user["id"], "email": user["email"], "name": user.get("name", "Admin")}}


@api_router.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return user

# ------------------------------------------------------------------ public card

def _public_card(card: dict) -> dict:
    card.pop("_id", None)
    return card


@api_router.get("/cards/{slug}")
async def get_public_card(slug: str):
    card = await db.digital_cards.find_one({"slug": slug, "status": "published"}, {"_id": 0})
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    return card


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


@api_router.get("/cards/{slug}/qr")
async def get_qr(slug: str):
    url = f"{PUBLIC_APP_URL}/{slug}" if PUBLIC_APP_URL else f"/{slug}"
    qr = qrcode.QRCode(version=None, box_size=10, border=2,
                       error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#2D2B2A", back_color="#FAFAF8")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")

# ------------------------------------------------------------------ admin cards

@api_router.get("/admin/cards")
async def list_cards(user: dict = Depends(get_current_user)):
    cards = await db.digital_cards.find({}, {"_id": 0}).to_list(1000)
    return cards


@api_router.get("/admin/cards/{card_id}")
async def get_card_admin(card_id: str, user: dict = Depends(get_current_user)):
    card = await db.digital_cards.find_one({"id": card_id}, {"_id": 0})
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    return card


@api_router.post("/admin/cards")
async def create_card(body: CardUpsert, user: dict = Depends(get_current_user)):
    existing = await db.digital_cards.find_one({"slug": body.slug})
    if existing:
        raise HTTPException(status_code=400, detail="Slug already exists")
    card = CardData(**body.model_dump())
    await db.digital_cards.insert_one(card.model_dump())
    doc = await db.digital_cards.find_one({"id": card.id}, {"_id": 0})
    return doc


@api_router.put("/admin/cards/{card_id}")
async def update_card(card_id: str, body: CardUpsert, user: dict = Depends(get_current_user)):
    existing = await db.digital_cards.find_one({"id": card_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Card not found")
    slug_owner = await db.digital_cards.find_one({"slug": body.slug})
    if slug_owner and slug_owner["id"] != card_id:
        raise HTTPException(status_code=400, detail="Slug already used by another card")
    update = body.model_dump()
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.digital_cards.update_one({"id": card_id}, {"$set": update})
    doc = await db.digital_cards.find_one({"id": card_id}, {"_id": 0})
    return doc


@api_router.delete("/admin/cards/{card_id}")
async def delete_card(card_id: str, user: dict = Depends(get_current_user)):
    res = await db.digital_cards.delete_one({"id": card_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Card not found")
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
        init_storage()
        logger.info("Storage initialized")
    except Exception as e:
        logger.error(f"Storage init failed: {e}")


app.include_router(api_router)

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
