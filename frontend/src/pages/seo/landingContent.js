// SEO landing page content — factual, based ONLY on existing TapPresence capabilities.
// No fake stats/reviews/awards. Used by SeoLanding.jsx.

const TRIAL = "Start your free 14-day trial";

const FEAT = {
  nfc: { t: "NFC & QR sharing", d: "Share your profile with one tap of an NFC card or a scan of your QR code — no app required for the person receiving it." },
  save: { t: "Save Contact", d: "Recipients save your details straight to their phone as a vCard in one tap." },
  scanner: { t: "Business card scanner", d: "Scan paper business cards and turn them into digital contacts and leads automatically." },
  leads: { t: "Lead capture", d: "Collect visitor details from your profile and at events, so no connection is lost." },
  crm: { t: "CRM pipeline", d: "Organise every lead through pipeline stages with notes, tags and lead scoring." },
  followup: { t: "Follow up", d: "Send timely follow-ups and AI-assisted drafts so conversations don't go cold." },
  meetings: { t: "Meeting booking", d: "Let contacts book a meeting with you directly from your digital card." },
  analytics: { t: "Analytics", d: "See profile views, taps, scans and engagement to know what's working." },
  teams: { t: "Teams", d: "Roll out consistent branded cards across your team with shared leads and roles." },
};

export const LANDING_PAGES = {
  "digital-business-card": {
    title: "Digital Business Card — Share Your Profile in One Tap | TapPresence",
    description: "A TapPresence digital business card lets you share your contact details, links and portfolio instantly via NFC or QR — no app needed for the recipient. Free 14-day trial.",
    h1: "Your digital business card, ready in minutes",
    intro: "A digital business card replaces paper cards with a single, always-up-to-date online profile you can share instantly by NFC tap or QR scan. Update it once and everyone always has your latest details.",
    breadcrumb: "Digital business card",
    features: ["nfc", "save", "meetings", "analytics", "crm"],
    faq: [
      { q: "What is a digital business card?", a: "A digital business card is an online profile with your name, role, contact details and links that you share instantly by NFC tap or QR scan instead of handing over a paper card." },
      { q: "Does the recipient need an app?", a: "No. Recipients open your card in any web browser and can save your contact with one tap — no app or sign-up required." },
      { q: "Can I share using QR?", a: "Yes. Every TapPresence card has a QR code you can show on your phone, add to a badge, or print." },
      { q: "Can I update my card after sharing it?", a: "Yes. Your card lives at one link, so any edit you make is instantly reflected for everyone who has it." },
    ],
    related: ["nfc-business-card", "business-card-scanner", "teams", "pricing"],
  },
  "nfc-business-card": {
    title: "NFC Business Card — Tap to Share Your Details | TapPresence",
    description: "An NFC business card shares your TapPresence profile with a single tap on a smartphone — no app needed to receive it. Add QR as a fallback. Try free for 14 days.",
    h1: "NFC business cards that share with one tap",
    intro: "An NFC business card has a small chip that opens your digital profile when tapped against a smartphone. TapPresence pairs NFC with a QR fallback so you can share anywhere, with anyone.",
    breadcrumb: "NFC business card",
    features: ["nfc", "save", "analytics", "teams"],
    faq: [
      { q: "How does an NFC business card work?", a: "Tapping the card on a phone opens your TapPresence profile in the browser instantly. Most modern phones read NFC with no app installed." },
      { q: "What if a phone doesn't support NFC?", a: "Every card also has a QR code, so you can always share by scanning as a fallback." },
      { q: "Does the recipient need an app?", a: "No — the card opens in a normal web browser and they can save your contact in one tap." },
    ],
    related: ["digital-business-card", "teams", "pricing"],
  },
  "business-card-scanner": {
    title: "Business Card Scanner — Turn Paper Cards into Leads | TapPresence",
    description: "Scan paper business cards with TapPresence to instantly create digital contacts and leads, then follow up and track them in your CRM pipeline. Free 14-day trial.",
    h1: "Scan paper business cards into digital leads",
    intro: "Collected a stack of paper cards? TapPresence's business card scanner reads them and creates digital contacts and leads automatically, so you can follow up without manual typing.",
    breadcrumb: "Business card scanner",
    features: ["scanner", "leads", "crm", "followup"],
    faq: [
      { q: "Can I scan traditional business cards?", a: "Yes. TapPresence scans paper business cards and turns them into structured digital contacts and leads." },
      { q: "What happens after I scan a card?", a: "The scanned contact becomes a lead in your pipeline, where you can add notes, tags and follow up." },
      { q: "Can I capture cards at events?", a: "Yes — scanning is ideal at events and conferences to capture every contact quickly." },
    ],
    related: ["lead-capture", "event-networking", "digital-business-card"],
  },
  "lead-capture": {
    title: "Lead Capture App — Never Lose a Connection | TapPresence",
    description: "Capture leads from your digital card, QR scans and scanned business cards, then organise and follow up with them in a built-in CRM pipeline. Try TapPresence free for 14 days.",
    h1: "Capture and manage every lead in one place",
    intro: "TapPresence captures leads from your profile, QR shares and scanned cards, then keeps them organised in a pipeline so you can follow up, score and convert — nothing slips through the cracks.",
    breadcrumb: "Lead capture",
    features: ["leads", "scanner", "crm", "followup", "analytics"],
    faq: [
      { q: "Can TapPresence capture leads?", a: "Yes. TapPresence captures leads from your digital card, QR shares and scanned business cards." },
      { q: "Can I follow up with contacts?", a: "Yes — you can follow up directly, with AI-assisted drafts, and track each lead through pipeline stages." },
      { q: "Where do captured leads go?", a: "Every lead lands in your CRM pipeline with notes, tags and lead scoring." },
    ],
    related: ["business-card-scanner", "sales-teams", "event-networking"],
  },
  "teams": {
    title: "Digital Business Cards for Teams | TapPresence",
    description: "Give your whole team branded digital business cards with shared lead capture, roles and analytics. Consistent presence across everyone. Free 14-day trial.",
    h1: "Digital business cards for your whole team",
    intro: "TapPresence for teams rolls out consistent, on-brand digital cards to every member, with shared lead capture, roles and analytics — so your company presents one professional identity everywhere.",
    breadcrumb: "Teams",
    features: ["teams", "leads", "crm", "analytics", "nfc"],
    faq: [
      { q: "Does TapPresence support teams?", a: "Yes. Teams get branded cards for every member, shared leads, roles and analytics from one workspace." },
      { q: "Can we keep branding consistent?", a: "Yes — team cards follow a shared, branded template so everyone looks consistent." },
      { q: "Can I track team engagement?", a: "Yes, analytics show views, taps and scans across the team." },
    ],
    related: ["sales-teams", "lead-capture", "pricing"],
  },
  "real-estate": {
    title: "Digital Business Cards for Real Estate Agents | TapPresence",
    description: "Real estate agents share listings, contact details and booking links in one tap with a TapPresence digital card, and capture buyer and seller leads on the go. Free 14-day trial.",
    h1: "Digital business cards for real estate",
    intro: "Meet buyers and sellers at viewings and open houses and share your details, listings and a booking link in one tap — then capture every lead and follow up before the competition.",
    breadcrumb: "Real estate",
    features: ["nfc", "leads", "meetings", "followup", "crm"],
    faq: [
      { q: "How does this help at open houses?", a: "Share your card by NFC or QR to instantly capture visitor details as leads and follow up afterwards." },
      { q: "Can clients book a viewing?", a: "Yes — contacts can book a meeting directly from your card." },
    ],
    related: ["lead-capture", "digital-business-card", "pricing"],
  },
  "sales-teams": {
    title: "Digital Business Cards for Sales Teams | TapPresence",
    description: "Equip your sales team with digital cards, business card scanning, shared lead capture and a CRM pipeline so every conversation becomes a tracked opportunity. Free 14-day trial.",
    h1: "Turn every sales conversation into a tracked lead",
    intro: "TapPresence gives sales teams NFC/QR cards, a business card scanner and a shared pipeline, so reps capture leads in the field and managers see engagement and follow-up in one place.",
    breadcrumb: "Sales teams",
    features: ["scanner", "leads", "crm", "followup", "teams"],
    faq: [
      { q: "How does TapPresence help sales teams?", a: "Reps capture leads via card shares and scans; everything flows into a shared pipeline with follow-up and analytics." },
      { q: "Can managers see team activity?", a: "Yes — analytics cover views, taps, scans and follow-up across the team." },
    ],
    related: ["lead-capture", "teams", "business-card-scanner"],
  },
  "event-networking": {
    title: "Digital Business Cards & Lead Capture for Events | TapPresence",
    description: "At events and conferences, share your TapPresence card by tap or QR and scan attendee badges and cards to capture leads instantly, then follow up. Free 14-day trial.",
    h1: "Capture every lead at your next event",
    intro: "Conferences and expos move fast. Share your card by NFC or QR, scan attendee business cards, and capture leads on the spot — then follow up with everyone from one organised pipeline.",
    breadcrumb: "Events",
    features: ["scanner", "leads", "crm", "followup", "analytics"],
    faq: [
      { q: "Can I capture leads at events?", a: "Yes — share your card and scan attendee cards to capture leads instantly during the event." },
      { q: "What happens to event leads afterwards?", a: "They're organised in your pipeline so you can follow up while the conversation is still fresh." },
    ],
    related: ["business-card-scanner", "lead-capture", "sales-teams"],
  },
  "consultants": {
    title: "Digital Business Cards for Consultants & Freelancers | TapPresence",
    description: "Consultants share a polished digital card with their bio, links, portfolio and a booking link in one tap, and capture leads with follow-up built in. Free 14-day trial.",
    h1: "A polished digital presence for consultants",
    intro: "Present a professional, always-current digital card with your bio, links and a booking link. Share it in one tap, capture enquiries as leads and follow up — no paper cards needed.",
    breadcrumb: "Consultants",
    features: ["nfc", "save", "meetings", "leads", "followup"],
    faq: [
      { q: "Can clients book a call from my card?", a: "Yes — meeting booking lets contacts schedule directly from your profile." },
      { q: "Can I show my portfolio?", a: "Yes, your card can feature links and portfolio content alongside your contact details." },
    ],
    related: ["digital-business-card", "lead-capture", "pricing"],
  },
  "healthcare": {
    title: "Digital Business Cards for Healthcare Professionals | TapPresence",
    description: "Healthcare professionals and clinics share contact details, booking and location in one tap with a hygienic, contactless TapPresence digital card. Free 14-day trial.",
    h1: "Contactless digital cards for healthcare",
    intro: "Share your details, clinic location and a booking link with patients and colleagues in one contactless tap or scan — no paper cards to reprint when details change.",
    breadcrumb: "Healthcare",
    features: ["nfc", "save", "meetings", "analytics"],
    faq: [
      { q: "Is sharing contactless?", a: "Yes — sharing is by NFC tap or QR scan, with no paper card exchanged." },
      { q: "Can patients book appointments?", a: "Yes, contacts can book a meeting directly from your card." },
    ],
    related: ["digital-business-card", "consultants", "pricing"],
  },
  "digital-business-card-uae": {
    title: "Digital Business Cards in the UAE | TapPresence",
    description: "TapPresence digital business cards for professionals and teams across the UAE — share by NFC or QR, capture leads and follow up, with EN/AR support. Free 14-day trial.",
    h1: "Digital business cards for the UAE",
    intro: "Professionals and teams across the UAE use TapPresence to share their details by NFC tap or QR scan, capture leads and follow up — with English and Arabic support built in.",
    breadcrumb: "Digital business card UAE",
    features: ["nfc", "save", "leads", "teams", "analytics"],
    faq: [
      { q: "Is TapPresence available in the UAE?", a: "Yes. TapPresence works for individuals and teams across the UAE and supports English and Arabic." },
      { q: "Does it support Arabic?", a: "Yes — the interface supports English, Arabic (RTL) and Spanish." },
    ],
    related: ["digital-business-card-dubai", "digital-business-card", "teams"],
  },
  "digital-business-card-dubai": {
    title: "Digital Business Cards in Dubai | TapPresence",
    description: "Networking in Dubai? Share your TapPresence digital card by NFC or QR, capture leads at events and follow up — with English and Arabic support. Free 14-day trial.",
    h1: "Digital business cards for Dubai",
    intro: "From DIFC to expos across Dubai, share your details in one tap, capture leads at events and follow up from one pipeline — all with English and Arabic support.",
    breadcrumb: "Digital business card Dubai",
    features: ["nfc", "leads", "scanner", "meetings", "analytics"],
    faq: [
      { q: "Is TapPresence available in Dubai?", a: "Yes — professionals and teams in Dubai use TapPresence to share cards, capture leads and follow up." },
      { q: "Can I capture leads at Dubai events?", a: "Yes, share your card and scan attendee cards to capture leads on the spot." },
    ],
    related: ["digital-business-card-uae", "event-networking", "digital-business-card"],
  },
};

export const SEO_FOOTER_LINKS = [
  { path: "/digital-business-card", label: "Digital Business Card" },
  { path: "/nfc-business-card", label: "NFC Business Card" },
  { path: "/business-card-scanner", label: "Business Card Scanner" },
  { path: "/lead-capture", label: "Lead Capture" },
  { path: "/teams", label: "For Teams" },
  { path: "/pricing", label: "Pricing" },
  { path: "/real-estate", label: "Real Estate" },
  { path: "/sales-teams", label: "Sales Teams" },
  { path: "/event-networking", label: "Events" },
  { path: "/consultants", label: "Consultants" },
  { path: "/healthcare", label: "Healthcare" },
  { path: "/digital-business-card-uae", label: "UAE" },
  { path: "/digital-business-card-dubai", label: "Dubai" },
];

export { FEAT, TRIAL };
