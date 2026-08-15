import { useLocation, Link, Navigate } from "react-router-dom";
import { ArrowRight, Check, ChevronRight } from "lucide-react";
import { useSeo, breadcrumb, faqJsonLd, SOFTWARE_APP_JSONLD } from "@/lib/seo";
import { LANDING_PAGES, SEO_FOOTER_LINKS, FEAT, TRIAL } from "./landingContent";

const SeoFooter = () => (
  <footer className="border-t border-white/10 bg-[#08090B] px-6 py-12" data-testid="seo-footer">
    <div className="mx-auto max-w-5xl">
      <Link to="/" className="text-lg font-semibold text-white">TapPresence</Link>
      <nav className="mt-5 grid grid-cols-2 gap-x-6 gap-y-2 text-sm text-white/55 sm:grid-cols-3 md:grid-cols-4">
        {SEO_FOOTER_LINKS.map((l) => (
          <Link key={l.path} to={l.path} className="transition-colors hover:text-[#D6A653]" data-testid={`footer-link-${l.path.slice(1)}`}>{l.label}</Link>
        ))}
        <Link to="/industries" className="transition-colors hover:text-[#D6A653]">Industries</Link>
        <Link to="/legal/privacy" className="transition-colors hover:text-[#D6A653]">Privacy</Link>
        <Link to="/legal/terms" className="transition-colors hover:text-[#D6A653]">Terms</Link>
      </nav>
      <p className="mt-8 text-xs text-white/35">© {new Date().getFullYear()} TapPresence. Your presence, one tap away.</p>
    </div>
  </footer>
);

export default function SeoLanding() {
  const key = useLocation().pathname.replace(/^\/+/, "").replace(/\/+$/, "");
  const page = LANDING_PAGES[key];

  const jsonLd = page
    ? [
        breadcrumb([{ name: "Home", path: "/" }, { name: page.breadcrumb, path: `/${key}` }]),
        SOFTWARE_APP_JSONLD,
        ...(page.faq?.length ? [faqJsonLd(page.faq)] : []),
      ]
    : undefined;
  useSeo({
    title: page?.title,
    description: page?.description,
    path: page ? `/${key}` : undefined,
    jsonLd,
  });
  if (!page) return <Navigate to="/" replace />;

  const related = (page.related || []).map((r) => SEO_FOOTER_LINKS.find((l) => l.path === `/${r}`)).filter(Boolean);

  return (
    <div className="min-h-screen bg-[#0A0B0D] text-white" data-testid={`seo-landing-${key}`}>
      {/* top bar */}
      <header className="flex items-center justify-between px-6 py-5">
        <Link to="/" className="text-lg font-semibold">TapPresence</Link>
        <div className="flex items-center gap-3 text-sm">
          <Link to="/login" className="text-white/70 hover:text-white">Sign in</Link>
          <Link to="/register" className="rounded-full bg-[#D6A653] px-4 py-2 font-medium text-[#050607] hover:bg-[#E8B764]" data-testid="seo-cta-top">Start free</Link>
        </div>
      </header>

      {/* hero */}
      <section className="mx-auto max-w-3xl px-6 pt-10 pb-6 text-center">
        <p className="mb-3 flex items-center justify-center gap-1 text-xs uppercase tracking-widest text-white/40">
          <Link to="/" className="hover:text-[#D6A653]">Home</Link> <ChevronRight className="h-3 w-3" /> <span className="text-[#D6A653]">{page.breadcrumb}</span>
        </p>
        <h1 className="text-4xl font-light leading-tight sm:text-5xl lg:text-6xl" data-testid="seo-h1">{page.h1}</h1>
        <p className="mx-auto mt-5 max-w-2xl text-base text-white/65 sm:text-lg">{page.intro}</p>
        <Link to="/register" className="mt-8 inline-flex items-center gap-2 rounded-full bg-[#D6A653] px-6 py-3 text-sm font-medium text-[#050607] transition-colors hover:bg-[#E8B764]" data-testid="seo-cta-hero">
          {TRIAL} <ArrowRight className="h-4 w-4" />
        </Link>
        <p className="mt-3 text-xs text-white/40">No card required · Taxes calculated at checkout</p>
      </section>

      {/* features */}
      <section className="mx-auto max-w-4xl px-6 py-10">
        <h2 className="mb-6 text-center text-lg font-medium text-white/90">What you can do</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          {(page.features || []).map((f) => (
            <div key={f} className="rounded-2xl border border-white/10 bg-white/[0.02] p-5" data-testid={`seo-feature-${f}`}>
              <p className="flex items-center gap-2 text-sm font-medium text-white"><Check className="h-4 w-4 text-[#D6A653]" /> {FEAT[f].t}</p>
              <p className="mt-2 text-sm leading-relaxed text-white/60">{FEAT[f].d}</p>
            </div>
          ))}
        </div>
      </section>

      {/* FAQ */}
      {page.faq?.length ? (
        <section className="mx-auto max-w-3xl px-6 py-10" data-testid="seo-faq">
          <h2 className="mb-6 text-center text-lg font-medium text-white/90">Frequently asked questions</h2>
          <div className="space-y-3">
            {page.faq.map((x, i) => (
              <details key={i} className="rounded-xl border border-white/10 bg-white/[0.02] p-4" data-testid={`seo-faq-${i}`}>
                <summary className="cursor-pointer text-sm font-medium text-white">{x.q}</summary>
                <p className="mt-2 text-sm leading-relaxed text-white/60">{x.a}</p>
              </details>
            ))}
          </div>
        </section>
      ) : null}

      {/* related internal links */}
      {related.length ? (
        <section className="mx-auto max-w-4xl px-6 py-8">
          <h2 className="mb-4 text-center text-sm uppercase tracking-widest text-white/40">Explore more</h2>
          <div className="flex flex-wrap justify-center gap-3">
            {related.map((r) => (
              <Link key={r.path} to={r.path} className="rounded-full border border-white/15 px-4 py-2 text-sm text-white/70 transition-colors hover:border-[#D6A653]/50 hover:text-white" data-testid={`related-${r.path.slice(1)}`}>{r.label}</Link>
            ))}
          </div>
        </section>
      ) : null}

      {/* closing CTA */}
      <section className="mx-auto max-w-2xl px-6 py-14 text-center">
        <h2 className="text-2xl font-light sm:text-3xl">Ready to make your presence effortless?</h2>
        <Link to="/register" className="mt-6 inline-flex items-center gap-2 rounded-full bg-[#D6A653] px-6 py-3 text-sm font-medium text-[#050607] hover:bg-[#E8B764]" data-testid="seo-cta-bottom">
          {TRIAL} <ArrowRight className="h-4 w-4" />
        </Link>
      </section>

      <SeoFooter />
    </div>
  );
}

export { SeoFooter };
