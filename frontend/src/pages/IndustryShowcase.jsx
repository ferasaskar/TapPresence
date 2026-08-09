import { useState } from "react";
import { Link } from "react-router-dom";
import IndustryCustomizer from "@/components/admin/IndustryCustomizer";
import IndustryCards from "@/components/landing/IndustryCards";
import { IndustryCard } from "@/components/landing/IndustryCard";
import { INDUSTRY_CARDS, previewCardConfig } from "@/lib/industryCards";
import { ASSETS } from "@/components/landing/data";
import { ArrowLeft, ArrowRight } from "lucide-react";

const AriadniMark = ({ className = "" }) => (
  <svg viewBox="0 0 24 24" className={className} fill="none" aria-hidden>
    <path d="M12 3 L21 20 L15.6 20 L12 12 L8.4 20 L3 20 Z" fill="currentColor" />
  </svg>
);

const DEMO = {
  slug: "preview", templateId: "executive-black-gold", accent: "gold", custom_accent_color: "", status: "published",
  industry: "real_estate", background_style: "skyline", background_opacity: 0.16, background_intensity: "medium", background_position: "center", custom_background: "",
  identity: {
    fullName: "Alex Morgan", jobTitle: "Real Estate Consultant", company: "Morgan Properties",
    profilePhoto: ASSETS.heroPortrait, availabilityBadge: "Available for Work",
    city: "Dubai", country: "United Arab Emirates",
    bio: "Curating exceptional residences and investment properties across the Emirates. Two decades of quiet, trusted advisory for a discerning clientele.",
  },
  contact: { phone: "+971501234567", whatsapp: "+971501234567", email: "alex@morganproperties.ae", website: "morganproperties.ae", address: "Dubai, UAE", mapsUrl: "" },
  social: { linkedin: "#", instagram: "#", x: "", youtube: "", tiktok: "" },
  actions: [],
  services: [
    { icon: "Building2", title: "Luxury Residential", description: "Handpicked penthouses and waterfront villas.", enabled: true, order: 0 },
    { icon: "TrendingUp", title: "Investment Advisory", description: "Data-led guidance on yield and ROI.", enabled: true, order: 1 },
    { icon: "Key", title: "Private Concierge", description: "End-to-end white-glove acquisition.", enabled: true, order: 2 },
  ],
  projects: [], booking: { bookingUrl: "" }, languages: ["en"], i18n: {},
};

export default function IndustryShowcase() {
  const [demo, setDemo] = useState(DEMO);

  const set = (path, value) => {
    setDemo((f) => {
      const next = { ...f };
      if (path.includes(".")) { const [g, k] = path.split("."); next[g] = { ...next[g], [k]: value }; }
      else next[path] = value;
      if (path === "industry") {
        const p = INDUSTRY_CARDS.find((c) => c.id === value);
        if (p) {
          next.accent = p.accentId;
          next.custom_accent_color = "";
          next.identity = { ...next.identity, fullName: p.name, jobTitle: p.role, company: p.company, profilePhoto: p.portrait };
        }
      }
      return next;
    });
  };

  return (
    <div className="min-h-screen overflow-x-hidden bg-[#050607] text-neutral-200" style={{ fontFamily: "'Geist','Inter',sans-serif" }} data-testid="industry-showcase">
      {/* header */}
      <header className="sticky top-0 z-40 border-b border-white/8 bg-[#050607]/85 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-[1280px] items-center justify-between px-4 sm:px-8">
          <Link to="/" className="flex items-center gap-2 text-lg font-semibold tracking-tight" data-testid="showcase-home">
            <AriadniMark className="h-5 w-5 text-[#D6A653]" /> ARIADNI <span className="text-[#D6A653]">ID</span>
          </Link>
          <div className="flex items-center gap-3">
            <Link to="/admin" className="hidden text-sm text-neutral-300 hover:text-white sm:inline">Dashboard</Link>
            <Link to="/register" className="rounded-xl bg-gradient-to-b from-[#F3D593] to-[#C08F3D] px-5 py-2.5 text-sm font-semibold text-[#1A1206]" data-testid="showcase-create">Create Your ID</Link>
          </div>
        </div>
      </header>

      {/* hero */}
      <section className="mx-auto max-w-[1280px] px-4 pt-10 sm:px-8">
        <Link to="/admin" className="mb-6 inline-flex items-center gap-2 text-sm text-neutral-400 hover:text-white">
          <ArrowLeft className="h-4 w-4" /> Back to dashboard
        </Link>
        <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-[#D6A653]">Industry Template System</p>
        <h1 className="mt-2 font-semibold tracking-tight text-white" style={{ fontSize: "clamp(30px,5vw,52px)", lineHeight: 1.05 }}>
          One Template. <span className="bg-gradient-to-b from-[#F0CD84] to-[#C08F3D] bg-clip-text text-transparent">Endless Possibilities.</span>
        </h1>
        <p className="mt-4 max-w-[620px] text-[15px] leading-relaxed text-neutral-400">
          Choose your industry, set your brand color and adjust the background intensity to create a stunning digital identity that represents your business perfectly.
        </p>
      </section>

      {/* signature industry cards */}
      <section className="mx-auto max-w-[1280px] px-4 pt-12 sm:px-8">
        <IndustryCards />
      </section>

      {/* interactive builder heading */}
      <section className="mx-auto max-w-[1280px] px-4 pt-16 sm:px-8">
        <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-[#D6A653]">Build Your Own</p>
        <h2 className="mt-2 text-[26px] font-semibold text-white">Customize &amp; preview live</h2>
        <p className="mt-2 max-w-[620px] text-[14px] leading-relaxed text-neutral-400">
          One master card. Pick an industry to change the mood, background and accent — the card structure stays exactly the same.
        </p>
      </section>

      {/* main: live preview + customizer */}
      <section className="mx-auto grid max-w-[1280px] gap-8 px-4 pb-20 pt-10 sm:px-8 lg:grid-cols-[1fr_420px]">
        {/* preview column */}
        <div className="order-1">
          <div className="flex justify-center rounded-3xl border border-white/8 bg-gradient-to-b from-[#0a0b0d] to-[#050607] px-4 py-12" data-testid="showcase-preview">
            <IndustryCard c={previewCardConfig(demo)} />
          </div>
        </div>

        {/* customizer */}
        <div className="order-2">
          <IndustryCustomizer form={demo} set={set} />
          <Link to="/register" className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-b from-[#F3D593] to-[#C08F3D] py-3.5 text-[14px] font-semibold text-[#1A1206]" data-testid="showcase-apply">
            Create Your ID with this design <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </section>
    </div>
  );
}
