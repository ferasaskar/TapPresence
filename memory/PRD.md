# TapPresence (formerly ARIADNI ID) — Product Requirements & Build Log

## CORRECTION (2026-06): Template CTA task — reverted edits to OLD/HIDDEN templates
Earlier in this session I mistakenly added Exchange Contact + Book a Meeting to `BeigeLuxuryExecutive.jsx` and `FutureProfessional.jsx`. Those are OLD/HIDDEN/DEPRECATED templates (no user-facing picker exposes them; kept only for backward-compat rendering of legacy cards). Per user, hidden templates must NOT be modified. Both files were reverted via `git checkout d281f2a -- ...` to their exact original state (verified: additions removed, app compiles).
Template active/hidden truth (verified from code):
- NEW/CURRENT ACTIVE template offered to all new cards: **Executive Black Gold** (`executive-black-gold`) — set as the sole default in `components/admin/CardInfoTabs.jsx` `emptyCard.templateId`; the `/templates` studio (`pages/CreateCard.jsx`) has NO template-name picker (only Industry + accent), so users cannot select other templates. Executive Black Gold ALREADY has Exchange Contact + Book a Meeting → nothing to add.
- OLD/HIDDEN/DEPRECATED (backward-compat only, not selectable): **Beige Luxury Executive** (`beige-luxury`), **Future Professional** (`future-professional`).
- `components/templates/TemplateRenderer.jsx` still maps all 3 templateIds for rendering legacy cards; its `TEMPLATES` array is used ONLY as a name-label lookup in `pages/Admin.jsx` (`tplName`), NOT as a picker.



## EXCHANGE CONTACT + BOOK A MEETING CTAs ON ALL TEMPLATES (2026-06, preview only — NOT deployed) — IMPLEMENTED & screenshot-verified (desktop + mobile, all 3 templates)
Previously only ExecutiveBlackGold had the two large CTAs. Added the SAME shared functionality to the other two templates, styled to each:
- `BeigeLuxuryExecutive.jsx` and `FutureProfessional.jsx` now render **Exchange Contact** (opens shared `ExchangeContactDialog`) + **Book a Meeting** (opens shared `BookMeetingDialog` when `booking.nativeEnabled`, else external `bookingUrl` link). Reuses existing components/APIs — no new booking/exchange logic. Book a Meeting is gated by `nativeEnabled || bookingUrl` (hidden when booking not configured; Exchange spans full width then). Uses `useProfile().track` for tap analytics like the reference template.
- Styled per template (Beige: ink/ivory outline; Future: gradient + glass). Renamed each template's pre-existing framed booking CTA testid to `cta-consult-button` to avoid duplicate `cta-book-button`; new primary CTA row testid `cta-bar-primary`.
- Verified: feras-askar (beige, booking ON) → both buttons + book dialog opens; edrina-cepele (executive, booking OFF) → Exchange shown, Book correctly hidden (existing "Send a message" fallback); future-professional (temporarily applied to feras, then reverted to beige-luxury) → both buttons + both dialogs open; desktop 1280 + mobile 390.
- Google Sign-In / Calendar OAuth untouched. Not deployed to production.



## GOOGLE CALENDAR INTEGRATION (2026-06, preview/staging only — NOT deployed to prod) — IMPLEMENTED, backend curl-verified + UI smoke-verified; live OAuth round-trip requires manual test
Separate OAuth flow from Sign-In (own callback/scope) so the working Sign-In is untouched. Scope: `openid email https://www.googleapis.com/auth/calendar.events` (minimum), access_type=offline, prompt=consent. Reuses GOOGLE_OAUTH_CLIENT_ID/SECRET; new env `GOOGLE_CALENDAR_REDIRECT_URI`.
- Endpoints (server.py, /api): `GET /integrations/google/calendar/status`, `GET /integrations/google/calendar/connect` (XHR → {authorization_url}), `GET /integrations/google/calendar/callback`, `POST /integrations/google/calendar/disconnect` (revokes at Google + deletes record).
- Refresh tokens stored server-side only in Mongo `google_calendar_connections`; never sent to client or logged. Status returns only connected/email/connected_at/needs_reconnect.
- `sync_meeting_calendar()` hooked into booking + cancel + reschedule (guest/admin) + accept-proposal; stores `google_event_id` on the meeting; create/patch/delete on owner's primary calendar; best-effort (never breaks booking); handles revoked grant → needs_reconnect.
- Frontend: Settings → Integrations card (Connect/Disconnect/Reconnect, status badges) at `/settings`.
- ⚠️ Blocker for testing: register the preview calendar redirect URI in Google Cloud. calendar.events is SENSITIVE → needs Google verification before prod (Test Users work in Testing mode). Do NOT deploy to prod until verified.



## GOOGLE OAUTH SIGN-IN (server-side auth-code flow) (2026-06, iteration 32) — IMPLEMENTED & TESTING-AGENT VERIFIED (backend 11/11, frontend 100%)
User choices: backend authorization-code flow (not GIS); new Google users → Individual/Team selection step like normal signup (Individual→trial, Team→enforced min seats); existing email/password users auto-linked by Google-verified email (no duplicates); credentials via env only.

- **Backend** (`platform_v1.py`): `GET /api/auth/google/start` (302→Google consent, signed JWT `state`, scope `openid email profile`), `GET /api/auth/google/callback` (exchanges code via httpx, fetches userinfo, requires `email_verified`; existing user → auto-link `google_id` + issue session → redirect `/auth/google/finish?token=&refresh=`; new user → short-lived signed `gp` pending token → redirect `/register?gp=&email=&name=`), `POST /api/auth/google/complete` (validates `gp`, provisions account with `google_id`, `email_verified=true`, no password). Redirect URI is **env-driven** (`GOOGLE_OAUTH_REDIRECT_URI`) — preview set; production must set to `https://tappresence.com/api/auth/google/callback`. Frontend base derived by stripping the callback suffix.
- **Refactor:** normal `register()` and Google signup now share `_provision_account()` (single auth/workspace architecture, no parallel system). **Bug fixed:** team seat-minimum is now validated BEFORE any DB write, so a below-min team signup no longer leaves an orphaned user / blocks retry.
- **Frontend:** "Continue with Google" / "Sign up with Google" button (`GoogleButton.jsx`) on `/login` + `/register`; `/auth/google/finish` page (`GoogleFinish.jsx`) applies token/refresh via `AuthContext.applyExternalSession` and routes by role; Register **google-mode** (`?gp=`) shows a banner, prefilled read-only email, hidden password, keeps Individual/Team + seat pricing; `/login?google_error=` shows an inline message. i18n EN/AR/ES + RTL. Also fixed: Register title now "Create your account" (was "Create your ID"); auth pages scroll + clear the mobile cookie-consent banner so the signup CTA is reachable.
- **Env:** `backend/.env` has `GOOGLE_OAUTH_CLIENT_ID/SECRET/REDIRECT_URI`. `/api/config` `integrations.google_signin` → true.
- ⚠️ **Not machine-verifiable (needs manual browser test):** the live Google consent handshake (new Individual/Team via Google, existing-user linking), because Google blocks headless automation AND the OAuth consent screen is in **Testing mode** (only allowlisted Test Users can sign in). To go live for all users: publish/verify the consent screen in Google Cloud.

### Google OAuth — production checklist for user
1. Set `GOOGLE_OAUTH_REDIRECT_URI=https://tappresence.com/api/auth/google/callback` in the production environment (preview keeps the preview URL).
2. Redeploy so the OAuth env vars + code reach production.
3. Add your own Google account (and any testers) as **Test Users** on the OAuth consent screen, OR publish/verify the app to allow all users.
4. Manually test: new Individual, new Team, existing-user linking, logout→login-again, and the tappresence.com redirect.



## COMMERCIAL SOURCE-OF-TRUTH + REAL STRIPE CHECKOUT + LANDING/AUTH POLISH (2026-06, iteration 31) — IMPLEMENTED & TESTING-AGENT VERIFIED (backend 10/10, frontend 100%, zero action items)
User choices this phase: (1a) verify E2E, (2b) connect REAL Stripe (Emergent claimable sandbox), (3c) agent picks best visitor template route (→ /industries).

- **Real Stripe checkout (Flow A claimable sandbox).** `backend/.env` has STRIPE_SECRET/PUBLISHABLE/WEBHOOK_SECRET (test) + STRIPE_MODE=test. `ALLOW_DEMO_BILLING=false` → old `/billing/subscribe` demo path returns **402** (no unpaid bypass). New `POST /api/billing/checkout {plan,interval,seats,market,origin_url}` builds a subscription Checkout session with **amount resolved SERVER-SIDE from published commercial_config** (inline price_data, per-seat quantity for Team, remaining trial days honoured). `GET /api/payments/status/{session_id}` (unauth poll, webhook fallback that syncs from Stripe). `POST /api/stripe/webhook` handles checkout.session.completed / invoice.paid / subscription.deleted → `_sync_ws_from_stripe_sub` sets ws.subscription {provider:stripe, stripe_subscription_id, status, current_period_end} and calls record_paid_subscription_event only when active. Frontend: Billing "Upgrade" → Stripe hosted checkout; new `/payment/success` (polls) + `/payment/cancel` pages (pages/PaymentResult.jsx). AuthContext gained `refreshSession`.
  - ⚠️ **Stripe account NOT yet claimed** by user (onboarding_url shared in chat). Hosted-checkout completion with the 4242 test card was **NOT machine-automated** (checkout.stripe.com anti-bot); session creation + redirect + success-poll page + webhook code path verified. Recommend user completes one manual test purchase.
- **Pricing single source of truth (KEY gate — verified).** SUPER_ADMIN Draft→Preview→Publish (`/admin/control/pricing/preview|publish`) writes `commercial_config.regional_pricing`; public `/commercial/pricing`, landing PricingSection, Billing and `/billing/checkout` all resolve from it. Proven: publish pro_month 12.49 → public shows 12.49 → checkout payment_transactions.amount=1249 → reverted 9.99. No hard-coded public prices.
- **Individual vs Team registration.** `/register` offers Individual ('For me') / Team ('For my company or team'). Team shows company name, monthly/annual toggle, seat stepper (min from config = 3, cannot go below), live per-seat total + team total, 14-day trial note. Backend `register()` creates individual→plan trial/pending pro, or company workspace→plan trial/pending team with seats+interval; rejects seats<min (400). Registration = 14-day trial, NO card required. Reuses existing auth/workspace architecture.
- **Auth navigation + brand.** `/login` + `/register` have persistent "Back to TapPresence" (back-to-home) on mobile+desktop, TP mark+wordmark lockup, "Create your account" copy (no "Create your ID").
- **Landing templates from real catalog.** #templates now renders a mobile one-card swipe carousel (template-carousel) of the ACTUAL current template catalog (`lib/industryCards.js` via `IndustryCard`): real_estate/technology/healthcare/finance — full cards, no clipping. "Explore Templates" → /industries. Removed the old fake mock previews.
- **Removed unverified claims.** Hero stats now truthful capability labels (NFC+QR / AI / Wallet / Live) instead of fabricated 50K+/1M+ numbers; testimonials block replaced with unattributed benefit cards (no fake named people / no "Google"). Trial CTA copy → "Start free trial". TP header mark enlarged (h-8) for better hierarchy.
- **QR center mark** enlarged to ~26% with error-correction H + white backing; decode re-verified (pyzbar) → correct profile URL.
- i18n EN/AR/ES updated (stats, testimonialsTitle, startFree); Arabic RTL, no horizontal overflow at 390.

### Remaining / backlog after iter31
- User to **claim the Stripe sandbox** (onboarding link) + complete KYC before deploy; consider one manual 4242 test purchase to confirm webhook→active end-to-end.
- Email provider (Resend) + enforced verification still deferred (reset/verify links only logged).
- Legal substantive copy, custom domains, wallet issuance, native apps — unchanged deferrals.



## LAUNCH HARDENING (2026-06, iteration 25) — DONE & FULL-REGRESSION PASSED (100%, backend 18/18)
Credential-free launch work, all extending existing systems:
- **Branding**: removed all user-visible ARIADNI (3 locale strings, QR poster → "TapPresence", seed ws "TapPresence HQ"). Internal keys (ariadni_lang/token, AriadniMark) intentionally kept.
- **Plan cleanup**: DEFAULT_PLANS free `public:false`, Team.jsx badge fallback → "trial" (no public Free plan). remove_branding/white_label flags left dormant (no UI surfaces them; not touched to avoid entitlement-resolution regressions).
- **Auth flows (NEW frontend)**: `/forgot`, `/reset`, `/verify` pages (AuthExtra.jsx) + `POST /auth/resend-verification` (rate-limited) + unverified banner in OwnerNav. Forgot→reset→login verified end-to-end (email link only LOGGED until provider connected). Verification is soft (not enforced at login) — no lockout of paying users.
- **Leads dedupe**: `find_duplicate_lead` (same-card, normalized email/phone). Public capture merges inbound dupes; scanner returns `{ok:false,duplicate}` unless `force:true` (UI panel: update existing / create anyway).
- **Card list**: deterministic sort by created_at.
- **Analytics**: date-range 7/30/90 (`?days=`), CSV export `/admin/analytics/export.csv`, ranked event/team leaderboard (reuses existing breakdowns).
- **Super Admin ops**: `/admin/platform/users?q=`, `/workspaces?q=`, `POST /users/{id}/suspend` (blocks login, revokes sessions, can't suspend SUPER_ADMIN) + Command Center "Users & Support" UI.
- **Security**: suspend/login-block; CORS already env-driven (`CORS_ORIGINS` — set to prod domains at deploy); rate-limit/lockout preserved.
- **Legal**: production-structured Terms/Privacy/Cookies/Data-deletion (Legal.jsx) with `[[COMPANY FACT]]` placeholders.
- **SEO**: OG/Twitter/canonical meta, robots.txt, sitemap.xml (tappresence.com).

### REMAINING EXTERNAL BLOCKERS (need user input — see chat checklist)
1. **Stripe** — CAN start WITHOUT user keys (Emergent claimable sandbox, Flow A); user only claims via onboarding link + completes KYC before deploy. Next build.
2. **Email (Resend)** — needs user `RESEND_API_KEY` + verified sending domain + from-address.
3. **Legal facts** — company legal name, address, jurisdiction, effective date, DPO/EU-UK rep.
4. **Confirm production domain** = tappresence.com; set CORS_ORIGINS to it at deploy.



## P2 VALUE BATCH (2026-06, iteration 24) — IMPLEMENTED & QA VERIFIED
Three more high-value items, all EXTENDING existing systems (credit-controlled; no duplicate reminder/scanner/signature systems). Testing agent iteration_24: Follow Up Today + Event Capture Mode passed; Signature deep-link initially only worked on the executive template — FIXED and re-verified.

1. **Follow Up Today** (`Home.jsx`, testid `home-followup-today`): dashboard section listing leads whose `next_follow_up` is due today or overdue (computed from the existing `/admin/leads` — no new endpoint), sorted soonest-first, with count badge, Overdue/Due-today labels, Call/WhatsApp/Email quick actions, and row click → `/leads?lead={id}`. Hidden when nothing is due. Reuses P0 reminder architecture.
2. **Event Capture Mode** (`ScanCardDialog.jsx` + `ScanConfirmIn` gained `event`+`campaign`): user enables a capture mode once (event name + optional existing campaign from `GET /campaigns`), persisted in `localStorage tp_event_mode`; while active a green banner shows and EVERY scanned lead auto-inherits that event/campaign (+`event` tag). Easy Switch/Turn-off. Verified: scanned lead carries event/campaign and analytics `by_event`/`by_campaign` reflect it. Reuses existing campaigns/scanner/leads/analytics — no separate event scanner.
3. **Signature Booking Link** (`lib/signature.js` `opts.book` + `Signatures.jsx` `book` toggle + `PublicProfile.jsx`): optional "Book a meeting" button in the email signature linking to `{origin}/{slug}?book=1`. **Deep link handled at the PublicProfile page level (template-agnostic)**: `?book=1` opens the native `BookMeetingDialog` for ANY template when native booking is on, else redirects to the external booking URL. (Removed the earlier per-template ExecutiveBlackGold handler to avoid double dialogs; legacy templates untouched.) Verified on the beige demo card feras-askar.

i18n: added `home.*` (followUpToday/overdue/dueToday), `scan.*` (event-mode strings), `signatures.book` — EN/AR/ES in sync.



## P0 + P1 VALUE ROADMAP (2026-06, iteration 22) — IMPLEMENTED & QA VERIFIED
Extended existing systems only (no new DB, no duplicate scanner/CRM/analytics, no Free plan, no quota changes, no "Presences" abstraction). Backend 20/20 pytest (iteration_22.json), frontend 100% E2E. Uses existing collections/endpoints throughout.

### P0 (all four items — testing_agent verified)
1. **Contacts & Leads enrichment** (`server.py` create_lead / `platform_v1.py` scan_confirm / `Leads.jsx`): new/normalized lead fields company, title, website, tags, notes, event, met_at, captured_by, next_follow_up. New leads now store lowercase `status:"new"` (was "NEW"). Richer 7-stage pipeline replaces the old 6: **new, contacted, qualified, meeting, opportunity, customer, not_interested** with legacy aliases mapped for old data (meeting_booked→meeting, converted→customer, archived→not_interested, won→customer, lost→not_interested, follow_up→contacted) via `normalize_stage()`. New endpoint `PATCH /api/admin/leads/{id}/fields` (LeadFieldsIn) edits contact-context. Lead rows + detail modal show company/title/tags and an editable Contact Details block. CSV export extended (website/event/tags/met_at).
2. **Quick follow-up actions** (`Leads.jsx`): Call / WhatsApp / Email (existing) + **Book Meeting** (reuses `BookMeetingDialog` with new `initialGuest` prefill, scoped to the lead's card) + **Remind Me**. Reminder = `POST/DELETE /api/admin/leads/{id}/remind`: sets `next_follow_up` AND creates ONE in-app notification (type `lead_reminder`, `remind_at`) that stays hidden in `GET /notifications` until due (`remind_at<=now` filter added). Replacing a reminder deletes the prior one (no duplicates); clearing/deleting the lead removes it. Reuses existing Meetings engine, AI drafts, Notification Center — no new follow-up engine.
3. **Universal Scanner** (`ScanCardDialog.jsx` + new `lib/qrContact.js` using `jsqr`): ONE flow — on Scan it first decodes a **contact QR client-side** (offline, free, private): vCard/MECARD/mailto/tel/URL → straight to Review with `source=qr_scan`; if no QR, falls back to the existing LLM OCR for business cards/badges. `SCAN_SOURCES` gained `qr_scan`; `/scan/confirm` unchanged path creates the same Lead. No second scanner/contacts DB.
4. **NFC Destination UX** (new `pages/NfcCards.jsx` at `/nfc`, linked from Settings): lists workspace NFC devices, shows current destination card, and lets the user **re-point a token to any existing card** via the existing `POST /nfc/activate` rebind (no chip re-encode) + Mark lost / Reactivate via existing `/nfc/devices/{token}/status`. Empty state when no devices. Backend rebind already existed — this adds the owner-facing UX only.

### P1 (analytics + campaign attribution + branded QR — self-verified: curl + pyzbar decode + UI screenshot)
5+6. **Analytics breakdowns + campaign/event attribution** (extended the single `GET /api/admin/analytics/overview` + `AnalyticsOverview.jsx`): kept the existing funnel/trend/top-actions and ADDED `channels` (Direct/QR/NFC from view/scan/nfctap events + scanner_leads) and `breakdowns` = by_card (views/leads/meetings), by_source (incl. scanner sources), **by_event**, **by_campaign**, by_member (captured_by → resolved names). Campaign/event attribution folded into this ONE analytics surface (leads carry event/campaign). No second analytics DB/dashboard.
8. **Branded QR** (`server.py _brand_qr`): the existing `/cards/{slug}/qr` now centers the official TapPresence mark (`frontend/public/tp-mark.png`, ~20% size, white backing) with error correction bumped M→**H**. Verified it still decodes to the correct profile URL (pyzbar). No colors/styles/frames/config UI — logo-only, as approved.

### Intentionally SKIPPED/DEFERRED (per user credit-control directive)
- **P1 item 7 Email Signature "improvements": SKIPPED** — the existing Signature Manager already generates email-safe HTML with card data + QR + branding-lock + 3 templates + copy HTML/rich. No high-value gap identified; not rebuilding for roadmap-wording's sake. Will revisit only if the user names a specific need.
- The existing funnel keeps its stages (View→Engaged→Leads→Booked→Completed) rather than renaming to View→Share→Save→Lead→Meeting — same conversion narrative; Share/Save granularity is visible via top_actions + the new channel breakdown. Avoided churning stable localized funnel labels.
- Unchanged/deferred as before: Stripe/live payments, Wallet, enrichment, CRM connectors, mobile widgets, Free plan, quota changes, white-label.

### i18n: added `leads.*` (stages meeting/opportunity/customer/not_interested, contact-detail + reminder + book labels, source_* labels), `scan.*` (universalHint/qrRead/qrReviewIntro), `nfc.*`, `analytics.*` breakdown labels — EN/AR/ES in sync (Arabic RTL). 
### NOTE: In this preview env the member accounts (feras@/mona@/luis@) currently own NO cards (prior test-data pruning) — use SUPER_ADMIN admin@ariadni.id for admin testing. Restored `booking.nativeEnabled=true` on demo card feras-askar (auto-seeds 15/30/45 meeting types) so Book Meeting demos end-to-end.
### Pending: manual user confirmation.



## REFERRAL PHASE 2 — REDEMPTION / NUDGE / CELEBRATION / QUALIFICATION SAFETY + SAMPLE i18n (2026-06, iterations 20–21) — IMPLEMENTED & QA VERIFIED
Extended the existing "Invite 5 → Get 1 Month Free" ledger only (no new referral system). Backend 11/11 + lifecycle pass (iteration_20); dashboard-nudge HIGH fix re-verified 100% (iteration_21). No live payments/external providers activated. Pending manual user confirmation.

- **Reward Redemption View** (`Referral.jsx`): shows free months earned / available / redeemed + per-grant rows. Because live billing is deferred, every unredeemed grant reads **"Earned — will apply when eligible billing is active"**; NOTHING is marked redeemed without a real billing event. `redemption-none` copy when no rewards yet. Provider-neutral — Stripe can later consume `referral_reward_grants`.
- **Dashboard Nudge** (`ReferralNudge.jsx`, mounted in `Home.jsx` ABOVE the cards ternary so it shows for 0-card and populated owners): subtle premium banner, config-driven message (0 qualified → "Invite 5 friends. Get 1 month free."; in-progress → "N more paid referrals to unlock…"; unlocked → "🎉 You earned N free month…"), links to /referral, mini progress dots. Not a popup; reuses existing /referral state.
- **Reward Celebration** (`RewardCelebration.jsx`, CSS confetti, no deps): fires ONCE when `free_months_earned` exceeds `localStorage.tp_referral_earned_seen`; never loops on refresh; localized EN/AR/ES.
- **Qualification safety refactor**: new single idempotent hook `record_paid_subscription_event(ws_id, source, event_id)` (dedup via `billing_events` unique `key`) is the ONLY path that calls `_qualify_referral`. `/billing/subscribe` (demo) now calls it with `source='demo'`; a future Stripe webhook calls it with `source='stripe'` + event id. Pipeline states are now cleanly separated: signup → trial → checkout initiation → **verified paid** → qualified → grant. Checkout initiation alone can never qualify in a real flow.
- **Refund/chargeback room (NOT wired)**: `revoke_referral_qualification(ws_id, reason)` un-qualifies a referral and voids the newest UNREDEEMED grant (redeemed grants never silently revoked); recompute is voided-aware. Final refund eligibility window intentionally left for future approval.
- **Create Studio sample localization**: industry sample cards (`IndustryCard.jsx`) now localize industry label + role + action labels (Call/Email/WhatsApp/Save/Tap your card/Exchange Contact) via `industries.*` + `industryCard.*` (EN/AR/ES, Arabic RTL). Sample person/company names kept as proper nouns.
- **Super Admin**: `referrals_per_reward` (5) + `reward_months` (1) configurable via existing commercial config; threshold flows through nudge/progress/redemption/celebration everywhere (no hardcoding).
- Locales now **669 keys**, EN/AR/ES in sync.

### Known remaining user-visible i18n debt (reported, not in this scope):
Public-card ACTION button labels in the 3 templates + the Create Studio live-preview phone mockup (Exchange Contact / Send a Message / Save / Share / QR / Apple Wallet / Google Wallet) are still English — this is broader public-template-chrome localization touching all renderers; recommend a dedicated pass.



## REFERRAL REWARD MODEL REPLACED (2026-06, iteration 19) — IMPLEMENTED & QA VERIFIED
**Official model now: "Invite 5 Friends. Get 1 Month Free."** This SUPERSEDES the old percentage-based referrer reward (referrer_reward_pct / max_reward_discount_pct / per-cycle cap / overflow queue) — that model is NO LONGER the current rule and its config keys were removed from defaults + code and unset from the stored commercial_config.

- **Qualification**: a referral counts ONLY when the referred user becomes a **qualified paid referral** (subscribes to a paid plan pro/team). Clicks, registration, and trials do NOT count. Attribution still uses the EXISTING referral code (`workspaces.referral_code`) and `referrals` collection — no second system.
- **Referral lifecycle**: `_apply_referral()` at signup now creates a referral in status **`signed_up`** (no reward) and preserves the referred NEW-CUSTOMER discount. `_qualify_referral(referred_ws_id)` (called from `/billing/subscribe` for plan in pro/team) transitions it to **`qualified`** exactly once (idempotent status guard) and recomputes rewards.
- **Reward ledger** (`_recompute_referral_rewards`): `free_months_earned = floor(qualified_count / referrals_per_reward) * reward_months`. Progress continues after each reward (7 qualified = 1 month + 2/5). Durable idempotent grant records in **`referral_reward_grants`** (unique index `referrer_ws_id+index`) — each earned free month is one grant with `redeemed:false`; ready for live-billing redemption WITHOUT rebuilding referral logic. Same referral never counted twice.
- **PRESERVED**: the referred new-customer signup discount (`referred_discount_month_pct`/`year_pct`, default 20%). Anti-self-referral and once-per-workspace guards preserved.
- **Super Admin configurable**: `referral.referrals_per_reward` (default 5), `referral.reward_months` (default 1), `reward_type: free_month`, via existing `/admin/commercial` + CommercialSettings.jsx (fields cfg-ref-per-reward, cfg-ref-reward-months). Note: lowering the threshold recomputes/creates new grants; raising it does not void already-earned grants (safety).
- **`GET /api/referral` new shape**: `{enabled, code, share_url, config{referrals_per_reward, reward_months, reward_type, referred_discount_month_pct}, counts{total, signed_up, qualified}, reward{qualified_count, signed_up_count, per_reward, free_months_earned, free_months_available, progress}, referred_as}`. `get_referral` now guards against orphaned/missing workspace (404 instead of 500).
- **Frontend Referral page**: premium progress section (5 dots, "N of 5 friends subscribed", "X more to unlock", unlocked 🎉 state, stats: total/paid/free-months/next-progress, how-it-works, signup-discount note). Existing sharing preserved (copy/native/WhatsApp/email/QR). Billing referral card shows the new model. Fully localized EN/AR/ES (`referralProgram.*`) with Arabic RTL; `taglineShort` count is config-driven in all three locales.
- **Billing dependency (deferred)**: reward grants are recorded now; **actual monetary application of free months requires live billing activation** (still deferred, provider-neutral). No payment provider activated.
- **QA**: backend 17/17 pytest (`/app/backend/tests/test_iter19_referral.py`) + main-agent lifecycle script (`/app/scripts/test_referral_lifecycle.py`) — signups don't count, 4/5 no reward, idempotent no double-count, 5→1 month, 6→1 month+1/5, 10→2 months, self-referral blocked, admin config change+revert, discount preserved. Frontend 100% (EN/AR/ES + RTL, sharing, QR, Billing). iteration_19.json, retest_needed=false. Pending manual user confirmation.



## P0 PRODUCTION-READINESS + REBRAND PHASE (2026-06, iteration 18) — IMPLEMENTED & QA VERIFIED
Extended existing systems only (no rebuilds). Backend 14/14 pytest pass (iteration_18.json); frontend all P0 flows pass; the one HIGH flagged item (3 residual "ARIADNI ID" strings on Landing) was fixed + self-verified (source + live DOM clean). Pending manual user confirmation.

### Phase 1 — P0 (backend authoritative)
- **Team plan-gating** via existing entitlement engine: `require_team()` + `enforce_seat_limit()` in `platform_v1.py` applied to invite_member, update_member, set_branding, import_members (per-new-member seat check), create_api_key, create_webhook → trial/free/pro get **402**; SUPER_ADMIN/team pass. Verified.
- **Auth abuse protection**: in-memory per-IP `rate_limit()` + Mongo `login_attempts` lockout (5 fails ⇒ 15-min lock, 429). Applied to login (server.py), register/forgot/reset, and cost endpoints scan/ai. Failed-login logging (no passwords). Verified 5×401→6th 429.
- **CORS**: env-driven `CORS_ORIGINS`; `allow_credentials` disabled when wildcard (safe default). expose Retry-After.
- Unused entitlement flags (`custom_domain`, `white_label`) have no exposed endpoints; `api` now gated behind Team via hub key/webhook creation.

### Phase 2 — Data rights
- **Settings → Data & privacy** (`Settings.jsx`): Export (downloads `tappresence-data-*.json` from existing GET /account/export) + Delete account (typed-DELETE confirm dialog) + Privacy Center link. Localized EN/AR/ES.
- **delete_account cascade fixed**: deletes owned-workspace cards/leads/analytics/notifications/meetings/referrals/api-keys/webhooks + user's sessions/usage; for SHARED workspaces only removes the user's membership (preserves others' data). Token revoked after delete. Verified.

### Phase 3 — Partial-feature fixes
- **VCF access rules** (`server.py get_vcard`): now requires `status=published` AND active entitlement → draft/unknown 404, inactive 410. Verified.
- **Localization finished**: Legal (branded + placeholder badge + data-rights note), ExchangeContactDialog, QRBlock, Settings data-rights, public-card not-found — all `t()` EN/AR/ES; public card mirrors card language onto `document.dir` (Arabic RTL). Locales now **596 keys, in sync**.
- **Sharing UX**: Referral page adds one-tap WhatsApp + Email (reuse existing share_url). Public card adds native share button (navigator.share + clipboard fallback).

### Phase 4 — Official TapPresence rebrand (approved)
- All visible ARIADNI/ARIADNI ID → **TapPresence**: Landing (header/footer/body/testimonial), Login, Register, OwnerNav, Billing, Legal, Settings, public-card footers (3 templates), PublicProfile `<title>`, BookingEditor, PricingSection schema, index.html title/description, wallet org fallback (backend).
- Official gold **TP logomark** installed from supplied asset → `/public/tp-mark.png` (+ favicon.png, logo512.png). Header marks swapped from old triangle SVG to the TP image across Landing/OwnerNav/CreateCard/IndustryShowcase/IndustryCard/HeroVisual. theme-color #0B0D12. Arabic uses Tajawal font (index.html + `[dir=rtl]` CSS).
- Localized shared Dialog/Sheet `sr-only` "Close" via i18n singleton (EN Close / AR إغلاق / ES Cerrar).
- **Controlled migration**: legacy storage keys `ariadni_lang`/`ariadni_token` intentionally KEPT (internal `AriadniMark` component identifier also kept — not user-visible). Zero visible ARIADNI remains (source + live DOM verified).

### Phase 5 — Observability + DB
- **GET /api/health** → `{status, db, time}`, no secrets.
- New indexes: referrals(referrer/referred ws), usage_counters, notifications, idempotency_keys(unique), leads.workspace_id, login_attempts(unique), workspaces.referral_code.

### Legal (exception honored)
- Legal page structure + branding + localized labels done; **substantive legal text remains a clearly-marked placeholder** ("pending legal review"). Final Privacy Policy, Terms of Service, GDPR/refund/subscription wording still require approved copy before commercial launch.

### Still deferred (unchanged, need explicit approval): Stripe/live payments, RevenueCat, email provider + enforced verification, Apple/Google Wallet issuance, push/SMS, OAuth/social, CRM connectors, custom domains/DNS, enrichment, native iOS/Android, 2FA, PWA.

### Known minor debt: platform_v1.py >2100 lines (split later); in-memory rate limiter is per-process (move to shared store if multi-worker/multi-pod); Create Studio industry SAMPLE preview content (demo person names/marketing copy in lib/industryCards.js) still EN — chrome localized, sample data not.



## LOCALIZATION COMPLETION + CONSENT/REFERRAL WIRING (2026-06, iteration 17) — IMPLEMENTED & QA 100%
Completes remaining EN/AR/ES coverage and product wiring requested by user. All agent/testing-agent verified (iteration_17.json 100% backend + frontend, retest_needed=false); pending manual user confirmation.
- **Full-body localization** added (locales now 540 keys each, EN/AR/ES in sync):
  - `ScanCardDialog.jsx` — entire capture + review flow (title/desc, source select, camera prompt, retake/capture/camera/upload/scan buttons, all review field labels, save-to-card, language, rescan/save, all toasts) via `scan.*`.
  - `CreateCard.jsx` (route `/templates`) — header, stepper, all 3 step headings/subs, slug field, publish success screen (QR/copy/view/dashboard) via `createCard.*`.
  - `CardInfoTabs.jsx` — all tab triggers + Identity/Contact/Services/Projects field labels, add-service/add-project via `createCard.*`.
  - `CardEditor.jsx` — back/view-live/save, slug/accent labels, published/draft, live-preview, toasts via `createCard.ed_*`.
  - `Leads.jsx` + `AnalyticsDialog.jsx` — completed earlier this turn (`leads.*`, `analytics.*`).
- **Analytics consent gating**: `PublicProfile.jsx` `track()` now blocks POST `/api/cards/{slug}/track` ONLY when `getConsent()?.analytics === false` (explicit reject). Default (null/unset) and accepted → tracking fires. Verified via network: reject=0 calls, accept=4, default=2.
- **Referral discount at registration**: `Register.jsx` fetches `/api/commercial/pricing` when `?ref=` present and shows `auth.referralBannerPct` with code + `referred_discount_month_pct` (e.g. "20% off"); still submits `referral_code` for attribution; no false discount without ref.
- **Localized "Privacy choices"** footer link on Landing → `/privacy-center` (`landing.footer.privacyChoices`), where analytics consent can be re-toggled and saved.
- QA (iteration_17): login, EN/AR/ES bodies on Leads/Scan/CreateCard/Analytics, Arabic `dir=rtl` + 0px horizontal overflow, consent gate 3 states, referral banner with/without ref, privacy-choices link, Privacy Center persist, public QR + Exchange Contact, lang/market independence + persistence, backend 200s (pricing, card, track, referral QR). No regressions.
- **Known minor debt (not fixed, not a regression)**: shadcn Dialog/Sheet primitives contain an `sr-only` English "Close" accessibility label (global default, screen-reader-only, not visually shown). Left untouched to avoid injecting i18n into shared UI primitives used outside Router/i18n context. Industry preview sample cards on `/templates` step 1 are hard-coded EN demo data (acceptable as sample content).


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

## LANGUAGE AUTO-DETECT + RTL + PUBLIC FUNNEL LOCALIZATION (2026-06, iteration 15d) — IMPLEMENTED & verified
Auto-detect language like currency: DEFAULT only, user choice always wins & persists. Language and currency are INDEPENDENT preferences.
- **Mechanic (already-present i18n detector, confirmed)**: `i18n/index.js` LanguageDetector order localStorage(`ariadni_lang`)→navigator→htmlTag, `nonExplicitSupportedLngs` (ar-AE→ar, es-ES→es, en-*→en), fallback `en`. `applyDocumentDir()` sets `<html dir/lang>` → TRUE RTL on load + on change. Independence: language uses `ariadni_lang`, currency uses `tp_market` (separate).
- **Public language switcher** added to Landing navbar + Login + Register (was previously authenticated-only) so visitors can manually override; choice persists via i18n cache.
- **Localized (EN/AR/ES, returnObjects arrays)**: full Landing (navbar, hero, stats labels, features, journey, templates, teams, testimonials heading, pricing, final CTA, footer tagline/newsletter/copyright), PricingSection, Login, Register. New i18n namespaces `auth` + `landing`. Footer link-group labels remain EN (marketing nav terms) — acceptable partial.
- **Verified (isolated browser contexts)**: ar-AE→RTL/ar+AED, ar-SA→RTL/ar+SAR, en-AE→LTR/en+AED, en-SA→LTR/en+SAR, es-ES→LTR/es+EUR, en-US→LTR/en+USD, ja-JP→LTR/en+USD (both fallbacks). Manual EN over ar-AE→LTR/en+AED; manual AR over en-US→RTL/ar+USD (INDEPENDENCE proven). Arabic landing: 0px horizontal overflow, pro price "AED 369.99", Arabic pricing/referral text. Language + currency prefs persist independently.

## REMAINING SAFE ROADMAP (approved, auto-continue) — NEXT
- **Deep app-page localization (EN/AR/ES) — REMAINING**: Leads, CreateCard (card editor), Analytics dialog, and the ScanCardDialog BODY are still English. Done so far: Home, Settings, Team, Notifications, Signatures, Billing, Referral, Landing, Login, Register, PricingSection, **Meetings** (this pass), scanner entitlement banner.
- **DEFERRED EXTERNAL**: Stripe/RevenueCat/social login/Wallet certs/email/push/SMS/CRM/DNS/SSO/App Store; auth hardening/2FA; destructive cleanup.

## TECH DEBT / LATER (non-blocking)
- **Legacy key `ariadni_lang`**: i18next localStorage key still named `ariadni_lang` (pre-rebrand). Existing users depend on it — DO NOT rename now. Later: migrate to a neutral key (e.g. `tp_lang`) with a one-time compatibility read of the old key. Do not surface "Ariadni" anywhere new.
- platform_v1.py ~2013 lines — split into commercial/referral/nfc/admin modules later.
- `detectMarket()` could be memoized at module scope (called per render in ConsentBanner/LocaleToast).
- Register referral banner could echo the actual ref code (cosmetic).

## i18n + CONSENT + SCANNER + REFERRAL-QR + AUTO-DETECT (2026-06, iteration 16) — IMPLEMENTED & QA 100%
- **Language auto-detect** (existing i18next detector confirmed working app-wide): navigator→ar/es/en, key `ariadni_lang`, fallback en, `applyDocumentDir` true RTL. Public LanguageSwitcher added to Landing/Login/Register. Manual choice sets `tp_lang_manual` + persists. INDEPENDENT from currency (`tp_market`).
- **Auto-detect toast** `LocaleToast.jsx`: one-time (`tp_locale_toast_shown`), only when lang/market auto-selected (not after manual), i18n `common.localeToast`.
- **Consent & Privacy Center**: `ConsentBanner.jsx` (region-aware — GDPR opt-in for EUR/GBP: Accept all/Reject; else single Accept; persists `tp_consent`; mounted INSIDE BrowserRouter) + `PrivacyCenter.jsx` at `/privacy-center` (necessary always-on, analytics toggle, save, link to /legal/privacy). Additive only — no change to deletion/export/auth/billing.
- **Scanner exposure**: `ScanCardDialog` shows `scan-entitlement` banner from `/billing` usage.scanner (used/limit/period, unlimited, or unavailable→`scan-upgrade`→/billing). Reuses existing entitlement architecture.
- **Referral QR**: backend public `GET /api/referral/qr?code=` (reuses `qrcode`, referral_code; 404 unknown/422 missing) + Referral page QR preview/download/copy-code.
- **Meetings localization** (EN/AR/ES): full page incl. status labels via `meetings.status_*`, filters keep canonical English values for filtering.
- **Savings derived** from prices (`_annual_savings_pct`) across Billing + public pricing.
- QA (iteration_16): 7/7 auto-detect matrix, override independence (en+AED, ar+USD), market persist, 2 consent regions, toast once+persist, RTL 0px overflow desktop+mobile, Meetings EN+AR, Referral QR, scanner entitlement, member 403. Fixed crash: ConsentBanner Link was outside BrowserRouter. feras-askar preserved (200).

## PRICING SINGLE SOURCE OF TRUTH — Public site + dedicated Referral page (2026-06, iteration 15b) — IMPLEMENTED & verified
User directive: ONE authoritative pricing config across Super Admin → Billing → Public site → trial messaging → referral. No hard-coded prices anywhere; annual savings DERIVED from prices.
- **Backend**: `resolve_market_pricing()` now returns DERIVED `pro_annual_savings_pct` / `team_annual_savings_pct` via `_annual_savings_pct(monthly, yearly) = round((1 - annual/(monthly*12))*100)`. `/api/commercial/pricing` (public, market-resolved, USD fallback) feeds both the landing and Billing.
- **Public landing** `components/landing/PricingSection.jsx` (`#pricing`, added to nav): fetches `/api/commercial/pricing`, Monthly/Annual toggle, market selector (USD/AED/SAR/EUR/GBP), Trial/Pro/Team/Enterprise cards, trial-days + referral promo line, and JSON-LD (schema.org Product/Offers) reflecting the SAME resolved config. NO independent price data.
- **Billing** now shows DERIVED savings (`pricing.*_annual_savings_pct`) instead of the stored `annual_discount_pct`.
- **Dedicated Referral page** `pages/Referral.jsx` at `/referral` (+ nav Gift pill, EN/AR/ES): code, share link, copy/native-share, stats (referred count / reward applied w/ cap / queued), referred-as note, how-it-works, fair-use. Reuses `GET /api/referral` (authoritative referral config).
- **Verified (curl, 9-step)**: change Pro monthly → BOTH public + billing update (same value); change Pro annual → savings auto-recalc (e.g. 11.99mo/109.99yr → 24%); change GBP regional price → correct market price resolves; MEMBER PUT /admin/commercial → 403; referral values come from authoritative config. Landing + Billing + Referral pages screenshot-verified rendering from config. Config reverted to approved defaults (9.99/99.99, Save 17%).









---

## 2026-06 — Message 469: Account-scoping audit + UX correction phase

### P0 tenant/data-scoping audit — RESOLVED (verified iteration_27, tenant-isolation in iteration_26)
- **Root cause = legitimate ownership + a frontend role-label bug. NO backend leak.**
- Evidence: card `edrina-cepele` has `owner_user_id` + `created_by` = `work@gmail.com` user id and `workspace_id` = his workspace "Mohammed". He created it himself; its content name is "Edrina Cepele". Mohammed's `/admin/cards` returns ONLY that card; SUPER_ADMIN sees all 3 by design. Analytics are correctly scoped (his 49 events, no cross-tenant leak).
- The confusion came from `Settings.jsx` hardcoding "Member" for every non-admin. Fixed: role now derived from workspace memberships.
- testing_agent iteration_26: 100% backend (7/7) + frontend; tenant isolation confirmed.

### Implemented in this phase (all testing_agent-verified, iterations 26 & 27)
1. **Account Context UX** — sidebar/topbar show: "Personal Account" (individual), workspace name (team), or "TapPresence Admin Console" (super admin) + role badge (Owner/Admin/Manager/Member/Super Admin). `AuthContext` now stores `memberships`. "My Card(s)" nav label replaced with "Cards".
2. **Navigation redesign** — removed horizontal pill nav. New app shell (`OwnerNav.jsx`): fixed left sidebar (desktop, via `body.tp-shell` padding + `.tp-sidebar`), hamburger + slide-out drawer (mobile), sticky top bar with context + notifications + profile. Super Admin tools separated under an "Admin Tools" group. Nav now includes Home, Cards, Leads, Scanner, Meetings, Analytics, Signatures, NFC, Billing, Referral, Team/Integrations (entitled), Settings, Command Center (admin). RTL-safe via logical CSS properties.
3. **Analytics integrity** — confirmed metrics are correctly scoped per authorized card; no counter resets.
4. **Reusable Date Filter** — `components/admin/DateFilter.jsx` (Today | This Week | This Month | Custom + optional All time). Backend `/admin/analytics/overview` + `export.csv` and `_compute_overview` accept `start`/`end` ISO (days kept as fallback). Applied to Analytics overview (Home) and Leads list. Team leaderboard = analytics `by_member` which already respects the Home range.
5. **Email Signature install UX** — Signatures page: Copy Signature (primary), Copy HTML (advanced), Download HTML (optional) + install instructions tabs for Gmail/Outlook/Apple Mail and a note clarifying it's pasted into mail settings, not saved as an image.
6. **Timezone** — registration auto-detects browser tz (`Intl...timeZone`) and stores it (`timezone_source: auto`). New `PATCH /api/account/preferences` allows manual override (`timezone_source: manual`, validates IANA, syncs individual workspace region.timezone). Settings has a timezone dropdown + a one-time device-timezone suggestion banner (dismissal persisted in localStorage per user).

### i18n
- Added keys in en/ar/es: `nav.cards/leads/scanner/nfc/personalAccount/adminConsole/adminTools/owner/admin/manager/menu`, `dateFilter.*`, `settings.tz*`, `signatures.install*` + client step arrays.

### Test users
- `work@gmail.com` / `mohammed` — personal WORKSPACE_OWNER, owns `edrina-cepele` (see test_credentials.md). tz reset to America/New_York so the suggestion flow stays demonstrable.

### Still deferred (external credentials / out of scope)
- Real Stripe payments and transactional email delivery (auth/verification/reset flows built; delivery blocked until provider configured).
- Meetings date-filter (uses temporal tabs today/upcoming/past already); could adopt DateFilter later if desired.



---

## 2026-06 — TapPresence Control Center (SUPER_ADMIN operator console) — verified iteration_28 (backend 15/15, frontend 100%)

Distinct platform-operator experience at `/control/*`, separate from the customer app.
- **Routing/guard**: `SuperAdminRoute` in `App.js`; SUPER_ADMIN login → `/control` (Login.jsx). Old routes folded: `/admin/platform` → `/control`, `/admin/commercial` → `/control/plans`. Normal customers hitting `/control/*` redirect to `/dashboard`; all `/admin/control/*` APIs return 403 for non-super.
- **Backend** (`platform_v1.py`, all `_require_super`): `/admin/control/overview` (real counts + money=None), `/customers/{id}` + `/customers/{id}/action` (resend_verification/revoke_sessions), `/workspaces/{id}`, `/referrals`, `/flags` (GET/PUT), `/audit`, `/security`, `/health`, `/entitlements` (GET/PUT overrides merged in `resolve_entitlements`), `/pricing/preview`, `/pricing/publish` (versioned + audit), `/pricing/versions`. Reuses existing `/admin/platform/users|workspaces|suspend`, `/admin/commercial`, `/admin/industries`, `/integrations/status`.
- **Frontend**: single `pages/ControlCenter.jsx` (shell: fixed sidebar desktop + drawer mobile + top bar; footer "Open TapPresence App" + "Log out"). 15 sections all live.

### Page-by-page status (what is REAL vs deferred)
| Section | Live? | Real data | Deferred/unavailable |
|---|---|---|---|
| Overview | ✅ | account counts, trials/paid/cancellations (from subscription state), product usage (views/scans/nfc/leads/scanner/meetings/campaigns/referrals), plan distribution, global date filter | MRR/ARR/Revenue/Churn/Trial→Paid show "Not available until billing connected" |
| Customers | ✅ | search, detail (status/verify/plan/cards/leads/meetings/referrals/country/lang/tz/created/last activity), actions: resend verify, revoke sessions, suspend/unsuspend | email actually sends only when email provider connected |
| Companies/Workspaces | ✅ | owner, plan, status, seats, members, cards, leads, meetings, brand-lock | — |
| Subscriptions | ✅ | grouped by real subscription status | money figures need Stripe |
| Revenue & Analytics | ✅ | real product analytics | revenue KPIs "Not available" until Stripe |
| Plans & Pricing | ✅ | Draft→Impact Preview→Confirm→Publish; versioned snapshots (`commercial_config_versions`) + audit; new-only vs migrate decision recorded | real Stripe price migration executes only when Stripe connected |
| Product & Entitlements | ✅ | per-plan override editor; merged into `resolve_entitlements` (no source edits) | — |
| Referral Program | ✅ | funnel, qualified, months earned, top referrers, config | — |
| Templates & Industries | ✅ | list + enable/disable | — |
| Feature Flags | ✅ | add/toggle, stored in `feature_flags` collection | flags are stored/managed; wire into gates as needed |
| Integrations | ✅ | Connected/Not-configured from real env; no secrets shown | providers themselves not connected |
| System Health | ✅ | API/DB/AI/billing(demo)/email/Sentry states, pending verifications | deeper metrics after Sentry connected |
| Security & Abuse | ✅ | suspended accounts, throttled logins, revoked referrals | — |
| Audit Log | ✅ | actor/action/timestamp/meta (before/after for pricing/flags/entitlements); searchable | — |
| Settings | ✅ | operator info | — |

**Not connected (external creds needed): Stripe (all money metrics + real price migration), transactional email (delivery), Sentry (deep health).**


---

## Industry Preview Card CTAs — Book a Meeting added (2026-06-11) — DONE, verified in preview

**Request:** Add a **BOOK A MEETING** CTA next to **EXCHANGE CONTACT** on the "Industry template" preview cards (the ones in the user's screenshots: Alex Morgan/Real Estate, Michael Anderson/Business, etc.).

**What these "templates" actually are:** The single shared component `frontend/src/components/landing/IndustryCard.jsx`, which powers all **12** industry designs (real_estate, business, sales, technology, healthcare, legal, education, hospitality, automotive, beauty, finance, custom). Rendered on: Landing showcase, `/industries` (IndustryShowcase), and Create-card Step-1 industry picker.

**Implemented (preview only, not deployed):**
- Replaced the single "Exchange Contact" block in `IndustryCard.jsx` with a `grid grid-cols-2` row: **EXCHANGE CONTACT** (left, filled accent, `data-testid=ind-exchange-{id}`) + **BOOK A MEETING** (right, bordered accent tint, `data-testid=ind-book-{id}`), with UserPlus / CalendarClock icons.
- Kept **display-only** (no dialogs / no booking logic wired) — these are marketing/preview mockups, per user instruction.
- Each industry's accent/background/typography preserved (accent-driven styling via `ac`).
- Side-by-side on desktop AND mobile (fixed 360px card, no wrap/overflow); RTL-safe (grid auto-reverses, no directional margins).
- Added locale key `industryCard.book`: EN "Book a Meeting" / AR "احجز اجتماعاً" / ES "Reservar reunión".

**Verification (preview):**
- Desktop (/industries): all 12 cards show both CTAs, correct per-industry accents.
- Mobile 390px: Finance/Beauty confirmed side-by-side, clean.
- Arabic RTL: `dir=rtl`, Arabic label renders, Exchange on RIGHT / Book on LEFT (correct order, verified via bounding boxes).
- All 12 `ind-exchange-*` + `ind-book-*` present (DOM check). All 3 locale JSONs valid.

**Untouched (as required):** `ExecutiveBlackGold.jsx` (real published profile already has both working CTAs), `BeigeLuxuryExecutive.jsx`, `FutureProfessional.jsx` (legacy/hidden), Google Sign-In, Google Calendar OAuth, booking APIs.

---

## Enable native booking on existing published profiles (2026-06-11) — DONE, verified in preview

**Request:** Existing published profiles showed "SEND A MESSAGE" as the 2nd CTA instead of "BOOK A MEETING". Root cause: `ExecutiveBlackGold` intentionally falls back to "Send a Message" when booking is off. User chose: enable native booking on **all** published cards with default availability.

**Migration:** `scripts/enable_native_booking.py` (idempotent) — sets `booking.nativeEnabled=true` on all `status:"published"` cards (preserving timezone/bookingUrl) and pre-seeds default availability (Mon–Fri, 09:00–18:00, 30-min slots, 2h notice, 60-day window) + 3 meeting types (15/30/45 min). Backend already lazy-seeds these, so this is belt-and-suspenders.

**Result:** 3 published cards → 2 enabled + seeded, 1 already on. All now `native_enabled:true` (edrina-cepele, dr-leo, feras-askar).

**Verification (preview):** edrina-cepele profile now shows **BOOK A MEETING** side-by-side with Exchange Contact; dialog opens with 3 meeting types; `/api/cards/edrina-cepele/slots` returns 18 bookable slots on the next weekday. Fully functional.

**Note:** This changed live preview DB data only. Not deployed to production. feras-askar previously had a cal.com URL — native now takes precedence (URL retained as fallback).

---

## Calendar date/time + cancel — deep debug (2026-06-11) — preview only

### Issue 1: one-day shift (FIXED)
Root cause: booking/reschedule date chips built the date string with `toISOString().slice(0,10)` = UTC calendar date. For UTC+ zones (Asia/Dubai, UTC+4) between 00:00–03:59 local, the UTC date lags one day, so the picker offered/fetched the wrong day's slots.
Fix: generate date strings from LOCAL date parts via `ymd()` helper in `BookMeetingDialog.jsx`, `Meetings.jsx` (reschedule picker), `ManageMeeting.jsx`.
Backend was already instant-correct: slots are UTC ISO computed in owner tz; `start_utc` stored as UTC; `_gcal_event_body` sends `dateTime=start_utc` + `timeZone:"UTC"`. Live-verified (Asia/Dubai): book 09:00 -> 05:00Z -> 09:00; reschedule 10:00 -> 06:00Z -> 10:00. No shift/no unintended conversion on backend.

### Issue 2: cancel not deleting + REAL Google API verification
- The dashboard-cancel fix (sync call added to `admin_meeting_status`) is correct — stub test confirms DELETE fires + clears google_event_id.
- REAL API finding (preview): the ONLY connected calendar (user work@gmail.com, Google acct feras.m.askar@gmail.com) has token scope `email openid` — **NOT `calendar.events`**. So in preview NO events are created (POST 403), google_event_id stays None, nothing to reschedule/cancel. The user's working Create/Reschedule/Cancel were on PRODUCTION (properly-scoped). Could NOT exercise real cancel-delete in preview — no real event exists here.
- Cause: Google didn't grant the sensitive calendar.events scope during preview consent (scope not approved/added on the preview OAuth consent screen -> Google filters it). Connect code correctly requests GCAL_SCOPE.
- Additive fixes (do NOT touch OAuth creds/flow or production):
  1. `gcal_callback` rejects a grant missing calendar.events (redirect reason=calendar_permission_denied) — no more storing a dead "connected" record.
  2. `gcal_status` returns connected:false + needs_reconnect:true + reason:"calendar_permission_missing" when stored scope lacks calendar.events. UI (Settings) already renders amber "Reconnect needed" + clearer message.
  3. `sync_meeting_calendar` flags needs_reconnect on 401/403 and no longer clears google_event_id on a failed delete.

### ACTION for user to enable preview calendar (so a true live test is possible)
Add scope `https://www.googleapis.com/auth/calendar.events` to the Google Cloud OAuth consent screen, keep the account as a Test User, then Settings -> Integrations -> Reconnect. Then a real Create->Reschedule->Cancel with Google events can be verified in preview.

Test scripts: `backend/tests/test_cancel_calendar_sync.py` (stub, PASS), `backend/tests/live_calendar_e2e.py` (real; prints no secrets).

---

## Public Privacy Policy page /privacy (2026-06-11) — built & verified in preview; awaiting user deploy

Additive-only. For Google OAuth verification.
- New page `frontend/src/pages/Privacy.jsx` (public, no auth). Includes a prominent "Google Calendar & Google user data" section: uses `calendar.events` ONLY to Create / Update-reschedule / Delete events for the meeting-booking feature; only manages events it creates; disconnect from Settings revokes access; "We do not sell your Google user data, and we do not use it for advertising"; Google API Services User Data Policy (Limited Use) statement. Plus general privacy sections.
- Route `/privacy` added in `App.js` BEFORE the `/:slug` catch-all.
- Footer: "Privacy Policy" link now targets `/privacy`; added an extra always-visible `/privacy` link near the copyright (`data-testid=footer-privacy-policy`).
- NO changes to booking/calendar/OAuth/auth/routing-of-existing-features/DB/backend.
- Verified in preview: /privacy renders publicly (localStorage cleared), all required Google content present; `/:slug` public profiles still resolve; footer link href=/privacy; frontend compiled.
- DEPLOY NOTE: tappresence.com/privacy returns 200 (SPA shell) but shows the OLD bundle until user redeploys. After redeploy it renders the real page. Agent cannot deploy to production.

---

## Separate preview/production Google OAuth (2026-06-11) — preview switched & verified; production untouched

Reason: production Brand Verification blocked because the shared OAuth client's Authorized Domains included the Emergent preview domain (unverifiable by user).

Decision: existing client `1014661110922-vqq91nu...` stays PRODUCTION (tappresence.com). New isolated client created in separate GCP project `tappresence-preview` for PREVIEW.

Done (PREVIEW only — no code changes; all OAuth is env-driven):
- Updated `/app/backend/.env`: GOOGLE_OAUTH_CLIENT_ID -> `1053031140717-3pv721c5bhm76s1m22bhgje4lcgbsnhh.apps.googleusercontent.com` (project tappresence-preview); GOOGLE_OAUTH_CLIENT_SECRET -> new preview secret (masked). Removed stray empty duplicate `GOOGLE_OAUTH_CLIENT_ID=""`. Redirect URIs already preview. Backend restarted.
- Deleted the 1 stale calendar connection (belonged to old client) -> status now {configured:true, connected:false}, clean for reconnect.

Verified (automated, preview):
- Sign-In consent URL uses new client_id + preview sign-in redirect + scope `openid email profile`.
- Calendar consent URL uses new client_id + preview calendar redirect + scope `openid email .../auth/calendar.events`, access_type offline, prompt consent.
- Dummy-code token exchange for BOTH redirect URIs => `invalid_grant` (client id/secret valid + redirects registered on the new client). No `invalid_client`.

Still needs USER manual confirm in preview (headless Google can't be automated): actually Sign in with Google, then Settings->Integrations->Connect Google Calendar (grant calendar.events), then book/reschedule/cancel a test meeting to confirm real event sync on the new client.

PRODUCTION untouched. After preview is human-confirmed, user removes preview redirect URIs + preview Authorized Domain + any preview JS origin from the PRODUCTION client (leaving only tappresence.com) -> brand verification unblocked. Agent did NOT and must NOT touch production credentials/config.

---

## Preview calendar_permission_denied diagnosis (2026-06-11) — NO changes made
User tested Calendar Connect on preview (new tappresence-preview client) with Test User Feras.M.askar@gmail.com -> app showed calendar_permission_denied.
Evidence (callback log 23:20:54): token exchange SUCCEEDED (200) but granted scope = `https://www.googleapis.com/auth/userinfo.email openid` — NO calendar.events.
Requested scope (verified): `openid email https://www.googleapis.com/auth/calendar.events`.
Conclusion: NOT a callback/code bug — the substring check `"calendar.events" not in granted_scope` correctly rejects because Google truly returned no calendar scope. Callback validation is correct; would accept `.../auth/calendar.events`.
Root cause: on the NEW tappresence-preview GCP project, calendar.events is not added to the OAuth consent screen scope list (and/or Google Calendar API not enabled), so Google filters the sensitive scope and grants only email/openid. Test-User status alone is insufficient.
Fix (USER, Google Cloud, no code change): enable Google Calendar API + add scope .../auth/calendar.events to the tappresence-preview OAuth consent screen, then retry Connect. No production/credential/code changes made.

---

## Homepage product-purpose copy for Google Brand Verification (2026-06-11) — preview done; awaiting deploy
Brand Verification rejected: "home page does not explain the purpose of your app."
Additive-only change (no OAuth/auth/routing/db/pricing/functionality touched):
- Landing hero (above the fold, always-visible plain text, no login) now shows purpose + capabilities:
  - purpose: "TapPresence is a digital business card and professional networking platform."
  - capabilities: "Create and share professional digital cards using QR and NFC, capture leads, book meetings, manage contacts, and track engagement — all in one place."
- Added i18n keys landing.hero.purpose + landing.hero.capabilities (EN/AR/ES).
- Updated public/index.html <meta name="description"> to the purpose statement.
Verified in preview: both texts render above fold (capabilities y~662 < 900) publicly.
Production tappresence.com still serves OLD bundle (main.1a92b477.js) without the copy -> user must REDEPLOY. Do not resubmit Brand Verification until after redeploy + agent re-verifies live text.

---

## Homepage Google Calendar Integration disclosure section (2026-06-11) — preview done; awaiting deploy
Brand Verification still flagged home page purpose re: Google data. Added a public crawlable section on Landing (before FinalCTA/Footer), additive-only.
- New `GoogleCalendarInfo` section in Landing.jsx (id=google-calendar, testids gcal-info-*), plain HTML text, no login.
- Copy: "Google Calendar Integration" + exact disclosure (calendar.events used only to create/reschedule/delete events for booked meetings; users can disconnect anytime).
- Visible crawlable link to https://tappresence.com/privacy (anchor text = URL).
- i18n keys landing.gcal.{title,body,linkLabel} added EN/AR/ES.
Verified in preview publicly. Production tappresence.com needs REDEPLOY; verify live after deploy before resubmitting Brand Verification.
No OAuth/Calendar/auth/routing/db/pricing/functionality changes.

---

## Header logo + QR center logo UI fixes (2026-06-11) — preview done, verified
1) Header logo: tp-mark.png had huge transparent padding (glyph filled only 33%x27% of canvas) → looked tiny. Created cropped square asset frontend/public/tp-mark-tight.png (glyph fills ~89%x72%); Landing AriadniMark now uses it. Brand icon h-9 lg:h-10, wordmark reduced to text-base lg:text-lg for balance. Original tp-mark.png untouched (QR still uses it).
2) QR center logo: backend _brand_qr increased center mark 26%->30% (server.py) with tighter white backing (pad=lw/8). Decoder-verified scannable with pyzbar (native + 3x upscale) — larger pad at 30% failed, lw/8 passes. Endpoint /api/cards/{slug}/qr decodes to correct URL.
3) Pricing: investigated — NOT a bug. Old CommercialSettings editor is redirected to /control/plans; Control Center edits regional_pricing which public/billing/checkout read (one source of truth); no hardcoded prices in frontend. User confirmed pricing updates correctly. Resolved, no changes.
Preview only; user must redeploy for production.

---

## Google Wallet auth method investigation (2026-06-11) — report only, NO changes
Google side ready: Issuer 3388000000023187647, Generic Class tappresence_business_card, SA tappresence-wallet@tappresence-production.iam.gserviceaccount.com (Developer access).
Runtime check (read-only): GOOGLE_APPLICATION_CREDENTIALS unset; GCP metadata server NOT reachable; google.auth.default() times out -> NOT on GCP, no keyless ADC / workload identity. WIF not viable (no configurable OIDC identity on Emergent runtime).
Conclusion: a JSON service-account key IS required, stored as backend secret env GOOGLE_WALLET_SA_JSON (never in repo/frontend). Backend already wired: env GOOGLE_WALLET_ISSUER_ID + GOOGLE_WALLET_SA_JSON; feature flag google_wallet gates on both (platform_v1.py:896); libs installed (google-auth, google-api-python-client, cryptography, PyJWT). Wallet passes section at platform_v1.py:1711.
No key created, no code/config changed. Next: user provides key -> set GOOGLE_WALLET_SA_JSON + ISSUER_ID in preview .env, wire Save-to-Wallet (RS256 JWT), verify in preview; prod set secret + redeploy. Least privilege: Wallet Object Issuer role; rotate periodically.
