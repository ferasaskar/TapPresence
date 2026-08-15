# TapPresence Changelog

## 2026-08-15 — Final SEO / AI-Search / Social-Sharing Completion (PREVIEW ONLY, agent-verified, NOT redeployed)

Continues SEO Phase 1 + Phase 2. Scope strictly: social image, OG/Twitter metadata, favicon/brand assets, structured-data + full SEO audit, content-accuracy audit, GA4/GSC/Bing checks, QA. No pricing/billing/auth/business-logic/design changes. No production deploy.

### Files changed
- `frontend/public/social-share.png` (NEW) — official supplied landscape banner, 1734×907, served as-is.
- `frontend/public/index.html` — OG/Twitter image tags now point to `/social-share.png` (was `logo512.png`); added `og:image:secure_url`, `og:image:type`, `og:image:width=1734`, `og:image:height=907`, `og:image:alt`, `twitter:image:alt`; added `<link rel=manifest>` + sized icon links.
- `frontend/public/manifest.json` (NEW) — web manifest, icons = favicon.png + logo512.png (brand logo, NOT the banner).
- `frontend/src/lib/seo.js` — added `SEO_SOCIAL_IMAGE` (+ width/height/alt consts); `useSeo()` now emits full OG image set + `og:type` + `og:site_name` + `twitter:card/image/image:alt` on every route (default image = social banner). Instagram `sameAs` aligned to `https://www.instagram.com/tappresence`. Organization `logo` remains `/logo512.png`.
- `frontend/src/pages/PublicProfile.jsx` — valid profile now passes `og:type=profile` + person's own photo as `image`; invalid slug stays `noindex,follow` + default. Marketing banner never overrides a real profile photo.

### Verification (agent-tested, testing_agent iteration_42 = frontend 100%, 0 issues)
- Static `index.html` OG/Twitter all reference `https://tappresence.com/social-share.png` (width 1734 / height 907 / image/png / summary_large_image).
- Runtime head tags PASS on all 14 marketing routes (unique title, self canonical, one H1, og:type, og:site_name, og:image banner, twitter card+image, valid JSON-LD).
- Homepage JSON-LD: Organization (logo=/logo512.png, sameAs=[LinkedIn, Instagram]) + WebSite + SoftwareApplication. Landing pages: BreadcrumbList + SoftwareApplication + FAQPage where a visible FAQ exists.
- Valid profile `/dr-leo` crawler prerender: og:type=profile, person photo, no noindex. Invalid slug: noindex,follow.
- Assets 200: /social-share.png, /favicon.png, /logo512.png, /manifest.json, /sitemap.xml, /robots.txt.
- Sitemap = https://tappresence.com only (no www), 14 marketing + industries + register + login + 4 legal, no private routes. robots.txt disallows admin/dashboard/leads/meetings/settings/billing/nfc/referral.
- Regression: /login, /register render; /dashboard & /leads redirect to /login; /pricing renders config-driven PricingSection. No console errors.

### Owner-required (external, cannot be done in code)
- GA4: no Measurement ID present in code/env → owner must provide `G-XXXXXXX`.
- Google Search Console: no verification value present → owner verification required.
- Bing Webmaster: no verification token present → owner verification required.
- Final production redeploy: pending owner authorization (one final deploy).

## 2026-08-15 — GA4 Analytics Connected (PREVIEW, agent-verified 100%; needs redeploy for production)

Measurement ID `G-YY864DN86T`. Additive to existing PostHog (PostHog untouched). No UI changes.

### Files changed
- `frontend/.env` — added `REACT_APP_GA4_MEASUREMENT_ID=G-YY864DN86T` (public, non-secret).
- `frontend/src/lib/ga.js` (NEW) — gtag.js loader + Google Consent Mode v2. Reads ID from env; if absent, GA no-ops. `initGA()` pushes consent default (ads always denied; analytics_storage per consent), `config` with anonymize_ip + google_signals off + send_page_view:false. `analyticsAllowed()` mirrors app rule: EU/UK (EUR/GBP) opt-in, else opt-out. Listens to `tp-consent-changed` → consent update. `trackPageView()` strips query strings and redacts token routes (reset/verify/activate/m/invite/auth) → no PII.
- `frontend/src/components/GAListener.jsx` (NEW) — initGA once + trackPageView on every route change.
- `frontend/src/App.js` — `<GAListener/>` mounted inside `<BrowserRouter>`.

### Verified (testing_agent iteration_43 — frontend 100%)
gtag.js loaded with correct ID; dataLayer has consent default + config; real network hits to googletagmanager.com/gtag/js and google-analytics.com/g/collect for /, /pricing, /digital-business-card with sanitized page_location (no query strings/PII); PostHog still present; consent reject→analytics_storage denied, grant→granted; no console errors. Production verification pending owner redeploy.

## 2026-08-15 — GA4 Conversion Funnel Tracking (PREVIEW, agent-verified; needs redeploy for production)

Acquisition-funnel conversion events on the existing GA4 integration (G-YY864DN86T). Additive to PostHog; Consent Mode v2 preserved; no UI changes.

Events: start_trial_click · sign_up_start · sign_up · trial_started · begin_checkout (value+currency+item) · purchase (transaction_id=session_id + real value + currency, deduped by session_id).

Files changed:
- frontend/src/lib/ga.js — added trackEvent(name, params, {dedupeKey, persist}) (auto-init, cleans undefined params, dedupe via in-memory Set or sessionStorage tp_ga_fired) + trackTrialClick().
- frontend/src/pages/Register.jsx — sign_up_start on mount (dedupe 'flow'); sign_up + trial_started on real register/google-complete success (dedupe by user id, persist).
- frontend/src/pages/Landing.jsx, pages/seo/SeoLanding.jsx, pages/seo/PricingPage.jsx, components/landing/PricingSection.jsx — start_trial_click on all CTAs (cta_location).
- frontend/src/pages/Billing.jsx — begin_checkout with value/currency/items from checkout response.
- frontend/src/pages/PaymentResult.jsx — purchase with transaction_id/value/currency, deduped by session_id (persist).
- backend/platform_v1.py — /billing/checkout and /payments/status now also return non-PII amount + currency.

Verified (testing_agent iteration_44): 5/6 events fully E2E with real dataLayer + /g/collect evidence + real backend outcomes; each fires exactly once (StrictMode/poll-safe). begin_checkout carried real value 99.99 USD. purchase code-path verified (Stripe hosted-form completion not automatable — env limit, not a code bug). NO PII in any GA payload; Consent Mode v2 intact; PostHog preserved; no console errors.

## 2026-08-15 — SEO P0 + P1 Implementation (PREVIEW, agent-verified 100%; needs redeploy)

Canonical host kept non-www https://tappresence.com. No redesign, no pricing/auth/billing changes. Reused SeoLanding.jsx + landingContent.js.

New routes: /event-lead-capture (SeoLanding), /about /contact /security (CompanyPages.jsx), /compare/:comp (ComparePage.jsx — 4 competitors, noindex until competitor data verified, out of sitemap).
Improved: 12 existing SEO pages gained in-depth `sections` (H2+prose), updated titles (digital-business-card "for Professionals & Teams"; UAE/Dubai keyworded; scanner "App"), differentiated /event-networking (networking) vs /event-lead-capture (lead-capture software), NFC page de-positioned from hardware store, internal linking expanded, homepage hero-purpose now semantic H2 (brand H1 preserved), Company footer nav added.
Files: landingContent.js (rewritten, +sections +event-lead-capture +COMPANY_FOOTER_LINKS), SeoLanding.jsx (sections render + company footer), CompanyPages.jsx (NEW), compareContent.js + ComparePage.jsx (NEW), App.js (routes), Landing.jsx (H2 + company footer), public/sitemap.xml (+event-lead-capture/about/contact/security; excludes /compare + private).
Verified (testing_agent iteration_45, frontend 100%, 0 action items): all pages load+hard-refresh, one H1, unique titles, self canonicals, indexable (compare=noindex), valid JSON-LD, sections present, internal links (no href='#'), EN/AR-RTL/ES OK, mobile OK, sitemap/robots correct, signup + protected-route + pricing regression PASS, no console-breaking errors.
Deferred to P2 (per user): blog/guides content, external authority (G2/Capterra/directories/backlinks), competitor-data verification for compare pages.
