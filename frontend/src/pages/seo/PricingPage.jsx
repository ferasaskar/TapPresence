import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import PricingSection from "@/components/landing/PricingSection";
import { useSeo, breadcrumb, SOFTWARE_APP_JSONLD } from "@/lib/seo";
import { trackTrialClick } from "@/lib/ga";
import { SeoFooter } from "./SeoLanding";

export default function PricingPage() {
  useSeo({
    title: "Pricing — TapPresence Digital Business Cards",
    description: "Simple TapPresence pricing for individuals and teams. Free 14-day trial, NFC & QR sharing, lead capture, CRM pipeline and analytics included. Taxes calculated at checkout.",
    path: "/pricing",
    jsonLd: [breadcrumb([{ name: "Home", path: "/" }, { name: "Pricing", path: "/pricing" }]), SOFTWARE_APP_JSONLD],
  });
  return (
    <div className="min-h-screen bg-[#0A0B0D] text-white" data-testid="seo-pricing-page">
      <header className="flex items-center justify-between px-6 py-5">
        <Link to="/" className="text-lg font-semibold">TapPresence</Link>
        <div className="flex items-center gap-3 text-sm">
          <Link to="/login" className="text-white/70 hover:text-white">Sign in</Link>
          <Link to="/register" onClick={() => trackTrialClick("pricing_top")} className="rounded-full bg-[#D6A653] px-4 py-2 font-medium text-[#050607] hover:bg-[#E8B764]">Start free</Link>
        </div>
      </header>
      <section className="mx-auto max-w-3xl px-6 pt-10 pb-2 text-center">
        <h1 className="text-4xl font-light sm:text-5xl" data-testid="pricing-h1">Simple pricing for every professional</h1>
        <p className="mx-auto mt-4 max-w-xl text-base text-white/65">Start free for 14 days. Upgrade when you're ready — for yourself or your whole team.</p>
      </section>
      {/* Pricing is rendered from the SAME authoritative /api/commercial/pricing source (no hardcoded prices). */}
      <PricingSection />
      <section className="mx-auto max-w-2xl px-6 py-12 text-center">
        <Link to="/register" onClick={() => trackTrialClick("pricing_bottom")} className="inline-flex items-center gap-2 rounded-full bg-[#D6A653] px-6 py-3 text-sm font-medium text-[#050607] hover:bg-[#E8B764]" data-testid="pricing-cta">
          Start your free 14-day trial <ArrowRight className="h-4 w-4" />
        </Link>
      </section>
      <SeoFooter />
    </div>
  );
}
