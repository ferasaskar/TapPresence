// Google Analytics 4 (gtag.js) — additive to the existing PostHog/internal analytics.
// Respects the app's existing cookie consent (opt-in for EU/UK, opt-out elsewhere),
// uses Google Consent Mode v2, sends NO PII (query strings stripped, token routes redacted),
// and drives SPA page_view events manually. Loads only when a Measurement ID is configured.
import { getConsent } from "@/components/ConsentBanner";
import { detectMarket } from "@/lib/market";

export const GA_ID = process.env.REACT_APP_GA4_MEASUREMENT_ID || "";

// Same GDPR-style opt-in regions as ConsentBanner (single source of behavior).
const GDPR_MARKETS = new Set(["EUR", "GBP"]);

function gtag() {
  window.dataLayer = window.dataLayer || [];
  window.dataLayer.push(arguments);
}

// Analytics is allowed when consent isn't required (opt-out region + not explicitly rejected)
// or when it has been explicitly granted (EU/UK opt-in region).
export function analyticsAllowed() {
  const c = getConsent();
  const isGdpr = GDPR_MARKETS.has(detectMarket() || "USD");
  if (isGdpr) return c?.analytics === true;
  return c?.analytics !== false;
}

// Never leak tokens/PII in the URL to GA: drop query strings and redact token-bearing routes.
const REDACT_FIRST_SEGMENT = new Set(["reset", "verify", "activate", "m", "invite", "auth"]);
export function sanitizePath(pathname) {
  const seg = (pathname || "/").split("/").filter(Boolean);
  if (seg.length && REDACT_FIRST_SEGMENT.has(seg[0])) return `/${seg[0]}/redacted`;
  return pathname || "/";
}

let initialized = false;

export function initGA() {
  if (initialized || !GA_ID) return;
  initialized = true;

  window.dataLayer = window.dataLayer || [];
  window.gtag = gtag;

  gtag("js", new Date());
  // Consent Mode v2 defaults — analytics gated by consent; advertising signals always denied.
  gtag("consent", "default", {
    ad_storage: "denied",
    ad_user_data: "denied",
    ad_personalization: "denied",
    analytics_storage: analyticsAllowed() ? "granted" : "denied",
  });
  gtag("config", GA_ID, {
    anonymize_ip: true,
    allow_google_signals: false,
    allow_ad_personalization_signals: false,
    send_page_view: false, // SPA — sent manually on navigation
  });

  const s = document.createElement("script");
  s.async = true;
  s.src = `https://www.googletagmanager.com/gtag/js?id=${GA_ID}`;
  document.head.appendChild(s);

  // React to consent changes from ConsentBanner / Privacy Center.
  window.addEventListener("tp-consent-changed", () => {
    gtag("consent", "update", {
      analytics_storage: analyticsAllowed() ? "granted" : "denied",
    });
  });
}

export function trackPageView(pathname) {
  if (!GA_ID || !initialized) return;
  const path = sanitizePath(pathname);
  gtag("event", "page_view", {
    page_path: path,
    page_location: `${window.location.origin}${path}`,
    page_title: document.title,
  });
}
