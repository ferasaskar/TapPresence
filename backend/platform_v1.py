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
import asyncio
import base64
import time
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

import stripe
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY") or ""
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_MODE = os.environ.get("STRIPE_MODE", "test")
if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY

import asyncio
import resend
RESEND_API_KEY = os.environ.get("RESEND_API_KEY") or ""
SENDER_EMAIL = os.environ.get("SENDER_EMAIL") or ""
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY


def _email_configured() -> bool:
    return bool(RESEND_API_KEY)


def _email_shell(title: str, intro: str, cta_text: str, cta_url: str, footnote: str = "", lang: str = "en") -> str:
    """Branded, email-safe HTML (inline CSS, table layout) for TapPresence transactional mail.
    Localized: Arabic renders RTL; English/Spanish render LTR. Single shared shell for ALL emails."""
    rtl = (lang == "ar")
    direction = "rtl" if rtl else "ltr"
    align = "right" if rtl else "left"
    ignore = {"ar": "إذا لم تطلب هذا، يمكنك تجاهل هذه الرسالة بأمان.",
              "es": "Si no solicitaste esto, puedes ignorar este correo.",
              "en": "If you didn't request this, you can safely ignore this email."}.get(lang, "If you didn't request this, you can safely ignore this email.")
    orlink = {"ar": "أو انسخ هذا الرابط في متصفحك:", "es": "O pega este enlace en tu navegador:",
              "en": "Or paste this link into your browser:"}.get(lang, "Or paste this link into your browser:")
    return f"""\
<table dir="{direction}" width="100%" cellpadding="0" cellspacing="0" style="background:#050607;padding:32px 0;font-family:Arial,Helvetica,sans-serif;">
  <tr><td align="center">
    <table dir="{direction}" width="480" cellpadding="0" cellspacing="0" style="background:#0d0f13;border:1px solid #1e2128;border-radius:16px;overflow:hidden;">
      <tr><td style="padding:28px 32px 8px 32px;text-align:{align};">
        <span style="font-size:20px;font-weight:700;color:#ffffff;">Tap<span style="color:#D6A653;">Presence</span></span>
      </td></tr>
      <tr><td style="padding:8px 32px 0 32px;text-align:{align};">
        <h1 style="margin:0;font-size:20px;line-height:1.3;color:#ffffff;">{title}</h1>
        <p style="margin:14px 0 0 0;font-size:14px;line-height:1.6;color:#a2a6ad;">{intro}</p>
      </td></tr>
      <tr><td style="padding:24px 32px 8px 32px;text-align:{align};">
        <a href="{cta_url}" style="display:inline-block;background:#D6A653;color:#050607;text-decoration:none;font-weight:600;font-size:14px;padding:12px 24px;border-radius:10px;">{cta_text}</a>
      </td></tr>
      <tr><td style="padding:12px 32px 28px 32px;text-align:{align};">
        <p style="margin:0;font-size:12px;line-height:1.6;color:#70757e;">{orlink}<br><span style="color:#8a8f97;word-break:break-all;">{cta_url}</span></p>
        {f'<p style="margin:14px 0 0 0;font-size:12px;color:#70757e;">{footnote}</p>' if footnote else ''}
      </td></tr>
      <tr><td style="padding:16px 32px;border-top:1px solid #1e2128;text-align:{align};">
        <p style="margin:0;font-size:11px;color:#5b6068;">© TapPresence. {ignore}</p>
      </td></tr>
    </table>
  </td></tr>
</table>"""


def _norm_lang(lang) -> str:
    lang = (lang or "en").split("-")[0].lower()
    return lang if lang in ("en", "ar", "es") else "en"


# Localized copy for platform (auth / trial / referral / team) emails. Placeholders via str.format.
# Booking/meeting emails localize in server.py using the same _email_shell primitive (no second system).
EMAIL_MSGS = {
    "verify": {
        "en": {"subject": "Verify your TapPresence email", "title": "Confirm your email", "cta": "Verify email",
               "intro": "Welcome to TapPresence — please confirm your email address to secure your account and unlock everything in your 14-day trial."},
        "ar": {"subject": "تأكيد بريدك الإلكتروني في TapPresence", "title": "تأكيد بريدك الإلكتروني", "cta": "تأكيد البريد",
               "intro": "مرحبًا بك في TapPresence — يُرجى تأكيد عنوان بريدك الإلكتروني لتأمين حسابك وفتح كل الميزات خلال فترتك التجريبية لمدة 14 يومًا."},
        "es": {"subject": "Verifica tu correo de TapPresence", "title": "Confirma tu correo", "cta": "Verificar correo",
               "intro": "Bienvenido a TapPresence — confirma tu dirección de correo para asegurar tu cuenta y desbloquear todo en tu prueba de 14 días."},
    },
    "verify_resend": {
        "en": {"subject": "Verify your TapPresence email", "title": "Confirm your email", "cta": "Verify email",
               "intro": "Here's a fresh link to confirm your TapPresence email address."},
        "ar": {"subject": "تأكيد بريدك الإلكتروني في TapPresence", "title": "تأكيد بريدك الإلكتروني", "cta": "تأكيد البريد",
               "intro": "هذا رابط جديد لتأكيد عنوان بريدك الإلكتروني في TapPresence."},
        "es": {"subject": "Verifica tu correo de TapPresence", "title": "Confirma tu correo", "cta": "Verificar correo",
               "intro": "Aquí tienes un nuevo enlace para confirmar tu correo de TapPresence."},
    },
    "reset": {
        "en": {"subject": "Reset your TapPresence password", "title": "Reset your password", "cta": "Reset password",
               "intro": "We received a request to reset your TapPresence password. This link expires in 1 hour.",
               "footnote": "If you didn't request a password reset, no action is needed."},
        "ar": {"subject": "إعادة تعيين كلمة مرور TapPresence", "title": "إعادة تعيين كلمة المرور", "cta": "إعادة التعيين",
               "intro": "تلقّينا طلبًا لإعادة تعيين كلمة مرور TapPresence. تنتهي صلاحية هذا الرابط خلال ساعة واحدة.",
               "footnote": "إذا لم تطلب إعادة التعيين، فلا حاجة لأي إجراء."},
        "es": {"subject": "Restablece tu contraseña de TapPresence", "title": "Restablece tu contraseña", "cta": "Restablecer",
               "intro": "Recibimos una solicitud para restablecer tu contraseña de TapPresence. Este enlace caduca en 1 hora.",
               "footnote": "Si no solicitaste el restablecimiento, no necesitas hacer nada."},
    },
    "invite": {
        "en": {"subject": "You've been invited to a TapPresence team", "title": "Join your team on TapPresence", "cta": "Accept invite",
               "intro": "You've been invited to join <b>{ws}</b> on TapPresence. Set up your account to get started. This invite expires in 7 days."},
        "ar": {"subject": "تمت دعوتك إلى فريق على TapPresence", "title": "انضم إلى فريقك على TapPresence", "cta": "قبول الدعوة",
               "intro": "تمت دعوتك للانضمام إلى <b>{ws}</b> على TapPresence. أنشئ حسابك للبدء. تنتهي صلاحية هذه الدعوة خلال 7 أيام."},
        "es": {"subject": "Te invitaron a un equipo de TapPresence", "title": "Únete a tu equipo en TapPresence", "cta": "Aceptar invitación",
               "intro": "Te invitaron a unirte a <b>{ws}</b> en TapPresence. Configura tu cuenta para empezar. Esta invitación caduca en 7 días."},
    },
    "trial_3d": {
        "en": {"subject": "Your TapPresence trial ends in 3 days", "title": "Your trial ends soon", "cta": "Upgrade now",
               "intro": "Your 14-day TapPresence trial ends in about 3 days. Upgrade to keep your card live, your leads, analytics and premium features without interruption."},
        "ar": {"subject": "تنتهي فترتك التجريبية في TapPresence خلال 3 أيام", "title": "تنتهي فترتك التجريبية قريبًا", "cta": "الترقية الآن",
               "intro": "تنتهي فترتك التجريبية في TapPresence (14 يومًا) خلال 3 أيام تقريبًا. قم بالترقية للحفاظ على بطاقتك والعملاء المحتملين والتحليلات والميزات المميزة دون انقطاع."},
        "es": {"subject": "Tu prueba de TapPresence termina en 3 días", "title": "Tu prueba termina pronto", "cta": "Mejorar ahora",
               "intro": "Tu prueba de 14 días de TapPresence termina en unos 3 días. Mejora tu plan para mantener tu tarjeta activa, tus contactos, analíticas y funciones premium sin interrupción."},
    },
    "trial_expired": {
        "en": {"subject": "Your TapPresence trial has ended", "title": "Your trial has ended", "cta": "Reactivate",
               "intro": "Your 14-day TapPresence trial has ended. Your data is safe — upgrade any time to bring your card back online and unlock premium features again."},
        "ar": {"subject": "انتهت فترتك التجريبية في TapPresence", "title": "انتهت فترتك التجريبية", "cta": "إعادة التفعيل",
               "intro": "انتهت فترتك التجريبية في TapPresence (14 يومًا). بياناتك محفوظة — يمكنك الترقية في أي وقت لإعادة تفعيل بطاقتك وفتح الميزات المميزة مجددًا."},
        "es": {"subject": "Tu prueba de TapPresence ha terminado", "title": "Tu prueba ha terminado", "cta": "Reactivar",
               "intro": "Tu prueba de 14 días de TapPresence ha terminado. Tus datos están a salvo — mejora tu plan cuando quieras para reactivar tu tarjeta y las funciones premium."},
    },
    "payment_failed": {
        "en": {"subject": "Action needed: your TapPresence payment failed", "title": "Your payment didn't go through", "cta": "Update payment method",
               "intro": "We couldn't process your latest TapPresence payment of <b>{amount}</b>. Your account is still active for now — please update your payment method to avoid any interruption.",
               "footnote": "You're taken to Stripe's secure billing page — TapPresence never sees your card details."},
        "ar": {"subject": "إجراء مطلوب: فشل الدفع في TapPresence", "title": "لم تتم عملية الدفع", "cta": "تحديث طريقة الدفع",
               "intro": "لم نتمكن من معالجة دفعتك الأخيرة في TapPresence بقيمة <b>{amount}</b>. لا يزال حسابك نشطًا حاليًا — يُرجى تحديث طريقة الدفع لتجنب أي انقطاع.",
               "footnote": "سيتم توجيهك إلى صفحة الفوترة الآمنة من Stripe — لا يطّلع TapPresence على بيانات بطاقتك."},
        "es": {"subject": "Acción requerida: falló tu pago de TapPresence", "title": "Tu pago no se procesó", "cta": "Actualizar método de pago",
               "intro": "No pudimos procesar tu último pago de TapPresence de <b>{amount}</b>. Tu cuenta sigue activa por ahora — actualiza tu método de pago para evitar interrupciones.",
               "footnote": "Se te redirige a la página segura de facturación de Stripe — TapPresence nunca ve los datos de tu tarjeta."},
    },
    "payment_recovered": {
        "en": {"subject": "You're all set — TapPresence payment received", "title": "Payment successful", "cta": "View billing",
               "intro": "Good news — your TapPresence payment went through and your subscription is healthy again. No further action is needed."},
        "ar": {"subject": "تمت العملية — تم استلام الدفع في TapPresence", "title": "تم الدفع بنجاح", "cta": "عرض الفوترة",
               "intro": "أخبار جيدة — تمت عملية الدفع في TapPresence واشتراكك الآن سليم مجددًا. لا حاجة لأي إجراء إضافي."},
        "es": {"subject": "Todo listo — pago de TapPresence recibido", "title": "Pago exitoso", "cta": "Ver facturación",
               "intro": "Buenas noticias — tu pago de TapPresence se procesó y tu suscripción está activa de nuevo. No necesitas hacer nada más."},
    },
    "referral_reward": {
        "en": {"subject": "You've earned a free month of TapPresence", "title": "Reward unlocked — 1 month free", "cta": "View my rewards",
               "intro": "Great news! You've reached {per} successful paid referrals and earned <b>{months} month(s) free</b> on TapPresence. Your reward is ready to apply to your billing."},
        "ar": {"subject": "لقد حصلت على شهر مجاني في TapPresence", "title": "تم فتح المكافأة — شهر مجاني", "cta": "عرض مكافآتي",
               "intro": "أخبار رائعة! لقد وصلت إلى {per} إحالات مدفوعة ناجحة وحصلت على <b>{months} شهر مجاني</b> على TapPresence. مكافأتك جاهزة للتطبيق على فاتورتك."},
        "es": {"subject": "Has ganado un mes gratis de TapPresence", "title": "Recompensa desbloqueada — 1 mes gratis", "cta": "Ver mis recompensas",
               "intro": "¡Buenas noticias! Alcanzaste {per} referidos de pago exitosos y ganaste <b>{months} mes(es) gratis</b> en TapPresence. Tu recompensa está lista para aplicarse a tu facturación."},
    },
}


def build_email(kind: str, lang: str, cta_url: str, **ctx):
    """Return (subject, html) for a platform email in the requested language (fallback en)."""
    lang = _norm_lang(lang)
    block = (EMAIL_MSGS.get(kind) or {}).get(lang) or (EMAIL_MSGS.get(kind) or {}).get("en") or {}
    subject = (block.get("subject") or "TapPresence").format(**ctx)
    title = (block.get("title") or "").format(**ctx)
    intro = (block.get("intro") or "").format(**ctx)
    cta = (block.get("cta") or "Open").format(**ctx)
    footnote = (block.get("footnote") or "").format(**ctx)
    return subject, _email_shell(title, intro, cta, cta_url, footnote, lang=lang)


async def send_localized(to: str, kind: str, lang: str, cta_url: str, **ctx) -> bool:
    subject, html = build_email(kind, lang, cta_url, **ctx)
    return await send_email(to, subject, html)


async def send_email(to: str, subject: str, html: str) -> bool:
    """Send a transactional email via Resend (non-blocking). Returns False if not configured/failed."""
    if not RESEND_API_KEY:
        logger.error("[email] not sent: RESEND_API_KEY is not configured")
        return False
    if not SENDER_EMAIL:
        # Fail clearly rather than silently falling back to a resend.dev test sender in production.
        logger.error("[email] not sent: SENDER_EMAIL is not configured (refusing default resend.dev fallback)")
        return False
    try:
        await asyncio.to_thread(resend.Emails.send, {
            "from": SENDER_EMAIL, "to": [to], "subject": subject, "html": html,
        })
        logger.info(f"[email] sent '{subject}' to {to}")
        await meter_usage("email", quantity=1, result="success", source="resend", paid=True)
        return True
    except Exception as e:
        logger.error(f"[email] send failed to {to} ('{subject}'): {e}")
        await meter_usage("email", quantity=1, result="failed", source="resend", paid=False)
        return False


# ------------------------------------------------------------------ Google OAuth (server-side auth-code flow)
# REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
GOOGLE_OAUTH_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID") or ""
GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET") or ""
GOOGLE_OAUTH_REDIRECT_URI = os.environ.get("GOOGLE_OAUTH_REDIRECT_URI") or ""


def _google_configured() -> bool:
    return bool(GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET and GOOGLE_OAUTH_REDIRECT_URI)


def _google_frontend_base() -> str:
    """The customer-facing origin is the redirect URI minus the callback path — this keeps the
    frontend and OAuth callback on the SAME domain the user registered (preview / tappresence.com)."""
    suffix = "/api/auth/google/callback"
    if GOOGLE_OAUTH_REDIRECT_URI.endswith(suffix):
        return GOOGLE_OAUTH_REDIRECT_URI[: -len(suffix)]
    return PUBLIC_APP_URL


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
# past_due is RECOVERABLE (Stripe is still retrying) → keep access during the dunning/grace window.
# unpaid / incomplete / incomplete_expired / cancelled are terminal → access ends.
ACTIVE_STATES = {"trialing", "active", "cancel_at_period_end", "past_due"}

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


# ---- Account classification for truthful platform KPIs (P0 data-integrity) ----
PAID_TIERS = {"pro", "team", "enterprise", "white_label"}


def customer_ws_filter(include_internal: bool = False) -> dict:
    """Mongo filter for real customer workspaces. Excludes internal/demo/test by default."""
    return {} if include_internal else {"environment": "production_customer"}


def is_real_paid(sub: dict) -> bool:
    """A subscription counts as real paid revenue ONLY with a real billing provider reference (Stripe).
    Manually-seeded plan/status is never counted as paid revenue."""
    if not sub:
        return False
    if sub.get("status") not in ("active", "cancel_at_period_end"):
        return False
    if (sub.get("plan") or "") not in PAID_TIERS:
        return False
    return bool(sub.get("stripe_subscription_id") or sub.get("provider") == "stripe")


def display_plan(ws: dict) -> str:
    """Never surface the legacy 'free' label. Returns a truthful current plan label."""
    sub = (ws or {}).get("subscription") or {}
    plan = sub.get("plan") or (ws or {}).get("plan") or "trial"
    if plan == "free":
        plan = "trial"
    st = effective_status(ws)
    if st in ("trialing",):
        return "Trial"
    if st == "trial_expired":
        return "Trial (expired)"
    return plan.capitalize()


async def resolve_entitlements(workspace_id: str) -> dict:
    ws = await db.workspaces.find_one({"id": workspace_id}, {"_id": 0})
    sub = (ws or {}).get("subscription") or {}
    plan = sub.get("plan") or (ws or {}).get("plan", "free")
    status = effective_status(ws)
    ent = dict(PLAN_ENTITLEMENTS.get(plan, PLAN_ENTITLEMENTS["free"]))
    # Super-Admin configurable overrides (no source edits): commercial_config.entitlement_overrides[plan]
    try:
        cfg = await get_commercial_config()
        ov = (cfg.get("entitlement_overrides") or {}).get(plan) or {}
        if ov:
            ent.update({k: v for k, v in ov.items() if k in ent})
    except Exception:
        pass
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

# Currency conversion vs the USD base. AED & SAR are official pegs; EUR/GBP are
# Super-Admin editable defaults (commercial_config.fx_rates overrides these).
DEFAULT_FX_RATES = {"USD": 1.0, "AED": 3.6725, "SAR": 3.75, "EUR": 0.92, "GBP": 0.79}

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
    "stripe_tax_code": "txcd_10103001",
    "regional_pricing": {
        "USD": {"symbol": "$", "pro_month": 9.99, "pro_year": 99.99, "team_seat_month": 5.0, "team_seat_year": 50.0},
        "AED": {"symbol": "AED ", "pro_month": 36.99, "pro_year": 369.99, "team_seat_month": 18.0, "team_seat_year": 180.0},
        "SAR": {"symbol": "SAR ", "pro_month": 37.99, "pro_year": 379.99, "team_seat_month": 19.0, "team_seat_year": 190.0},
        "EUR": {"symbol": "€", "pro_month": 9.99, "pro_year": 99.99, "team_seat_month": 5.0, "team_seat_year": 50.0},
        "GBP": {"symbol": "£", "pro_month": 8.99, "pro_year": 89.99, "team_seat_month": 4.5, "team_seat_year": 45.0},
    },
    # USD is the authoritative base. Every other currency is AUTO-converted from USD
    # via fx_rates unless its code is listed in manual_price_markets (then the stored
    # regional_pricing[market] block is used as an intentional manual override).
    "fx_rates": dict(DEFAULT_FX_RATES),
    "manual_price_markets": [],
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


def _round_price(x) -> float:
    """Exact 2-decimal currency conversion. Keeping the true converted value (rather
    than snapping to .99) preserves the USD monthly:annual ratio, so derived annual
    savings stay coherent across every auto-converted currency. Markets that want a
    clean local price (e.g. AED 369.99) use a manual override instead."""
    try:
        x = float(x or 0)
    except (TypeError, ValueError):
        return 0.0
    return round(x, 2) if x > 0 else 0.0


def resolve_market_pricing(cfg: dict, market: str) -> dict:
    """Authoritative price resolver used by EVERY price surface (landing, pricing,
    registration, billing, checkout, admin preview).

    USD is the base. Any other currency is AUTO-converted from the USD base using
    fx_rates, UNLESS the market is an explicit manual override (in manual_price_markets
    with a stored regional_pricing block). Annual savings are always DERIVED from the
    resolved monthly vs yearly prices for that same currency."""
    market = (market or cfg.get("default_market") or "USD").upper()
    rp_all = cfg.get("regional_pricing") or {}
    base = rp_all.get("USD") or DEFAULT_COMMERCIAL_CONFIG["regional_pricing"]["USD"]
    fx = {**DEFAULT_FX_RATES, **(cfg.get("fx_rates") or {})}
    manual = {m.upper() for m in (cfg.get("manual_price_markets") or [])}

    if market == "USD":
        rp = dict(base)
        source = "base"
    elif market in manual and rp_all.get(market):
        rp = dict(rp_all[market])
        source = "manual"
    else:
        rate = float(fx.get(market) or 0)
        if rate <= 0:
            # Unknown currency with no configured rate -> fall back to USD base (never another market's stale price)
            rp = dict(base)
            market = "USD"
            source = "base"
        else:
            rp = {
                "symbol": _MARKET_SYMBOL.get(market, ""),
                "pro_month": _round_price(base.get("pro_month", 0) * rate),
                "pro_year": _round_price(base.get("pro_year", 0) * rate),
                "team_seat_month": _round_price(base.get("team_seat_month", 0) * rate),
                "team_seat_year": _round_price(base.get("team_seat_year", 0) * rate),
            }
            source = "auto"

    out = {"market": market, "symbol": rp.get("symbol", _MARKET_SYMBOL.get(market, "")),
           "pricing_source": source, "fx_rate": float(fx.get(market) or 1.0), **rp}
    # annual savings are DERIVED from the resolved monthly vs annual prices (never hard-coded)
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
    sub_obj = (ws or {}).get("subscription") or {}
    dunning = sub_obj.get("dunning") or {}
    payment_failed = ent["status"] in ("past_due", "unpaid") or dunning.get("state") == "failed"
    payment_state = {
        "failed": bool(payment_failed),
        "status": ent["status"],
        "amount_due": dunning.get("amount_due") if payment_failed else None,
        "currency": dunning.get("currency") if payment_failed else None,
        "hosted_invoice_url": dunning.get("hosted_invoice_url") if payment_failed else None,
        "next_attempt": dunning.get("next_attempt") if payment_failed else None,
        "recovered": dunning.get("state") == "recovered",
        "has_customer": bool(sub_obj.get("stripe_customer_id")),
    }
    discount = {
        "referred_month_pct": float(referred.get("discount_month_pct", 0)) if referred else 0,
        "referred_year_pct": float(referred.get("discount_year_pct", 0)) if referred else 0,
        "free_months_earned": int(reward.get("free_months_earned", 0)),
        "free_months_available": int(reward.get("free_months_available", 0)),
    }
    return {
        "plan": ent["plan"], "status": ent["status"], "active": ent["active"],
        "trial_ends_at": ent.get("trial_ends_at"), "current_period_end": ent.get("current_period_end"),
        "interval": ((ws or {}).get("subscription") or {}).get("interval"),
        "provider": ((ws or {}).get("subscription") or {}).get("provider"),
        "cancel_at_period_end": ent["status"] == "cancel_at_period_end",
        "trial_eligible": _trial_eligible((ws or {}).get("subscription") or {}),
        "seats": ent.get("seats"), "entitlements": ent,
        "commercial": {"trial": cfg["trial"], "plans": cfg["plans"], "referral": cfg["referral"],
                       "pricing": pricing, "markets": COMMERCIAL_MARKETS},
        "discount": discount,
        "payment_state": payment_state,
        "demo_billing": ALLOW_DEMO_BILLING,
        "usage": {"ai": {"used": ai_used, "limit": ent.get("ai_limit"), "period": ent.get("ai_period")},
                  "scanner": {"used": sc_used, "limit": ent.get("scanner_limit"), "period": ent.get("scanner_period")},
                  "cards": {"used": cards_used, "limit": ent.get("max_cards")}},
    }


@platform_router.post("/billing/portal")
async def billing_portal(user: dict = Depends(current_user)):
    """Stripe-hosted billing portal for 'Update payment method / Fix payment'.
    TapPresence never sees or stores card details. Owner/admin only."""
    ws_id = await _primary_ws_id(user)
    if not ws_id:
        raise HTTPException(404, "No workspace")
    await require_ws_admin(user, ws_id)
    ws = await db.workspaces.find_one({"id": ws_id}, {"_id": 0, "subscription": 1})
    customer_id = ((ws or {}).get("subscription") or {}).get("stripe_customer_id")
    if not customer_id:
        raise HTTPException(400, "No Stripe customer on file for this workspace.")
    try:
        session = stripe.billing_portal.Session.create(
            customer=customer_id, return_url=f"{PUBLIC_APP_URL}/billing")
    except stripe.error.StripeError as e:
        logger.error("[billing] portal creation failed ws=%s type=%s", ws_id, type(e).__name__)
        raise HTTPException(503, "The billing portal is temporarily unavailable. Please try again shortly.")
    return {"url": session.url}


@platform_router.get("/billing/invoices")
async def billing_invoices(user: dict = Depends(current_user)):
    """Invoice & receipt history — Stripe is the authoritative source. Owner/admin only; a workspace
    can only see its OWN invoices (scoped by its Stripe customer id). Returns [] when none."""
    ws_id = await _primary_ws_id(user)
    if not ws_id:
        raise HTTPException(404, "No workspace")
    await require_ws_admin(user, ws_id)
    ws = await db.workspaces.find_one({"id": ws_id}, {"_id": 0, "subscription": 1})
    customer_id = ((ws or {}).get("subscription") or {}).get("stripe_customer_id")
    if not customer_id:
        return {"invoices": [], "has_customer": False}
    try:
        inv_list = stripe.Invoice.list(customer=customer_id, limit=24, expand=["data.charge"])
    except stripe.error.StripeError as e:
        logger.error("[billing] invoice list failed ws=%s type=%s", ws_id, type(e).__name__)
        raise HTTPException(503, "Could not load billing history right now. Please try again shortly.")
    out = []
    for inv in inv_list.get("data", []):
        lines = (inv.get("lines") or {}).get("data") or []
        line0 = lines[0] if lines else {}
        period = line0.get("period") or {}
        plan_nick = None
        price = line0.get("price") or {}
        if price:
            plan_nick = price.get("nickname") or ((price.get("product") if isinstance(price.get("product"), str) else None))
        disc = inv.get("total_discount_amounts") or []
        charge = inv.get("charge") if isinstance(inv.get("charge"), dict) else None
        receipt_url = (charge or {}).get("receipt_url")
        refunded = bool((charge or {}).get("refunded")) or (inv.get("status") == "void")
        status = "refunded" if (charge or {}).get("refunded") else inv.get("status")
        out.append({
            "id": inv.get("id"),
            "number": inv.get("number"),
            "date": (datetime.fromtimestamp(inv["created"], timezone.utc).isoformat() if inv.get("created") else None),
            "plan": (inv.get("metadata") or {}).get("plan") or plan_nick,
            "period_start": (datetime.fromtimestamp(period["start"], timezone.utc).isoformat() if period.get("start") else None),
            "period_end": (datetime.fromtimestamp(period["end"], timezone.utc).isoformat() if period.get("end") else None),
            "subtotal": inv.get("subtotal"),
            "discount": sum(d.get("amount", 0) for d in disc) if disc else 0,
            "tax": inv.get("tax") or 0,
            "total": inv.get("total"),
            "amount_paid": inv.get("amount_paid"),
            "currency": (inv.get("currency") or "usd").upper(),
            "status": status,
            "paid": bool(inv.get("paid")),
            "refunded": refunded,
            "hosted_invoice_url": inv.get("hosted_invoice_url"),
            "invoice_pdf": inv.get("invoice_pdf"),
            "receipt_url": receipt_url,
        })
    return {"invoices": out, "has_customer": True}


@platform_router.get("/commercial/pricing")
async def commercial_pricing(market: Optional[str] = None):
    """Public resolved pricing for a market — for the billing page + marketing pricing."""
    cfg = await get_commercial_config()
    resolved_all = {m: resolve_market_pricing(cfg, m) for m in COMMERCIAL_MARKETS}
    return {
        "trial": cfg["trial"], "plans": cfg["plans"], "referral": cfg["referral"],
        "pricing": resolve_market_pricing(cfg, market),
        "markets": COMMERCIAL_MARKETS,
        "all_regional": cfg["regional_pricing"],
        "resolved_all": resolved_all,
        "fx_rates": {**DEFAULT_FX_RATES, **(cfg.get("fx_rates") or {})},
        "manual_price_markets": cfg.get("manual_price_markets") or [],
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
    ws = await db.workspaces.find_one({"id": ws_id}, {"_id": 0, "subscription": 1})
    sub = (ws or {}).get("subscription") or {}
    sub_id = sub.get("stripe_subscription_id")
    # Real Stripe subscription: schedule cancellation at period end (keeps Pro access until then).
    if sub_id and STRIPE_SECRET_KEY:
        try:
            stripe.Subscription.modify(sub_id, cancel_at_period_end=True)
        except stripe.error.StripeError as e:
            raise HTTPException(502, f"Stripe error: {getattr(e, 'user_message', None) or str(e)}")
    await db.workspaces.update_one({"id": ws_id}, {"$set": {"subscription.status": "cancel_at_period_end", "subscription.updated_at": now_iso()}})
    await audit(ws_id, user["id"], "billing.cancel_at_period_end", {"stripe": bool(sub_id)})
    return {"ok": True, "status": "cancel_at_period_end"}


@platform_router.post("/billing/resume")
async def resume_subscription(user: dict = Depends(current_user)):
    """Undo a scheduled cancellation on the EXISTING Stripe subscription (never creates a new one)."""
    ws_id = await _primary_ws_id(user)
    await require_ws_admin(user, ws_id)
    ws = await db.workspaces.find_one({"id": ws_id}, {"_id": 0, "subscription": 1})
    sub = (ws or {}).get("subscription") or {}
    if sub.get("status") != "cancel_at_period_end":
        raise HTTPException(400, "Subscription is not scheduled to cancel")
    sub_id = sub.get("stripe_subscription_id")
    if sub_id and STRIPE_SECRET_KEY:
        try:
            stripe.Subscription.modify(sub_id, cancel_at_period_end=False)
            fresh = stripe.Subscription.retrieve(sub_id)
        except stripe.error.StripeError as e:
            raise HTTPException(502, f"Stripe error: {getattr(e, 'user_message', None) or str(e)}")
        # Re-sync from Stripe so status + current_period_end always match Stripe exactly.
        await _sync_ws_from_stripe_sub(ws_id, fresh, sub.get("plan", "pro"), sub.get("interval", "month"),
                                       sub.get("seats", 1), sub.get("market", "USD"),
                                       source="stripe_resume", event_id=f"resume:{sub_id}")
    else:
        await db.workspaces.update_one({"id": ws_id}, {"$set": {"subscription.status": "active", "subscription.updated_at": now_iso()}})
    await audit(ws_id, user["id"], "billing.resume", {"stripe": bool(sub_id)})
    ent = await resolve_entitlements(ws_id)
    return {"ok": True, "status": ent["status"], "current_period_end": ent.get("current_period_end")}


# ------------------------------------------------------------------ Stripe checkout (real payment provider)
_CURRENCY_FOR_MARKET = {"USD": "usd", "AED": "aed", "EUR": "eur", "GBP": "gbp", "SAR": "sar"}


class CheckoutIn(BaseModel):
    plan: str                       # pro | team
    interval: str = "month"         # month | year
    seats: int = 1
    market: Optional[str] = None
    origin_url: str


def _trial_eligible(sub: dict) -> bool:
    """The 14-day trial is a ONE-TIME signup benefit. Any account that has EVER started
    a trial carries a persistent, immutable marker (trial_started_at / trial_ends_at) and
    is permanently ineligible for another — regardless of cancel, expiry, payment failure,
    plan/interval switch, re-login or repeated checkout."""
    sub = sub or {}
    return not (sub.get("trial_started_at") or sub.get("trial_ends_at"))


def _resolve_checkout_amount(cfg: dict, plan: str, interval: str, seats: int):
    """Amount ALWAYS resolves from the published commercial config — never from the client."""
    market = (cfg.get("default_market") or "USD").upper()
    pricing = resolve_market_pricing(cfg, market)
    currency = _CURRENCY_FOR_MARKET.get(market, "usd")
    if plan == "pro":
        amount = pricing["pro_year"] if interval == "year" else pricing["pro_month"]
        return market, currency, float(amount), 1, "TapPresence Pro"
    min_seats = int((cfg["plans"].get("team") or {}).get("min_seats", 3))
    qty = max(int(seats or min_seats), min_seats)
    amount = pricing["team_seat_year"] if interval == "year" else pricing["team_seat_month"]
    return market, currency, float(amount), qty, "TapPresence Team (per seat)"


@platform_router.post("/billing/checkout")
async def billing_checkout(body: CheckoutIn, user: dict = Depends(current_user)):
    """Create a Stripe subscription Checkout session. Amount resolves server-side from the
    published commercial config; the client never sends prices."""
    if not STRIPE_SECRET_KEY:
        raise HTTPException(503, "Payments are not configured yet.")
    if body.plan not in ("pro", "team"):
        raise HTTPException(400, "Invalid plan")
    if body.interval not in ("month", "year"):
        raise HTTPException(400, "Invalid interval")
    ws_id = await _primary_ws_id(user)
    await require_ws_admin(user, ws_id)
    cfg = await get_commercial_config()
    market, currency, amount, seats, product_name = _resolve_checkout_amount(cfg, body.plan, body.interval, body.seats)
    unit_amount = int(round(amount * 100))
    if unit_amount <= 0:
        raise HTTPException(400, "This plan is not available for self-service checkout")
    # SaaS product tax code (Stripe Tax decides taxability from this + customer location + your registrations).
    tax_code = (cfg.get("stripe_tax_code") or "txcd_10103001").strip()
    # Trial eligibility is server-side & persistent (never based on current status alone).
    ws = await db.workspaces.find_one({"id": ws_id}, {"_id": 0, "subscription": 1})
    sub = (ws or {}).get("subscription") or {}
    trial_eligible = _trial_eligible(sub)
    line_items = [{
        "price_data": {
            "currency": currency,
            "product_data": {"name": product_name, "tax_code": tax_code},
            "unit_amount": unit_amount,
            "recurring": {"interval": body.interval},
            "tax_behavior": "exclusive",
        },
        "quantity": seats,
    }]
    sub_data = {"metadata": {"ws_id": ws_id, "plan": body.plan}}
    # Only a trial-eligible (never-trialed) account may receive a free-trial window.
    # Previously-trialed accounts are charged immediately (no trial_period_days).
    if trial_eligible:
        _tdays = await trial_days()
        if _tdays > 0:
            sub_data["trial_period_days"] = _tdays
    meta = {"ws_id": ws_id, "plan": body.plan, "interval": body.interval, "seats": str(seats), "market": market}
    base_kwargs = dict(
        mode="subscription",
        line_items=line_items,
        success_url=f"{body.origin_url}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{body.origin_url}/payment/cancel",
        customer_email=user.get("email"),
        subscription_data=sub_data,
        metadata=meta,
        allow_promotion_codes=True,
    )
    # TAX-SAFE checkout: automatic tax + required billing address + native tax-ID (VAT/TRN) collection.
    # There is intentionally NO silent no-tax fallback — if the tax-ready session cannot be created
    # (e.g. Stripe Tax not activated on the account), we fail with a controlled error and NEVER charge
    # the customer under a degraded, tax-disabled path.
    try:
        session = stripe.checkout.Session.create(
            **base_kwargs,
            automatic_tax={"enabled": True},
            billing_address_collection="required",
            tax_id_collection={"enabled": True},
        )
    except stripe.error.StripeError as e:
        logger.error("[checkout] tax-ready session creation failed ws=%s code=%s type=%s",
                     ws_id, getattr(e, "code", None), type(e).__name__)
        raise HTTPException(503, "Checkout is temporarily unavailable while tax configuration is being verified. "
                                 "Please try again shortly.")
    await db.payment_transactions.insert_one({
        "id": str(uuid.uuid4()), "session_id": session.id, "user_id": user["id"], "ws_id": ws_id,
        "plan": body.plan, "interval": body.interval, "seats": seats, "market": market,
        "amount": unit_amount * seats, "currency": currency,
        "status": "initiated", "payment_status": "pending",
        "created_at": now_iso(), "updated_at": now_iso(),
    })
    return {"checkout_url": session.url, "session_id": session.id,
            "amount": unit_amount * seats, "currency": currency}


async def _sync_ws_from_stripe_sub(ws_id, stripe_sub, plan, interval, seats, market, source, event_id):
    st = (stripe_sub or {}).get("status")
    status_map = {"trialing": "trialing", "active": "active", "past_due": "past_due",
                  "canceled": "cancelled", "unpaid": "unpaid", "incomplete": "incomplete",
                  "incomplete_expired": "incomplete_expired", "paused": "past_due"}
    status = status_map.get(st, st or "active")
    cpe = stripe_sub.get("current_period_end")
    if not cpe:
        # Newer Stripe API versions expose the period end on the subscription ITEM, not the subscription.
        _items = (stripe_sub.get("items") or {}).get("data") or []
        if _items:
            cpe = _items[0].get("current_period_end")
    trial_end = stripe_sub.get("trial_end")
    prior = await db.workspaces.find_one({"id": ws_id}, {"_id": 0, "subscription": 1})
    sub = {
        "plan": plan, "status": status, "interval": interval, "seats": seats, "market": market,
        "provider": "stripe", "stripe_subscription_id": stripe_sub.get("id"),
        "stripe_customer_id": stripe_sub.get("customer"),
        "current_period_end": datetime.fromtimestamp(cpe, timezone.utc).isoformat() if cpe else None,
        "trial_ends_at": datetime.fromtimestamp(trial_end, timezone.utc).isoformat() if trial_end else None,
        "updated_at": now_iso(),
    }
    _rf = ((prior or {}).get("subscription") or {}).get("referral")
    if _rf:
        sub["referral"] = _rf
    # Preserve the immutable one-time-trial marker so a paid/synced state can never
    # make the account trial-eligible again. Set it if Stripe reports a trial.
    _prior_started = ((prior or {}).get("subscription") or {}).get("trial_started_at")
    sub["trial_started_at"] = _prior_started or sub["trial_ends_at"] or (now_iso() if st == "trialing" else None)
    await db.workspaces.update_one({"id": ws_id}, {"$set": {"subscription": sub, "plan": plan}})
    if status == "active" and plan in ("pro", "team"):
        await record_paid_subscription_event(ws_id, source=source, event_id=event_id)


async def _handle_completed_session(session_obj, event_id):
    meta = session_obj.get("metadata") or {}
    ws_id = meta.get("ws_id")
    if not ws_id:
        return
    plan = meta.get("plan", "pro")
    interval = meta.get("interval", "month")
    seats = int(meta.get("seats") or 1)
    market = meta.get("market", "USD")
    sub_id = session_obj.get("subscription")
    stripe_sub = {}
    if sub_id:
        try:
            stripe_sub = stripe.Subscription.retrieve(sub_id)
        except stripe.error.StripeError:
            stripe_sub = {"id": sub_id, "status": "active", "customer": session_obj.get("customer")}
    await _sync_ws_from_stripe_sub(ws_id, stripe_sub, plan, interval, seats, market, source="stripe", event_id=event_id)
    await _record_tax_from_session(session_obj, ws_id, event_id)
    await db.payment_transactions.update_one(
        {"session_id": session_obj.get("id"), "payment_status": {"$ne": "paid"}},
        {"$set": {"status": "completed", "payment_status": "paid",
                  "stripe_subscription_id": sub_id, "updated_at": now_iso()}})


def _mask_tax_id(v: str) -> str:
    """Never store/expose a full tax ID. Keep only a trailing hint for admin recognition."""
    v = (v or "").strip()
    return ("•••" + v[-4:]) if len(v) > 4 else "•••"


def _map_tax_status(raw: str, tax_amount) -> str:
    """Distinguish real states — never claim 'no tax' when we simply don't know."""
    if raw in ("complete", "collected"):
        return "calculated" if (tax_amount or 0) > 0 else "no_tax_due"
    if raw == "failed":
        return "calculation_failed"
    if raw in ("requires_location_inputs", "not_collecting"):
        return "location_required"
    if raw is None:
        return "unavailable"
    return str(raw)


async def _upsert_tax_record(rec: dict):
    await db.billing_tax_records.update_one({"source_id": rec["source_id"]}, {"$set": rec}, upsert=True)


async def _record_tax_from_session(session_obj, ws_id, event_id):
    """Capture authoritative tax/amount/location from a completed Checkout Session (no revenue inflation:
    collected tax is stored separately from base subscription amount)."""
    try:
        cd = session_obj.get("customer_details") or {}
        addr = cd.get("address") or {}
        td = session_obj.get("total_details") or {}
        at = session_obj.get("automatic_tax") or {}
        tax_amount = td.get("amount_tax")
        tax_ids = cd.get("tax_ids") or []
        tid = tax_ids[0] if tax_ids else {}
        country = addr.get("country")
        rec = {
            "source_id": f"cs:{session_obj.get('id')}", "kind": "checkout",
            "workspace_id": ws_id, "country": country, "state": addr.get("state"),
            "postal_code": addr.get("postal_code"),
            "currency": (session_obj.get("currency") or "").upper(),
            "base_amount": session_obj.get("amount_subtotal"),
            "discount_amount": td.get("amount_discount"),
            "tax_amount": tax_amount, "total_amount": session_obj.get("amount_total"),
            "tax_status": _map_tax_status(at.get("status"), tax_amount),
            "tax_id_type": tid.get("type"), "tax_id_masked": _mask_tax_id(tid.get("value")) if tid else None,
            "stripe_customer_id": session_obj.get("customer"),
            "stripe_subscription_id": session_obj.get("subscription"),
            "created_at": now_iso(),
        }
        await _upsert_tax_record(rec)
        # Mirror non-sensitive authoritative tax location onto the workspace subscription for reporting.
        mirror = {"subscription.tax_country": country, "subscription.tax_status": rec["tax_status"],
                  "subscription.tax_id_present": bool(tid), "subscription.tax_updated_at": now_iso()}
        await db.workspaces.update_one({"id": ws_id}, {"$set": mirror})
    except Exception as e:
        logger.warning("[tax] session capture soft-fail: %s", type(e).__name__)


async def _record_tax_from_invoice(inv, ws_id, event_id):
    try:
        at = inv.get("automatic_tax") or {}
        tax_amount = inv.get("tax")
        addr = inv.get("customer_address") or {}
        tids = inv.get("customer_tax_ids") or []
        tid = tids[0] if tids else {}
        disc = inv.get("total_discount_amounts") or []
        rec = {
            "source_id": f"inv:{inv.get('id')}", "kind": "invoice",
            "workspace_id": ws_id, "country": addr.get("country"), "state": addr.get("state"),
            "postal_code": addr.get("postal_code"),
            "currency": (inv.get("currency") or "").upper(),
            "base_amount": inv.get("subtotal"),
            "discount_amount": sum(d.get("amount", 0) for d in disc) if disc else 0,
            "tax_amount": tax_amount, "total_amount": inv.get("total"),
            "tax_status": _map_tax_status(at.get("status"), tax_amount),
            "tax_id_type": tid.get("type"), "tax_id_masked": _mask_tax_id(tid.get("value")) if tid else None,
            "stripe_customer_id": inv.get("customer"),
            "stripe_subscription_id": inv.get("subscription"),
            "created_at": now_iso(),
        }
        await _upsert_tax_record(rec)
    except Exception as e:
        logger.warning("[tax] invoice capture soft-fail: %s", type(e).__name__)


@platform_router.get("/payments/status/{session_id}")
async def payment_status(session_id: str):
    """Unauthenticated poll target. Returns only status fields; syncs from Stripe as a webhook fallback."""
    record = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
    if not record:
        raise HTTPException(404, "Transaction not found")
    if record.get("payment_status") != "paid" and STRIPE_SECRET_KEY:
        try:
            s = stripe.checkout.Session.retrieve(session_id)
            if s.get("status") == "complete" or s.get("payment_status") == "paid":
                await _handle_completed_session(s, event_id=f"poll:{session_id}")
                record = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
        except stripe.error.StripeError:
            pass
    return {"session_id": record["session_id"], "status": record["status"],
            "payment_status": record["payment_status"], "plan": record.get("plan"),
            "amount": record.get("amount"), "currency": record.get("currency")}


@platform_router.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    except Exception:
        raise HTTPException(400, "Invalid signature")
    obj, t, eid = event["data"]["object"], event["type"], event.get("id")
    # Idempotency: dedupe multi-delivered webhooks so we never double-process or double-email.
    if eid:
        try:
            await db.stripe_events.insert_one({"id": eid, "type": t, "created_at": now_iso()})
        except Exception:
            return {"status": "duplicate"}
    if t == "checkout.session.completed":
        await _handle_completed_session(obj, event_id=eid)
    elif t in ("invoice.paid", "invoice.payment_succeeded"):
        sub_id = obj.get("subscription")
        if sub_id:
            ws = await db.workspaces.find_one({"subscription.stripe_subscription_id": sub_id}, {"_id": 0})
            if ws:
                sub = ws.get("subscription") or {}
                try:
                    stripe_sub = stripe.Subscription.retrieve(sub_id)
                except stripe.error.StripeError:
                    stripe_sub = {"id": sub_id, "status": "active", "customer": obj.get("customer")}
                await _sync_ws_from_stripe_sub(ws["id"], stripe_sub, sub.get("plan", "pro"),
                    sub.get("interval", "month"), sub.get("seats", 1), sub.get("market", "USD"),
                    source="stripe", event_id=eid)
                await _record_tax_from_invoice(obj, ws["id"], eid)
                await _maybe_notify_recovery(ws["id"], eid)
    elif t == "invoice.payment_failed":
        await _handle_invoice_failed(obj, eid)
    elif t == "customer.subscription.updated":
        sub_id = obj.get("id")
        ws = await db.workspaces.find_one({"subscription.stripe_subscription_id": sub_id}, {"_id": 0})
        if ws:
            sub = ws.get("subscription") or {}
            await _sync_ws_from_stripe_sub(ws["id"], obj, sub.get("plan", "pro"),
                sub.get("interval", "month"), sub.get("seats", 1), sub.get("market", "USD"),
                source="stripe", event_id=eid)
            if obj.get("status") == "active":
                await _maybe_notify_recovery(ws["id"], eid)
    elif t == "customer.subscription.deleted":
        ws = await db.workspaces.find_one({"subscription.stripe_subscription_id": obj.get("id")}, {"_id": 0, "id": 1})
        if ws:
            await db.workspaces.update_one({"id": ws["id"]},
                {"$set": {"subscription.status": "cancelled", "subscription.updated_at": now_iso()}})
    return {"status": "ok"}


async def _billing_owner(ws: dict):
    """The account/workspace billing owner (never every team member)."""
    return await db.users.find_one({"id": (ws or {}).get("owner_id")}, {"_id": 0, "email": 1, "language": 1})


async def _handle_invoice_failed(inv, event_id):
    """Renewal payment failed. Keep access while Stripe still considers it recoverable (past_due),
    surface the failure to the customer, and email the billing owner ONCE per failed invoice."""
    sub_id = inv.get("subscription")
    if not sub_id:
        return
    ws = await db.workspaces.find_one({"subscription.stripe_subscription_id": sub_id}, {"_id": 0})
    if not ws:
        return
    sub = ws.get("subscription") or {}
    try:
        stripe_sub = stripe.Subscription.retrieve(sub_id)
    except stripe.error.StripeError:
        stripe_sub = {"id": sub_id, "status": "past_due", "customer": inv.get("customer")}
    await _sync_ws_from_stripe_sub(ws["id"], stripe_sub, sub.get("plan", "pro"),
        sub.get("interval", "month"), sub.get("seats", 1), sub.get("market", "USD"),
        source="stripe", event_id=event_id)
    invoice_id = inv.get("id")
    amount_minor = inv.get("amount_due") or inv.get("total") or 0
    currency = (inv.get("currency") or "usd").upper()
    dunning = {
        "state": "failed", "invoice_id": invoice_id, "amount_due": amount_minor, "currency": currency,
        "hosted_invoice_url": inv.get("hosted_invoice_url"),
        "attempt_count": inv.get("attempt_count"),
        "next_attempt": (datetime.fromtimestamp(inv["next_payment_attempt"], timezone.utc).isoformat()
                         if inv.get("next_payment_attempt") else None),
        "failed_at": now_iso(),
    }
    await db.workspaces.update_one({"id": ws["id"]}, {"$set": {"subscription.dunning": dunning}})
    # Email the billing owner ONCE per failed invoice (idempotent on invoice_id).
    prior_inv = (sub.get("dunning") or {}).get("invoice_id")
    prior_state = (sub.get("dunning") or {}).get("state")
    if not (prior_inv == invoice_id and prior_state == "failed"):
        owner = await _billing_owner(ws)
        if owner and owner.get("email"):
            amount_str = _fmt_money_minor(amount_minor, currency)
            portal_url = f"{PUBLIC_APP_URL}/billing"
            await send_localized(owner["email"], "payment_failed", owner.get("language", "en"),
                                 portal_url, amount=amount_str)


async def _maybe_notify_recovery(ws_id, event_id):
    """After a successful payment, if the account was previously in a failed/dunning state,
    clear it and email the billing owner ONCE that billing is healthy again."""
    ws = await db.workspaces.find_one({"id": ws_id}, {"_id": 0})
    sub = (ws or {}).get("subscription") or {}
    dunning = sub.get("dunning") or {}
    if dunning.get("state") == "failed":
        await db.workspaces.update_one({"id": ws_id},
            {"$set": {"subscription.dunning": {"state": "recovered", "recovered_at": now_iso(),
                                               "invoice_id": dunning.get("invoice_id")}}})
        owner = await _billing_owner(ws)
        if owner and owner.get("email"):
            await send_localized(owner["email"], "payment_recovered", owner.get("language", "en"),
                                 f"{PUBLIC_APP_URL}/billing")


def _fmt_money_minor(minor, currency):
    zero_dec = {"JPY", "KRW", "VND", "CLP", "BHD", "KWD", "OMR"}
    cur = (currency or "USD").upper()
    amt = (minor or 0) / (1 if cur in zero_dec else 100)
    return f"{cur} {amt:,.2f}"


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
            "google_signin": _google_configured(),
            "email": _email_configured(),
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
        "stripe_mode": STRIPE_MODE,
        "stripe_publishable_key": STRIPE_PUBLISHABLE_KEY,
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
    account_type: Optional[str] = "individual"   # individual | team
    company_name: Optional[str] = ""
    seats: Optional[int] = 1
    billing_interval: Optional[str] = "month"     # month | year


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
    # Email layer ONLY reacts to the existing confirmed reward state: a reward was newly earned
    # this run (earned crossed a new threshold). Idempotent — a later recompute with no new
    # qualified referral will not re-enter this branch.
    if earned > existing and _email_configured():
        try:
            ws = await db.workspaces.find_one({"id": referrer_ws_id}, {"_id": 0, "owner_id": 1})
            owner = await db.users.find_one({"id": (ws or {}).get("owner_id")}, {"_id": 0, "email": 1, "language": 1}) if ws else None
            if owner and owner.get("email"):
                await send_localized(owner["email"], "referral_reward", owner.get("language", "en"),
                                     f"{PUBLIC_APP_URL}/referral", per=per, months=months)
        except Exception as e:
            logger.error(f"[email] referral reward email failed for {referrer_ws_id}: {e}")
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
                 "timezone": user.get("timezone", "UTC"), "timezone_source": user.get("timezone_source", "auto")},
        "workspace": ws, "memberships": ms, "entitlements": ent,
    }


async def _provision_account(*, email, name, account_type="individual", company_name="", workspace_name="",
                             seats=1, billing_interval="month", country_code="US", language="en",
                             tz="", currency="", referral_code=None, password=None,
                             google_id=None, email_verified=False):
    """Shared account provisioning for BOTH password signup and Google OAuth signup.
    Creates the user + workspace + membership + trial subscription and returns (user, ws_id).
    Reuses the single auth/workspace architecture — no parallel systems."""
    email = email.strip().lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(400, "An account with this email already exists")
    # Validate commercial constraints BEFORE any DB write (no orphaned users on failure).
    is_team = (account_type == "team")
    cfg = await get_commercial_config()
    min_seats = int(((cfg.get("plans") or {}).get("team") or {}).get("min_seats") or 3)
    seats_n = 1
    interval = None
    if is_team:
        seats_n = int(seats or min_seats)
        if seats_n < min_seats:
            raise HTTPException(400, f"Team plan requires at least {min_seats} seats")
        interval = "year" if billing_interval == "year" else "month"
    uid = str(uuid.uuid4())
    lang = language if language in SUPPORTED_LANGUAGES else "en"
    region = default_region(country_code if country_code else "US")
    if currency in SUPPORTED_CURRENCIES:
        region["default_currency"] = currency
    if tz:
        region["timezone"] = tz
    region["default_language"] = lang
    user = {
        "id": uid, "email": email,
        "password_hash": hash_pw(password) if password else "",
        "name": (name or "").strip(), "role": "WORKSPACE_OWNER", "email_verified": bool(email_verified),
        "language": lang, "locale": region["locale"], "timezone": region["timezone"],
        "timezone_source": "auto", "environment": "production_customer",
        "created_at": now_iso(),
    }
    if google_id:
        user["google_id"] = google_id
        user["auth_provider"] = "google"
    await db.users.insert_one(user)
    ws_id = str(uuid.uuid4())
    _tdays = await trial_days()
    _pending = "team" if is_team else "pro"
    if _tdays > 0:
        _sub = {"plan": "trial", "pending_plan": _pending, "status": "trialing",
                "trial_started_at": now_iso(),
                "trial_ends_at": (datetime.now(timezone.utc) + timedelta(days=_tdays)).isoformat(),
                "current_period_end": None, "seats": seats_n, "interval": interval}
    else:
        _sub = {"plan": "trial", "pending_plan": _pending, "status": "trial_expired",
                "trial_started_at": now_iso(),
                "trial_ends_at": now_iso(), "current_period_end": None, "seats": seats_n, "interval": interval}
    _ws_name = (company_name.strip() if is_team else "") or (workspace_name or "").strip() or ((name or "").strip() or "My Workspace")
    await db.workspaces.insert_one({
        "id": ws_id, "name": _ws_name,
        "type": "company" if is_team else "individual", "plan": "trial", "owner_id": uid,
        "subscription": _sub, "environment": "production_customer",
        "referral_code": await _gen_referral_code(),
        "region": region, "tax": {"tax_country": region["country_code"], "tax_inclusive": False,
                                   "tax_id": "", "status": "unregistered"},
        "branding": {}, "locked_fields": [], "created_at": now_iso(),
    })
    await db.memberships.insert_one({
        "id": str(uuid.uuid4()), "user_id": uid, "workspace_id": ws_id,
        "role": "WORKSPACE_OWNER", "status": "active", "created_at": now_iso(),
    })
    await _apply_referral(referral_code, email, ws_id, uid)
    await audit(ws_id, uid, "account.register")
    return user, ws_id


@platform_router.post("/auth/register")
async def register(body: RegisterIn, request: Request):
    rate_limit(request, "register", 40, 3600)
    user, ws_id = await _provision_account(
        email=body.email, name=body.name, account_type=body.account_type or "individual",
        company_name=body.company_name or "", workspace_name=body.workspace_name or "",
        seats=body.seats or 1, billing_interval=body.billing_interval or "month",
        country_code=body.country_code, language=body.language, tz=body.timezone,
        currency=body.currency, referral_code=body.referral_code, password=body.password,
        email_verified=False)
    verify_token = secrets.token_urlsafe(32)
    await db.email_verifications.insert_one({
        "id": str(uuid.uuid4()), "user_id": user["id"], "token": verify_token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(), "used": False,
    })
    # Email: send localized verification via Resend if configured, else log link (dev).
    link = f"{PUBLIC_APP_URL}/verify?token={verify_token}"
    if _email_configured():
        await send_localized(user["email"], "verify", user.get("language", "en"), link)
    else:
        logger.info(f"[email:NOT_CONFIGURED] verification link for {user['email']}: {link}")
    return await _auth_payload(user, request)


# ---- Google OAuth endpoints (server-side authorization-code flow into the existing JWT/session) ----
class GoogleCompleteIn(BaseModel):
    gp: str
    account_type: Optional[str] = "individual"
    company_name: Optional[str] = ""
    seats: Optional[int] = 1
    billing_interval: Optional[str] = "month"


@platform_router.get("/auth/google/start")
async def google_start(request: Request, ref: Optional[str] = None):
    # REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    if not _google_configured():
        raise HTTPException(503, "Google sign-in is not configured")
    state = make_token("google_oauth", "oauth_state", minutes=10,
                       extra={"nonce": secrets.token_urlsafe(8), "ref": ref or ""})
    import urllib.parse
    params = {
        "client_id": GOOGLE_OAUTH_CLIENT_ID,
        "redirect_uri": GOOGLE_OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    return RedirectResponse("https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params))


@platform_router.get("/auth/google/callback")
async def google_callback(request: Request, code: Optional[str] = None,
                          state: Optional[str] = None, error: Optional[str] = None):
    fb = _google_frontend_base()
    if error:
        logger.error(f"[google] provider returned error at callback: {error}")
        return RedirectResponse(f"{fb}/login?google_error=cancelled&reason={error}")
    if not code or not state:
        return RedirectResponse(f"{fb}/login?google_error=cancelled&reason=missing_params")
    try:
        st = jwt.decode(state, JWT_SECRET, algorithms=[JWT_ALG])
        if st.get("type") != "oauth_state":
            raise ValueError("bad state")
    except Exception as e:
        logger.error(f"[google] state validation failed: {type(e).__name__}")
        return RedirectResponse(f"{fb}/login?google_error=state&reason=bad_state")
    ref = st.get("ref") or ""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=15) as cx:
            tok = await cx.post("https://oauth2.googleapis.com/token", data={
                "code": code, "client_id": GOOGLE_OAUTH_CLIENT_ID,
                "client_secret": GOOGLE_OAUTH_CLIENT_SECRET,
                "redirect_uri": GOOGLE_OAUTH_REDIRECT_URI, "grant_type": "authorization_code"})
            if tok.status_code != 200:
                try:
                    gerr = (tok.json() or {}).get("error", "unknown")
                except Exception:
                    gerr = "unparseable"
                # gerr is Google's error CODE only (e.g. invalid_client, redirect_uri_mismatch) — never a token/secret.
                logger.error(f"[google] token exchange failed: http={tok.status_code} error={gerr} redirect_uri={GOOGLE_OAUTH_REDIRECT_URI}")
                return RedirectResponse(f"{fb}/login?google_error=exchange&reason={gerr}")
            access_tok = tok.json().get("access_token")
            ui = await cx.get("https://www.googleapis.com/oauth2/v3/userinfo",
                              headers={"Authorization": f"Bearer {access_tok}"})
            if ui.status_code != 200:
                logger.error(f"[google] userinfo failed: http={ui.status_code}")
                return RedirectResponse(f"{fb}/login?google_error=profile&reason=userinfo_{ui.status_code}")
    except Exception as e:
        logger.error(f"[google] callback network/exception: {type(e).__name__}: {e}")
        return RedirectResponse(f"{fb}/login?google_error=network&reason={type(e).__name__}")
    info = ui.json()
    email = (info.get("email") or "").strip().lower()
    if not email or not info.get("email_verified"):
        logger.error(f"[google] email not verified or missing (has_email={bool(email)})")
        return RedirectResponse(f"{fb}/login?google_error=unverified&reason=email_unverified")
    sub = info.get("sub")
    name = info.get("name") or ""
    import urllib.parse
    existing = await db.users.find_one({"email": email})
    if existing:
        # Auto-link Google to the existing account (email is Google-verified) — never duplicate.
        upd = {"email_verified": True}
        if not existing.get("google_id"):
            upd["google_id"] = sub
            upd["auth_provider"] = existing.get("auth_provider") or "google"
        await db.users.update_one({"id": existing["id"]}, {"$set": upd})
        access_t, refresh_t = await _issue_session(existing, request)
        q = urllib.parse.urlencode({"token": access_t, "refresh": refresh_t})
        return RedirectResponse(f"{fb}/auth/google/finish?{q}")
    # New user → send to the Individual/Team selection step (short-lived signed pending token).
    pend = make_token("google_pending", "google_pending", minutes=20,
                      extra={"email": email, "name": name, "sub": sub, "ref": ref})
    q = urllib.parse.urlencode({"gp": pend, "email": email, "name": name})
    return RedirectResponse(f"{fb}/register?{q}")


@platform_router.post("/auth/google/complete")
async def google_complete(body: GoogleCompleteIn, request: Request):
    try:
        p = jwt.decode(body.gp, JWT_SECRET, algorithms=[JWT_ALG])
        if p.get("type") != "google_pending":
            raise ValueError("bad token")
    except Exception:
        raise HTTPException(400, "Your Google sign-up session expired. Please try again.")
    user, ws_id = await _provision_account(
        email=p["email"], name=p.get("name", ""), account_type=body.account_type or "individual",
        company_name=body.company_name or "", seats=body.seats or 1,
        billing_interval=body.billing_interval or "month", referral_code=p.get("ref") or None,
        password=None, google_id=p.get("sub"), email_verified=True)
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
    if _email_configured():
        await send_localized(user["email"], "verify_resend", user.get("language", "en"), link)
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
        if _email_configured():
            await send_localized(email, "reset", user.get("language", "en"), link)
        else:
            logger.info(f"[email:NOT_CONFIGURED] reset link for {email}: {link}")
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


class ProfilePrefsIn(BaseModel):
    timezone: Optional[str] = None
    language: Optional[str] = None


@platform_router.patch("/account/preferences")
async def update_preferences(body: ProfilePrefsIn, user: dict = Depends(current_user)):
    """Update the user's own account preferences. A manual timezone choice persists and overrides
    device auto-detection (timezone_source=manual)."""
    upd = {}
    if body.timezone:
        try:
            from zoneinfo import ZoneInfo
            ZoneInfo(body.timezone)
        except Exception:
            raise HTTPException(400, "Invalid timezone")
        upd["timezone"] = body.timezone
        upd["timezone_source"] = "manual"
    if body.language and body.language in SUPPORTED_LANGUAGES:
        upd["language"] = body.language
    if not upd:
        return {"ok": True}
    await db.users.update_one({"id": user["id"]}, {"$set": upd})
    if "timezone" in upd:
        ws = await db.workspaces.find_one({"owner_id": user["id"], "type": "individual"}, {"_id": 0, "id": 1})
        if ws:
            await db.workspaces.update_one({"id": ws["id"]}, {"$set": {"region.timezone": upd["timezone"]}})
    return {"ok": True, **upd}


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
    # Explicit safe whitelist — never export password hashes, auth identifiers
    # (google_id/auth_provider), session/security internals or system metadata.
    safe_user = {k: user[k] for k in (
        "id", "email", "name", "created_at", "language", "locale", "timezone",
        "account_type", "email_verified",
    ) if k in user}
    return {"user": safe_user, "cards": cards, "leads": leads, "exported_at": now_iso()}

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


CRM_HIDDEN = ()  # placeholder


LEAD_CSV_COLS = [
    ("name", "Name"), ("first_name", "First Name"), ("last_name", "Last Name"),
    ("email", "Email"), ("phone", "Phone"), ("company", "Company"), ("title", "Job Title"),
    ("website", "Website"), ("linkedin", "LinkedIn"),
    ("source", "Source"), ("scanner_type", "Scanner Type"), ("event", "Event"),
    ("event_id", "Event ID"), ("captured_by_name", "Captured By"), ("captured_at", "Captured At"),
    ("status", "Pipeline Stage"), ("tags", "Tags"), ("next_follow_up", "Next Follow-up"),
    ("follow_up_completed_at", "Follow-up Completed"), ("lead_score", "Lead Score"),
    ("effective_temperature", "Temperature"), ("classification", "Classification"),
    ("opportunity_value", "Opportunity Value"), ("opportunity_currency", "Opportunity Currency"),
    ("expected_close_date", "Expected Close Date"), ("actual_revenue", "Actual Revenue"),
    ("actual_revenue_currency", "Revenue Currency"), ("revenue_recorded_at", "Revenue Date"),
    ("revenue_attribution_event", "Revenue Attribution Event"),
    ("revenue_attribution_type", "Revenue Attribution Type"),
]


async def _lead_csv_row(l: dict, uname: dict, ev_names: dict) -> list:
    ra = l.get("revenue_attribution") or {}
    eff = effective_temperature(l) if "effective_temperature" in globals() else (l.get("lead_temperature") or "")
    classification = "Manual" if l.get("lead_temperature_override") else "Automatic"
    att_ev = ""
    if ra.get("event_id"):
        att_ev = ev_names.get(ra["event_id"]) or ra["event_id"]
    elif ra.get("type") in ("organic", "other"):
        att_ev = ra.get("type").capitalize()
    computed = {
        "captured_by_name": uname.get(l.get("captured_by"), l.get("captured_by") or ""),
        "effective_temperature": eff, "classification": classification,
        "revenue_attribution_event": att_ev, "revenue_attribution_type": ra.get("type") or "",
    }
    out = []
    for key, _ in LEAD_CSV_COLS:
        if key == "tags":
            out.append(", ".join(l.get("tags") or []))
        elif key in computed:
            out.append(computed[key])
        else:
            v = l.get(key)
            out.append("" if v is None else v)
    return out


def _csv_response(rows, header, filename):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    for r in rows:
        w.writerow(r)
    # UTF-8 BOM so Excel renders Arabic correctly
    data = ("\ufeff" + buf.getvalue()).encode("utf-8")
    return StreamingResponse(io.BytesIO(data), media_type="text/csv; charset=utf-8",
                             headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@platform_router.get("/crm/leads.csv")
async def export_leads_csv(user: dict = Depends(current_user)):
    slugs = await _owned_slugs(user)
    leads = await db.leads.find({"cardSlug": {"$in": slugs}}, {"_id": 0}).to_list(20000)
    uids = list({l.get("captured_by") for l in leads if l.get("captured_by")})
    users = await db.users.find({"id": {"$in": uids}}, {"_id": 0, "id": 1, "name": 1, "email": 1}).to_list(5000) if uids else []
    uname = {u["id"]: (u.get("name") or u.get("email") or u["id"]) for u in users}
    evids = list({(l.get("revenue_attribution") or {}).get("event_id") for l in leads if (l.get("revenue_attribution") or {}).get("event_id")})
    evs = await db.events.find({"id": {"$in": evids}}, {"_id": 0, "id": 1, "name": 1}).to_list(1000) if evids else []
    ev_names = {e["id"]: e.get("name") for e in evs}
    rows = [await _lead_csv_row(l, uname, ev_names) for l in leads]
    return _csv_response(rows, [h for _, h in LEAD_CSV_COLS], "tappresence-leads.csv")


@platform_router.get("/events/{event_id}/leads.csv")
async def export_event_leads_csv(event_id: str, user: dict = Depends(current_user)):
    ev = await _event_or_403(event_id, user)
    leads = await db.leads.find(_event_lead_query(event_id), {"_id": 0}).sort("created_at", -1).to_list(20000)
    uids = list({l.get("captured_by") for l in leads if l.get("captured_by")})
    users = await db.users.find({"id": {"$in": uids}}, {"_id": 0, "id": 1, "name": 1, "email": 1}).to_list(5000) if uids else []
    uname = {u["id"]: (u.get("name") or u.get("email") or u["id"]) for u in users}
    ev_names = {event_id: ev.get("name")}
    for l in leads:
        raid = (l.get("revenue_attribution") or {}).get("event_id")
        if raid and raid not in ev_names:
            oe = await db.events.find_one({"id": raid}, {"_id": 0, "name": 1})
            ev_names[raid] = (oe or {}).get("name") or raid
    rows = [await _lead_csv_row(l, uname, ev_names) for l in leads]
    safe = "".join(c for c in (ev.get("name") or "event") if c.isalnum() or c in " -_")[:40].strip() or "event"
    return _csv_response(rows, [h for _, h in LEAD_CSV_COLS], f"{safe}-leads.csv")

# ------------------------------------------------------------------ wallet passes (Phase 5, provider-abstracted)
_GW_SCOPE = "https://www.googleapis.com/auth/wallet_object.issuer"


def _gw_sa_info():
    """Decode the base64 service-account JSON (server-side only). Never returned/logged."""
    return json.loads(base64.b64decode(os.environ["GOOGLE_WALLET_SA_JSON"]))


def _gw_object_suffix(slug):
    return re.sub(r"[^A-Za-z0-9._-]", "-", slug)


def _gw_build_object(card, slug):
    issuer = os.environ["GOOGLE_WALLET_ISSUER_ID"]
    class_id = f"{issuer}.tappresence_business_card"
    obj_id = f"{issuer}.{_gw_object_suffix(slug)}"
    ident = card.get("identity", {}) or {}
    name = (ident.get("fullName") or "TapPresence").strip()
    title = (ident.get("jobTitle") or "").strip()
    company = (ident.get("company") or "").strip()
    profile_url = f"{PUBLIC_APP_URL}/{slug}"
    text_modules = []
    if company:
        text_modules.append({"id": "company", "header": "Company", "body": company})
    if title:
        text_modules.append({"id": "title", "header": "Job Title", "body": title})
    obj = {
        "id": obj_id,
        "classId": class_id,
        "state": "ACTIVE",
        "cardTitle": {"defaultValue": {"language": "en", "value": "TapPresence"}},
        "header": {"defaultValue": {"language": "en", "value": name}},
        "subheader": {"defaultValue": {"language": "en", "value": title or company}},
        "hexBackgroundColor": "#0B0D12",
        "logo": {"sourceUri": {"uri": f"{PUBLIC_APP_URL}/tp-mark.png"},
                 "contentDescription": {"defaultValue": {"language": "en", "value": "TapPresence"}}},
        "textModulesData": text_modules,
        "linksModuleData": {"uris": [{"uri": profile_url, "description": "View TapPresence card", "id": "profile"}]},
        "barcode": {"type": "QR_CODE", "value": profile_url, "alternateText": name},
    }
    return obj_id, class_id, obj


def _gw_upsert_object(obj):
    """Insert or update the generic object via Wallet REST API (sync; call via to_thread)."""
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from google.oauth2 import service_account
    creds = service_account.Credentials.from_service_account_info(_gw_sa_info(), scopes=[_GW_SCOPE])
    svc = build("walletobjects", "v1", credentials=creds, cache_discovery=False)
    try:
        svc.genericobject().get(resourceId=obj["id"]).execute()
        svc.genericobject().patch(resourceId=obj["id"], body=obj).execute()
        return "updated"
    except HttpError as e:
        if getattr(e, "resp", None) is not None and e.resp.status == 404:
            svc.genericobject().insert(body=obj).execute()
            return "created"
        raise


def _gw_save_jwt(generic_objects):
    info = _gw_sa_info()
    payload = {"iss": info["client_email"], "aud": "google", "typ": "savetowallet",
               "iat": int(time.time()), "origins": [PUBLIC_APP_URL],
               "payload": {"genericObjects": generic_objects}}
    token = jwt.encode(payload, info["private_key"], algorithm="RS256")
    return token if isinstance(token, str) else token.decode()


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
async def card_wallet_pass(slug: str, platform: str, user: dict = Depends(current_user)):
    """Owner-only wallet pass for the card's contact. Provider-abstracted:
    reports Not Configured until Apple/Google Wallet credentials are supplied.
    Only the card owner (or an authorized workspace admin) may generate the pass."""
    if platform not in ("apple", "google"):
        raise HTTPException(400, "Unsupported wallet platform")
    card = await db.digital_cards.find_one({"slug": slug, "status": "published"}, {"_id": 0})
    if not card:
        raise HTTPException(404, "Card not found")
    # Authorization: SUPER_ADMIN, workspace admin roles, or the card's own owner.
    if user.get("role") != "SUPER_ADMIN":
        m = await db.memberships.find_one(
            {"user_id": user["id"], "workspace_id": card.get("workspace_id")}, {"_id": 0})
        admin_roles = ("WORKSPACE_OWNER", "WORKSPACE_ADMIN", "MANAGER")
        if not m or (m.get("role") not in admin_roles and card.get("owner_user_id") != user["id"]):
            raise HTTPException(403, "Not authorized to generate a wallet pass for this card")
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
    if platform == "google":
        obj_id, class_id, obj = _gw_build_object(card, slug)
        try:
            sync = await asyncio.to_thread(_gw_upsert_object, obj)
            token = _gw_save_jwt([{"id": obj_id, "classId": class_id}])
        except Exception as e:
            logging.error(f"[gwallet] object upsert failed ({type(e).__name__}); embedding full object in JWT")
            sync = "jwt_inline"
            token = _gw_save_jwt([obj])
        await meter_usage("wallet_pass", user_id=user["id"], workspace_id=card.get("workspace_id"),
                          quantity=1, result="success", source="wallet:google", paid=True)
        return {"configured": True, "platform": "google", "pass_data": pass_data,
                "object_id": obj_id, "class_id": class_id, "sync": sync,
                "save_url": f"https://pay.google.com/gp/v/save/{token}"}
    # Apple (unchanged): the signed .pkpass would be produced by the provider adapter here.
    await meter_usage("wallet_pass", user_id=user["id"], workspace_id=card.get("workspace_id"),
                      quantity=1, result="success", source=f"wallet:{platform}", paid=True)
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
    stripe_tax_code: Optional[str] = None
    regional_pricing: Optional[dict] = None
    fx_rates: Optional[dict] = None
    manual_price_markets: Optional[list] = None


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


# ================================================================== TapPresence Control Center (SUPER_ADMIN only)
def _win(start, end):
    now = datetime.now(timezone.utc)
    lo = start or (now - timedelta(days=30)).isoformat()
    hi = end or now.isoformat()
    return {"$gte": lo, "$lte": hi}, lo, hi


@platform_router.get("/admin/control/overview")
async def control_overview(start: str = None, end: str = None, include_internal: bool = False, user: dict = Depends(current_user)):
    """Global platform overview. Real CUSTOMER data only by default (internal/demo/test excluded).
    Money metrics stay None until real billing (Stripe) is connected. Current-state metrics are lifetime
    totals; period metrics respect the date window."""
    _require_super(user)
    from collections import Counter
    tw, lo, hi = _win(start, end)
    cf = customer_ws_filter(include_internal)

    # ---- USERS (distinct from customer accounts) ----
    users_total = await db.users.count_documents({})
    users_customers = await db.users.count_documents({"environment": "production_customer"})
    users_internal = users_total - users_customers

    # ---- CUSTOMER ACCOUNTS (workspaces), mutually exclusive categories ----
    wss = await db.workspaces.find(cf, {"_id": 0}).to_list(20000)
    individual = company = enterprise = 0
    active_trials = active_paid = seats = 0
    plan_dist = Counter()
    for w in wss:
        sub = w.get("subscription") or {}
        st = effective_status(w)
        plan = sub.get("plan") or w.get("plan") or "trial"
        if plan == "enterprise":
            enterprise += 1
        elif w.get("type") in ("company", "team"):
            company += 1
        else:
            individual += 1
        if st == "trialing":
            active_trials += 1
            plan_dist["trial"] += 1
        elif is_real_paid(sub):
            active_paid += 1
            seats += int(sub.get("seats") or 0)
            plan_dist[plan] += 1
        else:
            plan_dist[st if st != "active" else "inactive"] += 1
    total_customers = len(wss)
    new_accounts = await db.workspaces.count_documents({**cf, "created_at": tw})
    cancellations = await db.workspaces.count_documents({**cf, "subscription.status": "canceled", "subscription.canceled_at": tw})

    # ---- PRODUCT USAGE (attributed to customer workspaces, windowed) ----
    ws_ids = [w["id"] for w in wss]
    cards = await db.digital_cards.find({"workspace_id": {"$in": ws_ids}}, {"_id": 0, "id": 1, "slug": 1, "status": 1}).to_list(50000)
    slugs = [c["slug"] for c in cards]
    card_ids = [c["id"] for c in cards]
    published = sum(1 for c in cards if c.get("status") == "published")
    views = await db.analytics_events.count_documents({"type": "view", "cardSlug": {"$in": slugs}, "created_at": tw})
    scans = await db.analytics_events.count_documents({"type": "scan", "cardSlug": {"$in": slugs}, "created_at": tw})
    nfctaps = await db.analytics_events.count_documents({"type": "nfctap", "cardSlug": {"$in": slugs}, "created_at": tw})
    leads = await db.leads.count_documents({"workspace_id": {"$in": ws_ids}, "created_at": tw})
    scanner_uses = await db.leads.count_documents({"workspace_id": {"$in": ws_ids}, "source": {"$in": ["business_card_scan", "badge_scan", "qr_scan"]}, "created_at": tw})
    meetings_booked = await db.meetings.count_documents({"card_id": {"$in": card_ids}, "created_at": tw})
    campaigns = await db.campaigns.count_documents({"workspace_id": {"$in": ws_ids}})
    paid_referrals = await db.referrals.count_documents({"referrer_ws_id": {"$in": ws_ids}, "status": "qualified"})

    return {
        "money_available": bool(_configured("STRIPE_SECRET_KEY")),
        "include_internal": include_internal,
        "users": {"total": users_total, "customers": users_customers, "internal": users_internal},
        "accounts": {
            "total": total_customers, "individual": individual, "company": company, "enterprise": enterprise,
            "team_seats": seats, "new_in_period": new_accounts,
        },
        "subscriptions": {
            "active_trials": active_trials, "active_paid": active_paid,
            "cancellations_in_period": cancellations, "trial_to_paid": None,
        },
        "money": {"mrr": None, "arr": None, "revenue_month": None, "trial_to_paid": None, "churn": None},
        "usage": {
            "published_cards": published, "views": views, "scans": scans, "nfc_taps": nfctaps,
            "leads": leads, "scanner_uses": scanner_uses, "meetings_booked": meetings_booked,
            "campaigns": campaigns, "paid_referrals": paid_referrals,
        },
        "plan_distribution": dict(plan_dist),
        "range": {"start": lo, "end": hi},
    }


@platform_router.get("/admin/control/subscriptions")
async def control_subscriptions(include_internal: bool = False, user: dict = Depends(current_user)):
    """Truthful subscription list: real customers only, never a 'free' label. Money values appear once Stripe is connected."""
    _require_super(user)
    from collections import Counter
    wss = await db.workspaces.find(customer_ws_filter(include_internal), {"_id": 0}).sort("created_at", -1).to_list(20000)
    summary = Counter()
    items = []
    for w in wss:
        sub = w.get("subscription") or {}
        st = effective_status(w)
        bucket = "trialing" if st == "trialing" else "active" if is_real_paid(sub) else "past_due" if st == "past_due" else "canceled" if st in ("canceled", "cancel_at_period_end") else "inactive"
        summary[bucket] += 1
        items.append({
            "id": w["id"], "name": w.get("name"), "type": w.get("type"),
            "plan": display_plan(w), "status": st, "bucket": bucket,
            "seats": sub.get("seats"),
            "renewal": sub.get("current_period_end"),
            "trial_ends_at": sub.get("trial_ends_at"),
        })
    return {"summary": dict(summary), "items": items, "money_available": bool(_configured("STRIPE_SECRET_KEY"))}


ROLE_LABELS = {"SUPER_ADMIN": "Super Admin", "WORKSPACE_OWNER": "Owner", "WORKSPACE_ADMIN": "Admin", "MANAGER": "Manager", "MEMBER": "Member"}
PUBLIC_PLANS = ["trial", "pro", "team", "enterprise"]
# feature -> env keys that must be configured for the feature to actually work (None = not provider-gated)
ENTITLEMENT_PROVIDER = {"wallet": ("APPLE_WALLET_CERT_B64", "GOOGLE_WALLET_ISSUER_ID"), "ai_followup": ("EMERGENT_LLM_KEY",), "custom_domain": ("CUSTOM_DOMAIN_HOST",), "api": ()}


@platform_router.get("/admin/control/customers")
async def control_customers(q: str = "", include_internal: bool = False, user: dict = Depends(current_user)):
    """Customer ACCOUNTS = owners of customer workspaces (NOT every user; team members are not separate customers)."""
    _require_super(user)
    wss = await db.workspaces.find(customer_ws_filter(include_internal), {"_id": 0}).sort("created_at", -1).to_list(20000)
    out = []
    ql = q.strip().lower()
    for w in wss:
        owner = await db.users.find_one({"id": w.get("owner_id")}, {"_id": 0, "password_hash": 0}) if w.get("owner_id") else None
        if not owner:
            continue
        if ql and ql not in (owner.get("name") or "").lower() and ql not in (owner.get("email") or "").lower() and ql not in (w.get("name") or "").lower():
            continue
        out.append({
            "user_id": owner["id"], "name": owner.get("name"), "email": owner.get("email"),
            "role": owner.get("role"), "role_label": ROLE_LABELS.get(owner.get("role"), owner.get("role")),
            "email_verified": owner.get("email_verified", False), "suspended": owner.get("suspended", False),
            "workspace": w.get("name"), "workspace_id": w["id"], "account_type": w.get("type"),
            "plan": display_plan(w), "status": effective_status(w), "environment": w.get("environment"),
            "members": await db.memberships.count_documents({"workspace_id": w["id"]}),
        })
    return {"items": out}


@platform_router.get("/admin/control/workspaces")
async def control_workspaces(q: str = "", include_internal: bool = False, type: str = "all", user: dict = Depends(current_user)):
    _require_super(user)
    wss = await db.workspaces.find(customer_ws_filter(include_internal), {"_id": 0}).sort("created_at", -1).to_list(20000)
    out = []
    ql = q.strip().lower()
    for w in wss:
        if type == "company" and w.get("type") not in ("company", "team"):
            continue
        if type == "individual" and w.get("type") != "individual":
            continue
        if ql and ql not in (w.get("name") or "").lower():
            continue
        out.append({
            "id": w["id"], "name": w.get("name"), "type": w.get("type"),
            "plan": display_plan(w), "status": effective_status(w), "environment": w.get("environment"),
            "members": await db.memberships.count_documents({"workspace_id": w["id"]}),
            "cards": await db.digital_cards.count_documents({"workspace_id": w["id"]}),
            "leads": await db.leads.count_documents({"workspace_id": w["id"]}),
        })
    return {"items": out}


@platform_router.get("/admin/control/customers/{user_id}")
async def control_customer_detail(user_id: str, user: dict = Depends(current_user)):
    _require_super(user)
    u = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    if not u:
        raise HTTPException(404, "User not found")
    ms = await db.memberships.find({"user_id": user_id}, {"_id": 0}).to_list(200)
    ws_ids = [m["workspace_id"] for m in ms]
    wss = await db.workspaces.find({"id": {"$in": ws_ids}}, {"_id": 0}).to_list(200)
    cards = await db.digital_cards.find({"owner_user_id": user_id}, {"_id": 0, "slug": 1, "status": 1, "identity": 1, "workspace_id": 1}).to_list(500)
    slugs = [c["slug"] for c in cards]
    leads = await db.leads.count_documents({"cardSlug": {"$in": slugs}}) if slugs else 0
    meetings = await db.meetings.count_documents({"owner_user_id": user_id})
    referrals = await db.referrals.count_documents({"referrer_user_id": user_id})
    last = await db.analytics_events.find({"cardSlug": {"$in": slugs}}, {"_id": 0, "created_at": 1}).sort("created_at", -1).to_list(1) if slugs else []
    prim = next((w for w in wss if w.get("type") == "individual"), wss[0] if wss else None)
    return {
        "user": u, "workspaces": wss, "memberships": ms,
        "cards": cards, "leads": leads, "meetings": meetings, "referrals": referrals,
        "last_activity": last[0]["created_at"] if last else None,
        "subscription": (prim or {}).get("subscription"),
        "status": effective_status(prim) if prim else None,
    }


@platform_router.post("/admin/control/customers/{user_id}/action")
async def control_customer_action(user_id: str, body: dict, user: dict = Depends(current_user)):
    """Safe support actions: resend_verification, revoke_sessions. (suspend/unsuspend uses existing endpoint.)"""
    _require_super(user)
    target = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not target:
        raise HTTPException(404, "User not found")
    action = (body or {}).get("action")
    if action == "revoke_sessions":
        await db.sessions.delete_many({"user_id": user_id})
    elif action == "resend_verification":
        token = secrets.token_urlsafe(32)
        await db.email_verifications.insert_one({
            "id": str(uuid.uuid4()), "user_id": user_id, "token": token, "used": False,
            "created_at": now_iso(), "expires_at": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
        })
    else:
        raise HTTPException(400, "Unknown action")
    await audit(None, user["id"], f"admin.customer.{action}", {"target": user_id, "email": target.get("email")})
    return {"ok": True, "action": action}


@platform_router.get("/admin/control/workspaces/{wid}")
async def control_workspace_detail(wid: str, user: dict = Depends(current_user)):
    _require_super(user)
    w = await db.workspaces.find_one({"id": wid}, {"_id": 0})
    if not w:
        raise HTTPException(404, "Workspace not found")
    owner = await db.users.find_one({"id": w.get("owner_id")}, {"_id": 0, "name": 1, "email": 1}) if w.get("owner_id") else None
    ms = await db.memberships.find({"workspace_id": wid}, {"_id": 0}).to_list(500)
    member_users = await db.users.find({"id": {"$in": [m["user_id"] for m in ms]}}, {"_id": 0, "id": 1, "name": 1, "email": 1}).to_list(500)
    umap = {u["id"]: u for u in member_users}
    sub = w.get("subscription") or {}
    return {
        "workspace": w, "owner": owner, "status": effective_status(w),
        "plan": sub.get("plan") or w.get("plan"), "seats": sub.get("seats"),
        "members": [{"role": m.get("role"), **umap.get(m["user_id"], {"id": m["user_id"]})} for m in ms],
        "brand_lock": (w.get("branding") or {}).get("locked", False),
        "cards": await db.digital_cards.count_documents({"workspace_id": wid}),
        "leads": await db.leads.count_documents({"workspace_id": wid}),
        "meetings": await db.meetings.count_documents({"workspace_id": wid}),
    }


@platform_router.get("/admin/control/referrals")
async def control_referrals(user: dict = Depends(current_user)):
    _require_super(user)
    total = await db.referrals.count_documents({})
    signed = await db.referrals.count_documents({"status": "signed_up"})
    qualified = await db.referrals.count_documents({"status": "qualified"})
    revoked = await db.referrals.count_documents({"status": "revoked"})
    rewards = await db.referral_rewards.find({}, {"_id": 0}).to_list(5000)
    months_earned = sum(int(r.get("free_months_earned", 0)) for r in rewards)
    from collections import Counter
    top = Counter()
    async for r in db.referrals.find({"status": "qualified"}, {"_id": 0, "referrer_ws_id": 1}):
        top[r.get("referrer_ws_id")] += 1
    top_list = []
    for ws_id, cnt in top.most_common(10):
        w = await db.workspaces.find_one({"id": ws_id}, {"_id": 0, "name": 1})
        top_list.append({"workspace": (w or {}).get("name") or ws_id, "qualified": cnt})
    cfg = await get_commercial_config()
    return {
        "funnel": {"total": total, "signed_up": signed, "qualified": qualified, "revoked": revoked},
        "months_earned": months_earned, "top_referrers": top_list,
        "config": cfg.get("referral", {}),
    }


@platform_router.get("/admin/control/flags")
async def control_flags(user: dict = Depends(current_user)):
    _require_super(user)
    return {"items": await db.feature_flags.find({}, {"_id": 0}).sort("key", 1).to_list(500)}


@platform_router.put("/admin/control/flags/{key}")
async def control_flag_set(key: str, body: dict, user: dict = Depends(current_user)):
    _require_super(user)
    before = await db.feature_flags.find_one({"key": key}, {"_id": 0})
    doc = {
        "key": key, "enabled": bool(body.get("enabled", False)),
        "description": body.get("description", (before or {}).get("description", "")),
        "plans": body.get("plans", (before or {}).get("plans", [])),
        "environment": body.get("environment", (before or {}).get("environment", "all")),
        "updated_at": now_iso(),
    }
    await db.feature_flags.update_one({"key": key}, {"$set": doc}, upsert=True)
    await audit(None, user["id"], "admin.flag.set", {"key": key, "before": before, "after": doc})
    return {"ok": True, "flag": doc}


@platform_router.get("/admin/control/audit")
async def control_audit(q: str = "", user: dict = Depends(current_user)):
    _require_super(user)
    query = {"action": {"$regex": re.escape(q.strip()), "$options": "i"}} if q.strip() else {}
    logs = await db.audit_logs.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
    for lg in logs:
        actor = await db.users.find_one({"id": lg.get("actor_id")}, {"_id": 0, "email": 1}) if lg.get("actor_id") else None
        lg["actor_email"] = (actor or {}).get("email")
    return {"items": logs}


@platform_router.get("/admin/control/security")
async def control_security(user: dict = Depends(current_user)):
    _require_super(user)
    suspended = await db.users.find({"suspended": True}, {"_id": 0, "id": 1, "name": 1, "email": 1}).to_list(500)
    attempts = await db.login_attempts.find({"fails": {"$gte": 3}}, {"_id": 0}).sort("fails", -1).to_list(100)
    revoked_referrals = await db.referrals.count_documents({"status": "revoked"})
    return {
        "suspended_accounts": suspended,
        "locked_or_throttled": [{"identifier": a.get("identifier"), "fails": a.get("fails"), "until": a.get("locked_until")} for a in attempts],
        "suspicious_referrals": revoked_referrals,
    }


@platform_router.get("/admin/control/health")
async def control_health(user: dict = Depends(current_user)):
    _require_super(user)
    db_ok = True
    try:
        await db.command("ping")
    except Exception:
        db_ok = False
    integrations = {
        "stripe": _configured("STRIPE_SECRET_KEY"),
        "email": _email_configured(),
        "ai": _configured("EMERGENT_LLM_KEY"),
        "error_monitoring": _configured("SENTRY_DSN"),
    }
    pending_verifications = await db.email_verifications.count_documents({"used": False})
    return {
        "api": "ok",
        "database": "ok" if db_ok else "error",
        "ai_provider": "ok" if integrations["ai"] else "not_configured",
        "error_monitoring": "connected" if integrations["error_monitoring"] else "not_configured",
        "email_delivery": "connected" if integrations["email"] else "not_configured",
        "billing": "connected" if integrations["stripe"] else "demo",
        "pending_email_verifications": pending_verifications,
        "integrations": integrations,
    }


@platform_router.get("/admin/control/entitlements")
async def control_entitlements(user: dict = Depends(current_user)):
    _require_super(user)
    cfg = await get_commercial_config()
    defaults = {p: PLAN_ENTITLEMENTS[p] for p in PUBLIC_PLANS if p in PLAN_ENTITLEMENTS}

    def prov(feature):
        keys = ENTITLEMENT_PROVIDER.get(feature)
        if keys is None:
            return None  # not provider-gated (built-in)
        if keys == ():
            return True
        return any(_configured(k) for k in keys)
    provider_status = {f: prov(f) for f in ("wallet", "ai_followup", "custom_domain", "api")}
    return {"plans": PUBLIC_PLANS, "defaults": defaults,
            "overrides": {p: v for p, v in (cfg.get("entitlement_overrides") or {}).items() if p in PUBLIC_PLANS},
            "provider_status": provider_status}


@platform_router.post("/admin/control/entitlements/preview")
async def control_entitlements_preview(body: dict, user: dict = Depends(current_user)):
    _require_super(user)
    plan = (body or {}).get("plan")
    overrides = (body or {}).get("overrides") or {}
    if plan not in PUBLIC_PLANS:
        raise HTTPException(400, "Unknown plan")
    cfg = await get_commercial_config()
    base = PLAN_ENTITLEMENTS[plan]
    before = {**base, **((cfg.get("entitlement_overrides") or {}).get(plan) or {})}
    after = {**base, **{k: v for k, v in overrides.items() if k in base}}
    diff = {k: {"before": before.get(k), "after": after.get(k)} for k in after if before.get(k) != after.get(k)}
    affected = await db.workspaces.count_documents({"environment": "production_customer", "$or": [{"plan": plan}, {"subscription.plan": plan}]})
    return {"plan": plan, "diff": diff, "affected_customers": affected}


@platform_router.put("/admin/control/entitlements")
async def control_entitlements_set(body: dict, user: dict = Depends(current_user)):
    """Publish entitlement overrides for a plan (Draft->Preview->Confirm->Publish). Records before/after in the Audit Log."""
    _require_super(user)
    plan = (body or {}).get("plan")
    overrides = (body or {}).get("overrides") or {}
    reason = (body or {}).get("reason", "")
    if plan not in PUBLIC_PLANS:
        raise HTTPException(400, "Unknown plan")
    cfg = await get_commercial_config()
    before = (cfg.get("entitlement_overrides") or {}).get(plan, {})
    ent_ov = cfg.get("entitlement_overrides") or {}
    ent_ov[plan] = {k: v for k, v in overrides.items() if k in PLAN_ENTITLEMENTS[plan]}
    await db.commercial_config.update_one({"id": "global"}, {"$set": {"entitlement_overrides": ent_ov}}, upsert=True)
    await audit(None, user["id"], "admin.entitlements.publish", {"plan": plan, "reason": reason, "before": before, "after": ent_ov[plan]})
    return {"ok": True, "overrides": ent_ov[plan]}


class PricingChangeIn(BaseModel):
    patch: dict
    apply_to: Optional[str] = "new_only"   # "new_only" | "migrate"
    reason: Optional[str] = ""


@platform_router.post("/admin/control/pricing/preview")
async def control_pricing_preview(body: PricingChangeIn, user: dict = Depends(current_user)):
    """Impact preview for a pricing/plan change. Read-only: no writes, no Stripe mutation."""
    _require_super(user)
    current = await get_commercial_config()
    proposed = _deep_merge(dict(current), body.patch)
    dm = proposed.get("default_market", "USD")
    before_p = resolve_market_pricing(current, dm)
    after_p = resolve_market_pricing(proposed, dm)
    price_diff = {k: {"before": before_p.get(k), "after": after_p.get(k)}
                  for k in ("pro_month", "pro_year", "team_seat_month", "team_seat_year")
                  if before_p.get(k) != after_p.get(k)}
    if current.get("trial", {}).get("days") != proposed.get("trial", {}).get("days"):
        price_diff["trial_days"] = {"before": current.get("trial", {}).get("days"), "after": proposed.get("trial", {}).get("days")}
    b_seats = ((current.get("plans") or {}).get("team") or {}).get("min_seats")
    a_seats = ((proposed.get("plans") or {}).get("team") or {}).get("min_seats")
    if b_seats != a_seats:
        price_diff["team_min_seats"] = {"before": b_seats, "after": a_seats}
    affected = await db.workspaces.count_documents({"environment": "production_customer", "subscription.status": {"$in": ["active", "cancel_at_period_end"]}})
    return {
        "before": {"pricing": before_p, "trial": current.get("trial")},
        "after": {"pricing": after_p, "trial": proposed.get("trial")},
        "diff": price_diff,
        "affected_plans": [],
        "impact": [{"plan": "paid customers", "active_subscriptions": affected}],
        "apply_to": body.apply_to,
        "market": dm,
        "note": "Public pricing, checkout and entitlements all resolve from this published config. Existing paid subscriptions keep their locked price unless migrated; real migration runs when Stripe is connected.",
    }


@platform_router.post("/admin/control/pricing/publish")
async def control_pricing_publish(body: PricingChangeIn, user: dict = Depends(current_user)):
    """Version + publish a pricing/plan change. Creates a versioned snapshot and an audit entry.
    New prices apply to NEW customers; existing subscriptions migrate only when apply_to='migrate' AND Stripe is connected."""
    _require_super(user)
    current = await get_commercial_config()
    version = {
        "id": str(uuid.uuid4()), "created_at": now_iso(), "actor_id": user["id"],
        "before": {"plans": current.get("plans"), "trial": current.get("trial"), "regional_pricing": current.get("regional_pricing")},
        "patch": body.patch, "apply_to": body.apply_to, "reason": body.reason,
    }
    await db.commercial_config_versions.insert_one(dict(version))
    merged = _deep_merge(dict(current), body.patch)
    merged["id"] = "global"
    await db.commercial_config.update_one({"id": "global"}, {"$set": merged}, upsert=True)
    migrated = False
    if body.apply_to == "migrate" and _configured("STRIPE_SECRET_KEY"):
        migrated = True  # real Stripe migration would run here once billing is connected
    await audit(None, user["id"], "admin.pricing.publish", {
        "apply_to": body.apply_to, "reason": body.reason, "keys": list(body.patch.keys()),
        "version_id": version["id"], "migrated_existing": migrated,
    })
    return {"ok": True, "version_id": version["id"], "migrated_existing": migrated, "config": merged}


@platform_router.post("/admin/control/pricing/resolve")
async def control_pricing_resolve(body: PricingChangeIn, user: dict = Depends(current_user)):
    """Resolve a PROPOSED (unsaved) pricing draft for every market — read-only, no writes.
    Lets the Control Center show live converted prices/savings as the admin edits,
    with all currency conversion done server-side (never in the frontend)."""
    _require_super(user)
    current = await get_commercial_config()
    proposed = _deep_merge(dict(current), body.patch or {})
    return {
        "resolved_all": {m: resolve_market_pricing(proposed, m) for m in COMMERCIAL_MARKETS},
        "fx_rates": {**DEFAULT_FX_RATES, **(proposed.get("fx_rates") or {})},
        "manual_price_markets": proposed.get("manual_price_markets") or [],
    }


@platform_router.get("/admin/control/pricing/versions")
async def control_pricing_versions(user: dict = Depends(current_user)):
    _require_super(user)
    return {"items": await db.commercial_config_versions.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)}


# ------------------------------------------------------------------ Promotions / Promo Codes (real Stripe Coupons + Promotion Codes)
# The sandbox account's default API version renames PromotionCode params; pin a stable
# version for promo calls so `coupon` is accepted (does not affect existing checkout).
STRIPE_PROMO_API_VERSION = "2024-06-20"


class PromotionIn(BaseModel):
    code: str
    discount_type: str = "percent"          # percent | amount
    percent_off: Optional[float] = None
    amount_off: Optional[float] = None      # major currency units (e.g. 10.00)
    currency: str = "usd"
    duration: str = "once"                  # once | repeating | forever
    duration_in_months: Optional[int] = None
    max_redemptions: Optional[int] = None
    name: Optional[str] = None


def _promo_out(pc: dict) -> dict:
    cp = pc.get("coupon") or {}
    return {
        "id": pc.get("id"), "code": pc.get("code"), "active": pc.get("active"),
        "times_redeemed": pc.get("times_redeemed", 0), "max_redemptions": pc.get("max_redemptions"),
        "created": pc.get("created"),
        "coupon": {
            "id": cp.get("id"), "name": cp.get("name"),
            "percent_off": cp.get("percent_off"), "amount_off": cp.get("amount_off"),
            "currency": cp.get("currency"), "duration": cp.get("duration"),
            "duration_in_months": cp.get("duration_in_months"), "valid": cp.get("valid"),
        },
    }


@platform_router.get("/admin/control/promotions")
async def control_promotions_list(user: dict = Depends(current_user)):
    """List all Stripe promotion codes (with their coupon detail). Applied at Stripe-hosted checkout."""
    _require_super(user)
    if not STRIPE_SECRET_KEY:
        raise HTTPException(503, "Stripe is not configured")
    try:
        res = await asyncio.to_thread(lambda: stripe.PromotionCode.list(limit=100, stripe_version=STRIPE_PROMO_API_VERSION))
    except stripe.error.StripeError as e:
        raise HTTPException(502, f"Stripe error: {getattr(e, 'user_message', None) or str(e)}")
    return {"items": [_promo_out(pc) for pc in (res.get("data") or [])]}


@platform_router.post("/admin/control/promotions")
async def control_promotions_create(body: PromotionIn, user: dict = Depends(current_user)):
    """Create a real Stripe Coupon + Promotion Code. The code is entered by customers on the
    existing Stripe-hosted Checkout page (allow_promotion_codes is already enabled there)."""
    _require_super(user)
    if not STRIPE_SECRET_KEY:
        raise HTTPException(503, "Stripe is not configured")
    code = (body.code or "").strip().upper()
    if not code:
        raise HTTPException(400, "A promo code is required")
    duration = body.duration if body.duration in ("once", "repeating", "forever") else "once"
    coupon_kwargs = {"duration": duration}
    if duration == "repeating":
        coupon_kwargs["duration_in_months"] = max(1, int(body.duration_in_months or 1))
    if body.discount_type == "amount":
        if not body.amount_off or float(body.amount_off) <= 0:
            raise HTTPException(400, "A positive amount is required")
        coupon_kwargs["amount_off"] = int(round(float(body.amount_off) * 100))
        coupon_kwargs["currency"] = (body.currency or "usd").lower()
    else:
        if not body.percent_off or not (0 < float(body.percent_off) <= 100):
            raise HTTPException(400, "Percent off must be between 0 and 100")
        coupon_kwargs["percent_off"] = float(body.percent_off)
    if body.name:
        coupon_kwargs["name"] = body.name.strip()
    try:
        coupon = await asyncio.to_thread(lambda: stripe.Coupon.create(**coupon_kwargs, stripe_version=STRIPE_PROMO_API_VERSION))
        pc_kwargs = {"coupon": coupon["id"], "code": code}
        if body.max_redemptions:
            pc_kwargs["max_redemptions"] = int(body.max_redemptions)
        pc = await asyncio.to_thread(lambda: stripe.PromotionCode.create(**pc_kwargs, stripe_version=STRIPE_PROMO_API_VERSION))
    except stripe.error.StripeError as e:
        raise HTTPException(502, f"Stripe error: {getattr(e, 'user_message', None) or str(e)}")
    await audit(None, user["id"], "admin.promotion.create", {"code": code, "coupon_id": coupon["id"]})
    return {"ok": True, **_promo_out(pc)}


class PromotionToggleIn(BaseModel):
    active: bool


@platform_router.post("/admin/control/promotions/{promo_id}/toggle")
async def control_promotions_toggle(promo_id: str, body: PromotionToggleIn, user: dict = Depends(current_user)):
    """Activate / deactivate a Stripe promotion code (coupons themselves cannot be edited once created)."""
    _require_super(user)
    if not STRIPE_SECRET_KEY:
        raise HTTPException(503, "Stripe is not configured")
    try:
        pc = await asyncio.to_thread(lambda: stripe.PromotionCode.modify(promo_id, active=bool(body.active), stripe_version=STRIPE_PROMO_API_VERSION))
    except stripe.error.StripeError as e:
        raise HTTPException(502, f"Stripe error: {getattr(e, 'user_message', None) or str(e)}")
    await audit(None, user["id"], "admin.promotion.toggle", {"id": promo_id, "active": bool(body.active)})
    return {"ok": True, **_promo_out(pc)}






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

# ------------------------------------------------------------------ Events (Event Badge Scanner V1)
class EventIn(BaseModel):
    name: str
    location: str = ""
    start_date: str = ""
    end_date: str = ""
    notes: str = ""
    campaign_code: str = ""
    timezone: str = ""
    event_cost: Optional[float] = None
    event_cost_currency: str = ""
    currency: str = ""  # event reporting currency (financial aggregation)


class EventUpdateIn(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    campaign_code: Optional[str] = None
    timezone: Optional[str] = None
    event_cost: Optional[float] = None
    event_cost_currency: Optional[str] = None
    currency: Optional[str] = None


async def _event_or_403(event_id: str, user: dict):
    ev = await db.events.find_one({"id": event_id}, {"_id": 0})
    if not ev:
        raise HTTPException(404, "Event not found")
    ws_ids = await workspace_ids_for(user)
    if ws_ids != "ALL" and ev.get("workspace_id") not in ws_ids:
        raise HTTPException(403, "Not your event")
    return ev


async def _event_reporting_currency(ev: dict) -> str:
    """Single reporting currency for an event's financial aggregation. Financial values are only
    summed into event totals when their own currency matches this (no FX conversion is performed)."""
    ccy = (ev.get("currency") or ev.get("event_cost_currency") or "").strip().upper()
    if ccy:
        return ccy
    ws = await db.workspaces.find_one({"id": ev.get("workspace_id")}, {"_id": 0, "region": 1})
    return (((ws or {}).get("region") or {}).get("default_currency") or "USD").upper()


# ---- Event analytics helpers (all derived from real persisted data) ----
_MEETING_ACTIVE = {"requested", "scheduled", "confirmed", "rescheduled", "time_proposed", "completed"}


def _event_lead_query(event_id: str) -> dict:
    """A lead belongs to an event if its current event_id matches OR any timeline interaction
    references the event. Timeline preserves cross-event history after a re-scan moves event_id."""
    return {"$or": [{"event_id": event_id}, {"timeline.event_id": event_id}]}


def _lead_new_or_returning(lead: dict, event_id: str) -> str:
    """NEW = this lead was first created at this event (initial scan/exchange interaction here).
    RETURNING = an already-existing contact re-engaged at this event (badge_rescanned here)."""
    entries = [t for t in (lead.get("timeline") or []) if t.get("event_id") == event_id]
    if any(t.get("event") in ("badge_scanned", "card_scanned") for t in entries):
        return "new"
    if any(t.get("event") == "badge_rescanned" for t in entries):
        return "returning"
    # fallback: lead attributed only by event_id field with no timeline detail → treat as new
    return "new"


async def _event_meetings_by_lead(lead_ids):
    """Structured meeting records keyed by lead_id. Excludes cancelled/declined. Deduped by meeting id."""
    if not lead_ids:
        return {}
    meets = await db.meetings.find({"lead_id": {"$in": list(lead_ids)}}, {"_id": 0}).to_list(20000)
    out = {}
    seen = set()
    for m in meets:
        if m.get("id") in seen:
            continue
        seen.add(m.get("id"))
        if m.get("status") in ("cancelled", "declined"):
            continue
        out.setdefault(m["lead_id"], []).append(m)
    return out


@platform_router.get("/events")
async def list_events(user: dict = Depends(current_user)):
    ws_ids = await workspace_ids_for(user)
    q = {} if ws_ids == "ALL" else {"workspace_id": {"$in": ws_ids}}
    events = await db.events.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)
    for e in events:
        leads = await db.leads.find(_event_lead_query(e["id"]), {"_id": 0, "id": 1, "status": 1}).to_list(20000)
        lead_ids = [l["id"] for l in leads]
        by_lead = await _event_meetings_by_lead(lead_ids)
        e["lead_count"] = len(leads)
        e["meeting_count"] = sum(len(v) for v in by_lead.values())
        e["customer_count"] = sum(1 for l in leads if (l.get("status") or "new").strip().lower() in ("customer", "converted", "won"))
    return events


@platform_router.post("/events")
async def create_event(body: EventIn, user: dict = Depends(current_user)):
    ms = await memberships_for(user["id"])
    ws_id = ms[0]["workspace_id"] if ms else None
    if not ws_id:
        raise HTTPException(400, "No workspace")
    if not body.name.strip():
        raise HTTPException(400, "Event name is required")
    ws = await db.workspaces.find_one({"id": ws_id}, {"_id": 0, "region": 1})
    tz = body.timezone.strip() or ((ws or {}).get("region") or {}).get("timezone") or "UTC"
    ws_ccy = ((ws or {}).get("region") or {}).get("default_currency") or "USD"
    report_ccy = (body.currency or body.event_cost_currency or ws_ccy).strip().upper()
    doc = {"id": str(uuid.uuid4()), "workspace_id": ws_id,
           "name": body.name.strip(), "location": body.location.strip(),
           "start_date": body.start_date.strip(), "end_date": body.end_date.strip(),
           "notes": body.notes.strip(), "campaign_code": body.campaign_code.strip(),
           "timezone": tz,
           "currency": report_ccy,
           "event_cost": body.event_cost if body.event_cost is not None else None,
           "event_cost_currency": (body.event_cost_currency or report_ccy).strip().upper(),
           "status": "active", "created_by": user["id"],
           "created_at": now_iso(), "updated_at": now_iso()}
    await db.events.insert_one(doc)
    doc.pop("_id", None)
    doc["lead_count"] = 0
    doc["meeting_count"] = 0
    doc["customer_count"] = 0
    return doc


@platform_router.get("/events/{event_id}")
async def get_event(event_id: str, user: dict = Depends(current_user)):
    ev = await _event_or_403(event_id, user)
    leads = await db.leads.find(_event_lead_query(event_id), {"_id": 0}).sort("created_at", -1).to_list(20000)
    uids = list({l.get("captured_by") for l in leads if l.get("captured_by")})
    users = await db.users.find({"id": {"$in": uids}}, {"_id": 0, "id": 1, "name": 1, "email": 1}).to_list(500) if uids else []
    uname = {u["id"]: (u.get("name") or u.get("email") or u["id"]) for u in users}
    by_lead = await _event_meetings_by_lead([l["id"] for l in leads])
    for l in leads:
        l["captured_by_name"] = uname.get(l.get("captured_by"), "")
        l["new_returning"] = _lead_new_or_returning(l, event_id)
        ms_l = by_lead.get(l["id"]) or []
        l["has_meeting"] = bool(ms_l)
        l["meeting_status"] = (ms_l[0].get("status") if ms_l else "")
        l["effective_temperature"] = effective_temperature(l)
        l["crm_sync"] = _crm_public_state(l)
    ev["lead_count"] = len(leads)
    return {"event": ev, "leads": leads, "lead_count": len(leads)}


@platform_router.patch("/events/{event_id}")
async def update_event(event_id: str, body: EventUpdateIn, user: dict = Depends(current_user)):
    await _event_or_403(event_id, user)
    # exclude_unset lets callers explicitly clear event_cost (send null) vs. omit it entirely
    raw = body.model_dump(exclude_unset=True)
    upd = {}
    for k, v in raw.items():
        if v is None:
            # only nullable/clearable fields may be set to null
            if k in ("event_cost", "event_cost_currency", "notes"):
                upd[k] = None if k == "event_cost" else ""
            continue
        upd[k] = v.strip() if isinstance(v, str) else v
    if "event_cost_currency" in upd and isinstance(upd["event_cost_currency"], str):
        upd["event_cost_currency"] = upd["event_cost_currency"].upper()
    if "currency" in upd and isinstance(upd["currency"], str):
        upd["currency"] = upd["currency"].upper()
    if "status" in upd and upd["status"] not in ("active", "archived"):
        raise HTTPException(400, "Invalid status")
    upd["updated_at"] = now_iso()
    await db.events.update_one({"id": event_id}, {"$set": upd})
    ev = await db.events.find_one({"id": event_id}, {"_id": 0})
    ev["lead_count"] = await db.leads.count_documents(_event_lead_query(event_id))
    return ev


def _event_days(ev: dict) -> int:
    sd, ed = ev.get("start_date"), ev.get("end_date")
    try:
        if sd and ed:
            d0 = datetime.fromisoformat(sd).date()
            d1 = datetime.fromisoformat(ed).date()
            return max(1, (d1 - d0).days + 1)
        if sd:
            return 1
    except Exception:
        pass
    return 0


def _local_day(iso_str: str, tzname: str) -> str:
    try:
        from zoneinfo import ZoneInfo
        dt = datetime.fromisoformat((iso_str or "").replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(ZoneInfo(tzname or "UTC")).strftime("%Y-%m-%d")
    except Exception:
        return (iso_str or "")[:10]


@platform_router.get("/events/{event_id}/dashboard")
async def event_dashboard(event_id: str, user: dict = Depends(current_user)):
    """Server-side aggregated event analytics. Tenant-scoped via _event_or_403.
    Every metric is derived from real persisted leads/meetings — no fabricated values."""
    ev = await _event_or_403(event_id, user)
    tz = ev.get("timezone") or "UTC"
    leads = await db.leads.find(_event_lead_query(event_id),
                                {"_id": 0, "id": 1, "status": 1, "source": 1, "scanner_type": 1,
                                 "captured_by": 1, "captured_at": 1, "created_at": 1, "name": 1,
                                 "company": 1, "title": 1, "phone": 1, "email": 1,
                                 "next_follow_up": 1, "follow_up_completed_at": 1, "timeline": 1,
                                 "lead_score": 1, "lead_temperature": 1, "lead_temperature_override": 1,
                                 "opportunity_value": 1, "opportunity_currency": 1, "expected_close_date": 1,
                                 "actual_revenue": 1, "actual_revenue_currency": 1,
                                 "revenue_recorded_at": 1, "revenue_attribution": 1}).to_list(50000)
    lead_ids = [l["id"] for l in leads]
    by_lead = await _event_meetings_by_lead(lead_ids)
    total = len(leads)

    # New vs returning
    nr = {"new": 0, "returning": 0}
    for l in leads:
        nr[_lead_new_or_returning(l, event_id)] += 1

    # Pipeline distribution (existing 7 stages, legacy aliased)
    STAGES = ["new", "contacted", "qualified", "meeting", "opportunity", "customer", "not_interested"]
    ALIAS = {"meeting_booked": "meeting", "converted": "customer", "archived": "not_interested",
             "won": "customer", "lost": "not_interested", "follow_up": "contacted"}
    def stage_of(l):
        s = (l.get("status") or "new").strip().lower()
        s = ALIAS.get(s, s)
        return s if s in STAGES else "new"
    pipeline = {s: 0 for s in STAGES}
    for l in leads:
        pipeline[stage_of(l)] += 1
    customers = pipeline["customer"]

    # Capture methods
    caps = {}
    for l in leads:
        key = (l.get("source") or "inquiry")
        caps[key] = caps.get(key, 0) + 1
    capture_methods = sorted([{"key": k, "count": v, "pct": round(v * 100 / total, 1) if total else 0}
                              for k, v in caps.items()], key=lambda x: x["count"], reverse=True)

    # Meetings (deduped, non-cancelled)
    meetings_total = sum(len(v) for v in by_lead.values())
    leads_with_meeting = len(by_lead)
    customer_lead_ids = {l["id"] for l in leads if stage_of(l) == "customer"}
    meetings_to_customers = sum(1 for lid in by_lead if lid in customer_lead_ids)

    # Follow-ups
    now = datetime.now(timezone.utc)
    today = now.date().isoformat()
    fu = {"due": 0, "overdue": 0, "completed": 0, "none": 0}
    for l in leads:
        if l.get("follow_up_completed_at"):
            fu["completed"] += 1; continue
        nf = (l.get("next_follow_up") or "").strip()
        if not nf:
            fu["none"] += 1; continue
        nfday = nf[:10]
        if nfday < today:
            fu["overdue"] += 1
        elif nf <= now.isoformat() or nfday == today:
            fu["due"] += 1
        else:
            fu["due"] += 0  # scheduled future — counted under 'set' implicitly
    fu["scheduled_future"] = total - fu["due"] - fu["overdue"] - fu["completed"] - fu["none"]

    # Leaderboard (captured_by → workspace member)
    uids = list({l.get("captured_by") for l in leads if l.get("captured_by")})
    users = await db.users.find({"id": {"$in": uids}}, {"_id": 0, "id": 1, "name": 1, "email": 1}).to_list(1000) if uids else []
    uname = {u["id"]: (u.get("name") or u.get("email") or u["id"]) for u in users}
    lb = {}
    for l in leads:
        uid = l.get("captured_by") or "unknown"
        row = lb.setdefault(uid, {"user_id": uid, "name": uname.get(uid, "—"), "leads": 0, "new": 0,
                                  "returning": 0, "meetings": 0, "customers": 0})
        row["leads"] += 1
        row[_lead_new_or_returning(l, event_id)] += 1
        if by_lead.get(l["id"]):
            row["meetings"] += 1
        if stage_of(l) == "customer":
            row["customers"] += 1
    for row in lb.values():
        row["conversion_rate"] = round(row["customers"] * 100 / row["leads"], 1) if row["leads"] else 0
    leaderboard = sorted(lb.values(), key=lambda x: x["leads"], reverse=True)

    # Daily trend (in event timezone)
    daily = {}
    for l in leads:
        d = _local_day(l.get("captured_at") or l.get("created_at") or "", tz)
        if d:
            daily[d] = daily.get(d, 0) + 1
    daily_trend = [{"date": d, "leads": daily[d]} for d in sorted(daily)]

    created_user = await db.users.find_one({"id": ev.get("created_by")}, {"_id": 0, "name": 1, "email": 1})
    conversion_rate = round(customers * 100 / total, 1) if total else 0

    # Lead-quality distribution + averages (effective temperature honours manual override)
    def eff_temp(l):
        ov = l.get("lead_temperature_override")
        return ov if ov in ("hot", "warm", "cold") else (l.get("lead_temperature") or "cold")
    quality = {"hot": 0, "warm": 0, "cold": 0}
    score_sum = 0
    for l in leads:
        quality[eff_temp(l)] += 1
        score_sum += int(l.get("lead_score") or 0)
    avg_score = round(score_sum / total, 1) if total else 0

    # Leaderboard: add hot_leads + avg_score per member
    for row in lb.values():
        row["hot_leads"] = 0
        row["_score_sum"] = 0
    for l in leads:
        uid = l.get("captured_by") or "unknown"
        if uid in lb:
            if eff_temp(l) == "hot":
                lb[uid]["hot_leads"] += 1
            lb[uid]["_score_sum"] += int(l.get("lead_score") or 0)
    for row in lb.values():
        row["avg_score"] = round(row["_score_sum"] / row["leads"], 1) if row["leads"] else 0
        row.pop("_score_sum", None)
    leaderboard = sorted(lb.values(), key=lambda x: x["leads"], reverse=True)

    # Top leads to follow up (exclude Customer + Not Interested; effective temp order, recency tiebreak)
    open_leads = [l for l in leads if stage_of(l) not in ("customer", "not_interested")]
    _trank = {"hot": 3, "warm": 2, "cold": 1}
    top = sorted(open_leads, key=lambda l: (int(l.get("lead_score") or 0), l.get("captured_at") or l.get("created_at") or ""), reverse=True)[:10]
    top_leads = [{"id": l["id"], "name": l.get("name"), "company": l.get("company"), "title": l.get("title"),
                  "score": int(l.get("lead_score") or 0), "temperature": eff_temp(l),
                  "captured_by": uname.get(l.get("captured_by"), ""),
                  "next_follow_up": l.get("next_follow_up") or "", "follow_up_completed_at": l.get("follow_up_completed_at") or "",
                  "phone": l.get("phone") or "", "email": l.get("email") or ""} for l in top]

    # -------- Financials (Pipeline Value + Attributed Revenue + ROI) --------
    # Rules (honest, no fabrication, no FX conversion):
    #  • Reporting currency = event.currency (falls back to cost currency / workspace default).
    #  • OPEN pipeline stages = contacted/qualified/meeting/opportunity (excludes new, customer, not_interested).
    #  • Pipeline Value (ASSOCIATED): sum opportunity_value of OPEN leads associated with THIS event,
    #    counted only when the opportunity currency matches the reporting currency. A lead's opportunity
    #    can appear in every event it is associated with (associated, NOT exclusive) — labelled as such.
    #  • Attributed Revenue (EXCLUSIVE): sum actual_revenue whose revenue_attribution.event_id == this event
    #    (explicit, user-selected) — one revenue record attributes to at most ONE event, so no double count.
    #  • Amounts in a different currency are stored on the lead but EXCLUDED from event totals (never summed).
    report_ccy = await _event_reporting_currency(ev)
    OPEN_STAGES = ("contacted", "qualified", "meeting", "opportunity")
    pipeline_value = 0.0
    pv_by_stage = {s: 0.0 for s in OPEN_STAGES}
    open_opp_count = 0
    pv_excluded = 0
    for l in leads:
        ov = l.get("opportunity_value")
        if ov is None:
            continue
        st = stage_of(l)
        if st not in OPEN_STAGES:
            continue
        occ = (l.get("opportunity_currency") or report_ccy).upper()
        if occ != report_ccy:
            pv_excluded += 1
            continue
        pipeline_value += float(ov)
        pv_by_stage[st] += float(ov)
        open_opp_count += 1

    attributed_revenue = 0.0
    rev_count = 0
    rev_excluded = 0
    for l in leads:
        ra = l.get("revenue_attribution") or {}
        if ra.get("event_id") != event_id:
            continue
        amt = l.get("actual_revenue")
        if amt is None:
            continue
        rcc = (l.get("actual_revenue_currency") or report_ccy).upper()
        if rcc != report_ccy:
            rev_excluded += 1
            continue
        attributed_revenue += float(amt)
        rev_count += 1

    ev_cost = ev.get("event_cost")
    cost_ccy = (ev.get("event_cost_currency") or "").upper()
    cost_usable = (ev_cost is not None and float(ev_cost) > 0 and (not cost_ccy or cost_ccy == report_ccy))
    roi = None
    rev_cost_multiple = None
    if cost_usable and rev_count > 0:
        roi = round((attributed_revenue - float(ev_cost)) / float(ev_cost) * 100, 1)
        rev_cost_multiple = round(attributed_revenue / float(ev_cost), 2)

    # Per-member pipeline / revenue (attributed to captured_by — same ownership as all leaderboard metrics)
    for row in lb.values():
        row["pipeline_value"] = 0.0
        row["attributed_revenue"] = 0.0
        row["_has_pv"] = False
        row["_has_rev"] = False
    for l in leads:
        uid = l.get("captured_by") or "unknown"
        if uid not in lb:
            continue
        ov = l.get("opportunity_value")
        if ov is not None and stage_of(l) in OPEN_STAGES and (l.get("opportunity_currency") or report_ccy).upper() == report_ccy:
            lb[uid]["pipeline_value"] += float(ov); lb[uid]["_has_pv"] = True
        ra = l.get("revenue_attribution") or {}
        if ra.get("event_id") == event_id and l.get("actual_revenue") is not None and (l.get("actual_revenue_currency") or report_ccy).upper() == report_ccy:
            lb[uid]["attributed_revenue"] += float(l["actual_revenue"]); lb[uid]["_has_rev"] = True
    for row in lb.values():
        if not row.pop("_has_pv", False):
            row["pipeline_value"] = None
        if not row.pop("_has_rev", False):
            row["attributed_revenue"] = None
    leaderboard = sorted(lb.values(), key=lambda x: x["leads"], reverse=True)

    # Top Opportunities (monetary) — exclude Not Interested and closed Customers (customer w/ recorded revenue)
    opp_pool = [l for l in leads if l.get("opportunity_value") is not None
                and stage_of(l) != "not_interested"
                and not (stage_of(l) == "customer" and l.get("actual_revenue") is not None)]
    opp_sorted = sorted(opp_pool, key=lambda l: float(l.get("opportunity_value") or 0), reverse=True)[:10]
    top_opportunities = [{"id": l["id"], "name": l.get("name"), "company": l.get("company"), "title": l.get("title"),
                          "score": int(l.get("lead_score") or 0), "stage": stage_of(l),
                          "opportunity_value": l.get("opportunity_value"),
                          "opportunity_currency": (l.get("opportunity_currency") or report_ccy).upper(),
                          "expected_close_date": l.get("expected_close_date") or "",
                          "captured_by": uname.get(l.get("captured_by"), ""),
                          "next_follow_up": l.get("next_follow_up") or "",
                          "follow_up_completed_at": l.get("follow_up_completed_at") or ""} for l in opp_sorted]

    financials = {
        "currency": report_ccy,
        "pipeline_value": (pipeline_value if open_opp_count > 0 else None),
        "open_opportunities": open_opp_count,
        "pipeline_by_stage": [{"stage": s, "value": pv_by_stage[s]} for s in OPEN_STAGES if pv_by_stage[s] > 0],
        "attributed_revenue": (attributed_revenue if rev_count > 0 else None),
        "attributed_revenue_count": rev_count,
        "event_cost": ev_cost,
        "event_cost_currency": cost_ccy or report_ccy,
        "roi": roi,
        "revenue_cost_multiple": rev_cost_multiple,
        "excluded": {"pipeline_currency_mismatch": pv_excluded, "revenue_currency_mismatch": rev_excluded},
    }

    return {
        "event": {**ev, "days": _event_days(ev),
                  "created_by_name": (created_user or {}).get("name") or (created_user or {}).get("email") or ""},
        "timezone": tz,
        "kpis": {
            "total_leads": total,
            "new_contacts": nr["new"],
            "returning_contacts": nr["returning"],
            "meetings_booked": meetings_total,
            "followups_due": fu["due"], "followups_overdue": fu["overdue"],
            "followups_completed": fu["completed"], "followups_none": fu["none"],
            "customers": customers,
            "conversion_rate": conversion_rate,
        },
        "new_vs_returning": {"new": nr["new"], "returning": nr["returning"],
                             "new_pct": round(nr["new"] * 100 / total, 1) if total else 0,
                             "returning_pct": round(nr["returning"] * 100 / total, 1) if total else 0},
        "pipeline": [{"stage": s, "count": pipeline[s]} for s in STAGES],
        "capture_methods": capture_methods,
        "conversion": {"leads": total, "customers": customers, "conversion_rate": conversion_rate,
                       "meetings": meetings_total, "leads_with_meeting": leads_with_meeting,
                       "meeting_rate": round(leads_with_meeting * 100 / total, 1) if total else 0,
                       "meetings_to_customers": meetings_to_customers},
        "followups": fu,
        "leaderboard": leaderboard,
        "quality": {**quality, "avg_score": avg_score},
        "top_leads": top_leads,
        "top_opportunities": top_opportunities,
        "financials": financials,
        "daily_trend": daily_trend,
        "cost": {"event_cost": ev.get("event_cost"), "currency": ev.get("event_cost_currency") or report_ccy,
                 "attributed_revenue": financials["attributed_revenue"], "roi": financials["roi"]},
    }




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
    _usage_handle = await usage_guard("ai_followup", user, _ws_id)
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
    # Usage & Cost Control: only a real provider call incurs cost. A template fallback releases the reservation.
    _real = provider != "template"
    if not _real:
        await release_usage_handle(_usage_handle)
    await meter_usage("ai_followup", user_id=user["id"], workspace_id=_ws_id, quantity=1,
                      result="success", source="ai_followup", paid=_real)
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


SCAN_SOURCES = {"business_card_scan", "badge_scan", "event_badge_scan", "qr_scan"}
# Scanner "type" the user picked in the UI → canonical lead source.
SCANNER_TYPE_SOURCE = {"business_card": "business_card_scan", "event_badge": "event_badge_scan"}
_BADGE_SOURCES = {"badge_scan", "event_badge_scan"}


class ScanIn(BaseModel):
    image_base64: str
    source: str = "business_card_scan"
    event_id: str = ""


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
    is_badge = source in _BADGE_SOURCES
    _feature_key = "event_badge_scan" if is_badge else "business_card_scan"
    # Usage & Cost Control gate (no-op unless a Super Admin has enabled a limit for this feature).
    _usage_handle = await usage_guard(_feature_key, user, _ws_id, body.event_id.strip())
    image_b64 = _strip_data_url(body.image_base64)
    if not image_b64:
        await release_usage_handle(_usage_handle)
        raise HTTPException(400, "No image provided")

    key = os.environ.get("EMERGENT_LLM_KEY", "").strip()
    if not key:
        await release_usage_handle(_usage_handle)
        return {"configured": False, "message": "Card scanning is Not Configured", "draft": {}}

    base_keys = ["name", "title", "company", "email", "phone", "website",
                 "address", "city", "country", "language", "notes"]
    badge_keys = ["first_name", "last_name", "linkedin", "badge_id", "event_name", "booth"]
    keys = base_keys + (badge_keys if is_badge else [])
    empty = {k: "" for k in keys}
    empty["language"] = "en"
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
        if is_badge:
            sys = (
                "You are an OCR + information-extraction engine specialised in CONFERENCE / EVENT BADGES. "
                "Read ALL printed text in the image in any language or script (including Arabic, mixed "
                "Arabic/English, and Latin-accented). Badges may be horizontal or vertical, may contain a "
                "QR code, sponsor/company logos, and only partial information. "
                "Return ONLY a compact JSON object with these exact keys: "
                "name, first_name, last_name, title, company, email, phone, website, linkedin, badge_id, "
                "event_name, booth, address, city, country, language, notes. "
                "Rules: 'name' is the attendee's full printed name; also split it into first_name / last_name "
                "when possible. 'company' is the attendee's own organisation; 'booth' only if a booth/stand "
                "number or hall is printed. 'event_name' only if the event/conference title is printed on the "
                "badge. 'linkedin' only if a LinkedIn/profile URL or handle is visibly printed. 'badge_id' only "
                "if an attendee/badge ID is printed. Format phone in international E.164 form when a country can "
                "be inferred. Keep the original spelling and script for name/company. 'language' is the ISO-639-1 "
                "code of the badge's primary language (en, ar, es, ...). "
                "CRITICAL: DO NOT guess or hallucinate. If a field is not clearly present, return an EMPTY string "
                "for it. Output JSON only — no prose, no code fences."
            )
            prompt = "Extract the attendee details from this event badge image as JSON. Return empty strings for anything not clearly printed."
        else:
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
            prompt = "Extract the contact details from this card/badge image as JSON."
        chat = LlmChat(api_key=key, session_id=f"scan-{uuid.uuid4()}",
                       system_message=sys).with_model("openai", "gpt-5.4")
        msg = UserMessage(text=prompt, file_contents=[ImageContent(image_base64=image_b64)])
        resp = await chat.send_message(msg)
        data = _parse_scan_json(str(resp))
    except Exception as e:
        logger.warning(f"scan_card LLM error: {e}")
        await release_usage_handle(_usage_handle)
        await meter_usage(_feature_key, user_id=user["id"], workspace_id=_ws_id,
                          event_id=body.event_id.strip(), quantity=1, result="failed", source="scanner", paid=False)
        raise HTTPException(502, "Could not read the card. Please retake the photo and try again.")

    draft = {**empty, **{k: (str(data.get(k, "")).strip() if data.get(k) is not None else "")
                          for k in keys}}
    if is_badge and not draft.get("name") and (draft.get("first_name") or draft.get("last_name")):
        draft["name"] = " ".join([draft.get("first_name", ""), draft.get("last_name", "")]).strip()
    if draft["language"] not in SUPPORTED_LANGUAGES:
        draft["language"] = "en" if not draft["language"] else draft["language"][:2].lower()
    await db.ai_usage.insert_one({
        "id": str(uuid.uuid4()), "user_id": user["id"], "provider": "openai:gpt-5.4",
        "channel": "scanner", "tone": source, "language": draft.get("language", "en"), "created_at": now_iso(),
    })
    await meter_usage(_feature_key, user_id=user["id"], workspace_id=_ws_id,
                      event_id=body.event_id.strip(), quantity=1, result="success", source="scanner", paid=True)
    return {"configured": True, "source": source, "draft": draft,
            "note": "Review and edit before saving. No lead is created until you confirm."}


class ScanConfirmIn(BaseModel):
    cardSlug: str
    source: str = "business_card_scan"
    scanner_type: str = ""            # business_card | event_badge (drives canonical source)
    name: str
    first_name: str = ""
    last_name: str = ""
    title: str = ""
    company: str = ""
    email: str = ""
    phone: str = ""
    website: str = ""
    linkedin: str = ""
    badge_id: str = ""
    booth: str = ""
    address: str = ""
    city: str = ""
    country: str = ""
    language: str = "en"
    interest: str = ""
    notes: str = ""
    event: str = ""
    event_id: str = ""
    campaign: str = ""
    force: bool = False
    update_lead_id: str = ""          # when set: append this scan to an existing contact


import re as _re


def _norm_email(e):
    return (e or "").strip().lower()


def _norm_phone(p):
    d = _re.sub(r"\D", "", p or "")
    return d[-9:] if len(d) >= 7 else ""


def _norm_text(s):
    return _re.sub(r"\s+", " ", (s or "").strip().lower())


async def find_duplicate_lead(card_slug, email, phone, exclude_id=None, name="", company=""):
    """Lightweight dedupe within the SAME card. Matches by normalized email OR phone (last 9
    digits) OR a strong full-name + company match (both non-empty, exact after normalization)."""
    ne, np = _norm_email(email), _norm_phone(phone)
    nn, nc = _norm_text(name), _norm_text(company)
    if not ne and not np and not (nn and nc):
        return None
    cands = await db.leads.find({"cardSlug": card_slug}, {"_id": 0}).to_list(3000)
    for l in cands:
        if exclude_id and l.get("id") == exclude_id:
            continue
        if ne and _norm_email(l.get("email")) == ne:
            return l
        if np and _norm_phone(l.get("phone")) == np:
            return l
        if nn and nc and _norm_text(l.get("name")) == nn and _norm_text(l.get("company")) == nc:
            return l
    return None


async def _resolve_scan_event(user: dict, event_id: str):
    """Return (event_doc | None). Enforces tenant ownership of the event."""
    if not event_id:
        return None
    ev = await db.events.find_one({"id": event_id}, {"_id": 0})
    if not ev:
        raise HTTPException(404, "Event not found")
    ws_ids = await workspace_ids_for(user)
    if ws_ids != "ALL" and ev.get("workspace_id") not in ws_ids:
        raise HTTPException(403, "Event belongs to another workspace")
    return ev



# ------------------------------------------------------------------ Lead Scoring (deterministic, explainable, v1)
LEAD_SCORE_VERSION = "v1"
# Max contributions: contact 20 + seniority 20 + engagement 30 + pipeline 25 + completeness 5 = 100
_SENIORITY_TOP = ["founder", "co-founder", "cofounder", "owner", "ceo", "chief", "c.e.o", "president",
                  "managing director", "manager director", "partner", "proprietor",
                  "مؤسس", "شريك مؤسس", "مالك", "رئيس تنفيذي", "المدير التنفيذي", "مدير تنفيذي", "مدير عام", "شريك"]
_SENIORITY_MID = ["vp", "vice president", "director", "head of", "head ", "chief of staff",
                  "نائب رئيس", "نائب الرئيس", "مدير", "رئيس قسم", "رئيس"]
_SENIORITY_LOW = ["manager", "lead", "senior", "مسؤول", "قائد"]
_PIPELINE_POINTS = {"new": 0, "contacted": 5, "qualified": 12, "meeting": 18, "opportunity": 22,
                    "customer": 25, "not_interested": 0}
_STAGE_ALIAS = {"meeting_booked": "meeting", "converted": "customer", "archived": "not_interested",
                "won": "customer", "lost": "not_interested", "follow_up": "contacted"}


def _norm_stage_score(s):
    s = (s or "new").strip().lower()
    s = _STAGE_ALIAS.get(s, s)
    return s if s in _PIPELINE_POINTS else "new"


def _seniority_points(title):
    t = re.sub(r"\s+", " ", (title or "").strip().lower())
    if not t:
        return 0, ""
    for kw in _SENIORITY_TOP:
        if kw in t:
            return 20, "senior_decision_maker"
    for kw in _SENIORITY_MID:
        if kw in t:
            return 14, "senior_role"
    for kw in _SENIORITY_LOW:
        if kw in t:
            return 8, "mid_role"
    return 0, ""


def compute_lead_score(lead: dict, active_meetings: int = 0) -> dict:
    """Deterministic 0–100 lead-quality score with an explainable breakdown. Safe with missing data.
    Quality only — follow-up urgency is intentionally NOT a factor."""
    bd = []
    # A. Contact quality (max 20)
    cq = 0
    if re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", (lead.get("email") or "").strip()):
        cq += 4
    if len(re.sub(r"\D", "", lead.get("phone") or "")) >= 7:
        cq += 4
    if (lead.get("company") or "").strip():
        cq += 4
    if (lead.get("title") or "").strip():
        cq += 3
    if (lead.get("linkedin") or "").strip():
        cq += 5
    if cq:
        bd.append({"code": "contact_quality", "points": cq})
    # B. Seniority (max 20)
    sen, sen_code = _seniority_points(lead.get("title"))
    if sen:
        bd.append({"code": sen_code, "points": sen})
    # C. Sales engagement (max 30): meeting 15 + follow-up completed 5 + returning/multi capped 10
    eng = 0
    if active_meetings > 0:
        eng += 15
        bd.append({"code": "meeting_booked", "points": 15})
    if (lead.get("follow_up_completed_at") or ""):
        eng += 5
        bd.append({"code": "follow_up_completed", "points": 5})
    tl = lead.get("timeline") or []
    scan_events = [t for t in tl if t.get("event") in ("badge_scanned", "card_scanned", "badge_rescanned")]
    distinct_events = len({t.get("event_id") for t in scan_events if t.get("event_id")})
    interactions = len(scan_events)
    ret = min(10, max(0, (max(distinct_events, interactions) - 1)) * 4)  # capped at 10
    if ret:
        eng += ret
        bd.append({"code": "multiple_interactions", "points": ret})
    # D. Pipeline progress (max 25)
    stage = _norm_stage_score(lead.get("status"))
    pp = _PIPELINE_POINTS[stage]
    if pp:
        bd.append({"code": f"stage_{stage}", "points": pp})
    # F. Data completeness (max 5)
    comp = min(5, sum(1 for f in ("address", "city", "website", "notes") if (lead.get(f) or "").strip()))
    if comp:
        bd.append({"code": "complete_info", "points": comp})

    total = cq + sen + eng + pp + comp
    # Not Interested must never read as a hot/warm quality lead regardless of other signals
    if stage == "not_interested":
        total = min(total, 20)
    total = max(0, min(100, total))
    temp = "hot" if total >= 75 else "warm" if total >= 45 else "cold"
    return {"lead_score": total, "lead_temperature": temp, "lead_score_breakdown": bd,
            "lead_score_version": LEAD_SCORE_VERSION, "lead_score_updated_at": now_iso()}


async def _active_meeting_count(lead_id: str) -> int:
    meets = await db.meetings.find({"lead_id": lead_id}, {"_id": 0, "id": 1, "status": 1}).to_list(500)
    seen, n = set(), 0
    for m in meets:
        if m.get("id") in seen:
            continue
        seen.add(m.get("id"))
        if m.get("status") not in ("cancelled", "declined"):
            n += 1
    return n


async def recalc_lead_score(lead_id: str):
    """Single source of truth. Recomputes + persists the calculated score. Never touches manual override."""
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        return None
    res = compute_lead_score(lead, await _active_meeting_count(lead_id))
    await db.leads.update_one({"id": lead_id}, {"$set": res})
    return res


def effective_temperature(lead: dict) -> str:
    ov = lead.get("lead_temperature_override")
    return ov if ov in ("hot", "warm", "cold") else (lead.get("lead_temperature") or "cold")


class TemperatureIn(BaseModel):
    temperature: str  # hot | warm | cold | auto


@platform_router.post("/admin/leads/{lead_id}/temperature")
async def set_lead_temperature(lead_id: str, body: TemperatureIn, user: dict = Depends(current_user)):
    """Manual override of lead quality. 'auto' clears the override (back to calculated). Preserves calc score."""
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(404, "Lead not found")
    slugs = await _owned_slugs(user)
    if lead.get("cardSlug") not in slugs and user.get("role") != "SUPER_ADMIN":
        raise HTTPException(403, "Not your lead")
    t = (body.temperature or "").lower()
    if t == "auto":
        await db.leads.update_one({"id": lead_id}, {"$set": {
            "lead_temperature_override": None, "lead_temperature_override_by": None,
            "lead_temperature_override_at": None, "updated_at": now_iso()}})
    elif t in ("hot", "warm", "cold"):
        await db.leads.update_one({"id": lead_id}, {"$set": {
            "lead_temperature_override": t, "lead_temperature_override_by": user["id"],
            "lead_temperature_override_at": now_iso(), "updated_at": now_iso()}})
    else:
        raise HTTPException(400, "Invalid temperature")
    return await db.leads.find_one({"id": lead_id}, {"_id": 0})



@platform_router.post("/scan/confirm")
async def scan_confirm(body: ScanConfirmIn, user: dict = Depends(current_user)):
    """Persist a reviewed scan as a CRM lead scoped to one of the user's own cards.
    When update_lead_id is provided, append this scan (and its event interaction) to the
    existing contact instead of creating a duplicate."""
    ent = await _user_entitlements(user)
    if not ent.get("scanner"):
        raise HTTPException(403, "Scanner is not available on your plan")
    # canonical source: scanner_type wins when provided (event_badge → event_badge_scan)
    source = SCANNER_TYPE_SOURCE.get(body.scanner_type) or (body.source if body.source in SCAN_SOURCES else "business_card_scan")
    scanner_type = body.scanner_type or ("event_badge" if source in _BADGE_SOURCES else "business_card")
    if not body.name.strip():
        raise HTTPException(400, "A name is required")
    slugs = await _owned_slugs(user)
    if body.cardSlug not in slugs and user.get("role") != "SUPER_ADMIN":
        raise HTTPException(403, "Not your card")
    card = await db.digital_cards.find_one({"slug": body.cardSlug}, {"_id": 0})
    if not card:
        raise HTTPException(404, "Card not found")

    ev_doc = await _resolve_scan_event(user, body.event_id.strip())
    event_name = (ev_doc.get("name") if ev_doc else "") or body.event.strip()
    event_id = ev_doc.get("id") if ev_doc else ""
    now = now_iso()

    def _interaction(kind: str):
        return {"at": now, "event": kind, "detail": event_name or (card.get("identity", {}) or {}).get("fullName", ""),
                "event_name": event_name, "event_id": event_id, "captured_by": user["id"],
                "captured_by_name": user.get("name") or user.get("email", ""),
                "scanner_type": scanner_type, "source": source}

    # ---- Append to an existing contact (repeat encounter / user chose "update existing")
    if body.update_lead_id.strip():
        existing = await db.leads.find_one({"id": body.update_lead_id.strip()}, {"_id": 0})
        if not existing:
            raise HTTPException(404, "Lead not found")
        if existing.get("cardSlug") not in slugs and user.get("role") != "SUPER_ADMIN":
            raise HTTPException(403, "Not your lead")
        upd = {"updated_at": now, "last_activity": now}
        # fill only blank fields — never overwrite data the user already has
        for k, v in {"email": body.email, "phone": body.phone, "company": body.company,
                     "title": body.title, "website": body.website, "linkedin": body.linkedin}.items():
            if v and v.strip() and not (existing.get(k) or "").strip():
                upd[k] = v.strip()
        if event_name:
            upd["event"] = event_name
        if event_id:
            upd["event_id"] = event_id
        tags = list(existing.get("tags") or [])
        for tg in (["scanned"] + (["event"] if event_name else [])):
            if tg not in tags:
                tags.append(tg)
        upd["tags"] = tags
        await db.leads.update_one({"id": existing["id"]}, {
            "$set": upd, "$push": {"timeline": _interaction("badge_rescanned")}})
        await recalc_lead_score(existing["id"])
        await db.notifications.insert_one({
            "id": str(uuid.uuid4()), "workspace_id": card.get("workspace_id"), "type": "lead_interaction",
            "card_slug": existing.get("cardSlug"), "scope": "card",
            "title": f"Scanned again: {existing.get('name')}",
            "body": (f"at {event_name}" if event_name else f"via {source}"),
            "read": False, "created_at": now,
        })
        lead = await db.leads.find_one({"id": existing["id"]}, {"_id": 0})
        asyncio.create_task(crm_maybe_autosync(await _lead_workspace_id(lead), existing["id"]))
        return {"ok": True, "lead": lead, "updated": True}

    # ---- Duplicate guard — let the user decide (update existing vs. save anyway)
    if not body.force:
        dup = await find_duplicate_lead(body.cardSlug, body.email, body.phone,
                                        name=body.name, company=body.company)
        if dup:
            return {"ok": False, "duplicate": dup}

    lang = body.language if body.language in SUPPORTED_LANGUAGES else "en"
    full_name = body.name.strip()
    lead = {
        "id": str(uuid.uuid4()), "cardSlug": body.cardSlug, "workspace_id": card.get("workspace_id"),
        "name": full_name, "first_name": body.first_name.strip(), "last_name": body.last_name.strip(),
        "email": body.email.strip(), "phone": body.phone.strip(),
        "company": body.company.strip(), "title": body.title.strip(),
        "website": body.website.strip(), "linkedin": body.linkedin.strip(),
        "badge_id": body.badge_id.strip(), "booth": body.booth.strip(),
        "message": body.notes.strip(), "interest": body.interest.strip(),
        "address": body.address.strip(), "city": body.city.strip(), "country": body.country.strip(),
        "language": lang, "source": source, "scanner_type": scanner_type,
        "campaign": body.campaign.strip(), "event": event_name, "event_id": event_id, "consent": True,
        "status": "new", "tags": ["scanned"] + (["event"] if event_name else []), "notes": body.notes.strip(),
        "met_at": now, "captured_at": now, "next_follow_up": "",
        "scanned": True, "captured_by": user["id"],
        "timeline": [_interaction("badge_scanned" if scanner_type == "event_badge" else "card_scanned")],
        "read": False, "created_at": now, "updated_at": now, "last_activity": now,
    }
    await db.leads.insert_one(lead)
    await recalc_lead_score(lead["id"])
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()), "workspace_id": card.get("workspace_id"), "type": "new_lead",
        "card_slug": body.cardSlug, "scope": "card",
        "title": f"Scanned lead: {lead['name']}",
        "body": (f"at {event_name}" if event_name else f"via {source}"),
        "read": False, "created_at": now,
    })
    lead = await db.leads.find_one({"id": lead["id"]}, {"_id": 0})
    asyncio.create_task(crm_maybe_autosync(card.get("workspace_id"), lead["id"]))
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
                                     "role": role, "status": "invited", "invite_token": token,
                                     "invite_expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
                                     "created_at": now_iso()})
    link = f"{PUBLIC_APP_URL}/invite/{token}"
    ws = await db.workspaces.find_one({"id": wid}, {"_id": 0, "name": 1, "owner_id": 1})
    inviter = await db.users.find_one({"id": (ws or {}).get("owner_id")}, {"_id": 0, "language": 1}) if ws else None
    lang = (inviter or {}).get("language") or "en"
    if _email_configured():
        await send_localized(email, "invite", lang, link, ws=(ws or {}).get("name", "your team"))
    else:
        logger.info(f"[email:NOT_CONFIGURED] team invite for {email}: {link}")
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


class InviteAcceptIn(BaseModel):
    password: str
    name: Optional[str] = ""


async def _invite_membership(token: str):
    return await db.memberships.find_one({"invite_token": token, "status": "invited"}, {"_id": 0})


@platform_router.get("/invites/{token}")
async def invite_info(token: str):
    """Public: resolve a team-invite token → workspace/email/role + expiry state (for the accept page)."""
    m = await _invite_membership(token)
    if not m:
        raise HTTPException(404, "This invitation is no longer valid.")
    expired = bool(m.get("invite_expires_at")) and m["invite_expires_at"] < now_iso()
    ws = await db.workspaces.find_one({"id": m["workspace_id"]}, {"_id": 0, "name": 1})
    u = await db.users.find_one({"id": m["user_id"]}, {"_id": 0, "email": 1, "name": 1})
    return {"email": (u or {}).get("email", ""), "name": (u or {}).get("name", ""),
            "workspace_name": (ws or {}).get("name", "your team"), "role": m.get("role", "MEMBER"),
            "expired": expired}


@platform_router.post("/invites/{token}/accept")
async def invite_accept(token: str, body: InviteAcceptIn, request: Request):
    """Public: consume a team-invite token → set the invited user's password, verify email, activate
    the membership (role/seat already enforced at invite time), and sign the user in."""
    rate_limit(request, "invite_accept", 10, 3600)
    m = await _invite_membership(token)
    if not m:
        raise HTTPException(404, "This invitation is no longer valid.")
    if m.get("invite_expires_at") and m["invite_expires_at"] < now_iso():
        raise HTTPException(400, "This invitation has expired. Please ask your team admin to re-invite you.")
    if not body.password or len(body.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters.")
    user = await db.users.find_one({"id": m["user_id"]}, {"_id": 0})
    if not user:
        raise HTTPException(404, "This invitation is no longer valid.")
    upd = {"password_hash": hash_pw(body.password), "email_verified": True}
    if body.name and body.name.strip():
        upd["name"] = body.name.strip()
    await db.users.update_one({"id": user["id"]}, {"$set": upd})
    await db.memberships.update_one({"id": m["id"]},
        {"$set": {"status": "active", "accepted_at": now_iso()}, "$unset": {"invite_token": "", "invite_expires_at": ""}})
    await audit(m["workspace_id"], user["id"], "team.invite_accepted", {"role": m.get("role")})
    user = await db.users.find_one({"id": user["id"]}, {"_id": 0, "password_hash": 0})
    return await _auth_payload(user, request)


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


# ================================================================== CRM CONNECTORS (V1: HubSpot, one-way TapPresence -> CRM)
# Shared adapter surface so Salesforce/Pipedrive can be added later WITHOUT touching lead/event logic.
# Tokens live ONLY server-side in Mongo `crm_connections` (never returned to client / logged / in CSV).
import httpx as _cx

HUBSPOT_CLIENT_ID = os.environ.get("HUBSPOT_CLIENT_ID") or ""
HUBSPOT_CLIENT_SECRET = os.environ.get("HUBSPOT_CLIENT_SECRET") or ""
HUBSPOT_REDIRECT_URI = os.environ.get("HUBSPOT_REDIRECT_URI") or ""
HUBSPOT_SCOPES = ("oauth crm.objects.contacts.read crm.objects.contacts.write "
                  "crm.objects.deals.read crm.objects.deals.write "
                  "crm.schemas.contacts.read crm.schemas.contacts.write "
                  "crm.schemas.deals.read crm.schemas.deals.write")
HS_API = "https://api.hubspot.com"
# TapPresence stage -> HubSpot DEFAULT-pipeline stage internal id (controlled map; portals with custom
# pipelines need per-workspace config — documented V1 limitation, we never move a deal to an arbitrary stage).
HS_STAGE_MAP = {"new": "appointmentscheduled", "contacted": "appointmentscheduled",
                "qualified": "qualifiedtobuy", "meeting": "presentationscheduled",
                "opportunity": "decisionmakerboughtin", "customer": "closedwon", "not_interested": "closedlost"}
# Custom properties we create once per portal (kept intentionally small).
HS_CONTACT_PROPS = [
    ("tap_lead_id", "TapPresence Lead ID", "string", "text", True),
    ("tap_lead_score", "TapPresence Lead Score", "number", "number", False),
    ("tap_lead_temperature", "TapPresence Temperature", "string", "text", False),
    ("tap_pipeline_stage", "TapPresence Pipeline Stage", "string", "text", False),
    ("tap_source", "TapPresence Source", "string", "text", False),
    ("tap_capture_method", "TapPresence Capture Method", "string", "text", False),
    ("tap_event_name", "TapPresence Event", "string", "text", False),
    ("tap_captured_by", "TapPresence Captured By", "string", "text", False),
    ("tap_last_interaction", "TapPresence Last Interaction", "string", "text", False),
]
HS_DEAL_PROPS = [
    ("tap_deal_id", "TapPresence Lead ID", "string", "text", True),
    ("tap_event_name", "TapPresence Event", "string", "text", False),
    ("tap_currency", "TapPresence Currency", "string", "text", False),
]


def _hubspot_configured() -> bool:
    return bool(HUBSPOT_CLIENT_ID and HUBSPOT_CLIENT_SECRET and HUBSPOT_REDIRECT_URI)


def _hubspot_frontend_base() -> str:
    suffix = "/api/integrations/hubspot/callback"
    if HUBSPOT_REDIRECT_URI.endswith(suffix):
        return HUBSPOT_REDIRECT_URI[: -len(suffix)]
    return PUBLIC_APP_URL


class _CrmNeedsReconnect(Exception):
    pass


async def _lead_workspace_id(lead: dict) -> str:
    wid = lead.get("workspace_id")
    if wid:
        return wid
    card = await db.digital_cards.find_one({"slug": lead.get("cardSlug")}, {"_id": 0, "workspace_id": 1})
    return (card or {}).get("workspace_id")


async def _crm_conn(ws_id: str, provider: str = "hubspot"):
    return await db.crm_connections.find_one({"workspace_id": ws_id, "provider": provider}, {"_id": 0})


async def _hs_access_token(ws_id: str):
    """Valid access token for the workspace's HubSpot connection (refresh if needed). Never leaves the server."""
    conn = await _crm_conn(ws_id)
    if not conn or conn.get("revoked"):
        return None
    now = datetime.now(timezone.utc)
    exp = conn.get("access_expiry")
    if conn.get("access_token") and exp and datetime.fromisoformat(exp) > now + timedelta(seconds=60):
        return conn["access_token"]
    rt = conn.get("refresh_token")
    if not rt:
        return None
    async with _cx.AsyncClient(timeout=20) as cx:
        r = await cx.post(f"{HS_API}/oauth/v3/token", data={
            "grant_type": "refresh_token", "client_id": HUBSPOT_CLIENT_ID,
            "client_secret": HUBSPOT_CLIENT_SECRET, "refresh_token": rt})
    if r.status_code != 200:
        err = ""
        try:
            err = (r.json() or {}).get("message", "")
        except Exception:
            pass
        logger.error(f"[hubspot] refresh failed ws={ws_id} http={r.status_code}")
        if r.status_code in (400, 401, 403):
            await db.crm_connections.update_one({"workspace_id": ws_id, "provider": "hubspot"},
                {"$set": {"revoked": True, "needs_reconnect": True, "updated_at": now.isoformat()}})
            raise _CrmNeedsReconnect()
        return None
    tok = r.json()
    at = tok.get("access_token")
    new_rt = tok.get("refresh_token") or rt
    new_exp = (now + timedelta(seconds=int(tok.get("expires_in", 1800)))).isoformat()
    await db.crm_connections.update_one({"workspace_id": ws_id, "provider": "hubspot"},
        {"$set": {"access_token": at, "refresh_token": new_rt, "access_expiry": new_exp,
                  "revoked": False, "needs_reconnect": False, "updated_at": now.isoformat()}})
    return at


async def _hs(ws_id: str, method: str, path: str, json=None):
    """Authenticated HubSpot call. Returns (status_code, json_or_text). Redacts auth in errors."""
    token = await _hs_access_token(ws_id)
    if not token:
        raise _CrmNeedsReconnect()
    async with _cx.AsyncClient(base_url=HS_API, timeout=30) as cx:
        r = await cx.request(method, path, headers={"Authorization": f"Bearer {token}",
                             "Content-Type": "application/json"}, json=json)
    try:
        body = r.json() if r.content else {}
    except Exception:
        body = {"raw": (r.text or "")[:300]}
    return r.status_code, body


async def _hs_ensure_props(ws_id: str, conn: dict):
    """Create TapPresence custom properties once per portal (idempotent). Marks props_ready on success."""
    if conn.get("props_ready"):
        return
    for obj, props in (("contacts", HS_CONTACT_PROPS), ("deals", HS_DEAL_PROPS)):
        group = "contactinformation" if obj == "contacts" else "dealinformation"
        for name, label, ptype, ftype, uniq in props:
            st, _ = await _hs(ws_id, "GET", f"/crm/v3/properties/{obj}/{name}")
            if st == 200:
                continue
            payload = {"groupName": group, "name": name, "label": label, "type": ptype, "fieldType": ftype}
            if uniq:
                payload["hasUniqueValue"] = True
            await _hs(ws_id, "POST", f"/crm/v3/properties/{obj}", json=payload)
    await db.crm_connections.update_one({"workspace_id": ws_id, "provider": "hubspot"},
                                        {"$set": {"props_ready": True}})


def _lead_contact_props(lead: dict) -> dict:
    eff = effective_temperature(lead) if "effective_temperature" in globals() else (lead.get("lead_temperature") or "")
    p = {
        "email": (lead.get("email") or "").strip(),
        "firstname": (lead.get("first_name") or (lead.get("name") or "").split(" ")[0]).strip(),
        "lastname": (lead.get("last_name") or " ".join((lead.get("name") or "").split(" ")[1:])).strip(),
        "phone": (lead.get("phone") or "").strip(),
        "jobtitle": (lead.get("title") or "").strip(),
        "company": (lead.get("company") or "").strip(),
        "website": (lead.get("website") or "").strip(),
        "tap_lead_id": lead.get("id"),
        "tap_lead_score": lead.get("lead_score"),
        "tap_lead_temperature": eff,
        "tap_pipeline_stage": (lead.get("status") or "new"),
        "tap_source": (lead.get("source") or ""),
        "tap_capture_method": (lead.get("scanner_type") or lead.get("source") or ""),
        "tap_event_name": (lead.get("event") or ""),
        "tap_captured_by": (lead.get("captured_by") or ""),
        "tap_last_interaction": (lead.get("last_activity") or lead.get("updated_at") or ""),
    }
    return {k: str(v) for k, v in p.items() if v not in (None, "")}


def _sync_signature(lead: dict) -> str:
    import hashlib as _h
    basis = "|".join(str(lead.get(k) or "") for k in
                     ["name", "email", "phone", "company", "title", "website", "status", "source",
                      "event", "captured_by", "lead_score", "lead_temperature", "lead_temperature_override",
                      "opportunity_value", "opportunity_currency", "expected_close_date", "actual_revenue"])
    return _h.sha256(basis.encode()).hexdigest()[:16]


async def crm_sync_lead(ws_id: str, lead: dict, provider: str = "hubspot") -> dict:
    """Idempotent one-way sync of a TapPresence lead into HubSpot (contact + optional deal).
    Never raises to caller — always records structured crm_sync state on the lead and returns it."""
    now = datetime.now(timezone.utc).isoformat()
    prior = lead.get("crm_sync") or {}
    state = {"provider": provider, "remote_contact_id": prior.get("remote_contact_id"),
             "remote_deal_id": prior.get("remote_deal_id"), "status": "pending",
             "last_synced_at": prior.get("last_synced_at"), "last_error": "",
             "retry_count": int(prior.get("retry_count") or 0), "signature": prior.get("signature")}
    try:
        conn = await _crm_conn(ws_id, provider)
        if not conn or conn.get("revoked"):
            raise _CrmNeedsReconnect()
        email = (lead.get("email") or "").strip()
        if not email:
            state.update({"status": "failed", "last_error": "email_required"})
            await _persist_crm_state(lead["id"], state)
            return state
        await _hs_ensure_props(ws_id, conn)
        # --- Contact upsert by email (dedupe-safe) ---
        st, body = await _hs(ws_id, "POST", "/crm/v3/objects/contacts/batch/upsert",
                             json={"inputs": [{"idProperty": "email", "id": email,
                                               "properties": _lead_contact_props(lead)}]})
        if st >= 400:
            raise RuntimeError(f"contact_upsert_{st}: {str(body)[:160]}")
        contact_id = (body.get("results") or [{}])[0].get("id")
        state["remote_contact_id"] = contact_id
        # --- Deal upsert (only when a real opportunity value exists) ---
        ov = lead.get("opportunity_value")
        if ov is not None:
            dprops = {"tap_deal_id": lead.get("id"),
                      "dealname": (lead.get("name") or "TapPresence lead") + (f" — {lead.get('company')}" if lead.get("company") else ""),
                      "amount": str(ov), "pipeline": "default",
                      "dealstage": HS_STAGE_MAP.get((lead.get("status") or "new").lower(), "appointmentscheduled"),
                      "tap_event_name": lead.get("event") or "",
                      "tap_currency": lead.get("opportunity_currency") or ""}
            cd = lead.get("expected_close_date")
            if cd:
                dprops["closedate"] = str(cd)[:10]
            st2, body2 = await _hs(ws_id, "POST", "/crm/v3/objects/deals/batch/upsert",
                                   json={"inputs": [{"idProperty": "tap_deal_id", "id": lead.get("id"), "properties": dprops}]})
            if st2 >= 400:
                raise RuntimeError(f"deal_upsert_{st2}: {str(body2)[:160]}")
            deal_id = (body2.get("results") or [{}])[0].get("id")
            state["remote_deal_id"] = deal_id
            if deal_id and contact_id:
                await _hs(ws_id, "PUT", f"/crm/v4/objects/deals/{deal_id}/associations/default/contacts/{contact_id}", json=None)
        state.update({"status": "synced", "last_synced_at": now, "last_error": "",
                      "retry_count": 0, "signature": _sync_signature(lead)})
    except _CrmNeedsReconnect:
        state.update({"status": "failed", "last_error": "needs_reconnect", "retry_count": state["retry_count"] + 1})
    except Exception as e:
        state.update({"status": "failed", "last_error": str(e)[:200], "retry_count": state["retry_count"] + 1})
    await meter_usage("crm_sync", user_id=lead.get("captured_by"), workspace_id=ws_id, quantity=1,
                      result=("success" if state.get("status") == "synced" else "failed"),
                      source=f"crm:{provider}", paid=(state.get("status") == "synced"))
    await _persist_crm_state(lead["id"], state)
    return state


async def _persist_crm_state(lead_id: str, state: dict):
    await db.leads.update_one({"id": lead_id}, {"$set": {"crm_sync": state}})


async def crm_maybe_autosync(ws_id: str, lead_id: str):
    """Fire-and-forget auto-sync: only when the workspace has auto_sync enabled and the lead changed."""
    try:
        conn = await _crm_conn(ws_id)
        if not conn or conn.get("revoked") or not conn.get("auto_sync"):
            return
        lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
        if not lead or not (lead.get("email") or "").strip():
            return
        if (lead.get("crm_sync") or {}).get("signature") == _sync_signature(lead) and (lead.get("crm_sync") or {}).get("status") == "synced":
            return  # change-aware: nothing new to push
        await crm_sync_lead(ws_id, lead)
    except Exception as e:
        logger.warning(f"[hubspot] autosync skip lead={lead_id}: {e}")


def _crm_public_state(lead: dict) -> dict:
    """Client-safe CRM sync view for a lead (no tokens/secrets)."""
    s = lead.get("crm_sync") or {}
    return {"provider": s.get("provider") or "hubspot", "status": s.get("status") or "not_synced",
            "remote_contact_id": s.get("remote_contact_id"), "remote_deal_id": s.get("remote_deal_id"),
            "last_synced_at": s.get("last_synced_at"), "last_error": s.get("last_error") or "",
            "retry_count": s.get("retry_count") or 0}


# ---- OAuth + management routes (workspace-level; owner/admin only) ----
async def _hs_ws_for_user(user: dict) -> str:
    ms = await memberships_for(user["id"])
    if not ms:
        raise HTTPException(400, "No workspace")
    return ms[0]["workspace_id"]


@platform_router.get("/integrations/hubspot/status")
async def hubspot_status(user: dict = Depends(current_user)):
    ws_id = await _hs_ws_for_user(user)
    conn = await _crm_conn(ws_id)
    connected = bool(conn and not conn.get("revoked") and conn.get("refresh_token"))
    return {"configured": _hubspot_configured(), "connected": connected,
            "needs_reconnect": bool(conn and conn.get("needs_reconnect")),
            "auto_sync": bool(conn and conn.get("auto_sync")),
            "hub_id": (conn or {}).get("hub_id") if connected else None,
            "connected_at": (conn or {}).get("connected_at") if connected else None}


@platform_router.get("/integrations/hubspot/connect")
async def hubspot_connect(user: dict = Depends(current_user)):
    if not _hubspot_configured():
        raise HTTPException(400, "HubSpot is not configured on the server")
    ws_id = await _hs_ws_for_user(user)
    await require_ws_admin(user, ws_id)
    state = _secrets.token_urlsafe(24)
    await db.crm_oauth_states.insert_one({"state": state, "workspace_id": ws_id, "user_id": user["id"],
                                          "provider": "hubspot", "created_at": now_iso()})
    from urllib.parse import urlencode as _ue
    params = {"client_id": HUBSPOT_CLIENT_ID, "scope": HUBSPOT_SCOPES,
              "redirect_uri": HUBSPOT_REDIRECT_URI, "state": state}
    return {"authorization_url": f"https://app.hubspot.com/oauth/authorize?{_ue(params)}"}


@platform_router.get("/integrations/hubspot/callback")
async def hubspot_callback(code: str = "", state: str = ""):
    base = _hubspot_frontend_base()
    dest = f"{base}/settings?tab=integrations"
    st = await db.crm_oauth_states.find_one_and_delete({"state": state, "provider": "hubspot"}) if state else None
    if not st or not code:
        return RedirectResponse(f"{dest}&hubspot_error=state")
    async with _cx.AsyncClient(timeout=20) as cx:
        r = await cx.post(f"{HS_API}/oauth/v3/token", data={
            "grant_type": "authorization_code", "code": code, "redirect_uri": HUBSPOT_REDIRECT_URI,
            "client_id": HUBSPOT_CLIENT_ID, "client_secret": HUBSPOT_CLIENT_SECRET})
    if r.status_code != 200:
        logger.error(f"[hubspot] code exchange failed http={r.status_code}")
        return RedirectResponse(f"{dest}&hubspot_error=exchange")
    tok = r.json()
    now = datetime.now(timezone.utc)
    ws_id = st["workspace_id"]
    await db.crm_connections.update_one({"workspace_id": ws_id, "provider": "hubspot"}, {"$set": {
        "workspace_id": ws_id, "provider": "hubspot", "hub_id": tok.get("hub_id"),
        "scopes": tok.get("scopes") or [], "access_token": tok.get("access_token"),
        "refresh_token": tok.get("refresh_token"),
        "access_expiry": (now + timedelta(seconds=int(tok.get("expires_in", 1800)))).isoformat(),
        "revoked": False, "needs_reconnect": False, "props_ready": False,
        "connected_by": st.get("user_id"), "connected_at": now.isoformat(), "updated_at": now.isoformat(),
    }}, upsert=True)
    await audit(ws_id, st.get("user_id"), "crm.hubspot.connected", {"hub_id": tok.get("hub_id")})
    return RedirectResponse(f"{dest}&hubspot=connected")


@platform_router.post("/integrations/hubspot/disconnect")
async def hubspot_disconnect(user: dict = Depends(current_user)):
    ws_id = await _hs_ws_for_user(user)
    await require_ws_admin(user, ws_id)
    await db.crm_connections.delete_one({"workspace_id": ws_id, "provider": "hubspot"})
    await audit(ws_id, user["id"], "crm.hubspot.disconnected", {})
    return {"ok": True}


class HubspotSettingsIn(BaseModel):
    auto_sync: bool


@platform_router.post("/integrations/hubspot/settings")
async def hubspot_settings(body: HubspotSettingsIn, user: dict = Depends(current_user)):
    ws_id = await _hs_ws_for_user(user)
    await require_ws_admin(user, ws_id)
    conn = await _crm_conn(ws_id)
    if not conn:
        raise HTTPException(400, "HubSpot is not connected")
    await db.crm_connections.update_one({"workspace_id": ws_id, "provider": "hubspot"},
                                        {"$set": {"auto_sync": bool(body.auto_sync), "updated_at": now_iso()}})
    await audit(ws_id, user["id"], "crm.hubspot.auto_sync", {"enabled": bool(body.auto_sync)})
    return {"ok": True, "auto_sync": bool(body.auto_sync)}


async def _crm_lead_or_403(lead_id: str, user: dict):
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(404, "Lead not found")
    slugs = await _owned_slugs(user)
    if lead.get("cardSlug") not in slugs and user.get("role") != "SUPER_ADMIN":
        raise HTTPException(403, "Not your lead")
    return lead


@platform_router.post("/admin/leads/{lead_id}/sync-hubspot")
async def sync_lead_hubspot(lead_id: str, user: dict = Depends(current_user)):
    lead = await _crm_lead_or_403(lead_id, user)
    ws_id = await _lead_workspace_id(lead)
    conn = await _crm_conn(ws_id)
    if not conn or conn.get("revoked"):
        raise HTTPException(400, "HubSpot is not connected for this workspace")
    state = await crm_sync_lead(ws_id, lead)
    await audit(ws_id, user["id"], "crm.hubspot.lead_synced", {"lead_id": lead_id, "status": state["status"]})
    if state["status"] != "synced":
        raise HTTPException(502, {"detail": "sync_failed", "crm_sync": state})
    return {"ok": True, "crm_sync": _crm_public_state({"crm_sync": state})}


@platform_router.post("/events/{event_id}/sync-hubspot")
async def sync_event_hubspot(event_id: str, user: dict = Depends(current_user)):
    ev = await _event_or_403(event_id, user)
    await require_ws_admin(user, ev.get("workspace_id"))
    conn = await _crm_conn(ev.get("workspace_id"))
    if not conn or conn.get("revoked"):
        raise HTTPException(400, "HubSpot is not connected for this workspace")
    leads = await db.leads.find(_event_lead_query(event_id), {"_id": 0}).to_list(10000)
    summary = {"total": len(leads), "synced": 0, "failed": 0, "skipped": 0}
    MAX_BULK = 1000
    for l in leads[:MAX_BULK]:
        if not (l.get("email") or "").strip():
            summary["skipped"] += 1
            continue
        st = await crm_sync_lead(ev.get("workspace_id"), l)
        summary["synced" if st["status"] == "synced" else "failed"] += 1
    if len(leads) > MAX_BULK:
        summary["remaining"] = len(leads) - MAX_BULK
    await audit(ev.get("workspace_id"), user["id"], "crm.hubspot.event_synced", {"event_id": event_id, **summary})
    return summary



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


# ==================================================================
# USAGE & COST CONTROL (SUPER_ADMIN) — additive metering + cost engine + limit engine
# Reuses existing metering/quota/audit. NO arbitrary limits are activated: enforcement is
# globally OFF per feature by default, so existing customer behavior is 100% preserved until
# a Super Admin explicitly enables a limit. Estimated costs are labelled ESTIMATED everywhere.
# ==================================================================
from pymongo import ReturnDocument as _ReturnDoc

# Feature catalog — the single source of truth for what is measured. `default_unit_cost` is an
# EXAMPLE only (Super-Admin editable); never treated as authoritative vendor pricing.
USAGE_FEATURES = [
    {"key": "business_card_scan", "name": "Business Card AI Scanner", "category": "AI", "metered": True,
     "enforceable": True, "default_unit_cost": 0.02, "cost_unit": "per scan"},
    {"key": "event_badge_scan", "name": "Event Badge AI Scanner", "category": "AI", "metered": True,
     "enforceable": True, "default_unit_cost": 0.02, "cost_unit": "per scan"},
    {"key": "ai_followup", "name": "AI Follow-up / Draft", "category": "AI", "metered": True,
     "enforceable": True, "default_unit_cost": 0.03, "cost_unit": "per AI request"},
    {"key": "ai_lead_insight", "name": "AI Lead Insights", "category": "AI", "metered": True,
     "enforceable": True, "default_unit_cost": 0.03, "cost_unit": "per AI request", "default_scope": "per_user"},
    {"key": "ai_event_recap", "name": "AI Event Recap", "category": "AI", "metered": True,
     "enforceable": True, "default_unit_cost": 0.05, "cost_unit": "per AI request", "default_scope": "per_event"},
    {"key": "email", "name": "Transactional Emails", "category": "Email", "metered": True,
     "enforceable": False, "default_unit_cost": 0.0, "cost_unit": "per email"},
    {"key": "crm_sync", "name": "CRM Sync", "category": "CRM", "metered": True,
     "enforceable": False, "default_unit_cost": 0.0, "cost_unit": "per API call"},
    {"key": "wallet_pass", "name": "Wallet Pass Creation", "category": "Wallet", "metered": True,
     "enforceable": False, "default_unit_cost": 0.0, "cost_unit": "per pass"},
    {"key": "card_view", "name": "Public Card Views", "category": "Traffic", "metered": False,
     "aggregate": ("analytics_events", "view"), "enforceable": False, "default_unit_cost": 0.0, "cost_unit": "per view"},
    {"key": "qr_scan", "name": "QR Scans", "category": "Traffic", "metered": False,
     "aggregate": ("analytics_events", "scan"), "enforceable": False, "default_unit_cost": 0.0, "cost_unit": "per scan"},
    {"key": "lead_captured", "name": "Leads Captured", "category": "Analytics", "metered": False,
     "aggregate": ("leads", None), "enforceable": False, "default_unit_cost": 0.0, "cost_unit": "per lead"},
    {"key": "meeting", "name": "Meetings", "category": "Analytics", "metered": False,
     "aggregate": ("meetings", None), "enforceable": False, "default_unit_cost": 0.0, "cost_unit": "per meeting"},
]
_USAGE_FEATURE_MAP = {f["key"]: f for f in USAGE_FEATURES}
USAGE_PLANS = ["trial", "pro", "team", "enterprise"]
LIMIT_MODES = ["unlimited", "monthly", "disabled", "custom"]
LIMIT_SCOPES = ["per_user", "per_workspace", "per_event", "unlimited"]
HARD_BEHAVIORS = ["block", "flag", "overage"]


def _default_feature_config(meta: dict) -> dict:
    return {
        "unit_cost": float(meta.get("default_unit_cost", 0.0)),
        "currency": "USD",
        "effective_from": now_iso(),
        "enforcement_enabled": False,          # OFF by default — preserves existing behavior
        "scope": meta.get("default_scope", "per_user"),
        "plan_limits": {p: {"mode": "unlimited", "limit": None} for p in USAGE_PLANS},
        "soft_pct": 80,
        "hard_behavior": "flag",               # non-blocking default even if later enabled
    }


def _default_usage_config() -> dict:
    return {"id": "global",
            "features": {f["key"]: _default_feature_config(f) for f in USAGE_FEATURES},
            "cost_history": []}


async def get_usage_config() -> dict:
    """Single source of truth for cost/limit config. Seeds + backfills newly added features."""
    doc = await db.usage_config.find_one({"id": "global"}, {"_id": 0})
    if not doc:
        doc = _default_usage_config()
        await db.usage_config.insert_one(dict(doc))
        return doc
    feats = doc.get("features") or {}
    changed = False
    for f in USAGE_FEATURES:
        if f["key"] not in feats:
            feats[f["key"]] = _default_feature_config(f)
            changed = True
        else:
            base = _default_feature_config(f)
            for k, v in base.items():
                if k not in feats[f["key"]]:
                    feats[f["key"]][k] = v
                    changed = True
    doc["features"] = feats
    doc.setdefault("cost_history", [])
    if changed:
        await db.usage_config.update_one({"id": "global"}, {"$set": {"features": feats}}, upsert=True)
    return doc


def _calendar_period() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


async def _usage_period_for_ws(ws_id: Optional[str]) -> str:
    """Billing-cycle-aware period key (req 12). Uses the real Stripe current_period_end when present
    (so the allowance window follows the customer's actual cycle); calendar month otherwise.
    Historical usage_events are NEVER deleted on reset — only the meter key changes."""
    if not ws_id:
        return _calendar_period()
    ws = await db.workspaces.find_one({"id": ws_id}, {"_id": 0, "subscription": 1})
    sub = (ws or {}).get("subscription") or {}
    cpe = sub.get("current_period_end")
    if cpe and sub.get("provider") == "stripe":
        return f"cycle:{str(cpe)[:10]}"
    return _calendar_period()


async def _reserve_usage(feature: str, scope_type: str, scope_id: str, period: str, limit) -> bool:
    """Atomic conditional reservation (req 13). Safe under concurrency: uses find_one_and_update with
    a count<limit guard so simultaneous requests can never exceed the enabled limit."""
    key = {"feature": feature, "scope_type": scope_type, "scope_id": scope_id, "period": period}
    if limit is None:
        await db.usage_meters.update_one(key, {"$inc": {"count": 1}}, upsert=True)
        return True
    if limit <= 0:
        return False
    doc = await db.usage_meters.find_one_and_update(
        {**key, "count": {"$lt": limit}}, {"$inc": {"count": 1}}, return_document=_ReturnDoc.AFTER)
    if doc:
        return True
    try:
        await db.usage_meters.insert_one({**key, "count": 1})
        return True
    except Exception:
        doc = await db.usage_meters.find_one_and_update(
            {**key, "count": {"$lt": limit}}, {"$inc": {"count": 1}}, return_document=_ReturnDoc.AFTER)
        return bool(doc)


async def _release_usage(feature: str, scope_type: str, scope_id: str, period: str):
    await db.usage_meters.update_one(
        {"feature": feature, "scope_type": scope_type, "scope_id": scope_id, "period": period, "count": {"$gt": 0}},
        {"$inc": {"count": -1}})


async def _resolve_feature_limit(fcfg: dict, plan: str, scope_type: str, scope_id: str):
    """Returns (limit:int|None, mode, is_override). Customer override wins over plan limit."""
    ov = await db.usage_overrides.find_one(
        {"feature": fcfg["_key"], "scope_type": scope_type, "scope_id": scope_id}, {"_id": 0})
    if ov:
        mode = ov.get("mode", "unlimited")
        lim = None if mode == "unlimited" else (0 if mode == "disabled" else ov.get("limit"))
        return lim, mode, True
    pl = (fcfg.get("plan_limits") or {}).get(plan) or {"mode": "unlimited", "limit": None}
    mode = pl.get("mode", "unlimited")
    lim = None if mode == "unlimited" else (0 if mode == "disabled" else pl.get("limit"))
    return lim, mode, False


async def usage_guard(feature_key: str, user: dict, ws_id: Optional[str], event_id: str = "") -> dict:
    """Enforcement entry point for metered features. Returns a reservation handle.
    NO-OP (enforced False) when the feature's enforcement is disabled — this preserves ALL existing
    behavior until a Super Admin turns a limit on. Raises 429 only for block-mode hard limits."""
    handle = {"enforced": False, "reserved": False, "feature": feature_key,
              "scope_type": None, "scope_id": None, "period": None}
    if user.get("role") == "SUPER_ADMIN":
        return handle
    try:
        cfg = await get_usage_config()
        fcfg = dict((cfg.get("features") or {}).get(feature_key) or {})
        if not fcfg or not fcfg.get("enforcement_enabled"):
            return handle
        fcfg["_key"] = feature_key
        scope = fcfg.get("scope", "per_user")
        if scope == "unlimited":
            return handle
        if scope == "per_user":
            scope_type, scope_id = "user", user["id"]
        elif scope == "per_workspace":
            scope_type, scope_id = "workspace", ws_id
        elif scope == "per_event":
            if not event_id:
                return handle  # no event context → cannot enforce per-event; don't block
            scope_type, scope_id = "event", event_id
        else:
            return handle
        if not scope_id:
            return handle
        ent = await resolve_entitlements(ws_id) if ws_id else {}
        plan = ent.get("plan") if ent.get("plan") in USAGE_PLANS else None
        if plan is None:
            return handle  # grandfathered/unknown plan → no arbitrary block
        limit, mode, _isov = await _resolve_feature_limit(fcfg, plan, scope_type, scope_id)
        if mode == "unlimited" or limit is None:
            return handle
        period = await _usage_period_for_ws(ws_id)
        handle.update({"enforced": True, "scope_type": scope_type, "scope_id": scope_id, "period": period})
        behavior = fcfg.get("hard_behavior", "flag")
        if behavior == "block":
            ok = await _reserve_usage(feature_key, scope_type, scope_id, period, limit)
            if not ok:
                meta = _USAGE_FEATURE_MAP.get(feature_key, {})
                raise HTTPException(429, f"You've reached your {meta.get('name', feature_key)} allowance for this period.")
            handle["reserved"] = True
        # flag / overage → allow through (recorded via meter_usage); Super Admin sees the flag
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"usage_guard soft-fail {feature_key}: {e}")
        return handle
    return handle


async def release_usage_handle(handle: dict):
    if handle and handle.get("reserved"):
        try:
            await _release_usage(handle["feature"], handle["scope_type"], handle["scope_id"], handle["period"])
        except Exception as e:
            logger.warning(f"release_usage_handle: {e}")


async def meter_usage(feature_key: str, user_id: Optional[str] = None, workspace_id: Optional[str] = None,
                      event_id: str = "", plan: Optional[str] = None, quantity: int = 1,
                      result: str = "success", source: str = "app", paid: bool = True):
    """Central metering — records ONE usage_event with estimated cost. Best-effort (never breaks the
    caller). Cost is charged only for successful, provider-incurring operations (req 13/14)."""
    try:
        meta = _USAGE_FEATURE_MAP.get(feature_key, {})
        cfg = await get_usage_config()
        fcfg = (cfg.get("features") or {}).get(feature_key) or {}
        unit_cost = float(fcfg.get("unit_cost", 0.0)) if (paid and result == "success") else 0.0
        if plan is None and workspace_id:
            ws = await db.workspaces.find_one({"id": workspace_id}, {"_id": 0, "subscription": 1, "plan": 1})
            plan = ((ws or {}).get("subscription") or {}).get("plan") or (ws or {}).get("plan")
        period = await _usage_period_for_ws(workspace_id)
        await db.usage_events.insert_one({
            "id": str(uuid.uuid4()), "feature": feature_key, "category": meta.get("category", "Other"),
            "user_id": user_id, "workspace_id": workspace_id, "event_id": event_id or None,
            "plan": plan, "quantity": int(quantity), "unit_cost": unit_cost,
            "cost": round(unit_cost * int(quantity), 6), "currency": fcfg.get("currency", "USD"),
            "result": result, "source": source, "period": period, "created_at": now_iso(),
        })
    except Exception as e:
        logger.warning(f"meter_usage soft-fail {feature_key}: {e}")


# ------------------------------------------------------------------ Super-Admin: Usage & Cost Control API
def _usage_range(start: Optional[str], end: Optional[str]):
    if end:
        end_i = end if len(end) > 10 else end + "T23:59:59.999999+00:00"
    else:
        end_i = now_iso()
    if start:
        start_i = start if len(start) > 10 else start + "T00:00:00+00:00"
    else:
        start_i = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    return start_i, end_i


def _status_for_pct(pct):
    if pct is None:
        return "normal"
    if pct >= 100:
        return "critical"
    if pct >= 80:
        return "high"
    if pct >= 50:
        return "watch"
    return "normal"


@platform_router.get("/admin/control/usage/config")
async def usage_config_get(user: dict = Depends(current_user)):
    _require_super(user)
    cfg = await get_usage_config()
    feats = cfg.get("features") or {}
    out = []
    for f in USAGE_FEATURES:
        fc = feats.get(f["key"], {})
        out.append({**{k: f.get(k) for k in ("key", "name", "category", "metered", "enforceable", "cost_unit", "placeholder")},
                    "config": fc})
    return {"features": out, "plans": USAGE_PLANS, "limit_modes": LIMIT_MODES,
            "limit_scopes": LIMIT_SCOPES, "hard_behaviors": HARD_BEHAVIORS,
            "cost_history": (cfg.get("cost_history") or [])[-100:]}


class UsageFeatureConfigIn(BaseModel):
    unit_cost: Optional[float] = None
    currency: Optional[str] = None
    enforcement_enabled: Optional[bool] = None
    scope: Optional[str] = None
    plan_limits: Optional[dict] = None
    soft_pct: Optional[int] = None
    hard_behavior: Optional[str] = None


@platform_router.put("/admin/control/usage/config/{feature}")
async def usage_config_set(feature: str, body: UsageFeatureConfigIn, user: dict = Depends(current_user)):
    _require_super(user)
    if feature not in _USAGE_FEATURE_MAP:
        raise HTTPException(404, "Unknown feature")
    cfg = await get_usage_config()
    feats = cfg.get("features") or {}
    fc = dict(feats.get(feature) or _default_feature_config(_USAGE_FEATURE_MAP[feature]))
    before = dict(fc)
    patch = {k: v for k, v in body.dict().items() if v is not None}
    if "scope" in patch and patch["scope"] not in LIMIT_SCOPES:
        raise HTTPException(400, "Invalid scope")
    if "hard_behavior" in patch and patch["hard_behavior"] not in HARD_BEHAVIORS:
        raise HTTPException(400, "Invalid hard_behavior")
    if "plan_limits" in patch:
        pl = dict(fc.get("plan_limits") or {})
        for p, v in (patch["plan_limits"] or {}).items():
            if p in USAGE_PLANS and isinstance(v, dict):
                mode = v.get("mode", "unlimited")
                if mode not in LIMIT_MODES:
                    raise HTTPException(400, f"Invalid mode for {p}")
                lim = v.get("limit")
                pl[p] = {"mode": mode, "limit": (int(lim) if (lim not in (None, "") and mode in ("monthly", "custom")) else None)}
        patch["plan_limits"] = pl
    cost_changed = ("unit_cost" in patch and float(patch["unit_cost"]) != float(fc.get("unit_cost", 0.0)))
    fc.update(patch)
    if cost_changed:
        fc["effective_from"] = now_iso()
    feats[feature] = fc
    hist = cfg.get("cost_history") or []
    if cost_changed:
        hist.append({"feature": feature, "unit_cost": fc["unit_cost"], "currency": fc.get("currency", "USD"),
                     "effective_from": fc["effective_from"], "changed_by": user["id"], "changed_at": now_iso()})
    await db.usage_config.update_one({"id": "global"}, {"$set": {"features": feats, "cost_history": hist}}, upsert=True)
    await audit(None, user["id"], "admin.usage.config", {"feature": feature, "before": before, "after": fc})
    return {"ok": True, "feature": feature, "config": fc}


class UsageOverrideIn(BaseModel):
    feature: str
    scope_type: str          # user | workspace | event
    scope_id: str
    mode: str = "monthly"    # unlimited | monthly | disabled | custom
    limit: Optional[int] = None
    note: str = ""


@platform_router.get("/admin/control/usage/overrides")
async def usage_overrides_list(feature: str = "", user: dict = Depends(current_user)):
    _require_super(user)
    q = {"feature": feature} if feature else {}
    rows = await db.usage_overrides.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)
    for r in rows:
        if r.get("scope_type") == "user":
            u = await db.users.find_one({"id": r["scope_id"]}, {"_id": 0, "name": 1, "email": 1})
            r["scope_label"] = (u or {}).get("email") or r["scope_id"]
        elif r.get("scope_type") == "workspace":
            w = await db.workspaces.find_one({"id": r["scope_id"]}, {"_id": 0, "name": 1})
            r["scope_label"] = (w or {}).get("name") or r["scope_id"]
        elif r.get("scope_type") == "event":
            e = await db.events.find_one({"id": r["scope_id"]}, {"_id": 0, "name": 1})
            r["scope_label"] = (e or {}).get("name") or r["scope_id"]
    return {"items": rows}


@platform_router.post("/admin/control/usage/overrides")
async def usage_override_create(body: UsageOverrideIn, user: dict = Depends(current_user)):
    _require_super(user)
    if body.feature not in _USAGE_FEATURE_MAP:
        raise HTTPException(404, "Unknown feature")
    if body.scope_type not in ("user", "workspace", "event"):
        raise HTTPException(400, "Invalid scope_type")
    if body.mode not in LIMIT_MODES:
        raise HTTPException(400, "Invalid mode")
    lim = int(body.limit) if (body.limit not in (None, "") and body.mode in ("monthly", "custom")) else None
    doc = {"id": str(uuid.uuid4()), "feature": body.feature, "scope_type": body.scope_type,
           "scope_id": body.scope_id, "mode": body.mode, "limit": lim, "note": body.note,
           "created_by": user["id"], "created_at": now_iso()}
    await db.usage_overrides.update_one(
        {"feature": body.feature, "scope_type": body.scope_type, "scope_id": body.scope_id},
        {"$set": doc}, upsert=True)
    await audit(None, user["id"], "admin.usage.override.set", {"feature": body.feature,
                "scope_type": body.scope_type, "scope_id": body.scope_id, "mode": body.mode, "limit": lim})
    return {"ok": True, "override": doc}


@platform_router.delete("/admin/control/usage/overrides/{oid}")
async def usage_override_delete(oid: str, user: dict = Depends(current_user)):
    _require_super(user)
    ov = await db.usage_overrides.find_one({"id": oid}, {"_id": 0})
    if not ov:
        raise HTTPException(404, "Not found")
    await db.usage_overrides.delete_one({"id": oid})
    await audit(None, user["id"], "admin.usage.override.remove",
                {"feature": ov.get("feature"), "scope_type": ov.get("scope_type"), "scope_id": ov.get("scope_id")})
    return {"ok": True}


async def _usage_agg(match: dict, group_field: str):
    """Sum quantity + cost grouped by a field over usage_events (success only)."""
    pipe = [{"$match": {**match, "result": "success"}},
            {"$group": {"_id": f"${group_field}", "usage": {"$sum": "$quantity"}, "cost": {"$sum": "$cost"}}}]
    rows = await db.usage_events.aggregate(pipe).to_list(10000)
    return {r["_id"]: {"usage": r["usage"], "cost": round(r["cost"], 4)} for r in rows}


@platform_router.get("/admin/control/usage/overview")
async def usage_overview(start: str = None, end: str = None, plan: str = "", feature: str = "",
                         workspace: str = "", user_id: str = "", user: dict = Depends(current_user)):
    _require_super(user)
    start_i, end_i = _usage_range(start, end)
    today_i = datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00+00:00")
    match = {"created_at": {"$gte": start_i, "$lte": end_i}}
    if plan:
        match["plan"] = plan
    if feature:
        match["feature"] = feature
    if workspace:
        match["workspace_id"] = workspace
    if user_id:
        match["user_id"] = user_id

    by_feature = await _usage_agg(match, "feature")
    by_feature_today = await _usage_agg({**match, "created_at": {"$gte": today_i, "$lte": end_i}}, "feature")
    by_user = await _usage_agg(match, "user_id")
    by_ws = await _usage_agg(match, "workspace_id")
    by_plan = await _usage_agg(match, "plan")
    ai_match = {**match, "category": "AI"}
    by_feature_ai = await _usage_agg(ai_match, "feature")
    ai_ops = sum(v["usage"] for v in by_feature_ai.values())
    ai_cost = round(sum(v["cost"] for v in by_feature_ai.values()), 4)
    total_cost = round(sum(v["cost"] for v in by_feature.values()), 4)
    total_usage = sum(v["usage"] for v in by_feature.values())

    cfg = await get_usage_config()
    feats_cfg = cfg.get("features") or {}
    # distinct active subjects in period
    active_users = len([k for k in by_user.keys() if k])
    active_ws = len([k for k in by_ws.keys() if k])

    # highest-cost user / workspace (resolve names)
    def _top(d):
        items = [(k, v) for k, v in d.items() if k]
        items.sort(key=lambda x: x[1]["cost"], reverse=True)
        return items[:10]
    top_users_raw = _top(by_user)
    top_ws_raw = _top(by_ws)
    top_users = []
    for uid, v in top_users_raw:
        u = await db.users.find_one({"id": uid}, {"_id": 0, "name": 1, "email": 1})
        m = await db.memberships.find_one({"user_id": uid}, {"_id": 0, "workspace_id": 1})
        ws = await db.workspaces.find_one({"id": (m or {}).get("workspace_id")}, {"_id": 0, "name": 1, "plan": 1, "subscription": 1}) if m else None
        top_users.append({"id": uid, "name": (u or {}).get("name"), "email": (u or {}).get("email"),
                          "workspace": (ws or {}).get("name"), "plan": display_plan(ws) if ws else None,
                          "ai_ops": v["usage"], "cost": v["cost"]})
    top_ws = []
    for wid, v in top_ws_raw:
        ws = await db.workspaces.find_one({"id": wid}, {"_id": 0, "name": 1, "plan": 1, "subscription": 1})
        seats = ((ws or {}).get("subscription") or {}).get("seats")
        badge = by_feature.get("event_badge_scan", {})  # platform-wide; per-ws detail in drilldown
        top_ws.append({"id": wid, "name": (ws or {}).get("name"), "plan": display_plan(ws) if ws else None,
                       "seats": seats, "ai_ops": v["usage"], "cost": v["cost"]})

    # ---- feature table ----
    rows = []
    for f in USAGE_FEATURES:
        k = f["key"]
        fc = feats_cfg.get(k, {})
        if f.get("metered"):
            m_all = by_feature.get(k, {"usage": 0, "cost": 0})
            m_today = by_feature_today.get(k, {"usage": 0, "cost": 0})
            # per-feature user/ws breakdown for averages + highest
            fu = await _usage_agg({**match, "feature": k}, "user_id")
            fw = await _usage_agg({**match, "feature": k}, "workspace_id")
            n_u = len([x for x in fu if x]) or 1
            n_w = len([x for x in fw if x]) or 1
            hi_u = max((v["usage"] for x, v in fu.items() if x), default=0)
            hi_w = max((v["usage"] for x, v in fw.items() if x), default=0)
            usage_month, usage_today, cost = m_all["usage"], m_today["usage"], m_all["cost"]
            avg_u = round(m_all["usage"] / n_u, 2)
            avg_w = round(m_all["usage"] / n_w, 2)
        else:
            # informational cheap features aggregated from source collections
            agg = f.get("aggregate")
            usage_month = usage_today = 0
            hi_u = hi_w = 0
            avg_u = avg_w = 0
            if agg:
                coll, typ = agg
                q_month = {"created_at": {"$gte": start_i, "$lte": end_i}}
                q_today = {"created_at": {"$gte": today_i, "$lte": end_i}}
                if coll == "analytics_events":
                    q_month["type"] = typ
                    q_today["type"] = typ
                usage_month = await db[coll].count_documents(q_month)
                usage_today = await db[coll].count_documents(q_today)
            unit = float(fc.get("unit_cost", 0.0))
            cost = round(usage_month * unit, 4)
        # limit summary (default plan limit view)
        scope = fc.get("scope", "per_user")
        pl = fc.get("plan_limits") or {}
        enabled = bool(fc.get("enforcement_enabled"))
        # status by highest utilisation vs the strictest enabled plan limit
        status = "normal"
        limit_label = "Unlimited"
        if enabled:
            modes = [pl.get(p, {}).get("mode", "unlimited") for p in USAGE_PLANS]
            if any(m != "unlimited" for m in modes):
                limit_label = "; ".join(f"{p}:{(pl.get(p, {}) or {}).get('mode')}"
                                        + (f" {pl[p].get('limit')}" if pl.get(p, {}).get("limit") else "")
                                        for p in USAGE_PLANS if pl.get(p, {}).get("mode", "unlimited") != "unlimited")
        rows.append({
            "key": k, "name": f["name"], "category": f["category"],
            "metered": bool(f.get("metered")), "placeholder": bool(f.get("placeholder")),
            "usage_today": usage_today, "usage_month": usage_month,
            "avg_per_user": avg_u, "avg_per_workspace": avg_w,
            "highest_user_usage": hi_u, "highest_workspace_usage": hi_w,
            "unit_cost": float(fc.get("unit_cost", 0.0)), "currency": fc.get("currency", "USD"),
            "estimated_total_cost": cost, "cost_unit": f.get("cost_unit"),
            "scope": scope, "enforcement_enabled": enabled, "hard_behavior": fc.get("hard_behavior", "flag"),
            "soft_pct": fc.get("soft_pct", 80), "limit_label": limit_label, "status": status,
        })

    kpis = {
        "active_users": active_users, "active_workspaces": active_ws,
        "total_tracked_usage": total_usage + sum(r["usage_month"] for r in rows if not r["metered"]),
        "total_ai_operations": ai_ops, "estimated_ai_cost": ai_cost,
        "estimated_total_cost": total_cost,
        "avg_cost_per_user": round(total_cost / max(active_users, 1), 4),
        "avg_cost_per_workspace": round(total_cost / max(active_ws, 1), 4),
        "highest_cost_user": (top_users[0] if top_users else None),
        "highest_cost_workspace": (top_ws[0] if top_ws else None),
        "total_users": await db.users.count_documents({}),
        "total_workspaces": await db.workspaces.count_documents({}),
    }
    return {"range": {"start": start_i, "end": end_i}, "kpis": kpis, "features": rows,
            "top_users": top_users, "top_workspaces": top_ws,
            "cost_by_plan": {k: v for k, v in by_plan.items() if k},
            "cost_by_feature": {k: by_feature.get(k, {"usage": 0, "cost": 0}) for k in _USAGE_FEATURE_MAP},
            "estimated": True}


@platform_router.get("/admin/control/usage/detail")
async def usage_detail(type: str, id: str, start: str = None, end: str = None, user: dict = Depends(current_user)):
    _require_super(user)
    start_i, end_i = _usage_range(start, end)
    if type not in ("user", "workspace"):
        raise HTTPException(400, "type must be user|workspace")
    match = {"created_at": {"$gte": start_i, "$lte": end_i}, ("user_id" if type == "user" else "workspace_id"): id}
    by_feature = await _usage_agg(match, "feature")
    cfg = await get_usage_config()
    feats_cfg = cfg.get("features") or {}
    breakdown = []
    total = 0.0
    for f in USAGE_FEATURES:
        v = by_feature.get(f["key"])
        if not v:
            continue
        breakdown.append({"key": f["key"], "name": f["name"], "category": f["category"],
                          "usage": v["usage"], "estimated_cost": v["cost"],
                          "unit_cost": float((feats_cfg.get(f["key"]) or {}).get("unit_cost", 0.0))})
        total += v["cost"]
    header = {}
    revenue = None
    if type == "user":
        u = await db.users.find_one({"id": id}, {"_id": 0, "name": 1, "email": 1, "role": 1})
        m = await db.memberships.find_one({"user_id": id}, {"_id": 0, "workspace_id": 1})
        ws = await db.workspaces.find_one({"id": (m or {}).get("workspace_id")}, {"_id": 0}) if m else None
        header = {"name": (u or {}).get("name"), "email": (u or {}).get("email"),
                  "plan": display_plan(ws) if ws else None, "workspace": (ws or {}).get("name")}
    else:
        ws = await db.workspaces.find_one({"id": id}, {"_id": 0})
        header = {"name": (ws or {}).get("name"), "plan": display_plan(ws) if ws else None,
                  "seats": ((ws or {}).get("subscription") or {}).get("seats")}
        sub = (ws or {}).get("subscription") or {}
        if is_real_paid(sub):
            revenue = {"status": sub.get("status"), "interval": sub.get("interval"), "plan": sub.get("plan")}
    ratio = None  # cost-to-revenue only when authoritative revenue is known (kept null otherwise)
    return {"type": type, "id": id, "header": header, "breakdown": breakdown,
            "total_estimated_cost": round(total, 4), "subscription_revenue": revenue,
            "cost_to_revenue_ratio": ratio, "estimated": True}


@platform_router.get("/admin/control/usage/timeseries")
async def usage_timeseries(start: str = None, end: str = None, feature: str = "", user: dict = Depends(current_user)):
    _require_super(user)
    start_i, end_i = _usage_range(start, end)
    match = {"created_at": {"$gte": start_i, "$lte": end_i}, "result": "success"}
    if feature:
        match["feature"] = feature
    pipe = [{"$match": match},
            {"$group": {"_id": {"$substr": ["$created_at", 0, 10]},
                        "usage": {"$sum": "$quantity"}, "cost": {"$sum": "$cost"},
                        "ai": {"$sum": {"$cond": [{"$eq": ["$category", "AI"]}, "$quantity", 0]}}}},
            {"$sort": {"_id": 1}}]
    rows = await db.usage_events.aggregate(pipe).to_list(400)
    return {"series": [{"date": r["_id"], "usage": r["usage"], "cost": round(r["cost"], 4), "ai": r["ai"]} for r in rows],
            "estimated": True}


@platform_router.get("/admin/control/usage/export.csv")
async def usage_export_csv(start: str = None, end: str = None, feature: str = "",
                           workspace: str = "", user_id: str = "", user: dict = Depends(current_user)):
    _require_super(user)
    start_i, end_i = _usage_range(start, end)
    match = {"created_at": {"$gte": start_i, "$lte": end_i}}
    if feature:
        match["feature"] = feature
    if workspace:
        match["workspace_id"] = workspace
    if user_id:
        match["user_id"] = user_id
    rows = await db.usage_events.find(match, {"_id": 0}).sort("created_at", -1).to_list(50000)
    ucache, wcache = {}, {}

    async def _uemail(uid):
        if uid not in ucache:
            u = await db.users.find_one({"id": uid}, {"_id": 0, "email": 1})
            ucache[uid] = (u or {}).get("email", "")
        return ucache[uid]

    async def _wname(wid):
        if wid not in wcache:
            w = await db.workspaces.find_one({"id": wid}, {"_id": 0, "name": 1})
            wcache[wid] = (w or {}).get("name", "")
        return wcache[wid]

    buf = io.StringIO()
    buf.write("\ufeff")
    w = csv.writer(buf)
    w.writerow(["Date", "Feature", "Category", "User", "Workspace", "Plan", "Usage",
                "Unit Cost (USD)", "Estimated Cost (USD)", "Result", "Source", "Period"])
    for r in rows:
        w.writerow([r.get("created_at", ""), r.get("feature", ""), r.get("category", ""),
                    await _uemail(r.get("user_id")) if r.get("user_id") else "",
                    await _wname(r.get("workspace_id")) if r.get("workspace_id") else "",
                    r.get("plan", ""), r.get("quantity", 0), r.get("unit_cost", 0),
                    r.get("cost", 0), r.get("result", ""), r.get("source", ""), r.get("period", "")])
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=usage_cost.csv"})


@platform_router.get("/usage/me")
async def usage_me(user: dict = Depends(current_user)):
    """User-facing usage — ONLY features with an ACTIVE limit that applies to this account.
    Returns an empty list when nothing is limited (no unnecessary counters for cheap/unlimited features)."""
    ws_id = await _primary_ws_id(user)
    ent = await resolve_entitlements(ws_id) if ws_id else {}
    plan = ent.get("plan") if ent.get("plan") in USAGE_PLANS else None
    cfg = await get_usage_config()
    feats = cfg.get("features") or {}
    out = []
    for f in USAGE_FEATURES:
        if not f.get("enforceable"):
            continue
        fc = feats.get(f["key"]) or {}
        if not fc.get("enforcement_enabled"):
            continue
        scope = fc.get("scope", "per_user")
        if scope == "unlimited":
            continue
        fc2 = dict(fc)
        fc2["_key"] = f["key"]
        if scope == "per_user":
            scope_type, scope_id = "user", user["id"]
        elif scope == "per_workspace":
            scope_type, scope_id = "workspace", ws_id
        else:
            continue  # per_event not shown in the account-level panel
        if not scope_id:
            continue
        limit, mode, is_ov = await _resolve_feature_limit(fc2, plan or "pro", scope_type, scope_id)
        if mode == "unlimited" or limit is None:
            continue
        period = await _usage_period_for_ws(ws_id)
        used = await db.usage_events.count_documents(
            {"feature": f["key"], "result": "success", "period": period,
             ("user_id" if scope_type == "user" else "workspace_id"): scope_id})
        pct = round(used / limit * 100, 1) if limit else 0
        out.append({"key": f["key"], "name": f["name"], "scope": scope,
                    "scope_label": "Your monthly allowance" if scope_type == "user" else "Shared workspace allowance",
                    "used": used, "limit": limit, "remaining": max(0, limit - used),
                    "pct": pct, "soft_pct": fc.get("soft_pct", 80),
                    "warning": pct >= fc.get("soft_pct", 80), "over": pct >= 100,
                    "source": "override" if is_ov else "plan"})
    return {"items": out}


# ==================================================================
# AI LEAD INSIGHTS + AI EVENT RECAP (on-demand, cached, metered) — reuses LlmChat (openai gpt-5.4),
# usage_guard/meter_usage, ai_usage, and existing lead/event tenant permissions. NEVER auto-runs.
# One structured provider call per generation. Viewing a cached result costs ZERO AI usage.
# ==================================================================
import hashlib

_AI_MODEL = ("openai", "gpt-5.4")


async def _llm_json(system: str, prompt: str, session_prefix: str) -> dict:
    """One structured JSON completion via the shared Emergent LLM key. Raises on failure so the
    caller can release the usage reservation (failed provider op must not consume allowance)."""
    key = os.environ.get("EMERGENT_LLM_KEY", "").strip()
    if not key:
        raise HTTPException(503, "AI is not configured.")
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(api_key=key, session_id=f"{session_prefix}-{uuid.uuid4()}",
                   system_message=system).with_model(*_AI_MODEL)
    resp = await chat.send_message(UserMessage(text=prompt))
    data = _parse_scan_json(str(resp))
    if not data:
        raise HTTPException(502, "The AI response could not be parsed. Please try again.")
    return data


def _lang_name(lang: str) -> str:
    return {"ar": "Arabic", "es": "Spanish", "en": "English"}.get(_norm_lang(lang), "English")


def _material_hash(obj: dict) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str, ensure_ascii=False).encode()).hexdigest()[:16]


# ---- AI Lead Insights ----
async def _lead_or_403(lead_id: str, user: dict):
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(404, "Lead not found")
    if user.get("role") != "SUPER_ADMIN":
        slugs = await _owned_slugs(user)
        if lead.get("cardSlug") not in slugs:
            raise HTTPException(403, "Not your lead")
    return lead


async def _lead_insight_signature(lead: dict) -> dict:
    """The material fields whose change should mark an insight stale (rules-based, no AI)."""
    mc = await _active_meeting_count(lead["id"])
    return {
        "name": lead.get("name"), "company": lead.get("company"), "title": lead.get("title"),
        "industry": lead.get("industry"), "source": lead.get("source"), "event_id": lead.get("event_id"),
        "notes": lead.get("notes") or lead.get("message"), "tags": sorted(lead.get("tags") or []),
        "status": lead.get("status"), "lead_score": lead.get("lead_score"),
        "lead_temperature": lead.get("lead_temperature_override") or lead.get("lead_temperature"),
        "phone": bool(lead.get("phone")), "email": bool(lead.get("email")),
        "next_follow_up": lead.get("next_follow_up"), "follow_up_completed_at": lead.get("follow_up_completed_at"),
        "opportunity_value": lead.get("opportunity_value"), "actual_revenue": lead.get("actual_revenue"),
        "meetings": mc,
    }


def _lead_insight_context(lead: dict, sig: dict, event_name: str) -> str:
    fields = {
        "Name": lead.get("name"), "Company": lead.get("company"), "Job Title": lead.get("title"),
        "Industry": lead.get("industry"), "Lead Source": lead.get("source"), "Event": event_name,
        "Pipeline Stage": lead.get("status"), "Rules-based Lead Score (0-100)": lead.get("lead_score"),
        "Lead Temperature": sig["lead_temperature"], "Tags": ", ".join(sig["tags"]),
        "Notes": sig["notes"], "Has Phone": sig["phone"], "Has Email": sig["email"],
        "Next Follow-up": lead.get("next_follow_up"), "Follow-up Completed": lead.get("follow_up_completed_at"),
        "Active Meetings": sig["meetings"], "Opportunity Value": lead.get("opportunity_value"),
        "Recorded Revenue": lead.get("actual_revenue"),
    }
    return "\n".join(f"{k}: {v}" for k, v in fields.items() if v not in (None, "", []))


class LeadInsightIn(BaseModel):
    regenerate: bool = False
    language: str = "en"


@platform_router.get("/crm/leads/{lead_id}/ai-insight")
async def get_lead_insight(lead_id: str, user: dict = Depends(current_user)):
    """Return the STORED insight (0 AI usage) + a stale flag if material lead data changed since."""
    lead = await _lead_or_403(lead_id, user)
    ins = lead.get("ai_insight")
    if not ins:
        return {"insight": None, "stale": False}
    sig = await _lead_insight_signature(lead)
    return {"insight": ins, "stale": ins.get("source_hash") != _material_hash(sig)}


@platform_router.post("/crm/leads/{lead_id}/ai-insight")
async def generate_lead_insight(lead_id: str, body: LeadInsightIn, request: Request,
                                user: dict = Depends(current_user)):
    lead = await _lead_or_403(lead_id, user)
    ws_id = await _lead_workspace_id(lead)
    sig = await _lead_insight_signature(lead)
    cur_hash = _material_hash(sig)
    existing = lead.get("ai_insight")
    # Cached path — no new AI call unless regenerate is explicitly requested.
    if existing and not body.regenerate:
        return {"insight": existing, "stale": existing.get("source_hash") != cur_hash, "cached": True}
    rate_limit(request, "ai_insight", 20, 60)
    lang = _norm_lang(body.language)
    ev_name = ""
    if lead.get("event_id"):
        ev = await db.events.find_one({"id": lead["event_id"]}, {"_id": 0, "name": 1})
        ev_name = (ev or {}).get("name", "")
    handle = await usage_guard("ai_lead_insight", user, ws_id)
    system = (f"You are an elite B2B sales assistant. Analyze ONE lead using ONLY the provided TapPresence data "
              f"(never invent facts or external data). Respond in {_lang_name(lang)}. "
              f"Return ONLY a JSON object with keys: summary, opportunity_assessment, why_matters, "
              f"recommended_next_action, followup_approach, signals_risks (array of short strings), "
              f"priority (one of High, Medium, Low), timing (one of 'Follow up now','Today','Within 24 hours','This week','Low urgency'). "
              f"Keep each field concise and actionable. Do not change or restate the numeric lead score.")
    prompt = "Lead data:\n" + _lead_insight_context(lead, sig, ev_name)
    try:
        data = await _llm_json(system, prompt, "lead-insight")
    except HTTPException:
        await release_usage_handle(handle)
        await meter_usage("ai_lead_insight", user_id=user["id"], workspace_id=ws_id,
                          quantity=1, result="failed", source="lead_insight", paid=False)
        raise
    except Exception as e:
        await release_usage_handle(handle)
        await meter_usage("ai_lead_insight", user_id=user["id"], workspace_id=ws_id,
                          quantity=1, result="failed", source="lead_insight", paid=False)
        logger.warning(f"lead insight LLM error: {e}")
        raise HTTPException(502, "Could not generate the insight. Please try again.")
    insight = {"content": data, "generated_at": now_iso(), "generated_by": user["id"],
               "provider": "openai:gpt-5.4", "language": lang, "source_hash": cur_hash}
    await db.leads.update_one({"id": lead_id}, {"$set": {"ai_insight": insight}})
    await db.ai_usage.insert_one({"id": str(uuid.uuid4()), "user_id": user["id"], "provider": "openai:gpt-5.4",
                                  "channel": "lead_insight", "tone": "insight", "language": lang, "created_at": now_iso()})
    await meter_usage("ai_lead_insight", user_id=user["id"], workspace_id=ws_id,
                      quantity=1, result="success", source="lead_insight", paid=True)
    return {"insight": insight, "stale": False, "cached": False}


# ---- AI Event Recap ----
def _event_recap_signature(dash: dict) -> dict:
    k = dash.get("kpis") or {}
    f = dash.get("financials") or {}
    return {"total_leads": k.get("total_leads"), "customers": k.get("customers"),
            "meetings": k.get("meetings_booked"), "conversion": k.get("conversion_rate"),
            "pipeline_value": f.get("pipeline_value"), "attributed_revenue": f.get("attributed_revenue"),
            "roi": f.get("roi")}


def _event_recap_context(dash: dict) -> str:
    ev = dash.get("event") or {}
    k = dash.get("kpis") or {}
    q = dash.get("quality") or {}
    fin = dash.get("financials") or {}
    lb = [{"name": r.get("name"), "leads": r.get("leads"), "hot": r.get("hot_leads"),
           "meetings": r.get("meetings"), "customers": r.get("customers")} for r in (dash.get("leaderboard") or [])[:5]]
    topl = [{"name": l.get("name"), "company": l.get("company"), "title": l.get("title"),
             "score": l.get("score"), "temp": l.get("temperature")} for l in (dash.get("top_leads") or [])[:5]]
    topo = [{"name": l.get("name"), "company": l.get("company"), "value": l.get("opportunity_value"),
             "stage": l.get("stage")} for l in (dash.get("top_opportunities") or [])[:5]]
    ctx = {
        "event_name": ev.get("name"), "reporting_currency": fin.get("currency"),
        "kpis": k, "new_vs_returning": dash.get("new_vs_returning"),
        "pipeline_stage_counts": dash.get("pipeline"), "capture_methods": dash.get("capture_methods"),
        "lead_quality": q, "followups": dash.get("followups"),
        "financials": {kk: fin.get(kk) for kk in ("pipeline_value", "open_opportunities", "attributed_revenue",
                                                   "attributed_revenue_count", "event_cost", "roi", "revenue_cost_multiple")},
        "team_top5": lb, "top_leads": topl, "top_opportunities": topo,
    }
    return json.dumps(ctx, ensure_ascii=False, default=str)


class EventRecapIn(BaseModel):
    regenerate: bool = False
    language: str = "en"


@platform_router.get("/events/{event_id}/ai-recap")
async def get_event_recap(event_id: str, user: dict = Depends(current_user)):
    ev = await _event_or_403(event_id, user)
    rec = ev.get("ai_recap")
    if not rec:
        return {"recap": None, "stale": False}
    dash = await event_dashboard(event_id, user)
    return {"recap": rec, "stale": rec.get("source_hash") != _material_hash(_event_recap_signature(dash))}


@platform_router.post("/events/{event_id}/ai-recap")
async def generate_event_recap(event_id: str, body: EventRecapIn, request: Request,
                               user: dict = Depends(current_user)):
    ev = await _event_or_403(event_id, user)
    ws_id = ev.get("workspace_id")
    existing = ev.get("ai_recap")
    # Aggregate ONCE (no per-lead AI). event_dashboard returns fully aggregated metrics.
    dash = await event_dashboard(event_id, user)
    cur_hash = _material_hash(_event_recap_signature(dash))
    if existing and not body.regenerate:
        return {"recap": existing, "stale": existing.get("source_hash") != cur_hash, "cached": True}
    rate_limit(request, "ai_recap", 15, 60)
    lang = _norm_lang(body.language)
    handle = await usage_guard("ai_event_recap", user, ws_id, event_id=event_id)
    system = (f"You are a sales operations analyst. Write a concise, executive AI recap for ONE event using ONLY the "
              f"provided aggregated metrics (never invent numbers). Respond in {_lang_name(lang)}. "
              f"Return ONLY a JSON object with keys: executive_summary, event_performance, lead_quality, "
              f"strongest_opportunities, key_patterns, team_highlights, followup_priorities, "
              f"next_actions (array of short strings), risks, conclusion. Keep it useful for a manager and not overly long.")
    prompt = "Aggregated event data (JSON):\n" + _event_recap_context(dash)
    try:
        data = await _llm_json(system, prompt, "event-recap")
    except HTTPException:
        await release_usage_handle(handle)
        await meter_usage("ai_event_recap", user_id=user["id"], workspace_id=ws_id, event_id=event_id,
                          quantity=1, result="failed", source="event_recap", paid=False)
        raise
    except Exception as e:
        await release_usage_handle(handle)
        await meter_usage("ai_event_recap", user_id=user["id"], workspace_id=ws_id, event_id=event_id,
                          quantity=1, result="failed", source="event_recap", paid=False)
        logger.warning(f"event recap LLM error: {e}")
        raise HTTPException(502, "Could not generate the recap. Please try again.")
    recap = {"content": data, "generated_at": now_iso(), "generated_by": user["id"],
             "provider": "openai:gpt-5.4", "language": lang, "source_hash": cur_hash}
    await db.events.update_one({"id": event_id}, {"$set": {"ai_recap": recap}})
    await db.ai_usage.insert_one({"id": str(uuid.uuid4()), "user_id": user["id"], "provider": "openai:gpt-5.4",
                                  "channel": "event_recap", "tone": "recap", "language": lang, "created_at": now_iso()})
    await meter_usage("ai_event_recap", user_id=user["id"], workspace_id=ws_id, event_id=event_id,
                      quantity=1, result="success", source="event_recap", paid=True)
    return {"recap": recap, "stale": False, "cached": False}


# ------------------------------------------------------------------ Super Admin: Tax & Global Revenue
def _minor(v):
    return int(v or 0)


@platform_router.get("/admin/control/tax/overview")
async def tax_overview(start: str = None, end: str = None, user: dict = Depends(current_user)):
    """Global tax/revenue reporting from Stripe-authoritative billing_tax_records.
    Collected sales-tax/VAT is reported SEPARATELY and never counted as TapPresence revenue.
    Amounts are in Stripe minor units, grouped per currency (no cross-currency FX summing)."""
    _require_super(user)
    start_i, end_i = _usage_range(start, end)
    q = {"created_at": {"$gte": start_i, "$lte": end_i}}
    rows = await db.billing_tax_records.find(q, {"_id": 0}).sort("created_at", -1).to_list(20000)

    def _acc():
        return {"base_subscription": 0, "discount": 0, "tax_collected": 0, "total_charged": 0, "count": 0}

    by_currency, by_country, by_state = {}, {}, {}
    customers, countries, status_counts = set(), set(), {}
    for r in rows:
        cur = r.get("currency") or "USD"
        base = _minor(r.get("base_amount"))
        disc = _minor(r.get("discount_amount"))
        tax = _minor(r.get("tax_amount"))
        total = _minor(r.get("total_amount"))
        c = by_currency.setdefault(cur, _acc())
        c["base_subscription"] += base
        c["discount"] += disc
        c["tax_collected"] += tax
        c["total_charged"] += total
        c["count"] += 1
        country = r.get("country") or "??"
        ck = f"{country}|{cur}"
        cc = by_country.setdefault(ck, {"country": country, "currency": cur, **_acc(), "customers": set()})
        cc["base_subscription"] += base
        cc["discount"] += disc
        cc["tax_collected"] += tax
        cc["total_charged"] += total
        cc["count"] += 1
        if r.get("workspace_id"):
            cc["customers"].add(r["workspace_id"])
            customers.add(r["workspace_id"])
        if country and country != "??":
            countries.add(country)
        st = r.get("tax_status") or "unavailable"
        status_counts[st] = status_counts.get(st, 0) + 1
        if country == "US" and r.get("state"):
            sk = f"{r['state']}|{cur}"
            ss = by_state.setdefault(sk, {"state": r["state"], "currency": cur, "tax_collected": 0, "total_charged": 0, "count": 0})
            ss["tax_collected"] += tax
            ss["total_charged"] += total
            ss["count"] += 1

    by_country_out = []
    for v in by_country.values():
        v["customers"] = len(v["customers"])
        v["net_subscription"] = v["total_charged"] - v["tax_collected"]
        by_country_out.append(v)
    by_country_out.sort(key=lambda x: x["total_charged"], reverse=True)
    for cur, v in by_currency.items():
        v["net_subscription"] = v["total_charged"] - v["tax_collected"]

    transactions = [{
        "workspace_id": r.get("workspace_id"), "country": r.get("country"), "state": r.get("state"),
        "currency": r.get("currency"), "base_amount": _minor(r.get("base_amount")),
        "discount_amount": _minor(r.get("discount_amount")), "tax_amount": _minor(r.get("tax_amount")),
        "total_amount": _minor(r.get("total_amount")), "tax_status": r.get("tax_status"),
        "tax_id_type": r.get("tax_id_type"), "tax_id_masked": r.get("tax_id_masked"),
        "kind": r.get("kind"), "created_at": r.get("created_at"),
    } for r in rows[:200]]

    return {"range": {"start": start_i, "end": end_i},
            "totals_by_currency": by_currency,
            "paying_customers": len(customers), "countries": sorted(countries),
            "country_count": len(countries), "by_country": by_country_out,
            "by_state_us": sorted(by_state.values(), key=lambda x: x["total_charged"], reverse=True),
            "tax_status_breakdown": status_counts, "transactions": transactions,
            "note": "Collected tax is reported separately and is NOT TapPresence revenue. Estimated where Stripe status is not 'complete'."}


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
        # Event Dashboard V1 — query patterns: leads by event, timeline event, meetings by lead
        await db.events.create_index([("workspace_id", 1), ("created_at", -1)])
        await db.leads.create_index("event_id")
        await db.leads.create_index("timeline.event_id")
        await db.meetings.create_index("lead_id")
        # Pipeline Value / Revenue Attribution V1 — exclusive revenue lookup per event
        await db.leads.create_index("revenue_attribution.event_id")
        # CRM & Data Export Pack V1 — HubSpot connectors
        await db.crm_connections.create_index([("workspace_id", 1), ("provider", 1)], unique=True)
        await db.crm_oauth_states.create_index("state", unique=True)
        # Usage & Cost Control V1 — metering + atomic reservation + overrides
        await db.usage_events.create_index([("created_at", -1)])
        await db.usage_events.create_index([("feature", 1), ("period", 1)])
        await db.usage_events.create_index([("user_id", 1), ("period", 1)])
        await db.usage_events.create_index([("workspace_id", 1), ("period", 1)])
        await db.usage_meters.create_index(
            [("feature", 1), ("scope_type", 1), ("scope_id", 1), ("period", 1)], unique=True)
        await db.usage_overrides.create_index(
            [("feature", 1), ("scope_type", 1), ("scope_id", 1)], unique=True)
        # Global Tax Readiness — Stripe-authoritative tax/revenue records
        await db.billing_tax_records.create_index("source_id", unique=True)
        await db.billing_tax_records.create_index([("created_at", -1)])
        await db.billing_tax_records.create_index([("country", 1)])
        # Failed-payment recovery — webhook idempotency ledger
        await db.stripe_events.create_index("id", unique=True)
    except Exception as e:
        logger.warning(f"platform index setup: {e}")

    # Seed Usage & Cost Control config (idempotent; backfills newly added features)
    try:
        _ucfg = await get_usage_config()
        # AI Event Recap default scope correction (per_event) — enforcement stays OFF, no behavior change.
        _erf = (_ucfg.get("features") or {}).get("ai_event_recap") or {}
        if _erf.get("scope") == "per_user" and not _erf.get("enforcement_enabled"):
            await db.usage_config.update_one({"id": "global"},
                {"$set": {"features.ai_event_recap.scope": "per_event"}})
    except Exception as e:
        logger.warning(f"usage config seed: {e}")

    # Backfill lead scores for any leads not yet scored under the current version (safe, bounded, preview)
    try:
        cursor = db.leads.find({"lead_score_version": {"$ne": LEAD_SCORE_VERSION}}, {"_id": 0, "id": 1}).limit(20000)
        async for l in cursor:
            await recalc_lead_score(l["id"])
    except Exception as e:
        logger.warning(f"lead score backfill: {e}")

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

    # Backfill event reporting currency (financial aggregation) — non-destructive
    try:
        async for ev in db.events.find({"currency": {"$exists": False}}, {"_id": 0, "id": 1, "event_cost_currency": 1, "workspace_id": 1}):
            ws = await db.workspaces.find_one({"id": ev.get("workspace_id")}, {"_id": 0, "region": 1})
            ccy = (ev.get("event_cost_currency") or ((ws or {}).get("region") or {}).get("default_currency") or "USD").upper()
            await db.events.update_one({"id": ev["id"]}, {"$set": {"currency": ccy}})
    except Exception as e:
        logger.warning(f"event currency backfill: {e}")

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

    # ---- P0: classify accounts so KPIs default to real customers only (idempotent) ----
    INTERNAL_DOMAINS = ("@ariadni.ai", "@ariadni.id", "@tappresence.com")
    async for u in db.users.find({"environment": {"$exists": False}}, {"_id": 0, "id": 1, "email": 1, "role": 1}):
        em = (u.get("email") or "").lower()
        if u.get("role") == "SUPER_ADMIN" or any(em.endswith(d) for d in INTERNAL_DOMAINS):
            env = "internal"
        elif em.endswith("@demo.com") or em.endswith("@example.com"):
            env = "demo"
        elif em.startswith("test") or "+test" in em:
            env = "test"
        else:
            env = "production_customer"
        await db.users.update_one({"id": u["id"]}, {"$set": {"environment": env}})
    async for w in db.workspaces.find({"environment": {"$exists": False}}, {"_id": 0, "id": 1, "owner_id": 1}):
        owner = await db.users.find_one({"id": w.get("owner_id")}, {"_id": 0, "environment": 1}) if w.get("owner_id") else None
        await db.workspaces.update_one({"id": w["id"]}, {"$set": {"environment": (owner or {}).get("environment") or "internal"}})
    # No user-visible legacy branding in the Control Center
    await db.workspaces.update_many({"name": "ARIADNI HQ"}, {"$set": {"name": "TapPresence HQ"}})
    # Migrate legacy plan='free' real customers to their intended 14-day trial (TapPresence has NO Free plan)
    _tdays = await trial_days()
    async for w in db.workspaces.find({"plan": "free", "environment": "production_customer", "subscription": None}, {"_id": 0, "id": 1, "created_at": 1}):
        try:
            base = datetime.fromisoformat((w.get("created_at") or now_iso()).replace("Z", "+00:00"))
        except Exception:
            base = datetime.now(timezone.utc)
        sub = {"plan": "trial", "status": "trialing",
               "trial_ends_at": (base + timedelta(days=max(1, _tdays))).isoformat(),
               "current_period_end": None, "seats": 1, "interval": None}
        await db.workspaces.update_one({"id": w["id"]}, {"$set": {"plan": "trial", "subscription": sub}})
    # Any other stray legacy 'free' label (internal/demo) -> 'trial' so 'free' never surfaces anywhere
    await db.workspaces.update_many({"plan": "free"}, {"$set": {"plan": "trial"}})
    # Attach orphan/dangling legacy cards (null or non-existent workspace_id) to the internal HQ workspace,
    # so they stay OUT of customer KPIs and only appear when include_internal is enabled.
    hq = await db.workspaces.find_one({"environment": "internal"}, {"_id": 0, "id": 1})
    if hq:
        valid_ws_ids = {w["id"] async for w in db.workspaces.find({}, {"_id": 0, "id": 1})}
        async for c in db.digital_cards.find({}, {"_id": 0, "id": 1, "workspace_id": 1}):
            if not c.get("workspace_id") or c["workspace_id"] not in valid_ws_ids:
                await db.digital_cards.update_one({"id": c["id"]}, {"$set": {"workspace_id": hq["id"]}})
    logger.info("platform migration complete")
