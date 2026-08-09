// Market/currency auto-detection for the PUBLIC pricing surface.
// Uses ONLY safe, already-available browser/locale signals — NO external geolocation provider,
// NO FX conversion. Detection is a DEFAULT only; a manual choice always wins and is remembered.

const STORAGE_KEY = "tp_market";

// Eurozone country codes → EUR
const EUROZONE = new Set([
  "AT", "BE", "HR", "CY", "EE", "FI", "FR", "DE", "GR", "IE", "IT",
  "LV", "LT", "LU", "MT", "NL", "PT", "SK", "SI", "ES",
]);

const COUNTRY_TO_MARKET = { AE: "AED", SA: "SAR", GB: "GBP", US: "USD" };

// Minimal timezone → country hints (secondary signal, no external service)
const TZ_TO_COUNTRY = {
  "Asia/Dubai": "AE",
  "Asia/Riyadh": "SA",
  "Europe/London": "GB",
};

export function countryToMarket(cc) {
  if (!cc) return null;
  cc = String(cc).toUpperCase();
  if (COUNTRY_TO_MARKET[cc]) return COUNTRY_TO_MARKET[cc];
  if (EUROZONE.has(cc)) return "EUR";
  return null; // unknown → caller falls back to configured default
}

// Detect a market string from browser signals, or null if indeterminate.
export function detectMarket() {
  // 1) Locale region (e.g. en-GB → GB, ar-AE → AE, ar-SA → SA)
  try {
    const langs = (typeof navigator !== "undefined" && (navigator.languages?.length ? navigator.languages : [navigator.language])) || [];
    for (const l of langs) {
      let region = null;
      try { region = new Intl.Locale(l).region; } catch { /* older engines */ }
      if (!region) { const m = /[-_]([A-Za-z]{2})$/.exec(l || ""); if (m) region = m[1].toUpperCase(); }
      const market = countryToMarket(region);
      if (market) return market;
    }
  } catch { /* ignore */ }

  // 2) Timezone hint (secondary)
  try {
    const tz = (typeof Intl !== "undefined" && Intl.DateTimeFormat().resolvedOptions().timeZone) || "";
    if (TZ_TO_COUNTRY[tz]) return countryToMarket(TZ_TO_COUNTRY[tz]);
    if (tz.startsWith("Europe/")) return "EUR"; // generic Europe → EUR
  } catch { /* ignore */ }

  return null;
}

// Resolve the market to show: saved manual choice → auto-detected → configured default.
// Only returns a market that is actually in `supported`; otherwise the safe fallback.
export function getPreferredMarket(supported = [], fallback = "USD") {
  const safeFallback = supported.includes(fallback) ? fallback : (supported[0] || "USD");
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved && supported.includes(saved)) return saved;
  } catch { /* ignore */ }
  const detected = detectMarket();
  if (detected && supported.includes(detected)) return detected;
  return safeFallback;
}

export function saveMarketPreference(market) {
  try { localStorage.setItem(STORAGE_KEY, market); } catch { /* ignore */ }
}
