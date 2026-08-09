import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Check, Crown, Users, Sparkles, Building2, ArrowRight } from "lucide-react";
import { api } from "@/lib/api";
import { getPreferredMarket, saveMarketPreference } from "@/lib/market";

const fmtMoney = (sym, n) => `${sym}${Number(n).toFixed(2).replace(/\.00$/, "")}`;

// Public pricing — resolved from the SAME authoritative /api/commercial/pricing config
// (Super Admin Commercial → Billing → Public site all share one source of truth).
export default function PricingSection() {
  const [data, setData] = useState(null);
  const [interval, setInterval] = useState("year");
  const [market, setMarket] = useState(null);

  const load = (mk) => api.get(`/commercial/pricing${mk ? `?market=${mk}` : ""}`).then(({ data }) => {
    setData(data);
    if (mk) setMarket(data.pricing.market);
  }).catch(() => {});

  // On mount: fetch config, then auto-select the visitor's preferred market (saved > detected > default).
  useEffect(() => {
    api.get("/commercial/pricing").then(({ data }) => {
      const pref = getPreferredMarket(data.markets, data.pricing.market);
      if (pref === data.pricing.market) { setData(data); setMarket(pref); }
      else { setMarket(pref); load(pref); }
    }).catch(() => {});
  }, []);

  // Manual selection always wins and is remembered locally.
  const changeMarket = (m) => { saveMarketPreference(m); setMarket(m); load(m); };

  const pricing = data?.pricing;
  const sym = pricing?.symbol || "$";
  const yr = interval === "year";

  const plans = useMemo(() => {
    if (!data) return [];
    const t = data.plans, tr = data.trial;
    return [
      { id: "trial", name: "Trial", icon: Sparkles, price: fmtMoney(sym, 0), unit: "", tagline: `${tr.days}-day free trial · no card required`,
        features: ["1 profile card", "Full analytics", "AI follow-ups", "Card scanner", "Lead capture & CRM"], cta: "Start free", to: "/register" },
      { id: "pro", name: "Pro", icon: Crown, popular: true, tagline: "For professionals",
        price: fmtMoney(sym, yr ? pricing.pro_year : pricing.pro_month), unit: yr ? "/year" : "/month",
        save: yr ? `Save ${pricing.pro_annual_savings_pct}%` : null,
        features: ["Up to 3 cards", "12-month analytics", "100 AI follow-ups / mo", "50 scans / mo", "Remove branding", "Wallet passes"], cta: "Get Pro", to: "/register" },
      { id: "team", name: "Team", icon: Users, tagline: `Min ${t.team.min_seats} seats`,
        price: fmtMoney(sym, yr ? pricing.team_seat_year : pricing.team_seat_month), unit: yr ? "/seat / year" : "/seat / month",
        save: yr ? `Save ${pricing.team_annual_savings_pct}%` : null,
        features: ["Unlimited cards", "Team dashboard & roles", "Locked company branding", "100 AI / user / mo", "API & custom domain"], cta: "Start Team", to: "/register?intent=team" },
      { id: "enterprise", name: "Enterprise", icon: Building2, price: "Custom", unit: "", tagline: "For organizations",
        features: ["Everything in Team", "White-label", "SSO / SAML", "Dedicated support", "Custom invoicing"], cta: "Contact sales", to: "/register?intent=team" },
    ];
  }, [data, interval, pricing, sym, yr]);

  // SEO structured data reflecting the SAME resolved config
  const jsonLd = useMemo(() => {
    if (!data) return null;
    const offers = [
      { name: "Pro Monthly", price: pricing.pro_month }, { name: "Pro Annual", price: pricing.pro_year },
      { name: "Team Seat Monthly", price: pricing.team_seat_month }, { name: "Team Seat Annual", price: pricing.team_seat_year },
    ].map((o) => ({ "@type": "Offer", name: o.name, price: o.price, priceCurrency: pricing.market }));
    return { "@context": "https://schema.org", "@type": "Product", name: "TapPresence (ARIADNI ID)", description: "Digital business cards, NFC, AI follow-up and analytics.", offers };
  }, [data, pricing]);

  if (!data) return null;

  return (
    <section id="pricing" className="mx-auto max-w-[1320px] px-5 py-16 sm:px-8 lg:px-12 lg:py-24" data-testid="landing-pricing">
      {jsonLd ? <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} /> : null}
      <div className="text-center">
        <p className="lp-eyebrow text-[12px]">Simple, transparent pricing</p>
        <h2 className="mt-3 font-semibold tracking-tight text-white" style={{ fontSize: "clamp(26px,3.4vw,36px)" }}>Choose Your Plan</h2>
        <p className="mx-auto mt-3 max-w-[520px] text-[15px] text-[#8A8F97]">Start with a {data.trial.days}-day free trial — no credit card required.</p>
      </div>

      <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
        <div className="inline-flex rounded-full border border-white/12 bg-white/5 p-1" data-testid="landing-interval-toggle">
          {["month", "year"].map((iv) => (
            <button key={iv} onClick={() => setInterval(iv)} data-testid={`landing-interval-${iv}`}
              className={`rounded-full px-4 py-1.5 text-sm transition-all ${interval === iv ? "bg-[#D6A653] font-medium text-black" : "text-white/60 hover:text-white"}`}>
              {iv === "month" ? "Monthly" : "Annual"}
            </button>
          ))}
        </div>
        {yr ? <span className="text-xs text-[#D6A653]" data-testid="landing-save-badge">Save {pricing.pro_annual_savings_pct}% annually</span> : null}
        <select value={market || ""} onChange={(e) => changeMarket(e.target.value)} data-testid="landing-market"
          className="rounded-full border border-white/12 bg-white/5 px-3 py-1.5 text-sm text-white/80">
          {data.markets.map((m) => <option key={m} value={m} className="bg-[#0D1014]">{m}</option>)}
        </select>
      </div>

      <div className="mt-10 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        {plans.map((p, i) => {
          const Icon = p.icon;
          return (
            <motion.div key={p.id} initial={{ opacity: 0, y: 22 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.2 }}
              transition={{ duration: 0.5, delay: i * 0.06 }}
              className={`lp-card relative flex flex-col rounded-[18px] p-5 ${p.popular ? "ring-1 ring-[#D6A653]/50" : ""}`} data-testid={`landing-plan-${p.id}`}>
              {p.popular ? <span className="absolute -top-2.5 left-5 rounded-full bg-[#D6A653] px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-black">Most popular</span> : null}
              <div className="flex items-center gap-2"><Icon className="h-4 w-4 text-[#D6A653]" /><h3 className="text-base font-semibold text-white">{p.name}</h3></div>
              <p className="mt-1 text-xs text-[#8A8F97]">{p.tagline}</p>
              <div className="mt-4 flex items-end gap-1">
                <span className="text-3xl font-light text-white" data-testid={`landing-plan-${p.id}-price`}>{p.price}</span>
                {p.unit ? <span className="mb-1 text-xs text-white/45">{p.unit}</span> : null}
              </div>
              {p.save ? <span className="mt-1 text-[11px] font-medium text-[#D6A653]">{p.save}</span> : <span className="mt-1 h-[15px]" />}
              <ul className="mt-4 flex-1 space-y-2">
                {p.features.map((f, k) => (<li key={k} className="flex items-start gap-2 text-[13px] text-white/65"><Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#D6A653]" /> {f}</li>))}
              </ul>
              <Link to={p.to} data-testid={`landing-plan-${p.id}-cta`}
                className={`mt-5 inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium transition-all ${p.popular ? "lp-btn-gold lp-press" : "lp-btn-ghost lp-press"}`}>
                {p.cta} <ArrowRight className="h-4 w-4" />
              </Link>
            </motion.div>
          );
        })}
      </div>

      {data.referral?.enabled ? (
        <p className="mt-8 text-center text-[13px] text-[#8A8F97]" data-testid="landing-referral-note">
          🎁 Refer friends — they get {data.referral.referred_discount_month_pct}% off and you earn up to {data.referral.max_reward_discount_pct}% off your bill.
        </p>
      ) : null}
    </section>
  );
}
