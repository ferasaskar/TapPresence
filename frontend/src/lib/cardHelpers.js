import * as Icons from "lucide-react";

// Resolve a lucide icon by name from the DB, with a safe fallback.
export const getIcon = (name) => Icons[name] || Icons.Sparkles;

const digits = (v) => (v || "").replace(/[^\d+]/g, "");

// Build the ordered list of contact actions available for a card.
// Each template decides which subset to render.
export const buildActions = (card) => {
  const c = card.contact || {};
  const b = card.booking || {};
  const all = {
    message: c.whatsapp || c.phone
      ? { key: "message", label: "Message", sublabel: "Send a text", icon: "MessageCircle", href: `sms:${digits(c.whatsapp || c.phone)}` }
      : null,
    whatsapp: c.whatsapp
      ? { key: "whatsapp", label: "WhatsApp", sublabel: "Chat now", icon: "MessageSquare", href: `https://wa.me/${digits(c.whatsapp).replace("+", "")}` }
      : null,
    call: c.phone
      ? { key: "call", label: "Call", sublabel: "Direct line", icon: "Phone", href: `tel:${digits(c.phone)}` }
      : null,
    email: c.email
      ? { key: "email", label: "Email", sublabel: "Write to me", icon: "Mail", href: `mailto:${c.email}` }
      : null,
    meet: c.mapsUrl
      ? { key: "meet", label: "Meet", sublabel: "Get directions", icon: "MapPin", href: c.mapsUrl }
      : null,
    book: b.bookingUrl
      ? { key: "book", label: "Book a Call", sublabel: "Reserve time", icon: "CalendarClock", href: b.bookingUrl }
      : null,
  };
  return all;
};

export const socialList = (social = {}) => {
  const map = [
    { key: "linkedin", icon: "Linkedin", label: "LinkedIn" },
    { key: "instagram", icon: "Instagram", label: "Instagram" },
    { key: "x", icon: "Twitter", label: "X" },
    { key: "youtube", icon: "Youtube", label: "YouTube" },
    { key: "tiktok", icon: "Music2", label: "TikTok" },
  ];
  return map.filter((m) => social[m.key]).map((m) => ({ ...m, url: social[m.key] }));
};

export const orderedServices = (services = []) =>
  [...services].filter((s) => s.enabled !== false).sort((a, b) => (a.order || 0) - (b.order || 0));

export const orderedProjects = (projects = []) =>
  [...projects].sort((a, b) => (a.order || 0) - (b.order || 0));

// ONE source of truth for the public "Book Meeting" call-to-action label.
// Industry personalization only changes the WORDING — the booking flow/engine
// (BookMeetingDialog / external bookingUrl) stays identical across all templates.
const BOOKING_LABELS = {
  real_estate: "Book a Viewing",
  business: "Schedule a Consultation",
  sales: "Book a Call",
  technology: "Schedule a Demo",
  healthcare: "Book an Appointment",
  legal: "Schedule a Consultation",
  education: "Book a Session",
  hospitality: "Book a Meeting",
  automotive: "Book an Appointment",
  beauty: "Book an Appointment",
  finance: "Schedule a Consultation",
  custom: "Book a Meeting",
};

export const bookingLabel = (card) => BOOKING_LABELS[card?.industry] || "Book a Meeting";

// A booking CTA is shown ONLY when there is a valid booking path:
// native booking enabled, OR a non-empty external booking URL.
export const hasBooking = (card) => {
  const b = card?.booking || {};
  return !!(b.nativeEnabled || (b.bookingUrl && String(b.bookingUrl).trim()));
};
