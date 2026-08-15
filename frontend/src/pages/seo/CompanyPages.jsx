import { Link } from "react-router-dom";
import { ArrowRight, Mail, ShieldCheck, Building2 } from "lucide-react";
import { useSeo, breadcrumb, SEO_ORIGIN } from "@/lib/seo";
import { SeoFooter } from "./SeoLanding";
import { trackTrialClick } from "@/lib/ga";

const CONTACT_EMAIL = "sales@tappresence.com";

const Shell = ({ testid, children }) => (
  <div className="min-h-screen bg-[#0A0B0D] text-white" data-testid={testid}>
    <header className="flex items-center justify-between px-6 py-5">
      <Link to="/" className="text-lg font-semibold">TapPresence</Link>
      <div className="flex items-center gap-3 text-sm">
        <Link to="/login" className="text-white/70 hover:text-white">Sign in</Link>
        <Link to="/register" onClick={() => trackTrialClick("company_top")} className="rounded-full bg-[#D6A653] px-4 py-2 font-medium text-[#050607] hover:bg-[#E8B764]">Start free</Link>
      </div>
    </header>
    {children}
    <SeoFooter />
  </div>
);

const Crumb = ({ label }) => (
  <p className="mb-3 text-xs uppercase tracking-widest text-white/40">
    <Link to="/" className="hover:text-[#D6A653]">Home</Link> · <span className="text-[#D6A653]">{label}</span>
  </p>
);

const RelatedRow = ({ links }) => (
  <div className="mt-10 flex flex-wrap gap-3">
    {links.map((l) => (
      <Link key={l.to} to={l.to} className="rounded-full border border-white/15 px-4 py-2 text-sm text-white/70 transition-colors hover:border-[#D6A653]/50 hover:text-white" data-testid={`company-related-${l.to.slice(1)}`}>{l.label}</Link>
    ))}
  </div>
);

export function About() {
  useSeo({
    title: "About TapPresence — Digital Business Cards & Lead Capture",
    description: "TapPresence helps professionals and teams turn real-world introductions into tracked leads with digital business cards, NFC & QR sharing, business card scanning, follow-up and analytics.",
    path: "/about",
    jsonLd: [breadcrumb([{ name: "Home", path: "/" }, { name: "About", path: "/about" }])],
  });
  return (
    <Shell testid="about-page">
      <section className="mx-auto max-w-3xl px-6 pt-10 pb-16">
        <Crumb label="About" />
        <h1 className="text-4xl font-light sm:text-5xl" data-testid="about-h1">About TapPresence</h1>
        <p className="mt-6 text-base leading-relaxed text-white/70">TapPresence is a digital presence platform that turns every introduction into an opportunity. We replace paper business cards with a single, always-current digital profile you can share in one tap by NFC or QR — and we connect that moment of sharing to the follow-up that actually wins business.</p>
        <div className="mt-8 space-y-8">
          <div>
            <h2 className="text-xl font-medium sm:text-2xl">What we do</h2>
            <p className="mt-3 text-base leading-relaxed text-white/65">Professionals and teams use TapPresence to share their details, capture leads from their profile and from scanned paper business cards, organise those leads in a CRM pipeline, follow up with timely and AI-assisted messages, and see engagement through analytics. Teams roll out consistent, branded cards from one workspace.</p>
          </div>
          <div>
            <h2 className="text-xl font-medium sm:text-2xl">Who it's for</h2>
            <p className="mt-3 text-base leading-relaxed text-white/65">Anyone whose work depends on relationships — sales teams, consultants, real estate agents, founders, healthcare and event professionals — and whole companies who want one professional identity everywhere. TapPresence supports English, Arabic (right-to-left) and Spanish, and is used by professionals internationally, including across the UAE.</p>
          </div>
          <div>
            <h2 className="text-xl font-medium sm:text-2xl">How to get started</h2>
            <p className="mt-3 text-base leading-relaxed text-white/65">TapPresence uses a 14-day free trial — there's no permanent free plan. You can try every capability before you decide, then continue on an individual or seat-based team plan.</p>
          </div>
        </div>
        <Link to="/register" onClick={() => trackTrialClick("about_cta")} className="mt-10 inline-flex items-center gap-2 rounded-full bg-[#D6A653] px-6 py-3 text-sm font-medium text-[#050607] hover:bg-[#E8B764]" data-testid="about-cta">Start your free 14-day trial <ArrowRight className="h-4 w-4" /></Link>
        <RelatedRow links={[{ to: "/digital-business-card", label: "Digital Business Card" }, { to: "/teams", label: "For Teams" }, { to: "/pricing", label: "Pricing" }, { to: "/contact", label: "Contact" }]} />
      </section>
    </Shell>
  );
}

export function Contact() {
  useSeo({
    title: "Contact TapPresence — Sales & Support",
    description: "Get in touch with the TapPresence team about digital business cards, team rollouts and pricing. Email us or start your free 14-day trial.",
    path: "/contact",
    jsonLd: [breadcrumb([{ name: "Home", path: "/" }, { name: "Contact", path: "/contact" }])],
  });
  return (
    <Shell testid="contact-page">
      <section className="mx-auto max-w-3xl px-6 pt-10 pb-16">
        <Crumb label="Contact" />
        <h1 className="text-4xl font-light sm:text-5xl" data-testid="contact-h1">Contact TapPresence</h1>
        <p className="mt-6 text-base leading-relaxed text-white/70">Questions about digital business cards, rolling TapPresence out to your team, or pricing? We're happy to help.</p>
        <div className="mt-8 rounded-2xl border border-white/10 bg-white/[0.03] p-6">
          <p className="flex items-center gap-2 text-sm font-medium text-white"><Mail className="h-4 w-4 text-[#D6A653]" /> Email</p>
          <a href={`mailto:${CONTACT_EMAIL}`} className="mt-2 inline-block text-lg text-[#D6A653] hover:underline" data-testid="contact-email">{CONTACT_EMAIL}</a>
          <p className="mt-3 text-sm text-white/55">For sales, team plans and general enquiries. We aim to reply within one business day.</p>
        </div>
        <div className="mt-6 rounded-2xl border border-white/10 bg-white/[0.03] p-6">
          <p className="flex items-center gap-2 text-sm font-medium text-white"><Building2 className="h-4 w-4 text-[#D6A653]" /> Try it yourself</p>
          <p className="mt-2 text-sm text-white/55">The fastest way to see if TapPresence fits is to start a free 14-day trial — no card required to begin.</p>
          <Link to="/register" onClick={() => trackTrialClick("contact_cta")} className="mt-4 inline-flex items-center gap-2 rounded-full bg-[#D6A653] px-6 py-3 text-sm font-medium text-[#050607] hover:bg-[#E8B764]" data-testid="contact-cta">Start your free 14-day trial <ArrowRight className="h-4 w-4" /></Link>
        </div>
        <RelatedRow links={[{ to: "/pricing", label: "Pricing" }, { to: "/teams", label: "For Teams" }, { to: "/about", label: "About" }, { to: "/security", label: "Security" }]} />
      </section>
    </Shell>
  );
}

export function Security() {
  useSeo({
    title: "Security at TapPresence — How We Protect Your Data",
    description: "How TapPresence protects your account and data: encrypted connections, hashed passwords, PCI-compliant payment processing via Stripe, workspace data isolation and consent-based analytics.",
    path: "/security",
    jsonLd: [breadcrumb([{ name: "Home", path: "/" }, { name: "Security", path: "/security" }])],
  });
  const items = [
    { h: "Encrypted connections", p: "Traffic to TapPresence is served over HTTPS, so data moving between your device and our services is encrypted in transit." },
    { h: "Password protection", p: "Account passwords are stored as salted hashes, never in plain text. You can also sign in with Google." },
    { h: "Payments handled by Stripe", p: "Subscriptions and payments are processed by Stripe, a PCI-DSS-compliant payment provider. Card details are entered on Stripe's secure checkout and are never stored on TapPresence servers." },
    { h: "Workspace data isolation", p: "Your cards, leads and analytics belong to your workspace and are scoped to authorised members, so one workspace cannot access another's data." },
    { h: "Privacy and consent", p: "Analytics respect a cookie-consent mechanism, and you control your data. See our Privacy Policy for details on what we collect and why." },
  ];
  return (
    <Shell testid="security-page">
      <section className="mx-auto max-w-3xl px-6 pt-10 pb-16">
        <Crumb label="Security" />
        <h1 className="text-4xl font-light sm:text-5xl" data-testid="security-h1">Security at TapPresence</h1>
        <p className="mt-6 text-base leading-relaxed text-white/70">We take the security of your account and the contacts you capture seriously. Here are the concrete measures in place today.</p>
        <div className="mt-8 space-y-6">
          {items.map((s, i) => (
            <div key={i} className="rounded-2xl border border-white/10 bg-white/[0.03] p-6" data-testid={`security-item-${i}`}>
              <p className="flex items-center gap-2 text-base font-medium text-white"><ShieldCheck className="h-4 w-4 text-[#D6A653]" /> {s.h}</p>
              <p className="mt-2 text-sm leading-relaxed text-white/65">{s.p}</p>
            </div>
          ))}
        </div>
        <p className="mt-8 text-sm leading-relaxed text-white/55" data-testid="security-disclosure">For specific compliance or security questionnaires, contact <a href={`mailto:${CONTACT_EMAIL}`} className="text-[#D6A653] hover:underline">{CONTACT_EMAIL}</a>. We describe only the practices we actually operate and do not claim certifications we have not obtained.</p>
        <RelatedRow links={[{ to: "/legal/privacy", label: "Privacy Policy" }, { to: "/legal/terms", label: "Terms" }, { to: "/contact", label: "Contact" }]} />
      </section>
    </Shell>
  );
}
