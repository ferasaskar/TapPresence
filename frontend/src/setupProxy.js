/**
 * Crawler prerender bridge (preview/dev).
 *
 * Social crawlers cannot execute the React SPA, so for a published card URL
 * (`/:slug`) we serve the backend-generated Open Graph / Twitter metadata
 * instead. Only requests from known crawler user-agents are intercepted;
 * real browsers fall through to the normal SPA. If the backend returns a
 * non-200 (unknown / draft / paused card, or a non-card route) we also fall
 * through, so nothing about the human experience changes.
 *
 * Production note: the same "crawler UA on /:slug -> /api/og/:slug" rewrite
 * must exist at the deployment's edge/reverse proxy (this file only runs under
 * the dev server). The reusable logic lives in the backend endpoint.
 */
const http = require("http");

const BACKEND = "http://localhost:8001";

const CRAWLER_UA = /facebookexternalhit|facebot|twitterbot|linkedinbot|whatsapp|slackbot|telegrambot|discordbot|googlebot|bingbot|applebot|redditbot|pinterest|embedly|iframely|skypeuripreview|vkshare|w3c_validator|baiduspider|yandex|ia_archiver|slurp|bot|crawl|spider|preview/i;

// Non-card first path segments that must never be treated as a slug.
const RESERVED = new Set([
  "api", "login", "register", "dashboard", "admin", "control", "settings",
  "team", "leads", "templates", "billing", "referral", "meetings", "industries",
  "privacy", "privacy-center", "activate", "nfc", "signatures", "integrations",
  "payment", "auth", "m", "legal", "industry-studio", "static", "assets",
  "favicon.ico", "robots.txt", "sitemap.xml", "manifest.json", "logo512.png",
  "asset-manifest.json",
]);

function fetchOg(slug, search, ua) {
  return new Promise((resolve) => {
    const path = `/api/og/${encodeURIComponent(slug)}${search || ""}`;
    const req = http.request(
      { host: "localhost", port: 8001, path, method: "GET", headers: { "User-Agent": ua } },
      (res) => {
        let body = "";
        res.on("data", (c) => (body += c));
        res.on("end", () => resolve({ status: res.statusCode, body }));
      }
    );
    req.on("error", () => resolve({ status: 0, body: "" }));
    req.end();
  });
}

module.exports = function (app) {
  app.use(async (req, res, next) => {
    if (req.method !== "GET") return next();
    const ua = req.headers["user-agent"] || "";
    if (!CRAWLER_UA.test(ua)) return next();

    // Only single-segment, extension-less paths can be card slugs.
    const m = /^\/([A-Za-z0-9_-]+)\/?$/.exec(req.path || "");
    if (!m) return next();
    const slug = m[1];
    if (RESERVED.has(slug)) return next();

    const search = req.url.includes("?") ? req.url.slice(req.url.indexOf("?")) : "";
    const { status, body } = await fetchOg(slug, search, ua);
    if (status === 200 && body) {
      res.setHeader("Content-Type", "text/html; charset=utf-8");
      res.setHeader("X-TapPresence-Prerender", "og");
      return res.end(body);
    }
    return next();
  });
};
