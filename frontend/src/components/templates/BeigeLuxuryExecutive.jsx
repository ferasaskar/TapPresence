import { motion } from "framer-motion";
import { ArrowUpRight } from "lucide-react";
import { resolveImg } from "@/lib/api";
import { buildActions, getIcon, orderedServices, orderedProjects } from "@/lib/cardHelpers";
import { AvailabilityBadge } from "@/components/profile/AvailabilityBadge";
import { SocialIcons } from "@/components/profile/SocialIcons";
import { SaveContactButton } from "@/components/profile/SaveContactButton";
import { QRBlock } from "@/components/profile/QRBlock";
import { ActionButton } from "@/components/profile/ActionButton";

const fade = (i = 0) => ({
  initial: { opacity: 0, y: 24 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: "-40px" },
  transition: { duration: 0.7, delay: i * 0.08, ease: [0.22, 1, 0.36, 1] },
});

const Overline = ({ children }) => (
  <p className="text-[11px] uppercase tracking-[0.35em] text-gold mb-4">{children}</p>
);

export const BeigeLuxuryExecutive = ({ data }) => {
  const { identity: id = {}, contact: c = {}, booking: b = {}, social = {}, slug } = data;
  const actions = buildActions(data);
  const services = orderedServices(data.services);
  const projects = orderedProjects(data.projects);
  const location = [id.city, id.country].filter(Boolean).join(", ");

  return (
    <div className="relative min-h-screen bg-ivory-bg text-ink font-sans overflow-hidden">
      <div className="grain-overlay" />
      <div className="relative mx-auto w-full max-w-lg px-6 pb-16 pt-14 sm:px-8">

        {/* HERO */}
        <motion.header {...fade(0)} className="flex flex-col items-center text-center">
          <div className="relative mb-8">
            <div className="absolute -inset-3 rounded-t-[1000px] rounded-b-3xl border border-gold/40" />
            <img
              src={resolveImg(id.profilePhoto)}
              alt={id.fullName}
              data-testid="hero-portrait"
              className="relative w-52 h-72 object-cover rounded-t-[1000px] rounded-b-3xl shadow-sm"
            />
          </div>
          <AvailabilityBadge
            label={id.availabilityBadge}
            className="mb-5 inline-flex items-center gap-2 rounded-full border border-gold/60 px-4 py-1 text-xs tracking-widest uppercase text-gold"
            dotClassName="w-1.5 h-1.5 rounded-full bg-gold"
          />
          <h1 data-testid="hero-name" className="font-serif text-5xl sm:text-6xl leading-none tracking-tight text-ink">
            {id.fullName}
          </h1>
          <div className="mx-auto my-5 h-px w-16 bg-gold" />
          <p className="text-base tracking-wide text-ink-soft">{id.jobTitle}</p>
          {id.company ? <p className="mt-1 text-sm tracking-[0.2em] uppercase text-gold">{id.company}</p> : null}
          {location ? <p className="mt-3 text-xs tracking-widest uppercase text-ink-soft/70">{location}</p> : null}
          {id.bio ? <p className="mt-6 max-w-sm text-[15px] leading-relaxed text-ink-soft">{id.bio}</p> : null}
        </motion.header>

        {/* ACTIONS — two large buttons */}
        <motion.div {...fade(1)} className="mt-10 grid grid-cols-2 gap-3">
          <ActionButton
            action={actions.message || actions.whatsapp || actions.email}
            testId="hero-message-button"
            className="flex items-center justify-center gap-2 rounded-md border border-ink/20 bg-transparent px-4 py-4 text-sm tracking-wide text-ink transition-colors duration-300 hover:bg-ivory-hover"
            iconClassName="w-[18px] h-[18px]"
          />
          <ActionButton
            action={actions.book || actions.call}
            testId="hero-book-call-button"
            className="flex items-center justify-center gap-2 rounded-md bg-ink px-4 py-4 text-sm tracking-wide text-ivory-bg transition-colors duration-300 hover:bg-ink-soft"
            iconClassName="w-[18px] h-[18px]"
          />
        </motion.div>

        {/* SERVICES */}
        {services.length > 0 && (
          <section className="mt-16" data-testid="services-section">
            <motion.div {...fade(0)}>
              <Overline>Services</Overline>
              <h2 className="font-serif text-3xl tracking-tight mb-8">How I can help</h2>
            </motion.div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {services.map((s, i) => {
                const Icon = getIcon(s.icon);
                return (
                  <motion.div
                    key={i}
                    {...fade(i)}
                    data-testid={`service-card-${i}`}
                    className="group rounded-lg border border-ivory-border bg-ivory-surface p-7 transition-all duration-300 hover:-translate-y-1 hover:border-gold/60"
                  >
                    <Icon className="w-6 h-6 text-gold mb-5" strokeWidth={1.5} />
                    <h3 className="font-serif text-xl tracking-tight mb-2">{s.title}</h3>
                    <p className="text-sm leading-relaxed text-ink-soft">{s.description}</p>
                  </motion.div>
                );
              })}
            </div>
          </section>
        )}

        {/* PROJECTS — horizontal rows */}
        {projects.length > 0 && (
          <section className="mt-16" data-testid="projects-section">
            <motion.div {...fade(0)}>
              <Overline>Selected Work</Overline>
              <h2 className="font-serif text-3xl tracking-tight mb-6">Recent projects</h2>
            </motion.div>
            <div className="border-t border-ivory-border">
              {projects.map((p, i) => {
                const Row = (
                  <>
                    <img src={resolveImg(p.coverImage)} alt={p.name} className="w-20 h-20 rounded-md object-cover flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-[11px] uppercase tracking-[0.2em] text-gold mb-1 truncate">{p.category}</p>
                      <h3 className="font-serif text-xl tracking-tight truncate">{p.name}</h3>
                      {p.description ? <p className="text-sm text-ink-soft truncate">{p.description}</p> : null}
                    </div>
                    <ArrowUpRight className="w-5 h-5 text-gold transition-transform duration-300 group-hover:translate-x-1 group-hover:-translate-y-1" strokeWidth={1.5} />
                  </>
                );
                const cls = "group flex items-center gap-4 border-b border-ivory-border py-5 transition-colors duration-300 hover:bg-ivory-surface/60";
                return (
                  <motion.div key={i} {...fade(i)} data-testid={`project-row-${i}`}>
                    {p.url ? (
                      <a href={p.url} target="_blank" rel="noopener noreferrer" className={cls}>{Row}</a>
                    ) : (
                      <div className={cls}>{Row}</div>
                    )}
                  </motion.div>
                );
              })}
            </div>
          </section>
        )}

        {/* MAIN CTA — framed */}
        {(b.bookingUrl || c.phone) && (
          <motion.section {...fade(0)} className="mt-16 rounded-lg border border-gold p-8 text-center" data-testid="cta-bar">
            <Overline>Let's talk</Overline>
            <h2 className="font-serif text-3xl tracking-tight mb-3">Book a private consultation</h2>
            <p className="text-sm text-ink-soft mb-6 max-w-xs mx-auto">A focused conversation about what you're looking for — no obligation.</p>
            <ActionButton
              action={actions.book || actions.call}
              testId="cta-book-button"
              className="inline-flex items-center justify-center gap-2 rounded-md bg-ink px-8 py-3.5 text-sm tracking-wide text-ivory-bg transition-colors duration-300 hover:bg-ink-soft"
              iconClassName="w-[18px] h-[18px]"
            />
          </motion.section>
        )}

        {/* SAVE CONTACT + QR */}
        <motion.section {...fade(0)} className="mt-6 grid grid-cols-2 gap-4">
          <SaveContactButton
            slug={slug}
            className="flex flex-col items-start justify-between gap-6 rounded-lg border border-ivory-border bg-ivory-surface p-6 transition-colors duration-300 hover:border-gold/60"
            iconClassName="w-6 h-6 text-gold"
            label="Save Contact"
            subLabel="Add to phone (.vcf)"
          />
          <QRBlock
            slug={slug}
            className="flex flex-col items-center justify-center gap-2 rounded-lg border border-ivory-border bg-ivory-surface p-4"
            imgClassName="w-24 h-24"
            label="Scan to open"
          />
        </motion.section>

        {/* FOOTER */}
        <footer className="mt-16 border-t border-ivory-border pt-8 text-center">
          <div className="space-y-1 text-sm text-ink-soft">
            {c.phone ? <p data-testid="footer-phone">{c.phone}</p> : null}
            {c.email ? <p data-testid="footer-email">{c.email}</p> : null}
            {c.address ? <p>{c.address}</p> : null}
          </div>
          <SocialIcons
            social={social}
            className="mt-6 flex items-center justify-center gap-3"
            itemClassName="flex items-center justify-center w-10 h-10 rounded-full border border-ivory-border text-ink-soft transition-colors duration-300 hover:border-gold hover:text-gold"
          />
          <p className="mt-8 text-[11px] tracking-[0.2em] uppercase text-ink-soft/60">
            © {new Date().getFullYear()} {id.fullName} · ARIADNI ID
          </p>
        </footer>
      </div>
    </div>
  );
};
