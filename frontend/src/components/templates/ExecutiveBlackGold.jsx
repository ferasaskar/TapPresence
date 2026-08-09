import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { resolveImg } from "@/lib/api";
import { buildActions, getIcon, orderedServices, orderedProjects } from "@/lib/cardHelpers";
import { AvailabilityBadge } from "@/components/profile/AvailabilityBadge";
import { SocialIcons } from "@/components/profile/SocialIcons";
import { SaveContactButton } from "@/components/profile/SaveContactButton";
import { QRBlock } from "@/components/profile/QRBlock";
import { ActionButton } from "@/components/profile/ActionButton";
import { InquiryForm } from "@/components/profile/InquiryForm";
import { ShareBar } from "@/components/profile/ShareBar";
import { WalletButtons } from "@/components/profile/WalletButtons";
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
  <p className="text-[11px] uppercase tracking-[0.35em] mb-4" style={{ color: "var(--ac)" }}>{children}</p>
);

export const ExecutiveBlackGold = ({ data }) => {
  const { identity: id = {}, contact: c = {}, booking: b = {}, social = {}, slug } = data;
  const actions = buildActions(data);
  const services = orderedServices(data.services);
  const projects = orderedProjects(data.projects);
  const location = [id.city, id.country].filter(Boolean).join(", ");

  const iconRow = [actions.call, actions.whatsapp, actions.email, actions.message].filter(Boolean);

  const GOLD = accentHex("executive-black-gold", data.accent, data.custom_accent_color);
  const [g1, g2, g3] = accentGrad("executive-black-gold", data.accent, data.custom_accent_color);
  const gBorder = hexToRgba(GOLD, 0.4);
  const gBorder30 = hexToRgba(GOLD, 0.3);
  const gGlow = hexToRgba(GOLD, 0.5);
  const panelTint = hexToRgba(GOLD, 0.07);
  const panelHoverGlow = hexToRgba(GOLD, 0.2);

  // Match the showcase atmosphere: tint the background scrim with the chosen
  // industry's base tone (e.g. purple for Sales) instead of a neutral black.
  const indBase = INDUSTRY_CARDS.find((cc) => cc.id === data.industry)?.base;
  const scrimBase = data.industry && indBase ? indBase : BASE_RGB["executive-black-gold"];

  // Saved portrait framing (zoom / pan) applied identically in preview & public.
  const portraitTransform = `translate(${id.imageOffsetX || 0}%, ${id.imageOffsetY || 0}%) scale(${id.imageScale || 1})`;

  return (
    <div className="relative min-h-screen font-sans text-neutral-200 overflow-hidden" style={{ backgroundColor: `rgb(${scrimBase})`, "--ac": GOLD, ...industryRootStyle(data, scrimBase, GOLD) }}>
      <div className="grain-overlay" style={{ opacity: 0.06 }} />
      {/* soft gold radial glow behind hero */}
      <div className="pointer-events-none absolute left-1/2 top-0 h-[420px] w-[420px] -translate-x-1/2 rounded-full opacity-20 blur-3xl" style={{ background: GOLD }} />

      <div className="relative mx-auto w-full max-w-lg px-6 pb-16 pt-14 sm:px-8">

        {/* HERO */}
        <motion.header {...fade(0)} className="flex flex-col items-center text-center">
          <div className="relative mb-8">
            <div className="absolute -inset-2 rounded-full" style={{ background: `conic-gradient(from 180deg, ${GOLD}, ${hexToRgba(GOLD, 0.25)}, ${GOLD})` }} />
            <div className="absolute -inset-2 rounded-full blur-md opacity-50" style={{ background: GOLD }} />
            <div className="relative w-40 h-40 rounded-full overflow-hidden" style={{ border: "3px solid rgb(" + scrimBase + ")" }}>
              {id.profilePhoto ? (
                <img
                  src={resolveImg(id.profilePhoto)}
                  alt={id.fullName}
                  data-testid="hero-portrait"
                  className="w-full h-full object-cover"
                  style={{ transform: portraitTransform, transformOrigin: "center" }}
                />
              ) : (
                <div data-testid="hero-portrait" className="w-full h-full bg-neutral-800" />
              )}
            </div>
          </div>
          <AvailabilityBadge
            label={id.availabilityBadge}
            className="mb-5 inline-flex items-center gap-2 rounded-full px-4 py-1 text-xs tracking-widest uppercase"
            dotClassName="w-1.5 h-1.5 rounded-full"
          />
          <h1 data-testid="hero-name" className="font-serif text-5xl sm:text-6xl leading-none tracking-tight" style={{ color: GOLD }}>
            {id.fullName}
          </h1>
          <p className="mt-4 text-base tracking-wide text-neutral-300">{id.jobTitle}</p>
          {id.company ? <p className="mt-1 text-sm tracking-[0.2em] uppercase text-neutral-500">{id.company}</p> : null}
          {location ? <p className="mt-3 text-xs tracking-widest uppercase text-neutral-600">{location}</p> : null}
          {id.bio ? <p className="mt-6 max-w-sm text-[15px] leading-relaxed text-neutral-400">{id.bio}</p> : null}
        </motion.header>

        {/* ACTION BUTTON ROW — Call · WhatsApp · Email · Message */}
        <motion.div {...fade(1)} className="mt-10 grid grid-cols-4 gap-3" data-testid="hero-actions">
          {iconRow.map((a) => (
            <ActionButton
              key={a.key}
              action={a}
              testId={`hero-action-${a.key}`}
              className="flex h-[70px] w-full flex-col items-center justify-center gap-1.5 rounded-xl border text-[10px] uppercase tracking-[0.14em] text-neutral-300 transition-all duration-300 hover:-translate-y-1"
              iconClassName="w-5 h-5"
            />
          ))}
        </motion.div>

        {/* SERVICES */}
        {services.length > 0 && (
          <section className="mt-16" data-testid="services-section">
            <motion.div {...fade(0)}>
              <Overline>Services</Overline>
              <h2 className="font-serif text-3xl tracking-tight mb-8 text-neutral-100">What I offer</h2>
            </motion.div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {services.map((s, i) => {
                const Icon = getIcon(s.icon);
                return (
                  <motion.div
                    key={i}
                    {...fade(i)}
                    data-testid={`service-card-${i}`}
                    className="group rounded-xl border p-7 transition-all duration-300 hover:-translate-y-1"
                    style={{ borderColor: gBorder, backgroundColor: panelTint }}
                  >
                    <Icon className="w-6 h-6 mb-5" strokeWidth={1.5} style={{ color: GOLD }} />
                    <h3 className="font-serif text-xl tracking-tight mb-2 text-neutral-100">{s.title}</h3>
                    <p className="text-sm leading-relaxed text-neutral-400">{s.description}</p>
                  </motion.div>
                );
              })}
            </div>
          </section>
        )}

        {/* PROJECTS — image cards */}
        {projects.length > 0 && (
          <section className="mt-16" data-testid="projects-section">
            <motion.div {...fade(0)}>
              <Overline>Portfolio</Overline>
              <h2 className="font-serif text-3xl tracking-tight mb-6 text-neutral-100">Featured work</h2>
            </motion.div>
            <div className="space-y-4">
              {projects.map((p, i) => {
                const Card = (
                  <>
                    <img src={resolveImg(p.coverImage)} alt={p.name} className="h-44 w-full object-cover" />
                    <div className="flex items-center justify-between gap-3 p-5">
                      <div className="min-w-0">
                        <p className="text-[10px] uppercase tracking-[0.2em] mb-1 truncate" style={{ color: GOLD }}>{p.category}</p>
                        <h3 className="font-serif text-xl tracking-tight text-neutral-100 truncate">{p.name}</h3>
                        {p.description ? <p className="text-sm text-neutral-500 truncate">{p.description}</p> : null}
                      </div>
                      <ArrowRight className="w-5 h-5 transition-transform duration-300 group-hover:translate-x-1" style={{ color: GOLD }} strokeWidth={1.5} />
                    </div>
                  </>
                );
                const cls = "group block overflow-hidden rounded-xl border transition-colors duration-300";
                const st = { borderColor: gBorder30, backgroundColor: panelTint };
                return (
                  <motion.div key={i} {...fade(i)} data-testid={`project-card-${i}`}>
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

        {/* MAIN CTA — gold gradient bar */}
        {(b.bookingUrl || c.phone) && (
          <motion.section {...fade(0)} className="mt-16" data-testid="cta-bar">
            <ActionButton
              action={actions.book || actions.call}
              testId="cta-book-button"
              className="flex w-full items-center justify-center gap-3 rounded-full px-8 py-5 text-sm font-medium uppercase tracking-widest text-black transition-transform duration-300 hover:scale-[1.02]"
              iconClassName="w-5 h-5"
            />
          </motion.section>
        )}
        <style>{`[data-testid="cta-book-button"]{background:linear-gradient(90deg,${g1},${g2},${g3});}`}</style>

        {/* LEAD CAPTURE */}
        <InquiryForm slug={slug} variant="black" accentColor={GOLD} />

        {/* SAVE CONTACT + QR */}
        <motion.section {...fade(0)} className="mt-6 grid grid-cols-2 gap-4">
          <SaveContactButton
            slug={slug}
            className="flex flex-col items-start justify-between gap-6 rounded-xl border p-6 transition-colors duration-300"
            iconClassName="w-6 h-6"
            label="Save Contact"
            subLabel="Add to phone (.vcf)"
          />
          <QRBlock
            slug={slug}
            className="flex flex-col items-center justify-center gap-2 rounded-xl border p-4"
            imgClassName="w-24 h-24 rounded"
            label="Scan to open"
          />
        </motion.section>

        {/* SHARE */}
        <ShareBar slug={slug} name={id.fullName} variant="black" iconColor={GOLD} />
        <WalletButtons slug={slug} variant="black" iconColor={GOLD} />

        {/* FOOTER */}
        <footer className="mt-16 border-t pt-8 text-center" style={{ borderColor: "rgba(255,255,255,0.08)" }}>
          <SocialIcons
            social={social}
            className="flex items-center justify-center gap-3"
            itemClassName="flex items-center justify-center w-10 h-10 rounded-full border text-neutral-400 transition-colors duration-300"
          />
          <p className="mt-6 text-[11px] tracking-[0.2em] uppercase text-neutral-600">
            © {new Date().getFullYear()} {id.fullName} · ARIADNI ID
          </p>
        </footer>
      </div>

      <style>{`
        [data-testid="availability-badge"]{ color:${GOLD}; border:1px solid ${gGlow}; background:${panelTint}; }
        [data-testid="availability-badge"] span{ background:${GOLD}; }
        [data-testid="hero-action-call"],[data-testid="hero-action-whatsapp"],[data-testid="hero-action-email"],[data-testid="hero-action-message"]{ border-color:${gBorder}!important; background:${panelTint}!important; }
        [data-testid="hero-action-call"]:hover,[data-testid="hero-action-whatsapp"]:hover,[data-testid="hero-action-email"]:hover,[data-testid="hero-action-message"]:hover{ border-color:${GOLD}!important; box-shadow:0 0 20px ${panelHoverGlow}; }
        [data-testid="hero-action-call"] svg,[data-testid="hero-action-whatsapp"] svg,[data-testid="hero-action-email"] svg,[data-testid="hero-action-message"] svg{ color:${GOLD}; }
        [data-testid="inquiry-form"],[data-testid="inquiry-success"]{ border-color:${gBorder}!important; background:${panelTint}!important; backdrop-filter:blur(6px); }
        [data-testid="save-contact-button"],[data-testid="qr-block"],[data-testid="share-button"],[data-testid="download-poster"],[data-testid="wallet-apple"],[data-testid="wallet-google"]{ border-color:${gBorder}!important; background:${panelTint}!important; color:#ececec!important; backdrop-filter:blur(6px); }
        [data-testid="save-contact-button"] svg,[data-testid="qr-block"] svg,[data-testid="share-button"] svg,[data-testid="download-poster"] svg,[data-testid="wallet-apple"] svg,[data-testid="wallet-google"] svg{ color:${GOLD}; }
        [data-testid="share-button"]:hover,[data-testid="download-poster"]:hover,[data-testid="wallet-apple"]:hover,[data-testid="wallet-google"]:hover,[data-testid="save-contact-button"]:hover{ border-color:${GOLD}!important; box-shadow:0 0 20px ${panelHoverGlow}; }
        [data-testid="inquiry-form"] input:focus,[data-testid="inquiry-form"] textarea:focus{ border-color:${GOLD}!important; box-shadow:0 0 0 1px ${gGlow}; }
        [data-testid="social-icons"] a{ border-color:rgba(255,255,255,0.12); }
        [data-testid="social-icons"] a:hover{ color:${GOLD}; border-color:${GOLD}; }
      `}</style>
    </div>
  );
};
