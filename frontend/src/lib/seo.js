import { useEffect } from "react";

// Canonical production origin. All SEO URLs are absolute against this so prerendered
// snapshots (captured by the host) contain correct self-referencing canonicals.
export const SEO_ORIGIN = "https://tappresence.com";
export const SEO_LOGO = `${SEO_ORIGIN}/logo512.png`;

const upsertMeta = (attr, key, content) => {
  if (content == null) return;
  let el = document.head.querySelector(`meta[${attr}="${key}"]`);
  if (!el) {
    el = document.createElement("meta");
    el.setAttribute(attr, key);
    document.head.appendChild(el);
  }
  el.setAttribute("content", content);
};

const setCanonical = (href) => {
  let el = document.head.querySelector('link[rel="canonical"]');
  if (!el) {
    el = document.createElement("link");
    el.setAttribute("rel", "canonical");
    document.head.appendChild(el);
  }
  el.setAttribute("href", href);
};

const setRobots = (noindex) => {
  let el = document.head.querySelector('meta[name="robots"][data-seo]');
  if (noindex) {
    if (!el) {
      el = document.createElement("meta");
      el.setAttribute("name", "robots");
      el.setAttribute("data-seo", "1");
      document.head.appendChild(el);
    }
    el.setAttribute("content", "noindex, follow");
  } else if (el) {
    el.remove();
  }
};

const setJsonLd = (blocks) => {
  document.head.querySelectorAll('script[data-seo-jsonld]').forEach((n) => n.remove());
  (blocks || []).forEach((b) => {
    const s = document.createElement("script");
    s.type = "application/ld+json";
    s.setAttribute("data-seo-jsonld", "1");
    s.text = JSON.stringify(b);
    document.head.appendChild(s);
  });
};

/**
 * Dependency-free per-route <head> manager. Sets a unique title, description,
 * self-referencing canonical, OG/Twitter mirrors, optional noindex, and JSON-LD.
 * Captured by the host prerender because it mutates the live document head on mount.
 */
export function useSeo({ title, description, path, jsonLd, noindex = false }) {
  useEffect(() => {
    const url = path ? `${SEO_ORIGIN}${path}` : undefined;
    if (title) document.title = title;
    if (description !== undefined) upsertMeta("name", "description", description);
    if (url) {
      setCanonical(url);
      upsertMeta("property", "og:url", url);
    }
    if (title) {
      upsertMeta("property", "og:title", title);
      upsertMeta("name", "twitter:title", title);
    }
    if (description !== undefined) {
      upsertMeta("property", "og:description", description);
      upsertMeta("name", "twitter:description", description);
    }
    setRobots(noindex);
    setJsonLd(jsonLd);
    return () => { setRobots(false); setJsonLd([]); };
  }, [title, description, path, noindex, JSON.stringify(jsonLd)]);
}

// Reusable site-wide entity graph. sameAs uses ONLY verified official TapPresence profiles.
export const ORG_JSONLD = {
  "@context": "https://schema.org",
  "@type": "Organization",
  name: "TapPresence",
  url: SEO_ORIGIN,
  logo: SEO_LOGO,
  description:
    "TapPresence is a digital business card and professional networking platform — NFC & QR sharing, save-contact, business card scanner, lead capture, CRM pipeline, follow-up, meeting booking, analytics and teams.",
  sameAs: [
    "https://www.linkedin.com/company/tappresence/",
    "https://www.instagram.com/tappresence/",
  ],
};

export const WEBSITE_JSONLD = {
  "@context": "https://schema.org",
  "@type": "WebSite",
  name: "TapPresence",
  url: SEO_ORIGIN,
  inLanguage: ["en", "ar", "es"],
};

export const SOFTWARE_APP_JSONLD = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: "TapPresence",
  applicationCategory: "BusinessApplication",
  operatingSystem: "Web, iOS, Android",
  url: SEO_ORIGIN,
  description:
    "Premium digital business cards with NFC, QR, lead capture, AI follow-up, meetings and analytics — for individuals and teams.",
  offers: { "@type": "AggregateOffer", priceCurrency: "USD" },
};

export const breadcrumb = (items) => ({
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  itemListElement: items.map((it, i) => ({
    "@type": "ListItem",
    position: i + 1,
    name: it.name,
    item: `${SEO_ORIGIN}${it.path}`,
  })),
});

export const faqJsonLd = (qa) => ({
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: qa.map((x) => ({
    "@type": "Question",
    name: x.q,
    acceptedAnswer: { "@type": "Answer", text: x.a },
  })),
});
