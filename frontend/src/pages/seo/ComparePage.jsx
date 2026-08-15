import { useLocation, Link, Navigate } from "react-router-dom";
import { ArrowRight, Check } from "lucide-react";
import { useSeo, breadcrumb } from "@/lib/seo";
import { SeoFooter } from "./SeoLanding";
import { trackTrialClick } from "@/lib/ga";
import { COMPARE_PAGES, TAPPRESENCE_FACTS } from "./compareContent";

export default function ComparePage() {
  const slug = useLocation().pathname.replace(/^\/compare\//, "").replace(/\/+$/, "");
  const page = COMPARE_PAGES[slug];

  // SEO: comparison pages stay noindex until competitor data is verified.
  useSeo({
    title: page ? `TapPresence vs ${page.competitor} — Digital Business Cards Compared | TapPresence` : undefined,
    description: page ? `Compare TapPresence and ${page.competitor} for digital business cards, NFC & QR sharing, business card scanning, lead capture, follow-up, analytics and teams.` : undefined,
    path: page ? `/compare/${slug}` : undefined,
    noindex: !page || !page.verified,
    jsonLd: page ? [breadcrumb([{ name: "Home", path: "/" }, { name: "Compare", path: "/compare/" + slug }, { name: `TapPresence vs ${page.competitor}`, path: "/compare/" + slug }])] : undefined,
  });

  if (!page) return <Navigate to="/" replace />;

  return (
    <div className="min-h-screen bg-[#0A0B0D] text-white" data-testid={`compare-${slug}`}>
      <header className="flex items-center justify-between px-6 py-5">
        <Link to="/" className="text-lg font-semibold">TapPresence</Link>
        <div className="flex items-center gap-3 text-sm">
          <Link to="/login" className="text-white/70 hover:text-white">Sign in</Link>
          <Link to="/register" onClick={() => trackTrialClick(`compare_${slug}`)} className="rounded-full bg-[#D6A653] px-4 py-2 font-medium text-[#050607] hover:bg-[#E8B764]">Start free</Link>
        </div>
      </header>

      <section className="mx-auto max-w-3xl px-6 pt-10 pb-6">
        <p className="mb-3 text-xs uppercase tracking-widest text-white/40">
          <Link to="/" className="hover:text-[#D6A653]">Home</Link> · <span className="text-[#D6A653]">TapPresence vs {page.competitor}</span>
        </p>
        <h1 className="text-4xl font-light sm:text-5xl" data-testid="compare-h1">TapPresence vs {page.competitor}</h1>
        <p className="mt-6 text-base leading-relaxed text-white/70">
          Evaluating digital business card platforms? Here's exactly what TapPresence does, so you can compare it against {page.competitor} using verified facts. TapPresence focuses on turning in-person introductions into tracked, followable leads — with digital cards, NFC &amp; QR sharing, a business card scanner, a CRM pipeline, follow-up, analytics and team management.
        </p>
      </section>

      {/* TapPresence verified capabilities */}
      <section className="mx-auto max-w-3xl px-6 py-6">
        <h2 className="mb-6 text-xl font-medium sm:text-2xl">What TapPresence offers</h2>
        <div className="overflow-hidden rounded-2xl border border-white/10">
          {TAPPRESENCE_FACTS.map((row, i) => (
            <div key={i} className={`grid grid-cols-3 gap-3 px-5 py-4 text-sm ${i % 2 ? "bg-white/[0.02]" : ""}`} data-testid={`compare-row-${i}`}>
              <span className="col-span-1 font-medium text-white/80">{row.k}</span>
              <span className="col-span-2 flex items-start gap-2 text-white/65"><Check className="mt-0.5 h-4 w-4 shrink-0 text-[#D6A653]" /> {row.v}</span>
            </div>
          ))}
        </div>
      </section>

      {page.verified ? null : (
        <section className="mx-auto max-w-3xl px-6 pb-4">
          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6 text-sm leading-relaxed text-white/60" data-testid="compare-verify-note">
            We publish a full side-by-side only with independently verified competitor information. TapPresence's capabilities above are accurate; the detailed {page.competitor} column is being verified before publication so this comparison stays factual and fair.
          </div>
        </section>
      )}

      <section className="mx-auto max-w-2xl px-6 py-12 text-center">
        <h2 className="text-2xl font-light sm:text-3xl">See TapPresence for yourself</h2>
        <p className="mx-auto mt-3 max-w-lg text-sm text-white/60">The best comparison is a hands-on one. Try every capability free for 14 days — no card required to begin.</p>
        <Link to="/register" onClick={() => trackTrialClick(`compare_cta_${slug}`)} className="mt-6 inline-flex items-center gap-2 rounded-full bg-[#D6A653] px-6 py-3 text-sm font-medium text-[#050607] hover:bg-[#E8B764]" data-testid="compare-cta">
          Start your free 14-day trial <ArrowRight className="h-4 w-4" />
        </Link>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          {[{ to: "/digital-business-card", label: "Digital Business Card" }, { to: "/nfc-business-card", label: "NFC" }, { to: "/teams", label: "Teams" }, { to: "/pricing", label: "Pricing" }].map((l) => (
            <Link key={l.to} to={l.to} className="rounded-full border border-white/15 px-4 py-2 text-sm text-white/70 transition-colors hover:border-[#D6A653]/50 hover:text-white" data-testid={`compare-related-${l.to.slice(1)}`}>{l.label}</Link>
          ))}
        </div>
      </section>
      <SeoFooter />
    </div>
  );
}
