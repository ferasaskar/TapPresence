// Competitor comparison content. FACTUAL & DEFENSIBLE positioning only.
// TapPresence facts are verified against the live implementation (see report).
// Competitor facts reflect confirmed research provided by the owner; we openly
// acknowledge competitor strengths and never claim unsupported superiority.
// No fabricated pricing, ratings, reviews, user counts or feature claims.

// TapPresence differentiators that are VERIFIED LIVE in the product:
//  - Team plans from 3 seats (pricing config min_seats = 3)
//  - Built-in CRM pipeline + lead scoring, follow-up with AI-assisted drafts
//  - Business card + event badge scanning into the pipeline
//  - NFC & QR sharing, Save Contact (vCard), analytics, meeting booking
//  - EN / AR (RTL) / ES localization
//  - Outbound webhooks (team)
// NOT used as differentiators (not production-verified): public API consumption,
// custom domain (config-gated), SSO/SAML (none), Zapier/Salesforce/Pipedrive
// (no live connector), HubSpot (connector requires owner OAuth credentials).

const TP = {
  seats: "Team plans from 3 seats",
  card: "Yes — always-current digital profile",
  nfcqr: "Yes — NFC tap & QR, no app for recipient",
  scanner: "Yes — scan paper cards & event badges into leads",
  event: "Yes — scan badges/cards straight into your pipeline",
  crm: "Built-in pipeline, stages, tags & lead scoring",
  followup: "Built-in follow-up with AI-assisted drafts",
  meetings: "Yes — book from your card where enabled",
  analytics: "Yes — views, taps, scans & engagement",
  languages: "English, Arabic (RTL) & Spanish",
  webhooks: "Outbound webhooks (team)",
  trial: "14-day free trial (no permanent free plan)",
};

export const COMPARE_PAGES = {
  "tappresence-vs-blinq": {
    competitor: "Blinq",
    verified: true,
    title: "TapPresence vs Blinq — Digital Business Cards Compared | TapPresence",
    description: "Compare TapPresence and Blinq for digital business cards, NFC & QR sharing, lead capture, follow-up and team plans. TapPresence starts teams from 3 seats with built-in follow-up and AI-assisted drafts.",
    h1: "TapPresence vs Blinq",
    intro: "Blinq is a mature, well-established digital business card platform. TapPresence takes a relationship-first approach: an easy start for smaller teams and a built-in workflow that turns each new contact into a tracked lead with follow-up. Here's an honest, factual comparison.",
    competitorStrengths: "Blinq is a mature product with an established ecosystem — including integrations, event lead capture, business-card scanning and well-developed team and business features.",
    tpEdge: [
      "Lower team entry point — start from 3 seats",
      "Built-in CRM pipeline, follow-up and AI-assisted drafts",
      "Business card & event badge scanning into your pipeline",
      "English, Arabic (RTL) and Spanish out of the box",
    ],
    rows: [
      { dim: "Team entry point", tp: TP.seats, comp: "Business tier starts around a 5-card minimum" },
      { dim: "Digital business card", tp: TP.card, comp: "Yes" },
      { dim: "NFC & QR sharing", tp: TP.nfcqr, comp: "Yes" },
      { dim: "Business card scanner", tp: TP.scanner, comp: "Yes" },
      { dim: "Event lead capture", tp: TP.event, comp: "Yes — established" },
      { dim: "Relationship mgmt & follow-up", tp: TP.followup, comp: "Integration-led ecosystem" },
      { dim: "Analytics", tp: TP.analytics, comp: "Yes" },
      { dim: "Languages", tp: TP.languages, comp: "—" },
      { dim: "Free trial", tp: TP.trial, comp: "—" },
    ],
  },
  "tappresence-vs-hihello": {
    competitor: "HiHello",
    verified: true,
    title: "TapPresence vs HiHello — Digital Business Cards Compared | TapPresence",
    description: "Compare TapPresence and HiHello for digital business cards, business card scanning, lead capture, follow-up and team plans. TapPresence starts teams from 3 seats with integrated follow-up and AI-assisted drafts.",
    h1: "TapPresence vs HiHello",
    intro: "HiHello is a capable digital business card and contact-management platform with a strong feature set. TapPresence differentiates with a smaller team starting point and an integrated relationship and follow-up workflow, including AI-assisted follow-up drafts.",
    competitorStrengths: "HiHello has mature capabilities including digital cards, a business-card scanner, CRM integrations and team/business functionality.",
    tpEdge: [
      "Smaller team starting point — from 3 seats",
      "Integrated CRM pipeline and follow-up in one place",
      "AI-assisted follow-up drafts on every new lead",
      "English, Arabic (RTL) and Spanish support",
    ],
    rows: [
      { dim: "Team entry point", tp: TP.seats, comp: "Business tier starts around a 5-user minimum" },
      { dim: "Digital business card", tp: TP.card, comp: "Yes" },
      { dim: "NFC & QR sharing", tp: TP.nfcqr, comp: "Yes" },
      { dim: "Business card scanner", tp: TP.scanner, comp: "Yes" },
      { dim: "Lead management", tp: TP.crm, comp: "Contacts + CRM integrations" },
      { dim: "Follow-up", tp: TP.followup, comp: "—" },
      { dim: "Analytics", tp: TP.analytics, comp: "Yes" },
      { dim: "Languages", tp: TP.languages, comp: "—" },
      { dim: "Free trial", tp: TP.trial, comp: "—" },
    ],
  },
  "tappresence-vs-popl": {
    competitor: "Popl",
    verified: true,
    title: "TapPresence vs Popl — Digital Business Cards & Lead Capture | TapPresence",
    description: "Compare TapPresence and Popl. Popl offers extensive event lead capture; TapPresence focuses on a professional digital identity with built-in lead organisation, follow-up and AI-assisted drafts for professionals and small teams.",
    h1: "TapPresence vs Popl",
    intro: "Popl is heavily positioned around event lead capture with a deep tooling set. TapPresence is positioned differently — around a professional digital identity with simple, built-in lead organisation and follow-up for individuals and small teams. This comparison is honest about where each fits.",
    competitorStrengths: "Popl is strong at event lead capture, with capabilities such as badge scanning, contact enrichment, offline scanning, CRM integrations and event attribution/workflows.",
    tpEdge: [
      "Professional digital identity as the core, not just capture",
      "Built-in lead pipeline and follow-up with AI-assisted drafts",
      "Simple workflow for professionals and small teams — from 3 seats",
      "English, Arabic (RTL) and Spanish support",
    ],
    rows: [
      { dim: "Digital identity & card", tp: TP.card, comp: "Yes" },
      { dim: "NFC & QR sharing", tp: TP.nfcqr, comp: "Yes" },
      { dim: "Event lead capture", tp: TP.event, comp: "Extensive — badge & offline scanning, enrichment, attribution" },
      { dim: "Lead management & follow-up", tp: TP.followup, comp: "CRM integrations & event workflows" },
      { dim: "Analytics", tp: TP.analytics, comp: "Yes" },
      { dim: "Team entry point", tp: TP.seats, comp: "—" },
      { dim: "Languages", tp: TP.languages, comp: "—" },
      { dim: "Best fit", tp: "Professionals & small teams wanting identity + follow-up", comp: "Event & field teams needing heavy capture tooling" },
    ],
  },
  "tappresence-vs-wave": {
    competitor: "Wave Connect",
    verified: true,
    title: "TapPresence vs Wave Connect — Digital Business Cards Compared | TapPresence",
    description: "Compare TapPresence and Wave Connect. Wave offers a broad, enterprise-grade feature set; TapPresence focuses on a simple professional identity with built-in lead capture, follow-up and AI-assisted drafts for professionals and small teams.",
    h1: "TapPresence vs Wave Connect",
    intro: "Wave Connect offers a broad, enterprise-oriented feature set. TapPresence takes a simpler, relationship-first approach for professionals and small teams — a polished digital identity with built-in lead capture and follow-up. We compare honestly, without overstating.",
    competitorStrengths: "Wave Connect has a broad feature set including digital cards, NFC/QR, wallet passes, paper and event-badge scanning, offline functionality, integrations with Salesforce, HubSpot, Microsoft Dynamics and Zapier, analytics, team controls and enterprise SSO/SCIM capabilities.",
    tpEdge: [
      "Simpler, relationship-first workflow for small teams — from 3 seats",
      "Built-in pipeline and follow-up with AI-assisted drafts",
      "Fast to adopt without enterprise setup",
      "English, Arabic (RTL) and Spanish support",
    ],
    rows: [
      { dim: "Digital card, NFC & QR", tp: TP.nfcqr, comp: "Yes" },
      { dim: "Wallet passes", tp: "Google Wallet passes", comp: "Apple & Google Wallet" },
      { dim: "Card & badge scanning", tp: TP.scanner, comp: "Yes" },
      { dim: "Native CRM integrations", tp: TP.webhooks, comp: "Salesforce, HubSpot, Dynamics, Zapier" },
      { dim: "Enterprise SSO / SCIM", tp: "Not offered", comp: "Yes" },
      { dim: "Lead pipeline & follow-up", tp: TP.followup, comp: "Enterprise feature set" },
      { dim: "Languages", tp: TP.languages, comp: "—" },
      { dim: "Best fit", tp: "Professionals & small teams", comp: "Larger/enterprise teams needing broad integrations & controls" },
    ],
  },
};

// Cross-links between comparison pages (natural internal linking).
export const COMPARE_SLUGS = Object.keys(COMPARE_PAGES);
