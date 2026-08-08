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

## GLOBAL-READINESS INTEGRATION (2026-06-08, iteration 4) — folded into existing phases, ONE global codebase
Per updated master plan: US = launch market #1, architecture = global-first. No separate global version; existing models extended, data/URLs preserved.
- **Phase 1 (Accounts/Workspaces)** ← §1,§7,§26,§28: workspace gains `region{country,country_code,region,timezone,locale,default_language,default_currency,billing_country}` + `tax{}`; user gains `language,locale,timezone`. Register infers/accepts country/language/timezone/currency (defaults US/en/UTC/USD as *config*, not assumptions).
- **Billing (12/27/28)** ← §2,§3,§15: plans carry `regional_prices` per market; `/api/pricing?market=` resolves; entitlements stay currency/provider-independent; Super Admin markets config.
- **Tax (§4)**: configurable `tax` layer + provider adapter (Stripe Tax hook) behind Not-Configured flag; invoice tax metadata fields.
- **Profiles/Templates (8/16)** ← §10,§11,§9: `CardData.languages[]` + `i18n{}` localized content (bio/services/projects per lang); public `/api/cards/{slug}?lang=` merge with fallback; RTL for Arabic (web+app).
- **Contact/Leads/CRM (6/11/22)** ← §5,§6,§22: E.164 phones; structured intl address (line1/line2/city/adminArea/postalCode/countryCode); leads carry country/language.
- **NFC (4)** ← §12: token architecture unchanged, already market-agnostic; language applied at profile layer.
- **Wallet (5)** ← §13: provider architecture market/capability-aware (graceful per platform/country).
- **Hardware (6)** ← §14: order model gains destination_country/currency/intl address/shipping/tax/fulfillment_region.
- **Analytics/Campaigns (9/19/20)** ← §18,§19: market/country/language/currency/timezone dimensions; campaigns carry market/language/currency.
- **Teams/White-Label (10/18/24)** ← §20,§21: intl per-user settings within one workspace; reseller market/currency/languages.
- **AI (13)** ← §23: follow-up output language (EN/AR/ES) + auto by lead language; provider abstraction kept.
- **Formatting/Storage (§24,§25)**: locale-aware formatting on clients; Unicode/Arabic/Latin-accented safe (Mongo UTF-8).
- **Privacy (35)** ← §17: region-configurable consent/legal content.
- **Super Admin (43)** ← §29: Global Config (markets/currencies/regional pricing/languages/tax/legal/app-availability/hardware).
- **QA (50)** ← §30: multi-market cases (US/UAE-en/UAE-ar-RTL/Spain/UK).

### Global foundation — status (iteration 4, 87/87 backend tests pass)
IMPLEMENTED & TESTED: workspace.region + tax; user language/locale/timezone; markets (US/AE/EU/GB) + multi-currency regional pricing (`/api/pricing?market=`, 400 on unknown); Super Admin markets/pricing config; register-with-region; localized profile content (`languages[]`+`i18n{}`, `?lang=` merge + fallback); public language switcher + true RTL (Arabic) on templates; intl address fields; leads/campaigns carry market/lang; **AI follow-up wired to live LLM (openai gpt-5.4) in EN/AR/ES with deterministic template fallback**; config feature-flags.
STILL PENDING (subsequent phases, unchanged): native mobile app; Wallet pass issuance; Stripe/RevenueCat checkout UI + webhooks; CRM OAuth sync jobs; scanner OCR UI; industry-module editor UI; full EN/AR/ES UI string localization of dashboard/app (public profile localization done); custom domains/white-label UI; SSO/2FA/rate-limiting; store submission assets; deep links.

### Team & AI increment (iteration 5) — IMPLEMENTED & verified
- **Phase 10/18 Team/Company**: workspace members (invite/list/role/deactivate/remove), **locked corporate branding** (branding + locked_fields; MEMBER edits to templateId/accent/company/companyLogo are reverted — verified), **CSV import** creating branded member cards, workspace details.
- **Member card scoping** (Section 42 within-workspace): admins see whole workspace; MEMBERs see/edit ONLY their own assigned card (`owner_user_id`) — verified 403 cross-member.
- **AI-in-dashboard**: leads inbox now has a "Draft follow-up" panel (channel/tone/language) calling the **live gpt-5.4** writer with copy + RTL for Arabic — verified end-to-end.
- Added `emergentintegrations` to requirements.txt.
Native mobile app (Phase 3); Wallet pass generation wiring (5); scanner OCR UI (7); industry content-modules UI (8); full analytics-funnel + rollups UI (9/19); team dashboard + locked-branding UI + CSV import (10/18); CRM OAuth sync jobs UI (11); Stripe/RevenueCat checkout + entitlement webhooks (12/27/28); email-signature generator, custom domains, white-label/reseller UI (13/22/24/25); EN/AR/ES + RTL (14); security hardening (rate-limit/CAPTCHA/2FA/SSO) (15/33/34); store submission assets (16/36); deep links (37).

## Phase 7 — Business-card / Event-badge Scanner (2026-06-08, iteration 5) — IMPLEMENTED & QA-PASSED (10/10)
- **Backend** (`platform_v1.py`): `POST /api/scan/card` runs the uploaded image through **live OpenAI gpt-5.4 vision** (emergentintegrations `ImageContent`) and returns a STRUCTURED DRAFT only — never creates a lead. Extracts name/title/company/email/phone (E.164)/website/address/city/country/language/notes. Gated by `scanner` entitlement (pro/team/enterprise); returns 403 for free plan, `configured:false` when no EMERGENT_LLM_KEY.
- `POST /api/scan/confirm`: mandatory human review/edit → persists a CRM lead scoped to one of the user's OWN cards (`_owned_slugs`, 403 otherwise) with `source=business_card_scan|badge_scan`, `tags=['scanned']`, `scanned=true`, `captured_by`. Empty name → 400. Notification created.
- **Frontend** (`components/admin/ScanCardDialog.jsx`): "Scan card" button on `/admin`. Camera capture (facingMode=environment, primary on mobile) + file upload; client-side downscale to ≤1600px JPEG; review/edit step with per-field editing + target-card + language selectors; RTL for name/company on Arabic. No lead until confirm.
- QA: testing agent 10/10 backend + upload→review→save frontend flow verified. Reusable suite at `/app/backend/tests/test_scanner_phase7.py`; image rules in `/app/image_testing.md`.

## Phase 5 — Wallet passes (2026-06-08, iteration 5) — IMPLEMENTED (Not-Configured adapter) & verified
- **Backend** (`platform_v1.py`): `GET /api/wallet/status` (per-platform capability) and `GET /api/cards/{slug}/wallet/{apple|google}` — provider-abstracted; returns neutral `pass_data` + `configured:false` "Not Configured" until Apple/Google Wallet creds supplied (then adapter issues signed .pkpass / save-to-wallet link). Bad platform → 400.
- **Frontend** (`components/profile/WalletButtons.jsx`): "Apple Wallet" / "Google Wallet" buttons on all 3 public templates (beige/black/future variants) next to Share/QR-Poster; graceful "coming soon" toast when not configured, opens pass_url when configured. Tracks `wallet_apple`/`wallet_google` taps.
- Verified via curl (status + not-configured pass + 400) and public-profile screenshot render.

