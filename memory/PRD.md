# ARIADNI ID — Product Requirements & Build Log

## Original Problem Statement
Data-driven digital business-card template engine. React + FastAPI + MongoDB. Three premium,
mobile-first public profile templates rendering from ONE shared `CardData` contract — no
per-customer hard-coded files. Sections shared across all templates: Hero, Actions, Services,
Projects, Main CTA, Save Contact + QR, Footer.

## User Choices (locked)
- Build **Template 03 Beige Luxury Executive** first as the reference engine.
- **Built-in object storage** (Emergent) for image uploads — no Cloudinary keys.
- **Seed a polished demo profile**.
- **Include a simple admin editor** (JWT auth).
- Public demo slug: **feras-askar** → public URL `/feras-askar`. QR points to the same URL.

## Architecture
- **Backend** (`/app/backend/server.py`): FastAPI, MongoDB (uuid string `id`, not ObjectId).
  - Public: `GET /api/cards/{slug}` (published only), `/vcard` (dynamic VCF), `/qr` (dynamic PNG).
  - Auth (JWT/bcrypt): `POST /api/auth/login`, `GET /api/auth/me`.
  - Admin (Bearer-gated): `GET/POST /api/admin/cards`, `GET/PUT/DELETE /api/admin/cards/{id}`.
  - Uploads: `POST /api/upload`, `GET /api/files/{path}` (Emergent object storage).
  - Startup seeds admin + demo card (`seed_data.py`), creates indexes.
- **Frontend** (React JS, CRACO, `@` alias):
  - `TemplateRenderer` switches by `templateId` → `BeigeLuxuryExecutive` / `ExecutiveBlackGold` / `FutureProfessional`.
  - Shared building blocks: `ActionButton`, `ServiceCard` logic, `ProjectRow`, `QRBlock`,
    `SaveContactButton`, `SocialIcons`, `AvailabilityBadge`; helpers in `lib/cardHelpers.js`.
  - Routes: `/` → `/feras-askar`, `/:slug` public, `/login`, `/admin` (protected).
  - Admin editor: tabbed form (Identity/Contact/Social/Services/Projects/Booking), image upload,
    template switch, publish toggle, and a **live preview** of the actual template.

## Data Contract — CardData
`slug, templateId, accent, status` + `identity{}`, `contact{}`, `social{}`, `actions[]`,
`services[]`, `projects[]`, `booking{}`. Empty social/contact fields simply don't render.

## Implemented (2026-06-08)
- All 3 premium templates, data-driven, verified visually + E2E (14/14 backend, frontend 100%).
- Dynamic VCF + QR generation in sync with the DB.
- Emergent object-storage image uploads for photos/covers.
- JWT admin editor with live preview and full card CRUD.
- Seeded published demo profile `feras-askar` (Beige Luxury).

## Implemented — Iteration 2 (2026-06-08)
- **Lead Capture**: themed inquiry form on every profile → `POST /api/cards/{slug}/leads`; admin **Inbox** dialog (list, mark-read, delete) with unread badge.
- **Profile Analytics**: view/scan/tap tracking (`POST /api/cards/{slug}/track`, scans via QR `?src=qr`); admin **Analytics** dialog shows views, scans, taps-by-action, inquiries.
- **Accent Variants**: `accent` (gold/platinum/rose) selectable per card in the editor; each template recolors via CSS-var accents without layout change (`lib/accents.js`).
- **Share Card**: one-tap Web Share / copy-link + downloadable branded **QR poster** PNG (`GET /api/cards/{slug}/poster`).
- QA: 13/13 new backend tests + frontend flows 100%.

## Commercial V1 — Phase 1 foundation (2026-06-08, iteration 3)
Extended (not replaced) the existing app into a multi-tenant commercial platform. 62/62 backend tests pass. feras-askar preserved.
- **Accounts/Workspaces/Roles**: register/verify/refresh(rotating)/forgot/reset/session/logout; SUPER_ADMIN + WORKSPACE_OWNER etc; workspaces + memberships. Existing admin promoted to SUPER_ADMIN ("ARIADNI HQ", enterprise).
- **Entitlements/Plans**: PLAN_ENTITLEMENTS (free/pro/team/enterprise/white_label); admin-configurable plans; `/api/plans`, `/api/config` feature flags.
- **Multi-tenancy enforced** (Section 42): card + lead endpoints workspace-scoped; verified isolation (403 cross-tenant).
- **NFC token system** (Phase 4 backend): mint inventory, permanent `/api/t/{token}` redirect (unactivated→/activate, active→/{slug}?src=nfc + nfctap analytics), activate/deactivate/lost lifecycle.
- **CRM + Contact Exchange** (Phase 6 backend): unified leads w/ status/tags/notes/follow-up/source/campaign, activities, CSV export, mutual `/exchange`, notifications.
- **Campaigns/Attribution** (Phase 20 backend): campaign CRUD + stats + `?campaign=`/`?src=` support.
- **AI follow-up** (Phase 13): provider-abstracted draft generator (template provider live; EMERGENT_LLM_KEY available to wire an LLM). AI never auto-sends. Enrichment adapter returns Not Configured.
- **Config adapters** for Stripe/Apple+Google Wallet/OAuth/email/CRM/RevenueCat/push/Sentry — all report `configured:false` until creds supplied; nothing blocks.
- **Web surfaces**: repositioned landing (Meet·Connect·Follow Up·Convert with live profile mockup + pricing), self-service /register, /activate (NFC), /legal placeholders.

## Remaining V1 phases (queued, not yet built)
Native mobile app (Phase 3); Wallet pass generation wiring (5); scanner OCR UI (7); industry content-modules UI (8); full analytics-funnel + rollups UI (9/19); team dashboard + locked-branding UI + CSV import (10/18); CRM OAuth sync jobs UI (11); Stripe/RevenueCat checkout + entitlement webhooks (12/27/28); email-signature generator, custom domains, white-label/reseller UI (13/22/24/25); EN/AR/ES + RTL (14); security hardening (rate-limit/CAPTCHA/2FA/SSO) (15/33/34); store submission assets (16/36); deep links (37).
