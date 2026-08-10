# TapPresence — Full Product Status Report (audit-only, code-verified)
Date: 2026-06 · Method: direct inspection of backend routes, PLAN_ENTITLEMENTS, /api/config, .env, frontend pages/locales, tests. No implementation performed.

Legend: ✅ COMPLETE · 🟠 PARTIAL · 🔴 NOT BUILT · 🔵 EXTERNAL/BLOCKED · ⚪ NOT NEEDED · STUB · NOT VERIFIED

---
## 1. EXECUTIVE SUMMARY (not inflated)
- Overall product completion: **~72%**
- Core individual product: **~90%**
- Team / Business product: **~75%**
- Enterprise readiness: **~35%**
- Native / mobile readiness: **~5%** (no native app; responsive web only)
- External integrations readiness: **~10%** (only AI is live; everything else is stub/not configured)
- Launch readiness (commercial): **~60–65%**

**What TapPresence can genuinely do today:** A single person can register (14-day trial auto-starts), build one or more premium digital cards (3 templates, industry theming, RTL, multilingual), publish a public profile with branded QR (TP logo centered, scan-verified) + VCF + native share + NFC tap redirect, capture leads (rich contact fields + 7-stage pipeline + tags/notes/event), scan business cards/badges (LLM OCR) and contact QR/vCard (client-side) into leads, run Event Capture Mode, follow up (AI drafts + call/WhatsApp/email + Book Meeting + Remind Me + "Follow Up Today"), book meetings natively (availability, types, timezone, reschedule/cancel, ?book deep-link), view real analytics (funnel + channel/card/source/event/campaign/team breakdowns), run teams (invite/roles/CSV import/brand-lock/seats), generate email signatures with a booking CTA, and use a referral program (invite 5 → 1 free month). AI (scanner + follow-up) is the only live external service.

**Real blockers before commercial launch:**
1. 🔴/🔵 **No real payment provider.** Billing is demo-only (`ALLOW_DEMO_BILLING` default true); Stripe is coded-for but not connected. You cannot actually charge anyone.
2. 🔵 **No email delivery.** Verification / password-reset / notifications only *log* links — no provider (`EMAIL_API_KEY` empty). Forgot-password is not usable end-to-end.
3. 🟠 **User-visible legacy "ARIADNI ID" strings remain** (3 locale testimonial/CTA keys, the downloadable poster, one seed workspace name).
4. 🟠 **CORS is `*`** (safe-ish because auth is Bearer, credentials disabled — but should be restricted for prod).
5. 🟠 **Email verification is generated but not enforced** at login (acceptable interim, but note it).

---
## 2–3. FEATURE INVENTORY BY AREA (verified)

### A. Authentication & Account
- ✅ Registration (JWT, bcrypt, 14-day trial auto-provisioned, workspace+membership created)
- ✅ Login (rate-limited 30/5min, lockout after 5 fails → 429)
- ✅ Logout / session list / revoke session / refresh-token rotation
- ✅ Account settings / profile settings (Settings.jsx)
- ✅ 14-day trial + trial expiration (auto-expire → `trial_expired`, locks premium actions & public card, data preserved)
- ✅ Plan enforcement (`enforce_quota`, 402/403/429)
- ✅ Account deletion (cascade: owned ws + cards/leads/analytics/meetings/notifs/referrals/keys/webhooks; shared-ws only removes own membership) + Data export (`/account/export`)
- 🟠 Email verification — token created & endpoint works, but **email not sent** (logged only) and **not enforced at login** → 🔵 blocked on email provider
- 🟠 Forgot/reset password — fully coded, but reset link only logged → 🔵 not deliverable without email provider
- 🔴 2FA/MFA (only an unused shadcn OTP UI primitive exists) · 🔴 Social login (OAuth env empty)
- ✅ Auth hardening (rate limit + lockout + no account-existence leak on forgot)

### B. Billing & Plans
- Real plans (runtime commercial config): **Pro $9.99/mo · $99.99/yr**, **Team $5/seat/mo · $50/seat/yr (min 3 seats)**, **Enterprise (custom)**, **14-day trial**. Regional pricing USD/AED/SAR/EUR/GBP. Annual discount 17%.
- ✅ Trial, entitlements, feature gating, usage limits (`usage_counters`, monthly/total)
- ✅ Upgrade/subscribe + cancel (`cancel_at_period_end`) + regional currency + market selection
- 🟠 **Demo billing only** (`/billing/subscribe` guarded by ALLOW_DEMO_BILLING) — 🔵 real charging blocked on Stripe
- 🔴 Invoices/receipts, failed-payment handling, grace period, hosted billing portal, annual/monthly proration — not built (provider-dependent)
- 🔵 Stripe (env empty), RevenueCat (env empty)
- ⚪ **Free plan — intentionally absent from UI** (correct). ⚠️ Stale artifacts: `PLAN_ENTITLEMENTS["free"]` (grandfather fallback), `DEFAULT_PLANS` free `public:true`, and `Team.jsx` badge fallback `ws.plan || "free"`. Not shown on pricing, but should be cleaned to avoid confusion.

### C. Digital Cards
- ✅ Multiple cards per workspace, create, delete, **duplicate**, editor, draft/publish, public URL + slug, profile photo, cover/background, contact/company/job title, social + custom links, CTA, services, booking CTA, 3 templates, accent colors, industry personalization, custom backgrounds, RTL rendering, multilingual content, preview, mobile responsive, plan card quotas (trial 1 / pro 3 / team unlimited).
- 🟠 Card ordering/sorting — NOT VERIFIED (no explicit sort endpoint seen). 
- ⚪ "Default card" / Presence abstraction — intentionally NOT built (correct).

### D. Sharing
- ✅ Public link, copy, native Web Share (+clipboard fallback), QR with tracking, **TP logo centered in QR (H error-correction, scan-verified)**, VCF/Save Contact, WhatsApp/email share.
- ✅ NFC: activation, **destination reassignment/rebind**, device list, **NFC management page (/nfc)**, tap redirect + nfctap analytics.
- 🔵 Apple Wallet / Google Wallet — **STUB** (pass payload built, returns "Not Configured"; needs certs).
- 🔴 Offline sharing beyond QR/NFC, home-screen widget — not built (deferred).

### E. Leads / Contacts (intentionally lightweight — not a full CRM ✅)
- ✅ Capture form, inbox, contact details, company, job title, website, tags, notes, met_at, event, campaign, captured_by, source, card attribution, next_follow_up, 7-stage pipeline (new/contacted/qualified/meeting/opportunity/customer/not_interested + legacy aliases), search/filter, edit (`/fields`), delete, mark-read, ownership + team visibility rules, CSV **export** (`/crm/leads.csv`).
- 🟠 Duplicate handling — NOT VERIFIED (no dedupe logic seen). 
- 🔴 Lead CSV **import** (only team-member CSV import exists, not leads).
- Note: a second `/crm/leads` router exists (uppercase statuses) but is **unused by the frontend** — legacy, safe to ignore/retire.

### F. Follow-Up
- ✅ AI follow-up drafts (`/ai/followup`, quota-gated, live via EMERGENT_LLM_KEY), Email/WhatsApp/Call actions, Book Meeting (native dialog prefilled), Remind Me (sets next_follow_up + one due-gated notification, replace/cancel dedup), **Follow Up Today** dashboard section (due + overdue), edit/cancel reminders.
- ✅ Notification integration (in-app). ⚪ AI Notetaker / call & meeting recording — correctly NOT built.

### G. Scanner (Universal)
- ✅ Business card + event badge (LLM OCR, gpt-5.4 vision, live), QR + contact-QR (vCard/MECARD/mailto/tel/URL) decoded **client-side** (jsQR), auto-detect (QR first → OCR fallback), review → confirm → single Lead, **Event Capture Mode** (persisted, auto-tags event/campaign), error handling, entitlement + usage limits (trial 10 total / pro 50-mo / team 100-mo).
- 🟠 Fully offline capability — QR decode is offline, but saving the lead needs the API (online).

### H. Meetings
- ✅ Public + internal booking, booking page, availability, meeting types, duration, timezone, meeting links (manage token), reschedule, cancel, propose-time/accept-proposal, status, lead association, **signature ?book=1 deep-link (template-agnostic)**, external booking URL support, meeting counts in analytics.
- 🔵 Google/Microsoft calendar sync — NOT built (no OAuth). 🟠 Meeting analytics = counts only (booked/completed), no dedicated meetings dashboard.

### I. Analytics
- ✅ Card views, QR scans, NFC taps, CTA/link taps, contact saves (tap keys), leads, meetings; funnel (views→engaged→leads→booked→completed); trend series; top actions; **breakdowns**: by card, by channel (Direct/QR/NFC/Scanner), by source, by event, by campaign, by team member; per-campaign stats endpoint.
- 🔴 **Date-range selector** — only a fixed `days` param (dashboard hard-codes 30); no UI picker → *suggested only*.
- 🔴 **Analytics export** → *suggested only*.
- 🔴 **Event leaderboard** — data exists (by_event/by_member) but no ranked leaderboard UI → *suggested only*.

### J. Campaigns / Events
- ✅ Campaign create/list/stats, Event Capture Mode, card/source/event/campaign attribution on leads, team-member attribution, leads-per-event, meetings via analytics. ⚪ Complex "Event Intelligence" — correctly avoided.

### K. Teams / Companies
- ✅ Workspace model, invite/remove members, roles (OWNER/ADMIN/MANAGER/MEMBER), permission scoping, card ownership (`owner_user_id`), team cards, **CSV member import**, corporate branding + locked fields, seat enforcement, **team-plan gating (402 on trial)**, multi-tenant isolation (backend-authoritative), team analytics via overview.
- 🟠 **Preview data drift**: member accounts (feras@/mona@/luis@) currently own no cards (prior pruning) — data condition, not a code bug. 🟠 No dedicated team-billing seat management UI beyond subscribe seats.

### L. Email Signatures
- ✅ Signature Manager, 3 templates, live preview, copy (HTML/rich), card association, **Book-a-Meeting CTA + ?book deep-link**, external booking URL via card.
- 🔴 Team/centralized signature templates, brand-lock on signatures, signature analytics — not built. ⚪ Signature Gallery — no genuine usability gap; skip.

### M. Notifications
- ✅ Notification Center, read/unread/read-all, ownership-aware visibility, reminder notifications (due-gated). Lead/meeting/referral notifications: emitted in some flows (NOT FULLY VERIFIED which events write notifications).
- 🔴 Notification preferences, email/push delivery (in-app only; push env empty).

### N. Referral System (approved model — verified)
- ✅ referral_code per workspace, referred_by linkage, card/source attribution, signup tracking (`status: signed_up`), **paid qualification only** (`record_paid_subscription_event` → `_qualify_referral`; signup/trial/checkout-initiation do NOT qualify), 5-per-reward threshold (config), idempotent reward ledger (floor(qualified/5) free months), progress + reward UI, referral CTA + **referral QR**, **anti-self-referral** (not same ws/owner), referred-customer discount preserved across activation.
- ✅ Confirmed: rewards are NOT granted on mere signup.

### O. Localization & Global Readiness
- ✅ EN/AR/ES, **680 leaf keys, all three in sync**, browser auto-detect + manual override + persistence (`ariadni_lang`), true `<html dir="rtl">` for Arabic, localized across public pages/dashboard/editor/leads/meetings/scanner/analytics/settings/billing/referral/signatures/notifications/teams; currency detection + market selection + language↔currency independence + regional pricing; country/timezone/locale at registration; tax fields on workspace (architecture only).
- 🟠 3 locale keys still say "ARIADNI ID" (testimonials/CTA). 🟠 Tax = data fields only (no tax calc/VAT engine).

### P. Admin / Platform Management (product Super Admin ≠ workspace admin)
- ✅ Super Admin: platform overview (workspaces/users/memberships/leads/meetings), Commercial & Pricing config (plans/trial/referral/markets), Industry Studio, industries CRUD, mint NFC, sees-all scoping.
- 🔴 User management CRUD, per-workspace billing override, feature-flag toggles UI, abuse/ban controls, support tooling — not built (PARTIAL admin).

### Q. Security & Privacy
- ✅ bcrypt passwords, JWT access+refresh, rate limiting, login lockout, RBAC + tenant isolation (backend-authoritative), input validation (Pydantic), API authorization, audit_logs, data export, account deletion cascade, cookie/analytics consent + Privacy Center, secure uploads (`/upload` + served files).
- 🟠 CORS `*` (credentials disabled — OK for Bearer, restrict for prod). 🔴 2FA/MFA, SSO/SAML, SCIM.
- 🔵/🔴 **SOC 2 / ISO 27001 / GDPR certification — NOT achieved** (consent controls exist; no certification basis). Do not claim compliance.

### R. Integrations (only AI is live)
| Integration | Status |
|---|---|
| AI (Emergent LLM / OpenAI vision+text) | ✅ Working (scanner OCR + follow-up drafts) |
| Generic API keys + signed outbound webhooks (Integration Hub) | ✅ Working (real HMAC-signed dispatch) |
| Stripe | 🔵 Not configured (demo billing only) |
| RevenueCat | 🔵 Not configured |
| Apple Wallet / Google Wallet | STUB / Not configured |
| HubSpot / Salesforce / Pipedrive | STUB (config flags only, false) |
| Zapier | 🟠 = the generic webhook (no dedicated Zapier app) |
| Google / Microsoft Calendar | 🔴 Not built |
| Email provider (Resend/SendGrid) | 🔵 Not configured (adapters/logging only) |
| SMS / Push | 🔴 Not configured |
| Social login (Apple/Google OAuth) | 🔵 Not configured |
| SSO / SCIM / DNS custom domains | 🔴 Not built |
| Error monitoring (Sentry) | 🔵 Not configured |

### S. Native Apps
- 🔴 **No iOS app, no Android app, no native scanner/NFC/wallet module, no mobile widget, no push, no App Store/Play readiness.** Product is a responsive web app only.

### T. Landing / Marketing
- ✅ Landing, pricing (Billing), login/register, features, teams messaging, industry positioning/showcase, responsive, index.html title/description/OG/theme/fonts, legal links (structure), enterprise → sales@tappresence.com, referral acquisition CTA, TapPresence branding + TP mark.
- 🟠 Legal pages are **placeholder policy text** (structure/branding only) — real Terms/Privacy needed before launch. 🟠 SEO basic (no sitemap/robots verified). 🟠 Dedicated localized marketing pages beyond landing — minimal.

---
## 4. LEGACY / BRAND CLEANUP REPORT
**Safe internal (do NOT rename without migration):**
- `ariadni_lang`, `ariadni_token`, `ariadni_refresh` (localStorage keys); `AriadniMark` React component name; `APP_NAME="ariadni-id"`; `logger "ariadni.platform"`; platform_v1/seed_data docstrings; root API message "ARIADNI ID API".

**User-visible legacy (fix before launch):**
- `en/ar/es.json` keys `…desc`, `…appTitle`, `…subtitle` → contain "ARIADNI ID" (testimonials/CTA).
- `server.py` poster endpoint prints `"ARIADNI ID"` on the downloadable QR poster.
- `platform_v1.py` seed workspace `"name": "ARIADNI HQ"` (visible in Super Admin).

**Test/demo legacy data:** `admin@ariadni.id` (SUPER_ADMIN seed), demo card `feras-askar`, member seeds → keep for now (test), replace/scrub before production go-live.

Recommendation: fix the 3 user-visible items pre-launch; keep internal identifiers; scrub demo accounts at go-live. No destructive cleanup performed.

---
## 5. TEST COVERAGE STATUS
| Module | Backend | Frontend | E2E | Last iteration | Result |
|---|---|---|---|---|---|
| Leads P0 (fields/pipeline/remind) | ✅ | ✅ | ✅ | 22 | Pass |
| Follow-up actions / Book / Remind | ✅ | ✅ | ✅ | 22, 24 | Pass |
| Universal Scanner (QR+OCR) | ✅ | ✅ | ✅ | 22, 24 | Pass |
| NFC destination UX | ✅ | ✅ | ✅ | 22 | Pass |
| Analytics breakdowns | ✅ | ✅ | ✅ | 23 | Pass |
| Branded QR (decode-verified) | ✅ | ✅ | — | 23 | Pass |
| Follow Up Today | ✅ | ✅ | ✅ | 24 | Pass |
| Event Capture Mode | ✅ | ✅ | ✅ | 24 | Pass |
| Signature booking deep-link | ✅ | ✅ | ✅ | 24 (fixed post-report) | Pass (self-verified screenshot) |
| Referral lifecycle | ✅ | ✅ | ✅ | 19–21 | Pass |
| Commercial/pricing/trial/quotas | ✅ | 🟠 | 🟠 | 16–18 | Pass (not recently re-run) |
| Teams/roles/CSV/brand-lock | ✅ | 🟠 | 🟠 | ~14–18 | Pass (not recently regressed) |
| Meetings (book/reschedule/propose) | ✅ | 🟠 | 🟠 | 13–14 | Pass (not recently regressed) |
| Auth (login/lockout/reset/delete/export) | ✅ | 🟠 | — | 18 | Pass |
| Localization/RTL | 🟠 | 🟠 | — | various | Partly verified |

**Untested edge cases / gaps:** real payment webhooks (none), email delivery (none), lead dedupe, card ordering, notification emission per event type, concurrency on usage counters, large-team seat edge cases, full cross-module regression (auth+billing+teams+meetings together) not run since early iterations.

---
## 6. PLAN / ENTITLEMENT MATRIX (actual, from PLAN_ENTITLEMENTS)
| Entitlement | trial | pro | team | enterprise | free* (legacy) | white_label* |
|---|---|---|---|---|---|---|
| max_cards | 1 | 3 | 9999 | 99999 | 1 | 99999 |
| premium_templates | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| analytics | full | full | full | full | full | full |
| analytics_months | 1 | 12 | 24 | 0(∞) | 12 | 0(∞) |
| leads / crm / campaigns / wallet | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| ai_followup (limit/period) | 10/total | 100/mo | 100/mo | 1M/mo | 100/mo | 1M/mo |
| scanner (limit/period) | 10/total | 50/mo | 100/mo | 1M/mo | 50/mo | 1M/mo |
| team | ✗ | ✗ | ✓ | ✓ | ✗ | ✓ |
| remove_branding | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ |
| white_label | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ |
| custom_domain | ✗ | ✗ | ✓ | ✓ | ✗ | ✓ |
| api | ✗ | ✗ | ✓ | ✓ | ✗ | ✓ |
Prices (config): Pro $9.99/mo·$99.99/yr; Team $5/seat/mo·$50/seat/yr (min 3); Enterprise custom. Trial = 14 days.

**Stale/conflict flags (do NOT modify yet):**
- `free` entitlement + `DEFAULT_PLANS` free `public:true` + `Team.jsx` "free" badge fallback conflict with "no Free plan." Currently harmless (not shown on pricing) but should be retired/renamed to `grandfathered`.
- `remove_branding:true` on `pro`/`free`/`team` conflicts with the decision to NOT ship Remove-Branding — it's an unused flag today (no UI), but review before it surfaces.
- `white_label` plan + flags exist internally though white-label is out of scope — keep dormant.

---
## 7. REMAINING WORK — PRIORITIZED

### 🔴 MUST FIX BEFORE LAUNCH
1. **Real payments (Stripe)** — value: you literally cannot collect money without it. Difficulty: Medium. Extend existing provider-neutral billing + the `record_paid_subscription_event` webhook hook. External: Stripe account/keys. Regression risk: Medium (billing/entitlements/referral qualification). Timing: first.
2. **Email delivery provider** — value: verification, password reset, and reminders are undeliverable today. Difficulty: Low–Medium. Extend existing email adapter hook. External: Resend/SendGrid key. Regression: Low. Timing: first.
3. **Remove user-visible legacy "ARIADNI ID"** (3 locale keys, poster, seed ws name). Value: brand integrity. Difficulty: Low. Extend existing. External: none. Regression: Low.
4. **Real Terms/Privacy legal content.** Value: legal/compliance to charge users. Difficulty: Low (content) — needs your approved text. External: legal text. Regression: none.
5. **Restrict CORS + scrub demo/admin seed accounts** at go-live. Difficulty: Low. Regression: Low (verify frontend origin).

### 🟠 HIGH VALUE AFTER CORE
6. **Analytics date-range picker** (7/30/90/custom). Value: real comparison/insight. Difficulty: Low. Extend existing overview (already accepts `days`). Regression: Low.
7. **Enforce email verification (soft gate)** once email works. Difficulty: Low. Regression: Low.
8. **Event leaderboard view** (reuse by_event/by_member data). Value: events/teams ROI. Difficulty: Low. Regression: Low.
9. **Retire stale `free`/`remove_branding`/`white_label` flags** to match strategy. Difficulty: Low. Regression: Medium (entitlement resolution) — test carefully.
10. **Analytics export (CSV)**. Difficulty: Low. Value: medium.
11. **Lead dedupe on capture/scan** (merge by email/phone). Value: cleaner CRM. Difficulty: Medium. Regression: Medium.

### 🟡 EXTERNAL / REQUIRES APPROVAL
- Apple/Google Wallet (certs/issuer), Google/MS Calendar sync (OAuth), Contact enrichment provider, HubSpot/Salesforce/Zapier connectors, Social login (OAuth), Push/SMS, custom domains/DNS, Sentry, RevenueCat, SSO/SCIM (enterprise). Each requires provider credentials/approval; adapters/architecture partly exist.

### ⚪ SKIP / LOW VALUE (do not spend credits)
- Free plan, Multiple Presences abstraction, Remove-Branding feature, decorative QR customization, AI Notetaker, call/meeting recording, Signature Gallery, native app "for parity", complex Event Intelligence.

---
## 8. FINAL "WHAT IS LEFT?"

### Required for commercial launch (no duplicates, no parity fluff)
1. Connect Stripe (real charging, webhooks → existing entitlement + referral-qualification hooks).
2. Connect an email provider (verification, password reset, reminder delivery).
3. Enforce email verification once email works.
4. Replace user-visible "ARIADNI ID" strings (locales, poster, seed ws name).
5. Real Terms of Service + Privacy Policy content.
6. Restrict CORS to production domains; scrub demo/seed accounts.
7. Basic invoices/receipts + failed-payment/cancellation handling (comes with Stripe).
8. Retire/relabel stale `free`/`white_label`/`remove_branding` entitlement flags to match the no-Free strategy.
9. Full cross-module regression (auth + billing + teams + meetings + leads) before go-live.

### Nice-to-have (safe to defer post-launch)
1. Analytics date-range picker + CSV export + event leaderboard.
2. Wallet passes (Apple/Google), calendar sync (Google/MS).
3. Contact enrichment, CRM connectors (HubSpot/Salesforce/Zapier app), social login.
4. Lead dedupe/merge, notification preferences + email/push delivery.
5. Team/centralized signature templates + signature brand-lock.
6. Native apps, push/SMS, custom domains, SSO/SCIM, SOC2/ISO program.

Audit only — nothing implemented. Awaiting your decision on the launch roadmap.
