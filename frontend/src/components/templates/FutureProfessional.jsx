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
import { accentValue, hexToRgba } from "@/lib/accents";
import { industryRootStyle, BASE_RGB } from "@/lib/industries";

const fade = (i = 0) => ({
  initial: { opacity: 0, y: 24 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: "-40px" },
  transition: { duration: 0.7, delay: i * 0.08, ease: [0.22, 1, 0.36, 1] },
});

const glass = "border border-white/10 bg-white/[0.04] backdrop-blur-xl";

const Overline = ({ children }) => (
  <p className="text-[11px] uppercase tracking-[0.35em] mb-4 text-[color:var(--ac)]">{children}</p>
);

export const FutureProfessional = ({ data }) => {
  const { identity: id = {}, contact: c = {}, booking: b = {}, social = {}, slug } = data;
  const actions = buildActions(data);
  const services = orderedServices(data.services);
  const projects = orderedProjects(data.projects);
  const location = [id.city, id.country].filter(Boolean).join(", ");

  const panel = [actions.message || actions.whatsapp, actions.email, actions.call, actions.meet].filter(Boolean);

  const { p, s } = accentValue("future-professional", data.accent, data.custom_accent_color);

  return (
    <div className="relative min-h-screen font-sans text-slate-200 overflow-hidden" style={{ backgroundColor: "#070A16", "--ac": p, ...industryRootStyle(data, BASE_RGB["future-professional"], p) }}>
      <div className="grain-overlay" style={{ opacity: 0.05 }} />
      <div className="pointer-events-none absolute left-1/2 top-[-60px] h-[420px] w-[420px] -translate-x-1/2 rounded-full opacity-30 blur-3xl" style={{ background: `radial-gradient(circle, ${s} 0%, ${p} 55%, transparent 75%)` }} />

      <div className="relative mx-auto w-full max-w-lg px-6 pb-16 pt-14 sm:px-8">

        {/* HERO */}
        <motion.header {...fade(0)} className="flex flex-col items-center text-center">
          <div className="relative mb-8">
            <div className="absolute -inset-[6px] rounded-full opacity-80 blur-[6px]" style={{ background: `conic-gradient(from 90deg, ${p}, ${s}, ${p})` }} />
            <div className="absolute -inset-[6px] rounded-full" style={{ background: `conic-gradient(from 90deg, ${p}, ${s}, ${p})` }} />
            {id.profilePhoto ? (
              <img
                src={resolveImg(id.profilePhoto)}
                alt={id.fullName}
                data-testid="hero-portrait"
                className="relative w-40 h-40 rounded-full object-cover"
                style={{ border: "3px solid #070A16" }}
              />
            ) : (
              <div data-testid="hero-portrait" className="relative w-40 h-40 rounded-full bg-slate-800" style={{ border: "3px solid #070A16" }} />
            )}
          </div>
          <div className={`mb-5 rounded-full px-5 py-2 ${glass}`}>
            <AvailabilityBadge
              label={id.availabilityBadge}
              className="inline-flex items-center gap-2 text-xs tracking-widest uppercase text-[color:var(--ac)]"
              dotClassName="w-1.5 h-1.5 rounded-full bg-[color:var(--ac)] animate-pulse"
            />
          </div>
          <h1 data-testid="hero-name" className="text-4xl sm:text-5xl font-semibold leading-none tracking-tight text-white">
            {id.fullName}
          </h1>
          <p className="mt-4 text-base tracking-wide text-slate-300">{id.jobTitle}</p>
          {id.company ? <p className="mt-1 text-sm tracking-[0.2em] uppercase text-slate-500">{id.company}</p> : null}
          {location ? <p className="mt-3 text-xs tracking-widest uppercase text-slate-600">{location}</p> : null}
          {id.bio ? (
            <div className={`mt-6 max-w-sm rounded-2xl px-6 py-4 ${glass}`}>
              <p className="text-[15px] leading-relaxed text-slate-300">{id.bio}</p>
            </div>
          ) : null}
        </motion.header>

        {/* ACTIONS — glass panel with subtitles */}
        <motion.div {...fade(1)} className={`mt-10 grid grid-cols-2 gap-2 rounded-2xl p-2 ${glass}`}>
          {panel.map((a) => (
            <ActionButton
              key={a.key}
              action={a}
              showSub
              testId={`hero-action-${a.key}`}
              className="flex items-center gap-3 rounded-xl px-4 py-3.5 text-sm text-slate-200 transition-colors duration-300 hover:bg-white/[0.06]"
              iconClassName="w-5 h-5 text-[color:var(--ac)]"
            />
          ))}
        </motion.div>

        {/* SERVICES — neon underglow */}
        {services.length > 0 && (
          <section className="mt-16" data-testid="services-section">
            <motion.div {...fade(0)}>
              <Overline>Capabilities</Overline>
              <h2 className="text-3xl font-semibold tracking-tight mb-8 text-white">What I deliver</h2>
            </motion.div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {services.map((s, i) => {
                const Icon = getIcon(s.icon);
                return (
                  <motion.div
                    key={i}
                    {...fade(i)}
                    data-testid={`service-card-${i}`}
                    className={`group relative rounded-2xl p-7 transition-all duration-300 hover:-translate-y-1 ${glass}`}
                  >
                    <div className="absolute inset-x-6 -bottom-px h-px opacity-0 transition-opacity duration-300 group-hover:opacity-100" style={{ background: `linear-gradient(90deg,transparent,${p},transparent)` }} />
                    <span className="mb-5 inline-flex h-11 w-11 items-center justify-center rounded-xl" style={{ background: hexToRgba(p, 0.12) }}>
                      <Icon className="w-5 h-5 text-[color:var(--ac)]" strokeWidth={1.5} />
                    </span>
                    <h3 className="text-lg font-semibold tracking-tight mb-2 text-white">{s.title}</h3>
                    <p className="text-sm leading-relaxed text-slate-400">{s.description}</p>
                  </motion.div>
                );
              })}
            </div>
          </section>
        )}

        {/* PROJECTS — glowing cards */}
        {projects.length > 0 && (
          <section className="mt-16" data-testid="projects-section">
            <motion.div {...fade(0)}>
              <Overline>Case Studies</Overline>
              <h2 className="text-3xl font-semibold tracking-tight mb-6 text-white">Selected projects</h2>
            </motion.div>
            <div className="space-y-4">
              {projects.map((p, i) => {
                const Card = (
                  <>
                    <img src={resolveImg(p.coverImage)} alt={p.name} className="h-44 w-full object-cover" />
                    <div className="flex items-center justify-between gap-3 p-5">
                      <div className="min-w-0">
                        <p className="text-[10px] uppercase tracking-[0.2em] mb-1 text-[color:var(--ac)] truncate">{p.category}</p>
                        <h3 className="text-lg font-semibold tracking-tight text-white truncate">{p.name}</h3>
                        {p.description ? <p className="text-sm text-slate-500 truncate">{p.description}</p> : null}
                      </div>
                      <ArrowRight className="w-5 h-5 text-[color:var(--ac)] transition-transform duration-300 group-hover:translate-x-1" strokeWidth={1.5} />
                    </div>
                  </>
                );
                const cls = `group block overflow-hidden rounded-2xl ${glass}`;
                return (
                  <motion.div key={i} {...fade(i)} data-testid={`project-card-${i}`}>
                    {p.url ? (
                      <a href={p.url} target="_blank" rel="noopener noreferrer" className={cls}>{Card}</a>
                    ) : (
                      <div className={cls}>{Card}</div>
                    )}
                  </motion.div>
                );
              })}
            </div>
            <div className="mt-5 flex items-center justify-center gap-2" data-testid="slider-dots">
              {projects.map((_, i) => (
                <span key={i} className={`h-1.5 rounded-full transition-all ${i === 0 ? "w-6 bg-[color:var(--ac)]" : "w-1.5 bg-white/20"}`} />
              ))}
            </div>
          </section>
        )}

        {/* MAIN CTA — purple glow bar */}
        {(b.bookingUrl || c.phone) && (
          <motion.section {...fade(0)} className="mt-16 relative" data-testid="cta-bar">
            <div className="absolute inset-0 rounded-full blur-2xl opacity-50" style={{ background: `linear-gradient(90deg,${s},${p})` }} />
            <ActionButton
              action={actions.book || actions.call}
              testId="cta-book-button"
              className="relative flex w-full items-center justify-center gap-3 rounded-full px-8 py-5 text-sm font-semibold uppercase tracking-widest text-white transition-transform duration-300 hover:scale-[1.02]"
              iconClassName="w-5 h-5"
            />
          </motion.section>
        )}
        <style>{`[data-testid="cta-book-button"]{background:linear-gradient(90deg,${s},${p});box-shadow:0 8px 40px ${hexToRgba(s, 0.45)};}`}</style>

        {/* LEAD CAPTURE */}
        <InquiryForm slug={slug} variant="future" accentColor={p} />

        {/* SAVE CONTACT + QR */}
        <motion.section {...fade(0)} className="mt-6 grid grid-cols-2 gap-4">
          <SaveContactButton
            slug={slug}
            className={`flex flex-col items-start justify-between gap-6 rounded-2xl p-6 text-slate-200 ${glass}`}
            iconClassName="w-6 h-6 text-[color:var(--ac)]"
            label="Save Contact"
            subLabel="Add to phone (.vcf)"
          />
          <QRBlock
            slug={slug}
            className={`flex flex-col items-center justify-center gap-2 rounded-2xl p-4 text-slate-300 ${glass}`}
            imgClassName="w-24 h-24 rounded bg-white p-1"
            label="Scan to open"
          />
        </motion.section>

        {/* SHARE */}
        <ShareBar slug={slug} name={id.fullName} variant="future" iconColor={p} />

        {/* FOOTER */}
        <footer className="mt-16 border-t border-white/10 pt-8 text-center">
          <p className="text-lg font-semibold tracking-tight text-white">{id.company || id.fullName}</p>
          <SocialIcons
            social={social}
            className="mt-5 flex items-center justify-center gap-3"
            itemClassName="flex items-center justify-center w-10 h-10 rounded-full border border-white/10 bg-white/[0.03] text-slate-400 transition-colors duration-300 hover:text-[color:var(--ac)] hover:border-[color:var(--ac)]"
          />
          <p className="mt-6 text-[11px] tracking-[0.2em] uppercase text-slate-600">
            © {new Date().getFullYear()} {id.fullName} · TapPresence
          </p>
        </footer>
      </div>
    </div>
  );
};
