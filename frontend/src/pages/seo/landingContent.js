// SEO landing page content — factual, based ONLY on existing TapPresence capabilities.
// No fake stats/reviews/awards/hardware claims. Used by SeoLanding.jsx.
// `sections` = optional prose blocks (H2 + paragraph) for depth & heading hierarchy.

const TRIAL = "Start your free 14-day trial";

const FEAT = {
  nfc: { t: "NFC & QR sharing", d: "Share your profile with one tap of an NFC-compatible card or a scan of your QR code — no app required for the person receiving it." },
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
    title: "Digital Business Card for Professionals & Teams | TapPresence",
    description: "A TapPresence digital business card shares your contact details, links and portfolio instantly via NFC or QR — no app needed for the recipient. Save Contact, capture leads and follow up. Start a free 14-day trial.",
    h1: "Your digital business card, ready in minutes",
    intro: "A digital business card replaces paper cards with a single, always-up-to-date online profile you can share instantly by NFC tap or QR scan. Update it once and everyone always has your latest details.",
    breadcrumb: "Digital business card",
    sections: [
      { h: "What a TapPresence digital business card is", p: "It's an online profile with your name, role, company, contact details, links and portfolio, hosted at one shareable link. Because everything lives at that link, any edit is reflected instantly for everyone who already has your card — no reprinting, no outdated numbers." },
      { h: "Who it's for", p: "Individuals who network — sales, consultants, real estate agents, founders, healthcare and event professionals — as well as whole teams who want one consistent, branded presence. It works globally and supports English, Arabic (right-to-left) and Spanish." },
      { h: "How sharing works", p: "Tap an NFC-compatible card on a phone or let people scan your QR code to open your profile in any browser. They save your contact in one tap as a vCard — no app or sign-up required to receive it." },
      { h: "From contact to closed loop", p: "Interested contacts become leads you can organise in a CRM pipeline with notes, tags and lead scoring, then follow up with timely messages and AI-assisted drafts. Analytics show views, taps and scans so you know what's working. Where supported, contacts can also book a meeting straight from your card." },
    ],
    features: ["nfc", "save", "meetings", "crm", "analytics"],
    faq: [
      { q: "What is a digital business card?", a: "A digital business card is an online profile with your name, role, contact details and links that you share instantly by NFC tap or QR scan instead of handing over a paper card." },
      { q: "Does the recipient need an app?", a: "No. Recipients open your card in any web browser and can save your contact with one tap — no app or sign-up required." },
      { q: "Can I share using QR?", a: "Yes. Every TapPresence card has a QR code you can show on your phone, add to a badge, or print." },
      { q: "Can I update my card after sharing it?", a: "Yes. Your card lives at one link, so any edit you make is instantly reflected for everyone who has it." },
      { q: "Is there a free plan?", a: "TapPresence uses a 14-day free trial rather than a permanent free plan, so you can try everything before you decide." },
    ],
    related: ["teams", "nfc-business-card", "business-card-scanner", "lead-capture", "pricing"],
  },
  "nfc-business-card": {
    title: "NFC Digital Business Card — Tap to Share Your Profile | TapPresence",
    description: "Share your TapPresence digital profile with a single tap on an NFC-compatible smartphone — no app needed to receive it, with QR as a fallback. Save Contact, capture leads and follow up. Free 14-day trial.",
    h1: "NFC digital business cards that share with one tap",
    intro: "An NFC business card opens your digital profile when tapped against a smartphone. TapPresence pairs NFC-compatible sharing with a QR fallback so you can share anywhere, with anyone — the focus is your digital profile, not selling hardware.",
    breadcrumb: "NFC business card",
    sections: [
      { h: "How NFC sharing works", p: "Your TapPresence profile can be opened by tapping an NFC-compatible card or accessory on a phone. Most modern smartphones read NFC with no app installed, opening your card directly in the browser." },
      { h: "QR is always the fallback", p: "Not every phone or situation suits a tap, so every card also has a QR code. Show it on your screen, add it to a badge or print it — the same profile opens either way." },
      { h: "It's about the profile, not the plastic", p: "TapPresence is a digital presence platform. The value is your always-current online card, Save Contact, lead capture and follow-up — NFC is simply one convenient way to open it." },
      { h: "Device and browser notes", p: "Receiving a card only needs a modern web browser. NFC tap behaviour depends on the recipient's device and settings; when NFC isn't available, the QR code works everywhere." },
    ],
    features: ["nfc", "save", "leads", "analytics"],
    faq: [
      { q: "How does an NFC business card work?", a: "Tapping an NFC-compatible card on a phone opens your TapPresence profile in the browser instantly. Most modern phones read NFC with no app installed." },
      { q: "What if a phone doesn't support NFC?", a: "Every card also has a QR code, so you can always share by scanning as a fallback." },
      { q: "Does the recipient need an app?", a: "No — the card opens in a normal web browser and they can save your contact in one tap." },
      { q: "Do I have to buy a physical NFC card?", a: "TapPresence is a digital platform — your profile can be shared by QR alone. NFC-compatible accessories are an optional convenience, not a requirement to use TapPresence." },
    ],
    related: ["digital-business-card", "business-card-scanner", "teams", "pricing"],
  },
  "business-card-scanner": {
    title: "Business Card Scanner App — Turn Paper Cards into Leads | TapPresence",
    description: "Scan paper business cards with TapPresence to create digital contacts and leads, then follow up and track them in your CRM pipeline. Ideal for events and sales teams. Free 14-day trial.",
    h1: "Scan paper business cards into digital leads",
    intro: "Collected a stack of paper cards? TapPresence's business card scanner reads them and creates digital contacts and leads automatically, so you can follow up without manual typing.",
    breadcrumb: "Business card scanner",
    sections: [
      { h: "The scan-to-lead workflow", p: "Point your camera at a paper business card, TapPresence extracts the contact details, you review and confirm, and the contact is saved as a lead in your pipeline — ready for notes, tags and follow-up." },
      { h: "Built for events and the field", p: "Scanning is fastest exactly where you need it: at conferences, expos and sales meetings. Capture a whole stack of cards in minutes instead of typing them up later that night." },
      { h: "Accuracy and review", p: "Extraction is automatic but you always review the details before saving, so you stay in control of what lands in your CRM. Results depend on the quality and legibility of the original card." },
    ],
    features: ["scanner", "leads", "crm", "followup"],
    faq: [
      { q: "Can I scan traditional business cards?", a: "Yes. TapPresence scans paper business cards and turns them into structured digital contacts and leads after you review the details." },
      { q: "What happens after I scan a card?", a: "The scanned contact becomes a lead in your pipeline, where you can add notes, tags and follow up." },
      { q: "Can I capture cards at events?", a: "Yes — scanning is ideal at events and conferences to capture every contact quickly." },
      { q: "How accurate is the scanner?", a: "It reads the card automatically and lets you review before saving; accuracy depends on how clear and legible the original card is." },
    ],
    related: ["lead-capture", "event-lead-capture", "sales-teams", "digital-business-card"],
  },
  "lead-capture": {
    title: "Lead Capture App for In-Person Networking | TapPresence",
    description: "Capture leads from your digital card, QR scans and scanned paper cards during real-world networking, then organise, score and follow up in a built-in CRM pipeline. Free 14-day trial.",
    h1: "Capture every in-person connection as a lead",
    intro: "TapPresence is built for in-person networking, not generic web forms. Capture leads from your profile, QR shares and scanned paper cards, then keep them organised in a pipeline so you can follow up, score and convert — nothing slips through the cracks.",
    breadcrumb: "Lead capture",
    sections: [
      { h: "Made for the moment you meet someone", p: "Every share is a chance to capture a lead: tap or scan to swap details, or scan the paper card you're handed. The connection is recorded while it's fresh instead of ending up as a note you forget." },
      { h: "From lead to pipeline", p: "Captured leads land in a CRM pipeline with stages, notes, tags and lead scoring, so you can prioritise the people worth your time and see the whole picture in one place." },
      { h: "Follow up before it goes cold", p: "Send timely follow-ups with AI-assisted drafts and track each lead through your stages. Analytics show views, taps and scans so you know which conversations to chase." },
    ],
    features: ["leads", "scanner", "crm", "followup", "analytics"],
    faq: [
      { q: "How does TapPresence capture leads?", a: "It captures leads from your digital card, QR shares and scanned paper business cards during real-world networking." },
      { q: "Is this a web form lead generation tool?", a: "No — TapPresence focuses on in-person lead capture at meetings and events, not generic online form building." },
      { q: "Can I follow up with contacts?", a: "Yes — you can follow up directly, with AI-assisted drafts, and track each lead through pipeline stages." },
      { q: "Where do captured leads go?", a: "Every lead lands in your CRM pipeline with notes, tags and lead scoring." },
    ],
    related: ["business-card-scanner", "event-lead-capture", "sales-teams", "pricing"],
  },
  "teams": {
    title: "Digital Business Cards for Teams | TapPresence",
    description: "Give your whole team branded digital business cards from one workspace, with member roles, shared lead capture, analytics and seat-based pricing. Consistent presence across everyone. Free 14-day trial.",
    h1: "Digital business cards for your whole team",
    intro: "TapPresence for teams rolls out consistent, on-brand digital cards to every member from a single workspace, with member roles, shared lead capture and analytics — so your company presents one professional identity everywhere.",
    breadcrumb: "Teams",
    sections: [
      { h: "One workspace, every member", p: "Manage your team from a central workspace: add members, assign roles and keep everyone's cards on a shared, branded template so the whole company looks consistent — no matter who's handing out the card." },
      { h: "Shared leads and visibility", p: "Leads captured by any member flow into the team's pipeline, and analytics show views, taps and scans across everyone, so managers can see engagement and follow-up activity in one place." },
      { h: "Seat-based and simple", p: "Team plans are seat-based, so you pay for the members you add. Set up starts with a 14-day trial — no permanent free plan — so you can roll it out to the team before committing." },
    ],
    features: ["teams", "leads", "crm", "analytics", "nfc"],
    faq: [
      { q: "Does TapPresence support teams?", a: "Yes. Teams get branded cards for every member, shared leads, roles and analytics from one workspace." },
      { q: "Can we keep branding consistent?", a: "Yes — team cards follow a shared, branded template so everyone looks consistent." },
      { q: "How does team pricing work?", a: "Team plans are seat-based — you add the members you need. See the pricing page for current rates and the 14-day trial." },
      { q: "Can I track team engagement?", a: "Yes, analytics show views, taps and scans across the team." },
    ],
    related: ["sales-teams", "event-lead-capture", "real-estate", "pricing"],
  },
  "real-estate": {
    title: "Digital Business Cards for Real Estate Agents | TapPresence",
    description: "Real estate agents share listings, contact details and booking links in one tap with a TapPresence digital card, and capture buyer and seller leads at viewings and open houses. Free 14-day trial.",
    h1: "Digital business cards for real estate",
    intro: "Meet buyers and sellers at viewings and open houses and share your details, links and a booking link in one tap — then capture every lead and follow up before the competition.",
    breadcrumb: "Real estate",
    sections: [
      { h: "At the open house", p: "Share your card by NFC or QR to capture every visitor's details as a lead on the spot, instead of relying on a paper sign-in sheet you have to transcribe later." },
      { h: "Keep the deal moving", p: "Leads land in your pipeline for follow-up, and where supported, prospects can book a viewing or call straight from your card — so momentum doesn't stall after the first hello." },
    ],
    features: ["nfc", "leads", "meetings", "followup", "crm"],
    faq: [
      { q: "How does this help at open houses?", a: "Share your card by NFC or QR to instantly capture visitor details as leads and follow up afterwards." },
      { q: "Can clients book a viewing?", a: "Yes — contacts can book a meeting directly from your card where meeting booking is enabled." },
    ],
    related: ["lead-capture", "digital-business-card-uae", "digital-business-card", "pricing"],
  },
  "sales-teams": {
    title: "Digital Business Cards for Sales Teams | TapPresence",
    description: "Equip your sales team with digital cards, business card scanning, shared lead capture and a CRM pipeline so every conversation becomes a tracked, measurable opportunity. Free 14-day trial.",
    h1: "Turn every sales conversation into a tracked lead",
    intro: "TapPresence gives sales teams NFC/QR cards, a business card scanner and a shared pipeline, so reps capture leads in the field and managers see engagement and follow-up in one place.",
    breadcrumb: "Sales teams",
    sections: [
      { h: "Capture in the field", p: "Reps share their identity by tap or QR and scan the paper cards they're handed, so every prospect is captured as a lead the moment the conversation happens." },
      { h: "One shared pipeline", p: "Leads flow into a shared CRM pipeline with stages, notes and lead scoring, giving the team a single source of truth and managers visibility into activity and follow-up." },
      { h: "Measurable activity", p: "Analytics show views, taps, scans and engagement across the team, so you can see who's active and which conversations are turning into opportunities." },
    ],
    features: ["scanner", "leads", "crm", "followup", "teams"],
    faq: [
      { q: "How does TapPresence help sales teams?", a: "Reps capture leads via card shares and scans; everything flows into a shared pipeline with follow-up and analytics." },
      { q: "Can managers see team activity?", a: "Yes — analytics cover views, taps, scans and follow-up across the team." },
    ],
    related: ["teams", "lead-capture", "event-lead-capture", "business-card-scanner"],
  },
  "event-networking": {
    title: "Digital Business Cards for Event Networking | TapPresence",
    description: "Network smarter at conferences and expos: share your TapPresence card by tap or QR, swap details instantly and keep every new connection organised for follow-up. Free 14-day trial.",
    h1: "Make every event connection count",
    intro: "Conferences and expos are where relationships start. Share your card by NFC or QR, swap details in seconds and keep every conversation organised so the people you meet don't become a pile of forgotten paper cards.",
    breadcrumb: "Event networking",
    sections: [
      { h: "Networking without the friction", p: "Skip the fumble of paper cards and typos. Tap or show your QR to share a polished, always-current profile, and let new contacts save you in one tap — even if they've run out of cards themselves." },
      { h: "Remember who you met", p: "Every connection can be kept as a lead with notes and context, so a great five-minute hallway chat still means something a week later when you follow up." },
      { h: "Networking vs. lead capture", p: "This page is about person-to-person networking at events. If your goal is capturing and processing leads at scale — booth traffic, badge and card scanning into a pipeline — see the dedicated event lead capture page." },
    ],
    features: ["nfc", "save", "leads", "followup", "analytics"],
    faq: [
      { q: "How does TapPresence help at events?", a: "Share your card by tap or QR to swap details instantly and keep every new connection saved as a lead for follow-up." },
      { q: "What if the other person has no cards left?", a: "No problem — they open your profile in their browser and save your contact in one tap, and you can capture their details too." },
      { q: "What's the difference from event lead capture?", a: "Event networking is about individual connections; event lead capture focuses on capturing and processing leads at scale using scanning and a pipeline." },
    ],
    related: ["event-lead-capture", "business-card-scanner", "lead-capture", "teams"],
  },
  "event-lead-capture": {
    title: "Event Lead Capture App for Trade Shows & Conferences | TapPresence",
    description: "Capture and process leads at trade shows and conferences with TapPresence: scan business cards, capture visitor details, add context and push everything into a CRM pipeline for follow-up and analytics. Free 14-day trial.",
    h1: "Event lead capture that fills your pipeline",
    intro: "Turn booth traffic and conference conversations into organised, followable leads. Share your card, scan the paper cards you collect and capture visitor details — then work every lead from a single pipeline with follow-up and analytics.",
    breadcrumb: "Event lead capture",
    sections: [
      { h: "Capture leads at scale", p: "At a busy stand you can't type contacts one by one. Scan the business cards you're handed and share your own card by tap or QR, capturing each visitor as a lead in seconds so nobody is missed." },
      { h: "Add context while it's fresh", p: "Attach notes and tags to each lead as you go, so the follow-up team knows what was discussed and how hot the lead is — not just a name and an email." },
      { h: "Straight into your pipeline", p: "Every captured lead flows into a CRM pipeline with stages and lead scoring, and analytics show engagement, so you can prioritise and follow up while the event is still on people's minds." },
      { h: "Not event management software", p: "TapPresence is a lead capture and follow-up tool, not a ticketing or event-management platform. It's focused on one job: turning the people you meet at events into tracked, followable leads." },
    ],
    features: ["scanner", "leads", "crm", "followup", "analytics"],
    faq: [
      { q: "What is an event lead capture app?", a: "It's a tool for capturing the contacts you meet at trade shows and conferences — by scanning cards and sharing your profile — and organising them as leads for follow-up." },
      { q: "Does TapPresence scan business cards at events?", a: "Yes. Scan the paper cards you collect and TapPresence turns them into leads in your pipeline after you review the details." },
      { q: "Is this event-management or ticketing software?", a: "No. TapPresence focuses on lead capture and follow-up, not running or ticketing events." },
      { q: "Can my whole team capture leads at one event?", a: "Yes — team members capture into a shared pipeline so all the event's leads are in one place." },
    ],
    related: ["business-card-scanner", "lead-capture", "teams", "sales-teams", "pricing"],
  },
  "consultants": {
    title: "Digital Business Cards for Consultants & Freelancers | TapPresence",
    description: "Consultants share a polished digital card with their bio, links, portfolio and a booking link in one tap, and capture enquiries as leads with follow-up built in. Free 14-day trial.",
    h1: "A polished digital presence for consultants",
    intro: "Present a professional, always-current digital card with your bio, links and a booking link. Share it in one tap, capture enquiries as leads and follow up — no paper cards needed.",
    breadcrumb: "Consultants",
    sections: [
      { h: "Your credibility, in one link", p: "Show your bio, services, links and portfolio on a single polished profile that always reflects your latest work — far more than a name and number on card stock." },
      { h: "Turn interest into booked calls", p: "Contacts can book a meeting directly from your card where enabled, and enquiries are captured as leads you can follow up with AI-assisted drafts." },
    ],
    features: ["nfc", "save", "meetings", "leads", "followup"],
    faq: [
      { q: "Can clients book a call from my card?", a: "Yes — meeting booking lets contacts schedule directly from your profile where enabled." },
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
    sections: [
      { h: "Hygienic, contactless sharing", p: "Share by NFC tap or QR scan without exchanging paper, and keep your details, location and booking link current for patients and referring colleagues alike." },
      { h: "Easy for patients to reach you", p: "Patients save your contact in one tap and can book an appointment straight from your card where meeting booking is enabled." },
    ],
    features: ["nfc", "save", "meetings", "analytics"],
    faq: [
      { q: "Is sharing contactless?", a: "Yes — sharing is by NFC tap or QR scan, with no paper card exchanged." },
      { q: "Can patients book appointments?", a: "Yes, contacts can book a meeting directly from your card where enabled." },
    ],
    related: ["digital-business-card", "consultants", "pricing"],
  },
  "digital-business-card-uae": {
    title: "Digital Business Card UAE for Professionals & Teams | TapPresence",
    description: "Digital business cards for professionals and teams across the UAE — share by NFC or QR, capture leads and follow up, with English and Arabic (RTL) support. Free 14-day trial.",
    h1: "Digital business cards for the UAE",
    intro: "Professionals and teams across the UAE use TapPresence to share their details by NFC tap or QR scan, capture leads and follow up — with English and Arabic support built in.",
    breadcrumb: "Digital business card UAE",
    sections: [
      { h: "Built for how the UAE networks", p: "Business across the Emirates runs on relationships and fast introductions — at meetings, majlis, expos and industry events. A tap or QR share gets your details across instantly, in English or Arabic, without hunting for a paper card." },
      { h: "For companies and sales teams", p: "Roll out branded cards to a whole team from one workspace, capture leads in the field and keep them in a shared pipeline — useful for sales, real estate, consultants and event-heavy industries." },
      { h: "Bilingual by design", p: "TapPresence supports English, Arabic (right-to-left) and Spanish, so your card and the app read naturally for a multilingual UAE audience." },
    ],
    features: ["nfc", "save", "leads", "teams", "analytics"],
    faq: [
      { q: "Is TapPresence available in the UAE?", a: "Yes. TapPresence works for individuals and teams across the UAE and supports English and Arabic." },
      { q: "Does it support Arabic?", a: "Yes — the interface supports English, Arabic (RTL) and Spanish." },
      { q: "Can UAE companies use it for their teams?", a: "Yes — teams get branded cards, shared lead capture and analytics from one workspace, on seat-based pricing." },
    ],
    related: ["digital-business-card-dubai", "digital-business-card", "teams", "real-estate"],
  },
  "digital-business-card-dubai": {
    title: "Digital Business Card Dubai for Professionals & Teams | TapPresence",
    description: "Networking in Dubai? Share your TapPresence digital card by NFC or QR, capture leads at events and follow up — with English and Arabic (RTL) support. Free 14-day trial.",
    h1: "Digital business cards for Dubai",
    intro: "From DIFC and Business Bay to expos across the city, share your details in one tap, capture leads at events and follow up from one pipeline — all with English and Arabic support.",
    breadcrumb: "Digital business card Dubai",
    sections: [
      { h: "Made for Dubai's pace", p: "Dubai's calendar is packed with conferences, launches and networking events. Share your card by tap or QR to swap details in seconds, and scan the paper cards you collect so every introduction becomes a lead." },
      { h: "Follow up before the week is out", p: "Leads land in a pipeline with notes and lead scoring, so the connection you made at a Dubai expo turns into a real follow-up rather than a business card lost in a jacket pocket." },
      { h: "English and Arabic", p: "With English, Arabic (RTL) and Spanish support, your card works naturally across Dubai's international, multilingual business community." },
    ],
    features: ["nfc", "leads", "scanner", "meetings", "analytics"],
    faq: [
      { q: "Is TapPresence available in Dubai?", a: "Yes — professionals and teams in Dubai use TapPresence to share cards, capture leads and follow up." },
      { q: "Can I capture leads at Dubai events?", a: "Yes, share your card and scan attendee cards to capture leads on the spot." },
      { q: "Does it support Arabic in Dubai?", a: "Yes — the app and cards support English, Arabic (right-to-left) and Spanish." },
    ],
    related: ["digital-business-card-uae", "event-lead-capture", "event-networking", "digital-business-card"],
  },
};

export const SEO_FOOTER_LINKS = [
  { path: "/digital-business-card", label: "Digital Business Card" },
  { path: "/nfc-business-card", label: "NFC Business Card" },
  { path: "/business-card-scanner", label: "Business Card Scanner" },
  { path: "/lead-capture", label: "Lead Capture" },
  { path: "/event-lead-capture", label: "Event Lead Capture" },
  { path: "/teams", label: "For Teams" },
  { path: "/pricing", label: "Pricing" },
  { path: "/real-estate", label: "Real Estate" },
  { path: "/sales-teams", label: "Sales Teams" },
  { path: "/event-networking", label: "Event Networking" },
  { path: "/consultants", label: "Consultants" },
  { path: "/healthcare", label: "Healthcare" },
  { path: "/digital-business-card-uae", label: "UAE" },
  { path: "/digital-business-card-dubai", label: "Dubai" },
];

// Company / trust pages surfaced in footers.
export const COMPANY_FOOTER_LINKS = [
  { path: "/about", label: "About" },
  { path: "/contact", label: "Contact" },
  { path: "/security", label: "Security" },
];

export { FEAT, TRIAL };
