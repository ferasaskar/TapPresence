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
