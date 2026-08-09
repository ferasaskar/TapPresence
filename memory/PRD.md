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

## Landing Page — high-fidelity reference rebuild (2026-06-09) — IMPLEMENTED (frontend-only) & QA'd
- Rebuilt `/` to match the provided dark-luxury reference (black #050607 + champagne gold #D6A653). **Frontend-only** — backend, routes, auth, plans, NFC, profiles, leads, teams all untouched.
- New reusable structure: `pages/Landing.jsx` composes `components/landing/{Navbar, Hero, ConnectionFeatures, JourneyFlow, TemplateShowcase, TeamsTestimonials, FinalCTA, Footer}`; data-driven via `components/landing/data.js`; hero product composition in `components/landing/HeroVisual.jsx`; styles in `components/landing/landing.css`.
- Sections: sticky navbar (Product/Templates/Solutions/Resources/Pricing/About anchor-scroll; Login→/login, Create Your ID→/register); hero (phone with live ARIADNI profile UI + matte-black NFC card w/ real /feras-askar QR + glowing pedestal + ambient particles); stats row; 6-feature strip; 5-step tap→connection journey; 3 distinct premium template previews + App promo (App Store/Google Play badges + dashboard phone); Teams panel + 3 testimonials; gold-wave final CTA; 5-column footer with newsletter + socials.
- Motion via framer-motion (staggered hero entrance, scroll reveals) + CSS floats/breathe; `prefers-reduced-motion` respected. Assets: Unsplash portraits + generated gold-wave/ambient textures.
- QA: desktop (1440), mobile (390, no horizontal overflow) screenshots match reference; CTA/login routing verified (Create Your ID→/register, Login→/login); existing routes intact.

## Landing Page — "Cinematic Gold Signal" interactive layer (2026-06-09) — IMPLEMENTED (frontend-only) & QA'd
Design/structure/functionality unchanged; added a performant interactive layer on top.
- **Signature animated gold wave**: `components/landing/GoldWaveCanvas.jsx` — layered particle ribbons on a transparent canvas (pre-rendered sprite + additive blend), scroll+pointer reactive, `IntersectionObserver` pauses when offscreen, DPR-capped, ~50% fewer particles on mobile, static single frame under reduced-motion. Final CTA = hybrid (loved wave image as calm base + live particles on top).
- **Hero signal**: subtle gold→blue `variant="hero"` canvas behind phone/NFC (signal "generated" by the card). Phone & NFC card float at different durations + opposite scroll parallax (framer `useScroll`/`useTransform`, disabled under reduced-motion).
- **Journey (major upgrade)**: scroll-driven illuminated signal path connecting the 5 steps — desktop horizontal line through nodes, mobile vertical timeline; gold→blue gradient fill scales with scroll progress; active/done/dim states; AI step glows purple.
- **Light sweeps**: `.lp-sweep` (~9s) on primary CTAs + NFC card; `.lp-shine` gold shimmer on "Reinvented.".
- **Feature cards**: pointer-follow 3D tilt (≤3°) + radial glow (hover-capable only), in-view activation glow on mobile.
- **Navbar**: transparent at top → translucent blur + hairline border after 24px scroll. **CTAs**: hover lift + `.lp-press` 0.98 active + moving highlight.
- Accessibility/perf: `prefers-reduced-motion` removes floats/parallax/particle motion (page stays complete); GPU transforms/opacity only; no layout thrash.
- QA: 1440 + 390 screenshots, reduced-motion, and `scrollWidth<=clientWidth` (no overflow) all verified; routes/functionality untouched.

## Phase 8 — Industry Template Personalization (2026-06-09, iteration 6) — IMPLEMENTED & QA-PASSED (100%)
Data-driven "one base template + industry skin + accent + layered background" — NO per-industry templates, NO breaking changes.
- **Backend**: `CardData`/`CardUpsert` extended with `industry, background_style, custom_accent_color, background_opacity, background_intensity, background_position, custom_background` (safe defaults ⇒ existing cards unchanged). `GET /api/industries` returns a 12-item catalog (11 industries + Custom) merging Super-Admin `industry_overrides`. `update_card` locked_fields extended: MEMBERs cannot change locked `accent`/`industry`/`background`.
- **Frontend engine** `lib/industries.js`: `industryRootStyle(card, baseRgb, accentHex)` builds the layered background (readability overlay + image/CSS-pattern) merged onto each template root; returns `{}` when no industry (regression-safe). `lib/accents.js` extended to 7 accent presets + custom hex.
- **Templates**: all 3 (Beige/Executive/Future) render any industry skin (template-independent); content untouched, background sits behind via root layers; accent supports custom color.
- **Editor** `components/admin/IndustryCustomizer.jsx` + new "Industry" tab in `CardEditor`: premium dark panel with industry cards, accent swatches + custom picker, per-industry background-style thumbnails, opacity slider (0–30%), intensity (soft/medium/rich), position (left/center/right/full), custom image upload — all update the existing LIVE PREVIEW instantly.
- **Assets**: 11 generated premium dark industry backgrounds (CDN). Custom industry = user upload via existing storage.
- QA (iteration_6): backend 5/5; all 8 combos, template independence, existing-card regression, MEMBER locked-fields revert, mobile 2-col grid + no overflow, Arabic RTL — all pass. Demo `feras-askar` = Beige Luxury + Real Estate skyline @20%.

### Fix (2026-06-09, iteration 7) — "I can't find the new designs" (discoverability)
- Root cause: Industry personalization lived only inside Admin → Card editor → "Industry" tab (buried on mobile; accounts with 0 cards had nothing to open).
- Fix: new **browsable showcase page `/industries`** (`pages/IndustryShowcase.jsx`) — hero "Industry Template System", base-template chips, mobile/desktop toggle, live interactive `TemplateRenderer` preview + the full IndustryCustomizer panel. Registered BEFORE the `/:slug` catch-all in `App.js`.
- Discoverable from: Card Manager header button (`industry-templates-link`) and landing "Explore Templates". CTAs → `/register`.
- Verified (iteration_7): 13/13 critical FE tests pass — route renders, preview reacts (industry/accent/template/opacity/device), discoverable from dashboard + landing, `/feras-askar` regression clean. Minor 390px overflow fixed (overflow-x-hidden + smaller mobile frame; scrollWidth=clientWidth=390).

### Fix (2026-06-09, iteration 8) — "background picture not showing" + verify all buttons
- Root cause: `industryRootStyle` used one flat rgba overlay at alpha ~0.85–0.9 → image washed out (invisible, worst on light Beige).
- Fix: rewrote to a **directional 3-stop scrim** (lighter at top so the picture shows, denser toward content for readability), with an `isLight` brightness check keeping light templates subtle; opacity×intensity drives visibility.
- Verified (iteration_8, 100% FE): computed `backgroundImage` contains the industry `.jpeg` URL + gradient on both `/industries` preview and `/feras-askar`; switching industry changes the URL; opacity slider mutates alphas; photo vs CSS-pattern styles swap; ALL buttons work (showcase chips/device/industry/accent/style/position/CTAs; public-profile Message→sms, Book a Call→cal.com, Save→vCard, Share, Poster, Wallet, socials, inquiry submit); no console errors; no mobile overflow.

### Reference-match 3-card showcase (2026-06-09)
- Added `components/landing/IndustryCards.jsx` — pixel-faithful 3-card row (Real Estate/Alex Morgan/gold, Technology/Daniel Quinn/blue, Healthcare/Dr. Sophia Bennett/green) matching the user's reference: visible industry backgrounds (skyline, neural, medical + cross & heartbeat), gold ARIADNI ID logo, accent portrait ring, role/company in accent, 4 circular action buttons, Exchange Contact, "Tap your card", industry label beneath. Role-accurate portraits. Featured at the top of `/industries` above the interactive live builder. Verified via desktop screenshot; responsive grid (1/2/3 cols).

## Unified Master Industry-Card System (2026-06-10, iteration 9) — IMPLEMENTED & QA-PASSED (100% FE)
User directive: ALL 12 industries must render in ONE identical premium card structure (the attached showcase reference is the visual source of truth). Only background mood, accent color, industry icon and content change — never the layout.
- **`lib/industryCards.js`** (new): single `INDUSTRY_CARDS` data array of all 12 presets (real_estate, business, sales, technology, healthcare, legal, education, hospitality, automotive, beauty, finance, custom) — each with `label, icon, accentId, accent hex, base rgb, name/role/company, portrait, image` (healthcare has `decoration:'medical'`). `previewCardConfig(form)` maps live editor state → card config.
- **`components/landing/IndustryCard.jsx`** (new): the ONE master card component — accent-glow rounded frame, ARIADNI ID header, centered circular portrait w/ accent ring, name/role/company hierarchy, 4 circular OUTLINED action icons (Call/Email/WhatsApp/Save) w/ labels, "Exchange Contact" outlined button, "))) Tap your card", industry label+icon below. testids: `ind-card-{id}`, `ind-action-{id}-{call|email|whatsapp|save}`, `ind-exchange-{id}`, `ind-label-{id}`.
- **`IndustryCards.jsx`** rewritten: renders all 12 via `IndustryCard` in a responsive grid (1/2/3/4 cols).
- **`/industries` builder** now renders the master card in `showcase-preview` (removed the old TemplateRenderer preview + template chips + device toggle). Picking an industry auto-sets its recommended accent AND swaps demo person content so the preview fully reflects the industry family. Accent swatches recolor the live card.
- Accents: added **`red`** option (accents.js ACCENT_OPTIONS + all 3 template SETS) for Automotive; Sales→purple.
- Distinct **finance** background generated (dark emerald charts + skyline) so no two industries share an image.
- QA (iteration_9): 100% FE — all 12 cards render identical structure, live preview reacts to every industry + accent (incl. red), no console errors, no overflow at 1440/390, `/feras-askar` regression clean.
- NOTE: `IndustryCard` is currently used on the `/industries` showcase + builder (marketing/preview surface). The full-page public profile templates (Executive Black Gold etc.) remain the actual published-profile renderer and are unchanged.

## Premium Dark Redesign of ALL internal app pages (2026-06-10, iteration 10) — IMPLEMENTED & QA-PASSED (100% FE)
User directive: every app page must match the premium home-page look (black #050607 + champagne-gold #D6A653, glass-morphism, grain). Internal pages were light/white and inconsistent.
- Added scoped **`.aria-dark`** theme in `index.css` (dark inputs/textareas/labels/select-triggers) + **`.aria-pop`** for portaled Radix dropdown popovers + `.aria-gold-radial` glow. Public profile templates (beige/executive/future) intentionally NOT affected.
- Redesigned dark: **Login, Register, Activate (glowing NFC), Legal** (glass cards, gold CTAs), **Admin dashboard** (glass sticky header, bento card gallery, gold badges, framer stagger), **CardEditor** (the profile-completion studio — gold pill tabs, dark inputs, phone-bezel live preview), **ImageUploadField**, and all dialogs (**Leads, Analytics, Scan**). All data-testids + functionality preserved.
- Fixed the "not working" builder controls: `IndustryCard` now honors **Background Intensity** (soft/medium/rich alpha multiplier), **Position** (left/center/right + distinct **full** = 150% zoom) and **Opacity**; `previewCardConfig` forwards them.
- Profile-completion flow (answer to user's question): Dashboard `/admin` → New card / Edit → tabs (Identity/Industry/Contact/Social/Services/Projects/Booking) → Published toggle → live preview → Save.
- QA (iteration_10): 100% FE — login→dashboard→editor save/publish, dialogs, activate, legal, intensity/position/opacity controls all work; no console errors; no overflow at 1440/390; `/feras-askar` + `/industries` regressions clean. Fixed 2 minor findings (full-position distinct; dialog a11y descriptions).

## Single Card-Creation Pipeline (/templates studio) (2026-06-10, iteration 11) — IMPLEMENTED & QA-PASSED (5/5)
User directive: exactly ONE creation flow. Card Manager → Create Card → Templates page → Choose Industry → Customize Style → Enter Information → Live Preview → Save/Publish → Your Cards. Remove duplicate paths + customer-facing template chooser (keep legacy renderers for existing cards).
- **New `/templates` studio** (`pages/CreateCard.jsx`, protected): 3-step wizard with a persistent live full-profile preview (`create-preview`). Step 1 "Choose Your Industry" (12 clickable `IndustryCard`s, `choose-industry-{id}`) → Step 2 "Customize Your Style" (`IndustryCustomizer`) → Step 3 "Your Information" (slug + `CardInfoTabs`). Header + bottom **Save Draft** / **Publish Card** (`save-draft-button`, `publish-button`, `publish-button-bottom`). Slug auto-derives from full name.
- **Extracted `CardInfoTabs.jsx`** (Identity/Industry/Contact/Social/Services/Projects/Booking) + `emptyCard`/`mergeCard`; reused by both CreateCard and CardEditor. New cards silently default `templateId=executive-black-gold`.
- **Removed the customer-facing template selector** (Executive/Beige/Future) from `CardEditor` (existing cards keep their templateId when edited — legacy renderer untouched). Removed dashboard **"Industry Templates"** link.
- **Admin dashboard**: `Create Card` (renamed) + empty-state `Create your first card` both `navigate('/templates')`. Editing an existing card still opens the inline `CardEditor`.
- QA (iteration_11): 5/5 journeys pass — new-user publish, existing-user save-draft, direct /templates, legacy card edit (no `editor-template` in DOM, /feras-askar intact), no duplicate creation path. Fixed the one finding (mobile /templates header overflow → flex-wrap + collapse labels).

## Published-card visual fidelity + photo crop (2026-06-10, iteration 12) — IMPLEMENTED & QA-PASSED (6/6)
User: published card must match the approved showcase — accent-consistent panels, faithful industry background, and portrait crop control. Fixed at the template-engine level (all cards).
- **Accent-driven everything**: `accents.js` `accentGrad` now derives a light→base→dark gradient from the SELECTED accent via new `shadeHex` (no more gold fallback). `InquiryForm` black variant button + inputs derive from `accentColor`. `ExecutiveBlackGold` `<style>` block drives ALL panels/buttons (action buttons, CTA/Book, Send Message, inquiry form, Save Contact, QR, Share, QR Poster, Apple/Google Wallet, services/projects) from the accent — border + tint (`hexToRgba(ac,0.07)`) + hover glow + icon color. Purple card = purple everywhere; gold = gold.
- **Background atmosphere match**: template scrim base is now tinted with the chosen industry's `base` tone from `INDUSTRY_CARDS` (e.g. Sales → rgb(20,11,30) purple) instead of neutral black, so published matches the showcase mood. Preview & published share the same `TemplateRenderer` logic (parity verified — identical transforms).
- **Profile photo crop**: new `ProfilePhotoField` (upload / paste URL, draggable circular crop, zoom slider 1–3x, reset). Saved as `identity.imageScale/imageOffsetX/imageOffsetY` (backend `Identity` model extended). Applied via `transform: translate(x%,y%) scale()` on the portrait in preview AND public render.
- QA (iteration_12): 6/6 pass via computed-style checks — purple panels rgb(167,139,250), gold rgb(201,162,75), bg tones correct, crop persists & preview↔public transform matrices identical, feras-askar regression gold. Temp cards cleaned up.
- NOTE: fix currently lives in the default `ExecutiveBlackGold` template (all new cards use it). Beige/Future legacy templates unchanged (existing cards safe).

## Four enhancements: Auto-center, Accent picker, Publish confirmation, Duplicate (2026-06-10, iteration 13) — IMPLEMENTED & QA-PASSED (100%)
- **Face auto-center** (`ProfilePhotoField`): uses browser `FaceDetector` when available, else a portrait heuristic (scale ~1.15, offsetY ~6). Runs automatically on upload + manual `photo-autocenter` button. Writes `identity.imageScale/imageOffsetX/imageOffsetY`, applied identically in preview + published (`hero-portrait` transform).
- **Accent picker in studio** (Step 2 via `IndustryCustomizer`): swatches (`accent-{id}`, incl. red) + `accent-custom` color input; recolors the live full preview instantly.
- **Publish confirmation** (`CreateCard`): after Publish, a "You're live" screen (`publish-success`) with QR (`publish-qr`), shareable link + copy (`publish-link/publish-copy`), View card and Go to dashboard. Save Draft still routes to /admin.
- **Duplicate card**: `POST /api/admin/cards/{id}/duplicate` (unique `{slug}-copy-xxxxx`, status draft, re.sub strips stacking) + `duplicate-{slug}` button on each dashboard tile.
- QA (iteration_13): 100% — backend 6/6 pytest, frontend all 4 + regression. Testing agent caught & fixed a critical regression my duplicate insertion caused (the `@api_router.put` decorator for `update_card` was consumed → editing returned 405); decorator restored, verified. All temp cards cleaned; feras-askar untouched.

## Native ARIADNI Meetings & Calendar + Exchange Contact CTA (2026-06-10, iteration 14) — IMPLEMENTED & QA-PASSED (14/14 BE + FE)
- **Public CTAs** (ExecutiveBlackGold): `cta-exchange-button` "Exchange Contact" (primary, accent gradient) + `cta-book-button` "Book a Meeting". Exchange opens `ExchangeContactDialog` (visitor → CRM lead + returns owner vCard). Book opens `BookMeetingDialog` (multi-step: type → date → slots → details → confirm → "You're booked" + manage link), fully accent-themed.
- **Native booking engine** (server.py): meeting_types (auto-seed 15/30/45), availability (Mon–Fri 9–18 Asia/Dubai defaults), timezone-aware slot engine `_day_slots` (ZoneInfo, buffers, min-notice, max-window, overlap + blocked), **double-booking prevention** (409). Public: `GET /cards/{slug}/booking`, `GET /cards/{slug}/slots`, `POST /cards/{slug}/book`. Guest manage (secure token): `GET/POST /meetings/manage/{token}` (+cancel/reschedule) — no account needed.
- **CRM integration**: booking creates/updates a lead (source `meeting_booking`), lead timeline `meeting_booked`→`meeting_completed`, notification + `booking_completed` analytics event. Exchange creates a lead too.
- **Dashboard** `/meetings` (`meetings-link` in header): tabs Today/Upcoming/Past/Cancelled, status change (scheduled/confirmed/completed/cancelled/no-show), and AI **Draft follow-up** on completed (reuses `/ai/followup`, review-only). Past tab now always includes completed/no-show.
- **Owner settings** (editor Booking tab, `BookingEditor`): native toggle, timezone, meeting-types CRUD, availability editor. External booking URL kept as fallback when native OFF.
- **Deferred/architected (NOT_CONFIGURED)**: reminder sending (schedule stored: 24h+1h), Google/Outlook sync. Team = card-level owner (workspace access enforced via `_can_access_card`).
- QA (iteration_14): backend 14/14 pytest, frontend 100% (CTAs, exchange, full booking, guest manage, dashboard, booking editor, AI). Testing agent fixed a critical `list+tuple` TypeError that 500'd the today/upcoming tabs; I then fixed the Past-tab visibility for completed-future meetings. feras-askar has native booking ON as the live demo.

## Public card mobile-first redesign (2026-08-09) — ExecutiveBlackGold layout only
User report on /feras-askar mobile: Exchange/Book CTAs felt "missing" (they were buried BELOW Services+Projects), card was "far too long", wanted single Call + compact sections. Root cause: CTA bar rendered after services/projects. Fix (template-engine level, `ExecutiveBlackGold.jsx`; industry/accent untouched):
- New mobile hierarchy: PROFILE HERO → QUICK ACTIONS (Call·WhatsApp·Email·Message, one compact 4-col row, single Call only) → PRIMARY CTAs (Exchange Contact + Book a Meeting, 2-col, directly below quick actions, on first screen) → CAPABILITIES (compact 2-col cards, line-clamp-2) → PROJECTS (horizontal snap carousel on mobile, 2-col on sm+) → MESSAGE (compact "Send a Message" CTA opening InquiryForm in a modal — form no longer permanently open) → UTILITIES (Save·Share·QR 3-col compact; QR toggles inline; Apple/Google Wallet; QR Poster tucked under a "More" toggle) → footer/socials.
- `InquiryForm` gained an `embedded` prop (renders without the outer card wrapper/heading) for use inside the message modal.
- No duplicate Call CTA anywhere (Call lives only in Quick Actions).
- Dialog/booking wiring unchanged from iteration 14 (Exchange/Book dialogs + backend). New testids: cta-message-button, message-dialog, message-section, utilities-section, qr-toggle, more-toggle.
- Verified: top-of-page mobile layout renders with both CTAs on the first screen (screenshot). NOTE: preview screenshot tool only captures the top viewport, so below-fold sections (projects carousel, message modal, utilities) and dialog-open states were implemented + code-verified but NOT visually confirmed in-tool; user is self-testing (their chosen option b).

## Meetings ownership + approval + guest UX — PHASE 1 (2026-08-09) — IMPLEMENTED & backend-verified
User directive: fix meeting ownership/isolation + guest UX + confirmation model BEFORE any new features. Phased (approval to review each phase). Phase 1 only.
- **Ownership model**: `CardData` gains `created_by` (creator/audit) SEPARATE from `owner_user_id` (assignable business owner). `create_card`/`duplicate_card` now set `created_by`. New `PUT /api/admin/cards/{id}/owner` (SUPER_ADMIN or workspace admin; target must be a workspace member) reassigns owner + syncs meetings pointer. `GET /api/admin/workspaces/{ws}/members` lists assignable members.
- **Data fix (non-destructive)**: created MEMBER "Feras Askar" (feras@ariadni.ai/Feras@2026) and assigned feras-askar+feras-mahmmoud→Feras, mona-farah→Mona, luis-reyes→Luis; created_by=admin. Validates creator≠owner scenario. Seeding only inserts-if-absent so restarts won't clobber.
- **🔴 Security/isolation fixes**: `GET /api/admin/leads` now scoped to caller's visible cards (was global — cross-tenant leak). `PATCH/DELETE /api/admin/leads/{id}` now enforce `_can_access_card` via `_lead_or_403`. `GET /api/admin/cards/{id}/analytics` now enforces `_can_access_card`. Verified 403 cross-tenant (Feras→edrina leads/analytics/delete/patch = 403; Feras sees only his 2 cards/leads/meetings; SUPER_ADMIN sees all).
- **Confirmation model (backward-compatible)**: `MeetingTypeIn.confirmation_mode` = `auto` (default, unchanged behavior) | `approval`. Approval bookings start `status="requested"` (guest sees "Meeting request sent / waiting for confirmation"). Owner Accept→confirmed, Decline→declined, Propose New Time→`POST /api/admin/meetings/{id}/propose` sets `time_proposed`; guest `POST /api/meetings/manage/{token}/accept-proposal`→confirmed. `ACTIVE_STATUSES` extended (requested/time_proposed hold the slot). Verified full flow end-to-end via curl.
- **Guest manage UX (ManageMeeting.jsx)**: Back-to-profile (top + footer), Close, "Cancel rescheduling"/"Keep original time" so a guest starting reschedule can return without modifying; renders pending/confirmed/declined/cancelled/time_proposed states + Accept-new-time. Never traps the guest.
- **BookingEditor**: per-meeting-type "Requires approval" toggle. **BookMeetingDialog**: pending copy when requested. **Meetings.jsx**: Accept/Decline quick actions on requested + status options include requested/declined/time_proposed (full redesign deferred to Phase 3).
- QA: targeted backend curl tests only (no broad agents, per user). Frontend Phase 1 code-verified + manage page mounts. PHASE 2 (owner dashboard + role-aware nav) and PHASE 3 (Meetings + Inbox redesign) NOT started — awaiting user approval. Typography/readability presets explicitly deferred to a separate later phase.

## Meetings action-model UX (2026-08-09) — raw status dropdown removed
User reported the raw status dropdown exposed invalid actions (e.g. confirmed→time_proposed) then failed with "Could not update". Replaced with **context-aware actions** + human-readable labels (Meetings.jsx). No new status logic; backend validation stays the source of truth.
- Labels only (never raw enums): Pending Approval / New Time Proposed / Confirmed / Completed / Cancelled / Declined / No-show.
- Actions by state: **requested**→Accept·Decline·Propose New Time; **time_proposed**→Revise proposal·Cancel (shows proposed time; guest accepts via guest flow); **scheduled|confirmed|rescheduled** (all shown as "Confirmed")→Reschedule·Mark Completed·No-show·Cancel; **completed**→View Lead·AI Follow-up (no status editing); **cancelled|declined|no-show**→View details (read-only). Invalid actions are never rendered.
- New backend action `POST /api/admin/meetings/{id}/reschedule` (owner direct reschedule; reuses the same `_day_slots`/`_existing_intervals` engine — no duplicate scheduling logic). Inline date/slot picker drives Propose & Reschedule.
- Verified via targeted curl: auto→scheduled, owner reschedule→rescheduled(time moved), completed, PATCH status=time_proposed→**400 rejected**, approval→requested→propose→time_proposed→revise, decline→declined. Test data cleaned; feras-askar has its 6 real meetings.
- ⚠️ **NORMALIZATION FLAG (not actioned):** `scheduled` (auto-confirm bookings) has **no distinct business meaning** from `confirmed`/`rescheduled` — all are "active/agreed" (same slot-hold, same tabs, same actions). UI already unifies them as "Confirmed". Recommend a future **safe, non-destructive** normalization (map scheduled→confirmed for new writes, backfill old rows in a migration). NOT removed now to avoid a destructive change.

## Meetings temporal eligibility (2026-08-09) — time-aware actions
Actions are now state-aware AND time-aware. Enforced on BOTH server and client (server = source of truth, client clock never trusted for auth).
- **Mark Completed**: only at/after scheduled end = `start_utc + duration`. Server returns **409** before end.
- **No-show**: only after `start_utc + NO_SHOW_GRACE_MIN` (15 min). Server returns **409** before that.
- Before start, a Confirmed meeting shows only Reschedule + Cancel (no Complete/No-show).
- Backend: temporal check added in `PATCH /api/admin/meetings/{id}/status` using `datetime.now(timezone.utc)` vs stored `start_utc`+`duration`; constant `NO_SHOW_GRACE_MIN=15`. Frontend hides the buttons until eligible (Meetings.jsx ACTIVE branch).
- Verified via targeted curl (direct DB-seeded past/future meetings): future→complete **409**, future→no-show **409**, ended→complete **200**, started-not-ended→complete **409**, started+grace→no-show **200**, within-grace(5m)→no-show **409**. Test data cleaned; feras-askar unchanged.

## PHASE 2 — Owner dashboard + role-aware navigation (2026-08-09) — IMPLEMENTED
Goal: a MEMBER feels like they have their own account, not the Super Admin system. Reused existing scoped endpoints/dialogs; no parallel dashboard architecture.
- **Shared role-aware nav** `components/admin/OwnerNav.jsx`: Home / My Card(s) / Inbox / Meetings / Analytics / Settings pills (mobile horizontal-scroll), unread inbox badge, role badge. Self-contained: fetches `/admin/cards` (+primary) and `/admin/leads` (unread), owns the Inbox/Analytics/Scan dialogs. **Scan card gated to SUPER_ADMIN only** (removed from members). Analytics opens the owner's primary card.
- **Home** `/dashboard` (`pages/Home.jsx`): primary card preview + published status, stats (profile views / NFC taps / QR scans / new leads — reuses existing analytics, no new infra), upcoming meetings list, quick actions (Edit Card, View Public, Share, View Leads, Meetings). Empty-state → create card.
- **Settings** `/settings` (`pages/Settings.jsx`): account overview (name/email/role/workspace/timezone/language/card count) + manage-card + logout. Deeper profile/password editing flagged for later.
- **Reused**: `Admin.jsx` (My Card list/editor) header replaced with OwnerNav (removed bespoke header/Inbox/Scan/logout — now in nav); `Meetings.jsx` header replaced with OwnerNav. Login/Register redirect → `/dashboard`. Routes added in `App.js` (`/dashboard`, `/settings`).
- **Security**: unchanged Phase 1 backend isolation is the source of truth; nav hiding is cosmetic only. Set known passwords for Mona (`Mona@2026`) and Luis (`Luis@2026`) for testing/real login.
- **Targeted tests (curl, no broad QA)**: Feras→only feras-askar+feras-mahmmoud; Mona→only mona-farah; admin→5 cards (global); Feras→mona/edrina analytics & leads = **403**; Mona→feras leads = **403**; Feras→edit mona card = **403**. Frontend compiles clean. NOTE: authed dashboard nav couldn't be screenshotted in-tool (tool only captures the page_url's initial/unauth state) — visual nav review left to user. Phase 3 NOT started.

## PHASE 3 — Professional Meetings + Leads/Inbox redesign (2026-08-09) — IMPLEMENTED
UX/UI only; reused existing APIs/models. One tiny additive backend endpoint (lead pipeline stage). No duplicate CRM/meeting systems.
- **Meetings** (`pages/Meetings.jsx`, rewritten): summary cards with counts — **Today / Upcoming / Pending Approval / Completed**; **List + Calendar** views (List default, mobile-friendly month grid with per-day dots); filters **Type / Status / Card** (Card only when >1 owned card); human-readable status labels only (no raw enums); reused contextual + time-aware actions (Accept/Decline/Propose, Reschedule/Cancel, Completed/No-show gated by time, Revise proposal, View Lead→/leads, AI Follow-up); click a meeting → **detail modal** (guest info, when/tz, source card, notes, actions, reminder status, lead link, status history). No new scheduling logic — all via existing endpoints.
- **Leads/Inbox** (`pages/Leads.jsx`, new page; entry = Home "View Leads" → `/leads`): pipeline tabs **New / Contacted / Meeting Booked / Qualified / Converted / Archived** (+All) with counts; **search + Source + Card + Date** filters; lead rows show name, email/phone, source, card, latest real activity, meeting-status badge (client join on `lead_id`), stage badge, quick actions **Call / WhatsApp / Email**; **detail modal** with contact, source, card, **stage dropdown** (moves pipeline), meeting info, **activity timeline from real tracked events only** (Lead created + meeting_requested/confirmed/completed/cancelled), and **AI Follow-up** (channel/tone/language, editable draft, copy — draft-only, never auto-sent). Delete lead. Auto-opens `?lead=<id>` from Meetings.
- Stage derivation (honest, non-fabricating): stored `status` is source of truth; a default "new" lead that has a booking/linked meeting displays under "Meeting Booked" until the owner explicitly moves it.
- **Backend addition (minimal)**: `PATCH /api/admin/leads/{id}/status` (ownership-checked via `_lead_or_403`; `LEAD_STAGES`). No other backend/CRM/meeting logic changed.
- Home "View Leads" now routes to `/leads` (removed the old LeadsDialog usage). New route `/leads` in App.js.
- **Targeted tests (curl)**: lead stage update→200 & persists; invalid stage→400; cross-tenant stage change→**403**; meetings upcoming/past/cancelled→200 scoped to feras-askar only. Frontend compiles (mobile layout OK). Added `.aria-pop` dark dropdown styling. NOTE: authed pages not screenshottable in-tool — visual review left to user.
- Roadmap phases (Typography, Referral, Billing, Native App) NOT started.

## GLOBAL PRODUCT MASTER ROADMAP — approved (2026-08-09)
User approved the full phase-by-phase roadmap (A1→A2→B→C→D→E→F→G→H→I→J→K→L→M→N→O→P→【Native Q】→R→S→T→U→V→W→External). Governance: audit-before-each-phase, reuse-only/implement-gap-only, one source of truth per system, backward compatible (no destructive migration w/o approval), backend-authz source of truth, global/mobile-first, external integrations last, targeted tests then STOP for manual approval, never auto-continue. POSTPONED (kept, not dropped): T white-label, U enterprise, V enrichment, W advanced AI. Debt items deferred to a dedicated safe cleanup phase: retire unused LeadsDialog.jsx; normalize meeting `scheduled`→`confirmed`.

## PHASE A1 — Card Typography & Readability (2026-08-09) — IMPLEMENTED & verified
Engine-level typography/readability upgrade in `ExecutiveBlackGold.jsx` ONLY (the live renderer for all new cards + the create-flow live preview, so preview↔published parity preserved automatically). No backend, no data, no new fields — fully backward compatible.
- Fluid `clamp()` name sizing (1.85rem→3rem) with `overflow-wrap:anywhere` + `text-wrap:balance` so long/RTL/Spanish names never overflow (verified: 35-char single word at 360px = no horizontal overflow).
- Readability tuning: role 15px, company/location tightened tracking, bio 15px/1.7 line-height with `text-wrap:pretty`; section headings fluid clamp + balance; service descriptions 13px/1.55. RTL letter-spacing neutralized via `[dir=rtl]`.
- Reused: entire accent/industry/crop/CTA engine untouched. NOT touched: backend, CardData model, DB, legacy Beige/Future templates, dialogs, CTA logic.
- Tests: frontend compiles (only pre-existing eslint warning); `/feras-askar` 200; mobile 390px + 360px no overflow; long-name stress no overflow. Optional per-card typography preset = POSTPONED (avoids premature architecture).

## PHASE A2 — Public Card Conversion Polish (2026-08-09) — IMPLEMENTED & verified
Non-sensitive UX/analytics-presentation phase in `ExecutiveBlackGold.jsx` (+ tiny context flag). Reuses existing `/track` event system and dialogs — no new event semantics, no backend change.
- **Sticky mobile conversion bar**: fixed bottom Exchange + Book/Message bar, appears via IntersectionObserver only after the primary CTAs scroll out of view (`sm:hidden`, safe-area padding, accent-themed). Container bottom padding raised on mobile so content is never obscured.
- **CTA intent tracking**: primary + sticky Exchange/Book/Message now fire `track("tap", cta_exchange|cta_book|cta_message)` (additive tap keys the analytics already aggregates generically). Feeds the Phase J funnel.
- **Micro-interactions**: `active:scale` press feedback on CTAs.
- **Regression guard**: sticky bar (viewport-`fixed`) gated behind new `ProfileContext.publicView` flag (default false) → renders ONLY on the real public page, never in editor/showcase live previews. PublicProfile sets `publicView:true`.
- Reused: ExchangeContactDialog/BookMeetingDialog/InquiryForm, ProfileContext `track`, accent engine. NOT changed: backend, models, DB, event semantics, legacy templates.
- Tests: compiles (pre-existing warning only); sticky hidden→visible on scroll verified; 390px no overflow; Exchange tap fires `/track` + opens dialog (network-captured); preview isolation via publicView.

## ROADMAP PROGRESS REPORT (running)
- **COMPLETE**: A1 Typography · A2 Public Card Conversion · J Analytics Rollups · D Onboarding · F Notification Center (+secured notifications) · G Localization arch (EN/AR-RTL/ES) · M Team/Company · L Industry Studio · K Command Center · N Email Signature Manager · O Integration Hub foundation · P Offline/Reliability (idempotency)
- **PARTIAL — Localization coverage (G ext)**: DONE on nav/shell, Home, Settings, Notifications, Signatures, Team, funnel/onboarding. REMAINING (English for now, per-screen consistent): Meetings, Leads, Card creation/editor, Scanner, Analytics dialog, Super Admin/Industry Studio/Integrations internal tools, public marketing/login/register.

## PHASE N — Email Signature Manager (2026-08-09) — IMPLEMENTED & verified
Frontend-only, reuses existing card data + QR + workspace branding — no new backend system.
- `lib/signature.js` (email-safe table+inline-style HTML, absolute URLs, 3 templates classic/compact/modern) + `pages/Signatures.jsx` at `/signatures`: card select, template, field toggles, live preview, Copy HTML + Copy rich (ClipboardItem). Corporate-locked fields (from workspace `locked_fields`) are disabled + lock-iconed. Localized. NOT connected to M365/Workspace (deferred).
- Verified: preview renders real signature (name/title/company + View-my-card + QR); Company field locked for Feras via branding; template switch works.

## PHASE O — Integration Hub foundation (2026-08-09) — IMPLEMENTED & verified
Provider-neutral internal architecture (platform_v1), workspace-admin scoped. NO external providers connected.
- Backend: `dispatch_webhooks()` (HMAC-SHA256 signed, `X-TapPresence-Signature`); `GET /workspaces/{wid}/hub`; API keys `POST` (key shown once, sha256 hash stored, prefix), `DELETE` (revoke); webhooks `POST` (secret once), `DELETE`, `POST /{id}/test`. Events: lead.created, meeting.booked, card.published. Wired real dispatch into lead (server+platform) & meeting.booked.
- Frontend: `pages/IntegrationHub.jsx` at `/integrations` — API keys (create/reveal-once/revoke), webhooks (URL + event subscriptions, test, delete, secret reveal-once), external providers shown "not connected". Nav for workspace admins/super-admin.
- Tests: member→403; api-key create/redaction; webhook create/signed-test-dispatch (HTTP fired); hub redacts key_hash+secret; delete/revoke 200. UI verified. Test data cleaned.

## PHASE P — Offline / Event Reliability foundation (2026-08-09) — IMPLEMENTED & verified
Idempotency keys → retry-safe public writes (booth/offline resilience). Additive, non-destructive.
- Backend: `idempotency_lookup/store` (+ inline in platform exchange) keyed by `Idempotency-Key` header, scoped per endpoint+slug; applied to public lead (`/cards/{slug}/leads`), exchange (`/cards/{slug}/exchange`), booking (`/cards/{slug}/book`). Duplicate-key race safe (first write wins).
- Frontend: `lib/api.js` `newIdemKey()`/`idem()`; ExchangeContactDialog, BookMeetingDialog, InquiryForm send a stable per-submission key (reset on success, reused on retry).
- Tests: two identical lead POSTs with same key → exactly 1 lead created (deduped); public exchange smoke test confirms header sent + success flow intact. Test data cleaned.
- **PARTIAL (existing foundations)**: Localization (public done, dashboard strings pending — G) · Entitlements (model done, enforcement scanner-only — C) · Notifications (data+GET done, BUT workspace-scoped not ownership-scoped — see NEEDS APPROVAL) · Team (backend done, dashboard UI pending — M) · Industry overrides (backend done, studio UI pending — L) · Super Admin (config APIs done, tower UI pending — K)
- **PENDING (internal safe, next)**: N Email Signature Manager · G string-coverage extension (Meetings/Leads/CreateCard/Settings/Admin/marketing) · Team/Studio/Command RTL physical-property polish

## PHASE L — Admin Industry Studio (2026-08-09) — IMPLEMENTED & verified
Built on EXISTING `industry_overrides` merge; added missing write layer (SUPER_ADMIN-only, additive, non-destructive).
- Backend (platform_v1): `_require_super`; `GET /api/admin/industries`, `PUT /api/admin/industries/{id}` (name/accent/opacity/image/status upsert), `DELETE` (reset). Public `/industries` already merges → applies to every new card.
- Frontend: `pages/IndustryStudio.jsx` at `/industry-studio` — 12 industries editable (accent/opacity/image/enable-disable/save/reset). SUPER_ADMIN gate.
- Tests: PUT finance opacity→0.22 reflected in public `/industries`; reset 200; Feras(member) PUT→403; UI 12 rows.

## PHASE K — Super Admin Command Center (2026-08-09) — IMPLEMENTED & verified
Real analytics only — NO fabricated KPIs.
- Backend: `GET /api/admin/platform/overview` (SUPER_ADMIN) — real counts: workspaces/users/memberships/cards(+published)/leads/meetings(+by status)/plan distribution/30d views.
- Frontend: `pages/SuperAdmin.jsx` at `/admin/platform` — metric tiles, plan bars, status chips, deep-link to Industry Studio. Nav "Command Center" SUPER_ADMIN-only.
- Tests: admin overview real (9/14/6/4/8/6/212); Feras(member)→403; UI verified.

## SENSITIVE — AWAITING USER DECISION before enforcement (governance stop)
- **C Commercial Core**: may build provider-neutral subscription/usage models + paywall UI, but MUST get approved FREE/PRO/TEAM/ENTERPRISE feature+limit matrix before enforcing any gate against existing users/cards/CRM/meetings/teams.
- **B Referral**: approved economics on file; may build internal engine; STOP before connecting rewards to real billing.
- **I Auth hardening/2FA/rate-limit**: sensitive auth (integration_expert first).

## PHASE M — Team / Company Dashboard (2026-08-09) — IMPLEMENTED & verified
Customer-facing B2B team management on the EXISTING permission model — no backend change (all endpoints pre-existed).
- New `pages/Team.jsx` at `/team`: workspace header (name, plan, seat count), member roster (name/email, role, assigned-card count, status), invite dialog (email/name/role), inline role change, activate/deactivate, remove — owner protected. Localized (EN/AR/ES), mobile-first, data-testids on all controls.
- Reused: `GET /workspaces/me`, `GET/POST /workspaces/{wid}/members`, `PATCH /members/{uid}`, `DELETE /members/{uid}`, `GET /admin/cards` (for per-member card counts). Backend `require_ws_admin` remains source of truth.
- Nav: `OwnerNav` shows "Team" only for SUPER_ADMIN or workspace owners (computed via `/workspaces/me` owner_id); members don't get a dead-end; direct-nav members get a friendly admin-only state (backend 403 handled).
- Tests (curl, admin on ARIADNI HQ): invite→200, role→MANAGER 200, deactivate 200, Feras(member) list→403, remove→200, roster back to 5 (test member cleaned). UI verified at 390px, no overflow.

- **NEEDS APPROVAL (sensitive)**:
  - ✅ RESOLVED — **Notifications isolation** fixed in Phase F (ownership-aware; security-tested).
  - C entitlement enforcement rules · B referral reward economics · I auth hardening/2FA · any data migration
- **DEFERRED EXTERNAL**: Stripe/RevenueCat/Wallet certs/social login/email/push/CRM connectors/Zapier/DNS/custom-domain SSL/SSO/App Store
- **POSTPONED (kept)**: T white-label · U enterprise · V enrichment · W advanced AI · per-card typography preset · legacy cleanup (LeadsDialog, scheduled→confirmed)

## PHASE F — Notification Center + Secured Notifications (2026-08-09) — IMPLEMENTED & security-tested
Fixed a real tenant/member isolation gap, then built the center on the corrected endpoint. No destructive migration.
- **Authorization fix (smallest additive)**: notification writes now carry `scope` (`card`/`workspace`/`workspace_admin`) + `card_slug` (card-context) or `recipient_user_id` (user-specific). `GET /api/notifications` rewritten to be **ownership-aware** via `_notif_visibility_query`: user-specific→recipient only; card-context→users who can access that card (member=owner, admin=workspace); workspace/admin scopes→members/admins; **legacy records (no new fields)→workspace admins only** (safe default, no leak). Response now `{items, unread}`.
- **New endpoints**: `PATCH /api/notifications/{id}/read` (visibility-checked → 404 if not visible), `POST /api/notifications/read-all` (scoped).
- **Frontend**: `components/admin/NotificationCenter.jsx` — bell + unread badge in shared `OwnerNav` (all owner pages), right-side Sheet (mobile-first), human-readable types, relative timestamps, unread dots, mark-one (+deep-link to /leads or /meetings), mark-all, clean empty state. Reuses existing notification writes; no second system; no email/push/SMS (deferred external).
- **Security tests (curl, all pass)**: Feras sees only feras-askar (not mona-farah); Mona sees only mona-farah (not feras-askar); SUPER_ADMIN sees all; unauthenticated→401; Feras marks own→200; Feras marks Mona's→404. Test data cleaned.
- Verified UI: Feras dashboard bell badge=1, center opens, shows real "New inquiry from Amira Nasser · via /feras-askar", mark-all present. Mobile full-width sheet, no overflow.

## PHASE G — Global Localization Architecture (2026-08-09) — IMPLEMENTED & verified
One shared i18n system so every future screen localizes from the start (no per-screen rebuild later). No backend change.
- **Stack**: `i18next` + `react-i18next` + language detector. `src/i18n/index.js` (EN/AR/ES resources, fallback en, localStorage `ariadni_lang`), `src/i18n/locales/{en,ar,es}.json` (shared keys: common/nav/home/funnel/onboarding/notifications/settings), `src/i18n/useLocale.js` (single source for `t` + **locale-aware Intl formatters**: number/currency/date/datetime), `components/LanguageSwitcher.jsx` (globe menu in OwnerNav).
- **True RTL**: `applyDocumentDir` sets `<html dir=rtl lang=ar>` on language change (real layout mirroring, not only translated text); reversible to LTR. Public-card localization behavior untouched.
- **Applied to**: shared shell (OwnerNav), Home (welcome/stats/quick actions/statuses/upcoming with `formatDateTime`), and the new AnalyticsOverview / OnboardingChecklist / NotificationCenter components. Meetings/Leads/CreateCard/Settings/Admin/marketing string coverage extends incrementally on the same architecture (pattern established).
- Verified: switch to العربية → `html dir=rtl lang=ar`, nav mirrored right, Arabic strings render (الرئيسية/مسار التحويل/نقرات NFC), 390px no overflow; switch back → ltr/en. Language persists via localStorage.



## PHASE J — Analytics Rollups / Owner Funnel (2026-08-09) — IMPLEMENTED & verified
Additive read-only reporting; no writes, no new event semantics.
- **Backend**: `GET /api/admin/analytics/overview?days=` — aggregates across ALL cards the caller can access (reuses `_card_query` scoping + existing `analytics_events`/`leads`/`meetings`). Returns funnel (views→engaged→leads→meetings_booked→completed), totals, 30-day views/scans trend, top tap actions. Read-only.
- **Frontend**: new `components/admin/AnalyticsOverview.jsx` on owner Home — funnel bars with step conversion %, SVG sparkline trend, top-action chips. Wired in `Home.jsx`.
- Reused: existing analytics events + card scoping. NOT changed: event capture, semantics, other endpoints.
- Tests: Feras (MEMBER) scoped to his 2 cards (168 views); Admin global 5 cards (186 views) — isolation preserved. Mobile 390px renders funnel+sparkline+chips, no overflow. Authed dashboard screenshot confirmed.

## PHASE D — Onboarding Activation (2026-08-09) — IMPLEMENTED & verified
Pure-frontend activation guidance over existing scoped data (no backend, no auth changes — profile/password edit endpoints DEFERRED as auth-sensitive).
- New `components/admin/OnboardingChecklist.jsx` on Home: Create → Add photo → Publish → Share/first view → First lead, with progress bar; each incomplete step is a shortcut; auto-hides once all complete.
- Reused: cards/leads/overview data already fetched by Home. NOT changed: backend, auth.
- Tests: compiles; for a fully-set-up user (Feras) the checklist is correctly hidden; no overflow at 390px; dashboard intact. (Incomplete-user display is logic-driven from the same data.)


Audit: pre-Phase-3 the only inbox AI was per-lead **AI follow-up** in the now-orphaned `LeadsDialog.jsx` (still in code, unused). Phase 3 moved the SAME feature (same `POST /ai/followup`, same channel/tone/language, editable draft, copy, no auto-send) into the `/leads` Lead Details modal — nothing lost, only less discoverable.
Fix (UI-only, no new AI/backend/CRM): added a clear **AI Follow-up** quick action (sparkle icon; "AI Follow-up" on ≥sm, "AI" on mobile) on every lead row in `pages/Leads.jsx`, next to Call/WhatsApp/Email. It calls `openAI(l)` → opens that lead's existing detail modal → scrolls to `#lead-ai-section` (the existing AI panel). No duplicate AI component; `LeadsDialog.jsx` left unused. Verified: compiles; `/ai/followup` still returns draft-only (provider openai:gpt-5.4), no auto-send.

## COMMERCIAL CORE V1 — Billing + Super Admin Pricing Control + Referral Engine (2026-06, iteration 15) — IMPLEMENTED & QA-PASSED (BE 17/17, FE 9/9)
User-approved commercial rules enforced; provider-neutral (NO real payment provider connected). All commercial config is DB-driven and Super-Admin editable (no code changes needed to change pricing).
- **DB-driven config** (`platform_v1.py` `commercial_config` collection, `get_commercial_config()` seeds `DEFAULT_COMMERCIAL_CONFIG`): trial{enabled,days=14}, plans.pro{price_month 9.99, price_year 99.99, annual_discount_pct 17}, plans.team{price_seat_month 5, price_seat_year 50, min_seats 3, annual_discount_pct 17}, referral{enabled, referred_discount_month/year_pct 20, referrer_reward_pct 20, max_reward_discount_pct 50}, default_market USD, regional_pricing for **USD/AED/SAR/EUR/GBP** (explicit per-market prices — NO FX conversion). `TRIAL_DAYS`/`PRICES` kept only as legacy fallback.
- **Endpoints**: `GET /api/commercial/pricing?market=` (public, resolves market, USD fallback); `GET /api/billing` (plan/status/trial/usage{cards,ai,scanner}/commercial.pricing/discount/demo_billing); `POST /api/billing/subscribe` (provider-neutral demo activation, guarded by env `ALLOW_DEMO_BILLING` default true → returns 402 when disabled; preserves referral linkage; team seats bumped to config min); `POST /api/billing/cancel` (cancel_at_period_end); `GET/PUT /api/admin/commercial` (SUPER_ADMIN only; deep-merge; validation 400 on bad market/min_seats/non-numeric or out-of-range referral pct).
- **Enforcement** (already backend source of truth): trial=1 card/10 AI total/10 scans total; `enforce_quota` 402 when inactive / 403 not-on-plan / 429 over limit; card-create 402 over max (server.py ~555); public card 410 when subscription inactive (server.py ~348) — data/slug/QR/NFC preserved, reactivation restores.
- **Registration** now uses config trial days (0 ⇒ start trial_expired if trials disabled) and generates a `referral_code`.
- **Referral engine** (internal, no cash, no real billing): `_apply_referral()` on register with `referral_code` → referred-customer discount stored on their `subscription.referral`; referrer `referral_rewards` ledger accrues `referrer_reward_pct` per referral **capped at max_reward_discount_pct**, overflow → `queued_pct`; anti-self-referral (not same workspace, not same owner email); a workspace can be referred only once. `GET /api/referral` → code, share_url (`/register?ref=CODE`), referred_count, reward ledger, referred_as. Verified cap: 3×20% → applied 50 / queued 10.
- **Frontend**: `pages/Billing.jsx` at `/billing` (premium dark: status/trial banner, usage meters, Monthly/Annual toggle, market selector, Trial/Pro/Team/Enterprise plan cards with upgrade/reactivate/cancel CTAs → `/billing/subscribe`, live referral card with code+copy+reward). `pages/CommercialSettings.jsx` at `/admin/commercial` (SUPER_ADMIN: edit trial/pro/team/referral + regional pricing table for all 5 markets, Save persists). `OwnerNav` Billing pill (Receipt icon). `SuperAdmin` deep-link "Commercial & Pricing". `Register.jsx` captures `?ref=` → referral banner. Localized EN/AR/ES (new `billing` i18n block).
- **DEMO GUARD (highlighted)**: upgrade activation is DEMO/TEST behavior only via `ALLOW_DEMO_BILLING`; a future payment provider must become the authoritative activation source before production. NO Stripe connected.
- QA (iteration_15): backend 17/17 pytest (`/app/backend/tests/test_commercial_core.py`), frontend 9/9. Post-review hardening: non-numeric referral pct now 400 (was 500). feras-askar preserved; all qa_ throwaway accounts cleaned.

## LANDING CURRENCY AUTO-DETECT (2026-06, iteration 15c) — IMPLEMENTED & verified
Public pricing auto-selects the visitor's market using ONLY safe browser/locale signals — no external geolocation provider, no FX conversion. Detection is a DEFAULT; manual choice always wins and persists.
- **`lib/market.js`**: `detectMarket()` (locale region via `Intl.Locale(navigator.language).region` → country, e.g. ar-AE→AE→AED; secondary timezone hints Asia/Dubai→AE, Asia/Riyadh→SA, Europe/London→GB, generic Europe/*→EUR); `countryToMarket()` (AE→AED, SA→SAR, GB→GBP, Eurozone set→EUR, US→USD); `getPreferredMarket(supported, fallback)` = saved manual pref (localStorage `tp_market`) → detected → configured default; only returns a market present in the configured `markets`, else safe fallback (USD). `saveMarketPreference()`.
- **PricingSection**: on mount picks preferred market and loads `/api/commercial/pricing?market=`; manual `changeMarket()` saves + reloads. All prices from authoritative config; JSON-LD SEO uses the resolved config. Billing unchanged (defaults to workspace region currency).
- **Verified (isolated browser contexts)**: UAE→AED, Saudi→SAR, UK→GBP, US→USD, Germany→EUR, Japan(unsupported)→USD fallback, and manual USD pref persisted over UAE locale. Missing-market + regional-price fallback handled by backend `resolve_market_pricing` (verified earlier). Landing↔Billing consistency + Super-Admin-price-change propagation verified in the 9-step curl test.

## REMAINING SAFE ROADMAP (approved, auto-continue) — NEXT
- **Full EN/AR/ES localization coverage**: Meetings, Leads, CreateCard/editor, Scanner, Analytics dialog, internal admin tools, login/register/marketing.
- **Consent / Privacy Center** (audit-first; additive cookie/consent + privacy hub without touching sensitive delete/export semantics).
- **Scanner commercial exposure** deeper surfacing (usage already on Billing).
- **DEFERRED EXTERNAL**: Stripe/RevenueCat/social login/Wallet certs/email/push/SMS/CRM/DNS/SSO/App Store; auth hardening/2FA; destructive cleanup.

## PRICING SINGLE SOURCE OF TRUTH — Public site + dedicated Referral page (2026-06, iteration 15b) — IMPLEMENTED & verified
User directive: ONE authoritative pricing config across Super Admin → Billing → Public site → trial messaging → referral. No hard-coded prices anywhere; annual savings DERIVED from prices.
- **Backend**: `resolve_market_pricing()` now returns DERIVED `pro_annual_savings_pct` / `team_annual_savings_pct` via `_annual_savings_pct(monthly, yearly) = round((1 - annual/(monthly*12))*100)`. `/api/commercial/pricing` (public, market-resolved, USD fallback) feeds both the landing and Billing.
- **Public landing** `components/landing/PricingSection.jsx` (`#pricing`, added to nav): fetches `/api/commercial/pricing`, Monthly/Annual toggle, market selector (USD/AED/SAR/EUR/GBP), Trial/Pro/Team/Enterprise cards, trial-days + referral promo line, and JSON-LD (schema.org Product/Offers) reflecting the SAME resolved config. NO independent price data.
- **Billing** now shows DERIVED savings (`pricing.*_annual_savings_pct`) instead of the stored `annual_discount_pct`.
- **Dedicated Referral page** `pages/Referral.jsx` at `/referral` (+ nav Gift pill, EN/AR/ES): code, share link, copy/native-share, stats (referred count / reward applied w/ cap / queued), referred-as note, how-it-works, fair-use. Reuses `GET /api/referral` (authoritative referral config).
- **Verified (curl, 9-step)**: change Pro monthly → BOTH public + billing update (same value); change Pro annual → savings auto-recalc (e.g. 11.99mo/109.99yr → 24%); change GBP regional price → correct market price resolves; MEMBER PUT /admin/commercial → 403; referral values come from authoritative config. Landing + Billing + Referral pages screenshot-verified rendering from config. Config reverted to approved defaults (9.99/99.99, Save 17%).







