// Comparison-page architecture. We publish ONLY verified TapPresence facts.
// Competitor specifications are NOT hard-coded here because they cannot be
// reliably verified from within this project. Until a competitor's details are
// independently verified (`verified: true` + a populated `competitor` map),
// the page renders TapPresence's verified capabilities only and stays noindex
// and out of the sitemap. No fabricated competitor pricing/features/reviews.

// TapPresence's own, verified capabilities — the single source of truth reused
// across every comparison page.
export const TAPPRESENCE_FACTS = [
  { k: "Digital business card", v: "Always-current online profile at one shareable link" },
  { k: "QR sharing", v: "Yes — every card has a QR code" },
  { k: "NFC sharing", v: "NFC-compatible sharing opens your digital profile (software platform, not a hardware store)" },
  { k: "Save Contact", v: "One-tap vCard save — no app required for the recipient" },
  { k: "Business card scanner", v: "Scan paper cards into digital contacts and leads (with review)" },
  { k: "Lead capture", v: "From your profile, QR shares and scanned cards" },
  { k: "CRM pipeline", v: "Stages, notes, tags and lead scoring" },
  { k: "Follow-up", v: "Timely follow-ups with AI-assisted drafts" },
  { k: "Meeting booking", v: "Contacts can book from your card where enabled" },
  { k: "Analytics", v: "Views, taps, scans and engagement" },
  { k: "Teams", v: "One workspace, member roles, branded cards, shared leads" },
  { k: "Pricing model", v: "Individual plan and seat-based team plans" },
  { k: "Free trial", v: "14-day free trial (no permanent free plan)" },
  { k: "Localization", v: "English, Arabic (RTL) and Spanish" },
  { k: "Best for", v: "Professionals and teams who network in person" },
];

// slug (after /compare/) -> competitor definition.
// verified:false => noindex + excluded from sitemap; competitor column not rendered.
export const COMPARE_PAGES = {
  "tappresence-vs-blinq": { competitor: "Blinq", verified: false },
  "tappresence-vs-hihello": { competitor: "HiHello", verified: false },
  "tappresence-vs-popl": { competitor: "Popl", verified: false },
  "tappresence-vs-wave": { competitor: "Wave", verified: false },
};
