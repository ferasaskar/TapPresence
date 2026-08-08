import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { resolveImg } from "@/lib/api";
import { buildActions, getIcon, orderedServices, orderedProjects } from "@/lib/cardHelpers";
import { AvailabilityBadge } from "@/components/profile/AvailabilityBadge";
import { SocialIcons } from "@/components/profile/SocialIcons";
import { SaveContactButton } from "@/components/profile/SaveContactButton";
import { QRBlock } from "@/components/profile/QRBlock";
import { ActionButton } from "@/components/profile/ActionButton";

const GOLD = "#C9A24B";

const fade = (i = 0) => ({
  initial: { opacity: 0, y: 24 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: "-40px" },
  transition: { duration: 0.7, delay: i * 0.08, ease: [0.22, 1, 0.36, 1] },
});

const Overline = ({ children }) => (
  <p className="text-[11px] uppercase tracking-[0.35em] mb-4" style={{ color: GOLD }}>{children}</p>
);

export const ExecutiveBlackGold = ({ data }) => {
  const { identity: id = {}, contact: c = {}, booking: b = {}, social = {}, slug } = data;
  const actions = buildActions(data);
  const services = orderedServices(data.services);
  const projects = orderedProjects(data.projects);
  const location = [id.city, id.country].filter(Boolean).join(", ");

  const iconRow = [actions.call, actions.whatsapp, actions.email, actions.meet, actions.message].filter(Boolean);

  return (
    <div className="relative min-h-screen font-sans text-neutral-200 overflow-hidden" style={{ backgroundColor: "#0B0B0C" }}>
      <div className="grain-overlay" style={{ opacity: 0.06 }} />
      {/* soft gold radial glow behind hero */}
      <div className="pointer-events-none absolute left-1/2 top-0 h-[420px] w-[420px] -translate-x-1/2 rounded-full opacity-20 blur-3xl" style={{ background: GOLD }} />

      <div className="relative mx-auto w-full max-w-lg px-6 pb-16 pt-14 sm:px-8">

        {/* HERO */}
        <motion.header {...fade(0)} className="flex flex-col items-center text-center">
          <div className="relative mb-8">
            <div className="absolute -inset-2 rounded-full" style={{ background: `conic-gradient(from 180deg, ${GOLD}, #6b551f, ${GOLD})` }} />
            <div className="absolute -inset-2 rounded-full blur-md opacity-50" style={{ background: GOLD }} />
            <img
              src={resolveImg(id.profilePhoto)}
              alt={id.fullName}
              data-testid="hero-portrait"
              className="relative w-40 h-40 rounded-full object-cover"
              style={{ border: "3px solid #0B0B0C" }}
            />
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

        {/* ACTION ICON ROW */}
        <motion.div {...fade(1)} className="mt-10 flex items-center justify-center gap-3">
          {iconRow.map((a) => (
            <ActionButton
              key={a.key}
              action={a}
              testId={`hero-action-${a.key}`}
              className="flex h-14 w-14 flex-col items-center justify-center gap-1 rounded-2xl border text-[10px] uppercase tracking-wider text-neutral-300 transition-all duration-300 hover:-translate-y-1"
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
                    style={{ borderColor: "rgba(201,162,75,0.35)", backgroundColor: "#111112" }}
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
                const st = { borderColor: "rgba(201,162,75,0.3)", backgroundColor: "#111112" };
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
        <style>{`[data-testid="cta-book-button"]{background:linear-gradient(90deg,#E7C56B,#C9A24B,#8f7328);}`}</style>

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
        [data-testid="availability-badge"]{ color:${GOLD}; border:1px solid rgba(201,162,75,0.5); }
        [data-testid="availability-badge"] span{ background:${GOLD}; }
        [data-testid="hero-action-call"],[data-testid="hero-action-whatsapp"],[data-testid="hero-action-email"],[data-testid="hero-action-meet"],[data-testid="hero-action-message"]{ border-color:rgba(201,162,75,0.35); background:#111112; }
        [data-testid="save-contact-button"]{ border-color:rgba(201,162,75,0.35); background:#111112; color:#e5e5e5; }
        [data-testid="save-contact-button"] svg{ color:${GOLD}; }
        [data-testid="qr-block"]{ border-color:rgba(201,162,75,0.35); background:#111112; }
        [data-testid="social-icons"] a{ border-color:rgba(255,255,255,0.12); }
        [data-testid="social-icons"] a:hover{ color:${GOLD}; border-color:${GOLD}; }
      `}</style>
    </div>
  );
};
