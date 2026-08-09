import { useState } from "react";
import { Link } from "react-router-dom";
import IndustryCustomizer from "@/components/admin/IndustryCustomizer";
import IndustryCards from "@/components/landing/IndustryCards";
import { TemplateRenderer } from "@/components/templates/TemplateRenderer";
import { ASSETS } from "@/components/landing/data";
import { ArrowLeft, ArrowRight, Smartphone, Monitor } from "lucide-react";

const AriadniMark = ({ className = "" }) => (
  <svg viewBox="0 0 24 24" className={className} fill="none" aria-hidden>
    <path d="M12 3 L21 20 L15.6 20 L12 12 L8.4 20 L3 20 Z" fill="currentColor" />
  </svg>
);

const TEMPLATE_CHIPS = [
  { id: "executive-black-gold", label: "Executive Black Gold" },
  { id: "beige-luxury", label: "Beige Luxury" },
  { id: "future-professional", label: "Future Professional" },
];

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
  const [device, setDevice] = useState("mobile");

  const set = (path, value) => {
    setDemo((f) => {
      const next = { ...f };
      if (path.includes(".")) { const [g, k] = path.split("."); next[g] = { ...next[g], [k]: value }; }
      else next[path] = value;
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
      </section>

      {/* main: live preview + customizer */}
      <section className="mx-auto grid max-w-[1280px] gap-8 px-4 pb-20 pt-10 sm:px-8 lg:grid-cols-[1fr_420px]">
        {/* preview column */}
        <div className="order-1">
          <div className="mb-4 flex flex-wrap items-center gap-2">
            {TEMPLATE_CHIPS.map((t) => (
              <button key={t.id} onClick={() => set("templateId", t.id)}
                className={`rounded-full border px-4 py-2 text-[12px] transition-colors ${demo.templateId === t.id ? "border-[#D6A653] bg-[#D6A653]/12 text-white" : "border-white/12 text-neutral-400 hover:border-white/30"}`}
                data-testid={`chip-${t.id}`}>{t.label}</button>
            ))}
            <div className="ml-auto flex items-center gap-1 rounded-full border border-white/12 p-1">
              <button onClick={() => setDevice("mobile")} className={`flex h-8 w-8 items-center justify-center rounded-full ${device === "mobile" ? "bg-white/10 text-white" : "text-neutral-500"}`} data-testid="device-mobile"><Smartphone className="h-4 w-4" /></button>
              <button onClick={() => setDevice("desktop")} className={`flex h-8 w-8 items-center justify-center rounded-full ${device === "desktop" ? "bg-white/10 text-white" : "text-neutral-500"}`} data-testid="device-desktop"><Monitor className="h-4 w-4" /></button>
            </div>
          </div>

          <div className="flex justify-center">
            {device === "mobile" ? (
              <div className="w-full max-w-[340px] overflow-hidden rounded-[36px] border-4 border-neutral-800 bg-black shadow-2xl sm:max-w-[390px]">
                <div className="h-[680px] overflow-y-auto" data-testid="showcase-preview">
                  <TemplateRenderer data={demo} />
                </div>
              </div>
            ) : (
              <div className="w-full overflow-hidden rounded-2xl border border-white/10 shadow-2xl">
                <div className="h-[680px] overflow-y-auto" data-testid="showcase-preview">
                  <TemplateRenderer data={demo} />
                </div>
              </div>
            )}
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
