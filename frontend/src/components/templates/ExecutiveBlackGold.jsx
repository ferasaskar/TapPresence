import { motion } from "framer-motion";
import { useState, useEffect, useRef } from "react";
import { useProfile } from "@/context/ProfileContext";
import { ArrowRight, UserPlus, CalendarClock, MessageCircle, Share2, Printer, QrCode, ChevronDown } from "lucide-react";
import { toast } from "sonner";
import { resolveImg, posterUrl } from "@/lib/api";
import { buildActions, getIcon, orderedServices, orderedProjects } from "@/lib/cardHelpers";
import { AvailabilityBadge } from "@/components/profile/AvailabilityBadge";
import { SocialIcons } from "@/components/profile/SocialIcons";
import { SaveContactButton } from "@/components/profile/SaveContactButton";
import { QRBlock } from "@/components/profile/QRBlock";
import { ActionButton } from "@/components/profile/ActionButton";
import { InquiryForm } from "@/components/profile/InquiryForm";
import { BookMeetingDialog } from "@/components/profile/BookMeetingDialog";
import { ExchangeContactDialog } from "@/components/profile/ExchangeContactDialog";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { accentHex, accentGrad, hexToRgba } from "@/lib/accents";
import { industryRootStyle, BASE_RGB } from "@/lib/industries";
import { INDUSTRY_CARDS } from "@/lib/industryCards";

const fade = (i = 0) => ({
  initial: { opacity: 0, y: 24 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: "-40px" },
  transition: { duration: 0.7, delay: i * 0.08, ease: [0.22, 1, 0.36, 1] },
});

const Overline = ({ children }) => (
  <p className="text-[11px] uppercase tracking-[0.35em] mb-3" style={{ color: "var(--ac)" }}>{children}</p>
);

export const ExecutiveBlackGold = ({ data }) => {
  const { identity: id = {}, contact: c = {}, booking: b = {}, social = {}, slug } = data;
  const [exchangeOpen, setExchangeOpen] = useState(false);
  const [bookOpen, setBookOpen] = useState(false);
  const [msgOpen, setMsgOpen] = useState(false);
  const [qrOpen, setQrOpen] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);
  const [showSticky, setShowSticky] = useState(false);
  const { track, publicView } = useProfile();
  const ctaRef = useRef(null);
  const actions = buildActions(data);
  const services = orderedServices(data.services);
  const projects = orderedProjects(data.projects);
  const location = [id.city, id.country].filter(Boolean).join(", ");

  // Quick actions — Call · WhatsApp · Email · Message (single compact row, no duplicates)
  const iconRow = [actions.call, actions.whatsapp, actions.email, actions.message].filter(Boolean);

  const GOLD = accentHex("executive-black-gold", data.accent, data.custom_accent_color);
  const [g1, g2, g3] = accentGrad("executive-black-gold", data.accent, data.custom_accent_color);
  const gBorder = hexToRgba(GOLD, 0.4);
  const gBorder30 = hexToRgba(GOLD, 0.3);
  const gGlow = hexToRgba(GOLD, 0.5);
  const panelTint = hexToRgba(GOLD, 0.07);
  const panelHoverGlow = hexToRgba(GOLD, 0.2);

  const indBase = INDUSTRY_CARDS.find((cc) => cc.id === data.industry)?.base;
  const scrimBase = data.industry && indBase ? indBase : BASE_RGB["executive-black-gold"];

  const portraitTransform = `translate(${id.imageOffsetX || 0}%, ${id.imageOffsetY || 0}%) scale(${id.imageScale || 1})`;

  const bookingActive = b.nativeEnabled || b.bookingUrl;
  const openExchange = () => { track?.("tap", "cta_exchange"); setExchangeOpen(true); };
  const openBook = () => { track?.("tap", "cta_book"); setBookOpen(true); };
  const openMsg = (from = "cta_message") => { track?.("tap", from); setMsgOpen(true); };

  // Sticky mobile conversion bar: show once the primary CTAs scroll out of view.
  useEffect(() => {
    const el = ctaRef.current;
    if (!el || typeof IntersectionObserver === "undefined") return;
    const io = new IntersectionObserver(([e]) => setShowSticky(!e.isIntersecting), { rootMargin: "-8px 0px 0px 0px", threshold: 0 });
    io.observe(el);
    return () => io.disconnect();
  }, []);

  const utilBtn = "flex flex-col items-center justify-center gap-1.5 rounded-xl border py-3 text-[10px] uppercase tracking-[0.12em] transition-all duration-300 hover:-translate-y-0.5";
  const utilStyle = { borderColor: gBorder, background: panelTint, color: "#ececec" };

  const doShare = async () => {
    const url = `${window.location.origin}/${slug}`;
    if (navigator.share) {
      try { await navigator.share({ title: id.fullName, text: `${id.fullName} — digital card`, url }); } catch (_) {}
    } else {
      try { await navigator.clipboard.writeText(url); toast.success("Profile link copied"); }
      catch { toast.error("Could not copy link"); }
    }
  };

  return (
    <div className="relative min-h-screen font-sans text-neutral-200 overflow-hidden" style={{ backgroundColor: `rgb(${scrimBase})`, "--ac": GOLD, ...industryRootStyle(data, scrimBase, GOLD) }}>
      <div className="grain-overlay" style={{ opacity: 0.06 }} />
      <div className="pointer-events-none absolute left-1/2 top-0 h-[420px] w-[420px] -translate-x-1/2 rounded-full opacity-20 blur-3xl" style={{ background: GOLD }} />

      <div className="relative mx-auto w-full max-w-lg px-6 pb-28 pt-12 sm:px-8 sm:pb-16">

        {/* PROFILE HERO */}
        <motion.header {...fade(0)} className="flex flex-col items-center text-center">
          <div className="relative mb-6">
            <div className="absolute -inset-2 rounded-full" style={{ background: `conic-gradient(from 180deg, ${GOLD}, ${hexToRgba(GOLD, 0.25)}, ${GOLD})` }} />
            <div className="absolute -inset-2 rounded-full blur-md opacity-50" style={{ background: GOLD }} />
            <div className="relative h-32 w-32 overflow-hidden rounded-full" style={{ border: "3px solid rgb(" + scrimBase + ")" }}>
              {id.profilePhoto ? (
                <img
                  src={resolveImg(id.profilePhoto)}
                  alt={id.fullName}
                  data-testid="hero-portrait"
                  className="h-full w-full object-cover"
                  style={{ transform: portraitTransform, transformOrigin: "center" }}
                />
              ) : (
                <div data-testid="hero-portrait" className="h-full w-full bg-neutral-800" />
              )}
            </div>
          </div>
          <AvailabilityBadge
            label={id.availabilityBadge}
            className="mb-4 inline-flex items-center gap-2 rounded-full px-4 py-1 text-xs tracking-widest uppercase"
            dotClassName="w-1.5 h-1.5 rounded-full"
          />
          <h1
            data-testid="hero-name"
            className="tp-name font-serif"
            style={{ color: GOLD, fontSize: "clamp(1.85rem, 8.5vw, 3rem)", lineHeight: 1.05, letterSpacing: "-0.01em" }}
          >
            {id.fullName}
          </h1>
          {id.jobTitle ? <p className="tp-balance mt-3 text-[15px] leading-relaxed tracking-wide text-neutral-200 sm:text-base">{id.jobTitle}</p> : null}
          {id.company ? <p className="tp-balance mt-1.5 text-[13px] tracking-[0.18em] uppercase text-neutral-400">{id.company}</p> : null}
          {location ? <p className="tp-balance mt-2 text-[11px] tracking-[0.15em] uppercase text-neutral-500">{location}</p> : null}
          {id.bio ? <p className="tp-pretty mt-4 max-w-sm text-[15px] leading-[1.7] text-neutral-300">{id.bio}</p> : null}
        </motion.header>

        {/* QUICK ACTIONS — Call · WhatsApp · Email · Message */}
        <motion.div {...fade(1)} className="mt-7 grid grid-cols-4 gap-2.5" data-testid="hero-actions">
          {iconRow.map((a) => (
            <ActionButton
              key={a.key}
              action={a}
              testId={`hero-action-${a.key}`}
              className="flex h-[62px] w-full flex-col items-center justify-center gap-1.5 rounded-xl border text-[10px] uppercase tracking-[0.12em] text-neutral-300 transition-all duration-300 hover:-translate-y-1"
              iconClassName="w-[18px] h-[18px]"
            />
          ))}
        </motion.div>

        {/* PRIMARY CTAs — Exchange Contact + Book a Meeting (directly below quick actions) */}
        <motion.section ref={ctaRef} {...fade(1)} className="mt-4 grid grid-cols-2 gap-3" data-testid="cta-bar">
          <button
            onClick={openExchange}
            data-testid="cta-exchange-button"
            className="flex items-center justify-center gap-2 rounded-2xl px-3 py-4 text-center text-[11px] font-semibold uppercase leading-tight tracking-wide text-black transition-transform duration-300 hover:scale-[1.02] active:scale-[0.98]"
            style={{ background: `linear-gradient(90deg,${g1},${g2},${g3})` }}
          >
            <UserPlus className="h-4 w-4 shrink-0" /> Exchange Contact
          </button>
          {(b.nativeEnabled || b.bookingUrl) ? (
            b.nativeEnabled ? (
              <button
                onClick={openBook}
                data-testid="cta-book-button"
                className="flex items-center justify-center gap-2 rounded-2xl border px-3 py-4 text-center text-[11px] font-semibold uppercase leading-tight tracking-wide transition-transform duration-300 hover:scale-[1.02] active:scale-[0.98]"
                style={{ borderColor: gBorder, color: GOLD, background: panelTint }}
              >
                <CalendarClock className="h-4 w-4 shrink-0" /> Book a Meeting
              </button>
            ) : (
              <a
                href={b.bookingUrl}
                target="_blank"
                rel="noreferrer"
                onClick={() => track?.("tap", "cta_book")}
                data-testid="cta-book-button"
                className="flex items-center justify-center gap-2 rounded-2xl border px-3 py-4 text-center text-[11px] font-semibold uppercase leading-tight tracking-wide transition-transform duration-300 hover:scale-[1.02] active:scale-[0.98]"
                style={{ borderColor: gBorder, color: GOLD, background: panelTint }}
              >
                <CalendarClock className="h-4 w-4 shrink-0" /> Book a Meeting
              </a>
            )
          ) : (
            <button
              onClick={() => openMsg("cta_book")}
              data-testid="cta-book-button"
              className="flex items-center justify-center gap-2 rounded-2xl border px-3 py-4 text-center text-[11px] font-semibold uppercase leading-tight tracking-wide transition-transform duration-300 hover:scale-[1.02] active:scale-[0.98]"
              style={{ borderColor: gBorder, color: GOLD, background: panelTint }}
            >
              <MessageCircle className="h-4 w-4 shrink-0" /> Send a Message
            </button>
          )}
        </motion.section>

        {/* CAPABILITIES — compact */}
        {services.length > 0 && (
          <section className="mt-12" data-testid="services-section">
            <motion.div {...fade(0)}>
              <Overline>Capabilities</Overline>
              <h2 className="tp-balance mb-5 font-serif tracking-tight text-neutral-100" style={{ fontSize: "clamp(1.4rem, 5.5vw, 1.6rem)", lineHeight: 1.2 }}>What I offer</h2>
            </motion.div>
            <div className="grid grid-cols-2 gap-3">
              {services.map((s, i) => {
                const Icon = getIcon(s.icon);
                return (
                  <motion.div
                    key={i}
                    {...fade(i)}
                    data-testid={`service-card-${i}`}
                    className="group rounded-xl border p-4 transition-all duration-300 hover:-translate-y-0.5"
                    style={{ borderColor: gBorder, backgroundColor: panelTint }}
                  >
                    <Icon className="mb-2 h-[18px] w-[18px]" strokeWidth={1.5} style={{ color: GOLD }} />
                    <h3 className="tp-balance mb-1 font-serif text-base leading-snug tracking-tight text-neutral-100">{s.title}</h3>
                    <p className="line-clamp-2 text-[13px] leading-[1.55] text-neutral-400">{s.description}</p>
                  </motion.div>
                );
              })}
            </div>
          </section>
        )}

        {/* PROJECTS — horizontal swipe carousel on mobile */}
        {projects.length > 0 && (
          <section className="mt-12" data-testid="projects-section">
            <motion.div {...fade(0)}>
              <Overline>Portfolio</Overline>
              <h2 className="tp-balance mb-5 font-serif tracking-tight text-neutral-100" style={{ fontSize: "clamp(1.4rem, 5.5vw, 1.6rem)", lineHeight: 1.2 }}>Featured work</h2>
            </motion.div>
            <div className="proj-scroll -mx-6 flex snap-x snap-mandatory gap-4 overflow-x-auto px-6 pb-2 sm:mx-0 sm:grid sm:grid-cols-2 sm:overflow-visible sm:px-0">
              {projects.map((p, i) => {
                const Card = (
                  <>
                    <img src={resolveImg(p.coverImage)} alt={p.name} className="h-40 w-full object-cover" />
                    <div className="flex items-center justify-between gap-3 p-4">
                      <div className="min-w-0">
                        <p className="mb-1 truncate text-[10px] uppercase tracking-[0.2em]" style={{ color: GOLD }}>{p.category}</p>
                        <h3 className="truncate font-serif text-lg tracking-tight text-neutral-100">{p.name}</h3>
                        {p.description ? <p className="truncate text-xs text-neutral-500">{p.description}</p> : null}
                      </div>
                      <ArrowRight className="h-5 w-5 transition-transform duration-300 group-hover:translate-x-1" style={{ color: GOLD }} strokeWidth={1.5} />
                    </div>
                  </>
                );
                const cls = "group block overflow-hidden rounded-xl border transition-colors duration-300";
                const st = { borderColor: gBorder30, backgroundColor: panelTint };
                return (
                  <motion.div key={i} {...fade(i)} data-testid={`project-card-${i}`} className="w-[80%] shrink-0 snap-start sm:w-auto">
                    {p.url ? (
                      <a href={p.url} target="_blank" rel="noopener noreferrer" className={cls} style={st}>{Card}</a>
                    ) : (
                      <div className={cls} style={st}>{Card}</div>
                    )}
                  </motion.div>
                );
              })}
            </div>
          </section>
        )}

        {/* MESSAGE — compact CTA that opens the form in a modal */}
        <motion.section {...fade(0)} className="mt-12" data-testid="message-section">
          <button
            onClick={() => openMsg("cta_message")}
            data-testid="cta-message-button"
            className="flex w-full items-center justify-center gap-2 rounded-2xl border px-6 py-4 text-xs font-medium uppercase tracking-widest transition-transform duration-300 hover:scale-[1.01]"
            style={{ borderColor: gBorder, color: GOLD, background: panelTint }}
          >
            <MessageCircle className="h-4 w-4" /> Send a Message
          </button>
        </motion.section>

        {/* UTILITIES — compact */}
        <motion.section {...fade(0)} className="mt-6" data-testid="utilities-section">
          <div className="grid grid-cols-3 gap-3">
            <SaveContactButton
              slug={slug}
              className={utilBtn}
              iconClassName="w-[18px] h-[18px]"
              label="Save"
            />
            <button onClick={doShare} data-testid="share-button" className={utilBtn} style={utilStyle}>
              <Share2 className="h-[18px] w-[18px]" style={{ color: GOLD }} strokeWidth={1.75} /> Share
            </button>
            <button onClick={() => setQrOpen((v) => !v)} data-testid="qr-toggle" className={utilBtn} style={utilStyle}>
              <QrCode className="h-[18px] w-[18px]" style={{ color: GOLD }} strokeWidth={1.75} /> QR
            </button>
          </div>

          {qrOpen && (
            <div className="mt-3 flex flex-col items-center rounded-xl border p-4" style={{ borderColor: gBorder, background: panelTint }}>
              <QRBlock slug={slug} className="flex flex-col items-center gap-2" imgClassName="w-32 h-32 rounded" label="Scan to open" />
            </div>
          )}

          <div className="mt-3">
            <button onClick={() => setMoreOpen((v) => !v)} data-testid="more-toggle" className="flex w-full items-center justify-center gap-1.5 rounded-xl py-2.5 text-[10px] uppercase tracking-[0.2em] text-neutral-500 transition-colors hover:text-neutral-300">
              More <ChevronDown className={`h-3.5 w-3.5 transition-transform ${moreOpen ? "rotate-180" : ""}`} />
            </button>
            {moreOpen && (
              <a href={posterUrl(slug)} download data-testid="download-poster" className="mt-2 flex w-full items-center justify-center gap-2 rounded-xl border px-4 py-3 text-xs tracking-wide text-neutral-200" style={utilStyle}>
                <Printer className="h-4 w-4" style={{ color: GOLD }} strokeWidth={1.75} /> Download QR Poster
              </a>
            )}
          </div>
        </motion.section>

        {/* FOOTER */}
        <footer className="mt-14 border-t pt-8 text-center" style={{ borderColor: "rgba(255,255,255,0.08)" }}>
          <SocialIcons
            social={social}
            className="flex items-center justify-center gap-3"
            itemClassName="flex items-center justify-center w-10 h-10 rounded-full border text-neutral-400 transition-colors duration-300"
          />
          <p className="mt-6 text-[11px] tracking-[0.2em] uppercase text-neutral-600">
            © {new Date().getFullYear()} {id.fullName} · TapPresence
          </p>
        </footer>
      </div>

      {/* STICKY MOBILE CONVERSION BAR — appears after the primary CTAs scroll away */}
      {publicView && (
      <div
        data-testid="sticky-cta-bar"
        className={`tp-sticky fixed inset-x-0 bottom-0 z-40 sm:hidden ${showSticky ? "translate-y-0 opacity-100" : "pointer-events-none translate-y-full opacity-0"}`}
        style={{ paddingBottom: "max(0.75rem, env(safe-area-inset-bottom))" }}
      >
        <div
          className="mx-auto grid max-w-lg grid-cols-2 gap-2.5 px-4 pt-3"
          style={{ background: `linear-gradient(180deg, transparent, rgb(${scrimBase}) 42%)` }}
        >
          <button
            onClick={openExchange}
            data-testid="sticky-exchange-button"
            className="flex items-center justify-center gap-2 rounded-2xl px-3 py-3.5 text-[11px] font-semibold uppercase tracking-wide text-black shadow-lg transition-transform duration-200 active:scale-[0.97]"
            style={{ background: `linear-gradient(90deg,${g1},${g2},${g3})`, boxShadow: `0 8px 30px ${hexToRgba(GOLD, 0.35)}` }}
          >
            <UserPlus className="h-4 w-4 shrink-0" /> Exchange
          </button>
          <button
            onClick={bookingActive ? (b.nativeEnabled ? openBook : () => { track?.("tap", "cta_book"); window.open(b.bookingUrl, "_blank"); }) : () => openMsg("cta_book")}
            data-testid="sticky-book-button"
            className="flex items-center justify-center gap-2 rounded-2xl border px-3 py-3.5 text-[11px] font-semibold uppercase tracking-wide backdrop-blur-md transition-transform duration-200 active:scale-[0.97]"
            style={{ borderColor: gBorder, color: GOLD, background: hexToRgba(GOLD, 0.12) }}
          >
            {bookingActive ? <CalendarClock className="h-4 w-4 shrink-0" /> : <MessageCircle className="h-4 w-4 shrink-0" />}
            {bookingActive ? "Book" : "Message"}
          </button>
        </div>
      </div>
      )}

      <style>{`
        .proj-scroll::-webkit-scrollbar{ display:none; }
        .proj-scroll{ scrollbar-width:none; }
        .tp-sticky{ transition: transform .35s cubic-bezier(.22,1,.36,1), opacity .35s ease; }
        .tp-name{ overflow-wrap:anywhere; word-break:break-word; text-wrap:balance; }
        .tp-balance{ text-wrap:balance; overflow-wrap:anywhere; }
        .tp-pretty{ text-wrap:pretty; overflow-wrap:anywhere; }
        [dir="rtl"] .tp-name,[dir="rtl"] .tp-balance,[dir="rtl"] .tp-pretty{ letter-spacing:0 !important; }
        [data-testid="availability-badge"]{ color:${GOLD}; border:1px solid ${gGlow}; background:${panelTint}; }
        [data-testid="availability-badge"] span{ background:${GOLD}; }
        [data-testid="hero-action-call"],[data-testid="hero-action-whatsapp"],[data-testid="hero-action-email"],[data-testid="hero-action-message"]{ border-color:${gBorder}!important; background:${panelTint}!important; }
        [data-testid="hero-action-call"]:hover,[data-testid="hero-action-whatsapp"]:hover,[data-testid="hero-action-email"]:hover,[data-testid="hero-action-message"]:hover{ border-color:${GOLD}!important; box-shadow:0 0 20px ${panelHoverGlow}; }
        [data-testid="hero-action-call"] svg,[data-testid="hero-action-whatsapp"] svg,[data-testid="hero-action-email"] svg,[data-testid="hero-action-message"] svg{ color:${GOLD}; }
        [data-testid="inquiry-form"] input:focus,[data-testid="inquiry-form"] textarea:focus{ border-color:${GOLD}!important; box-shadow:0 0 0 1px ${gGlow}; }
        [data-testid="save-contact-button"],[data-testid="wallet-apple"],[data-testid="wallet-google"]{ border-color:${gBorder}!important; background:${panelTint}!important; color:#ececec!important; }
        [data-testid="save-contact-button"] svg,[data-testid="wallet-apple"] svg,[data-testid="wallet-google"] svg{ color:${GOLD}; }
        [data-testid="save-contact-button"]:hover,[data-testid="share-button"]:hover,[data-testid="qr-toggle"]:hover,[data-testid="wallet-apple"]:hover,[data-testid="wallet-google"]:hover,[data-testid="download-poster"]:hover{ border-color:${GOLD}!important; box-shadow:0 0 20px ${panelHoverGlow}; }
        [data-testid="social-icons"] a{ border-color:rgba(255,255,255,0.12); }
        [data-testid="social-icons"] a:hover{ color:${GOLD}; border-color:${GOLD}; }
      `}</style>

      <ExchangeContactDialog open={exchangeOpen} onOpenChange={setExchangeOpen} slug={slug} accent={GOLD} ownerName={id.fullName} />      <BookMeetingDialog open={bookOpen} onOpenChange={setBookOpen} slug={slug} accent={GOLD} ownerName={id.fullName} />

      {/* MESSAGE modal */}
      <Dialog open={msgOpen} onOpenChange={setMsgOpen}>
        <DialogContent className="max-w-md border text-white" style={{ background: "#0B0B0D", borderColor: hexToRgba(GOLD, 0.35) }} data-testid="message-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-white"><MessageCircle className="h-5 w-5" style={{ color: GOLD }} /> Send a Message</DialogTitle>
          </DialogHeader>
          <InquiryForm slug={slug} variant="black" accentColor={GOLD} embedded />
        </DialogContent>
      </Dialog>
    </div>
  );
};
