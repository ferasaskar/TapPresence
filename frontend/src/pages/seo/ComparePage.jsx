import { useLocation, Link, Navigate } from "react-router-dom";
import { ArrowRight, Check, Minus } from "lucide-react";
import { useSeo, breadcrumb } from "@/lib/seo";
import { SeoFooter } from "./SeoLanding";
import { trackTrialClick } from "@/lib/ga";
import { COMPARE_PAGES, COMPARE_SLUGS } from "./compareContent";

export default function ComparePage() {
  const slug = useLocation().pathname.replace(/^\/compare\//, "").replace(/\/+$/, "");
  const page = COMPARE_PAGES[slug];

  useSeo({
    title: page ? page.title : undefined,
    description: page ? page.description : undefined,
    path: page ? `/compare/${slug}` : undefined,
    noindex: !page || !page.verified, // indexable only once competitor data is verified
    jsonLd: page ? [breadcrumb([
      { name: "Home", path: "/" },
      { name: `TapPresence vs ${page.competitor}`, path: "/compare/" + slug },
    ])] : undefined,
  });

  if (!page) return <Navigate to="/" replace />;

  const others = COMPARE_SLUGS.filter((s) => s !== slug);

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
        <p className="mt-6 text-base leading-relaxed text-white/70">{page.intro}</p>
      </section>

      {/* comparison table */}
      <section className="mx-auto max-w-3xl px-6 py-6">
        <h2 className="mb-6 text-xl font-medium sm:text-2xl">Side-by-side comparison</h2>
        <div className="overflow-hidden rounded-2xl border border-white/10">
          <div className="grid grid-cols-3 gap-3 border-b border-white/10 bg-white/[0.04] px-5 py-3 text-xs font-semibold uppercase tracking-wide text-white/50">
            <span>Capability</span><span className="text-[#D6A653]">TapPresence</span><span>{page.competitor}</span>
          </div>
          {page.rows.map((r, i) => (
            <div key={i} className={`grid grid-cols-3 gap-3 px-5 py-4 text-sm ${i % 2 ? "bg-white/[0.02]" : ""}`} data-testid={`compare-row-${i}`}>
              <span className="font-medium text-white/80">{r.dim}</span>
              <span className="flex items-start gap-2 text-white/70"><Check className="mt-0.5 h-4 w-4 shrink-0 text-[#D6A653]" /> {r.tp}</span>
              <span className="flex items-start gap-2 text-white/55">
                {r.comp === "—" ? <Minus className="mt-0.5 h-4 w-4 shrink-0 text-white/30" /> : null}{r.comp}
              </span>
            </div>
          ))}
        </div>
        <p className="mt-3 text-xs text-white/40">TapPresence details reflect the live product. {page.competitor} details reflect publicly available information and may change — verify current specifics on {page.competitor}'s website.</p>
      </section>

      {/* honest positioning: competitor strengths + where TapPresence fits */}
      <section className="mx-auto max-w-3xl px-6 py-4">
        <div className="grid gap-6 sm:grid-cols-2">
          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6" data-testid="compare-competitor-strengths">
            <h2 className="text-lg font-medium">Where {page.competitor} is strong</h2>
            <p className="mt-3 text-sm leading-relaxed text-white/60">{page.competitorStrengths}</p>
          </div>
          <div className="rounded-2xl border border-[#D6A653]/25 bg-[#D6A653]/[0.06] p-6" data-testid="compare-tp-edge">
            <h2 className="text-lg font-medium">Where TapPresence fits</h2>
            <ul className="mt-3 space-y-2">
              {page.tpEdge.map((e, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-white/75"><Check className="mt-0.5 h-4 w-4 shrink-0 text-[#D6A653]" /> {e}</li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="mx-auto max-w-2xl px-6 py-12 text-center">
        <h2 className="text-2xl font-light sm:text-3xl">See TapPresence for yourself</h2>
        <p className="mx-auto mt-3 max-w-lg text-sm text-white/60">The best comparison is hands-on. Try every capability free for 14 days — no card required to begin.</p>
        <Link to="/register" onClick={() => trackTrialClick(`compare_cta_${slug}`)} className="mt-6 inline-flex items-center gap-2 rounded-full bg-[#D6A653] px-6 py-3 text-sm font-medium text-[#050607] hover:bg-[#E8B764]" data-testid="compare-cta">
          Start your free 14-day trial <ArrowRight className="h-4 w-4" />
        </Link>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          {[{ to: "/digital-business-card", label: "Digital Business Card" }, { to: "/teams", label: "Teams" }, { to: "/pricing", label: "Pricing" }].map((l) => (
            <Link key={l.to} to={l.to} className="rounded-full border border-white/15 px-4 py-2 text-sm text-white/70 transition-colors hover:border-[#D6A653]/50 hover:text-white" data-testid={`compare-related-${l.to.slice(1)}`}>{l.label}</Link>
          ))}
        </div>
        <div className="mt-6 flex flex-wrap justify-center gap-x-5 gap-y-2 text-xs text-white/40">
          <span>Other comparisons:</span>
          {others.map((s) => (
            <Link key={s} to={`/compare/${s}`} className="hover:text-[#D6A653]" data-testid={`compare-other-${s}`}>vs {COMPARE_PAGES[s].competitor}</Link>
          ))}
        </div>
      </section>
      <SeoFooter />
    </div>
  );
}
