import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Check, Crown, Users, Sparkles, Building2, ArrowRight } from "lucide-react";
import { api } from "@/lib/api";
import { getPreferredMarket, saveMarketPreference } from "@/lib/market";
import { useLocale } from "@/i18n/useLocale";

const fmtMoney = (sym, n) => `${sym}${Number(n).toFixed(2).replace(/\.00$/, "")}`;

// Public pricing — resolved from the SAME authoritative /api/commercial/pricing config
// (Super Admin Commercial → Billing → Public site all share one source of truth).
export default function PricingSection() {
  const { t } = useLocale();
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
    const tt = data.plans, tr = data.trial;
    return [
      { id: "trial", name: t("landing.pricing.trialName"), icon: Sparkles, price: fmtMoney(sym, 0), unit: "", tagline: t("landing.pricing.trialTag", { days: tr.days }),
        features: t("landing.pricing.featTrial", { returnObjects: true }), cta: t("landing.pricing.startFree"), to: "/register" },
      { id: "pro", name: t("landing.pricing.proName"), icon: Crown, popular: true, tagline: t("landing.pricing.proTag"),
        price: fmtMoney(sym, yr ? pricing.pro_year : pricing.pro_month), unit: yr ? t("landing.pricing.perYear") : t("landing.pricing.perMonth"),
        save: yr ? t("landing.pricing.save", { pct: pricing.pro_annual_savings_pct }) : null,
        features: t("landing.pricing.featPro", { returnObjects: true }), cta: t("landing.pricing.getPro"), to: "/register" },
      { id: "team", name: t("landing.pricing.teamName"), icon: Users, tagline: t("landing.pricing.teamTag", { n: tt.team.min_seats }),
        price: fmtMoney(sym, yr ? pricing.team_seat_year : pricing.team_seat_month), unit: yr ? t("landing.pricing.perSeatYear") : t("landing.pricing.perSeatMonth"),
        save: yr ? t("landing.pricing.save", { pct: pricing.team_annual_savings_pct }) : null,
        features: t("landing.pricing.featTeam", { returnObjects: true }), cta: t("landing.pricing.startTeam"), to: "/register?intent=team" },
      { id: "enterprise", name: t("landing.pricing.entName"), icon: Building2, price: t("landing.pricing.custom"), unit: "", tagline: t("landing.pricing.entTag"),
        features: t("landing.pricing.featEnt", { returnObjects: true }), cta: t("landing.pricing.contactSales"), to: "/register?intent=team" },
    ];
  }, [data, interval, pricing, sym, yr, t]);

  // SEO structured data reflecting the SAME resolved config
  const jsonLd = useMemo(() => {
    if (!data) return null;
    const offers = [
      { name: "Pro Monthly", price: pricing.pro_month }, { name: "Pro Annual", price: pricing.pro_year },
      { name: "Team Seat Monthly", price: pricing.team_seat_month }, { name: "Team Seat Annual", price: pricing.team_seat_year },
    ].map((o) => ({ "@type": "Offer", name: o.name, price: o.price, priceCurrency: pricing.market }));
    return { "@context": "https://schema.org", "@type": "Product", name: "TapPresence", description: "Digital business cards, NFC, AI follow-up and analytics.", offers };
  }, [data, pricing]);

  if (!data) return null;

  return (
    <section id="pricing" className="mx-auto max-w-[1320px] px-5 py-16 sm:px-8 lg:px-12 lg:py-24" data-testid="landing-pricing">
      {jsonLd ? <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} /> : null}
      <div className="text-center">
        <p className="lp-eyebrow text-[12px]">{t("landing.pricing.eyebrow")}</p>
        <h2 className="mt-3 font-semibold tracking-tight text-white" style={{ fontSize: "clamp(26px,3.4vw,36px)" }}>{t("landing.pricing.title")}</h2>
        <p className="mx-auto mt-3 max-w-[520px] text-[15px] text-[#8A8F97]">{t("landing.pricing.subtitle", { days: data.trial.days })}</p>
      </div>

      <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
        <div className="inline-flex rounded-full border border-white/12 bg-white/5 p-1" data-testid="landing-interval-toggle">
          {["month", "year"].map((iv) => (
            <button key={iv} onClick={() => setInterval(iv)} data-testid={`landing-interval-${iv}`}
              className={`rounded-full px-4 py-1.5 text-sm transition-all ${interval === iv ? "bg-[#D6A653] font-medium text-black" : "text-white/60 hover:text-white"}`}>
              {iv === "month" ? t("landing.pricing.monthly") : t("landing.pricing.annual")}
            </button>
          ))}
        </div>
        {yr ? <span className="text-xs text-[#D6A653]" data-testid="landing-save-badge">{t("landing.pricing.saveAnnually", { pct: pricing.pro_annual_savings_pct })}</span> : null}
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
              {p.popular ? <span className="absolute -top-2.5 left-5 rounded-full bg-[#D6A653] px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-black">{t("landing.pricing.mostPopular")}</span> : null}
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

      <p className="mt-4 text-center text-[12px] text-white/45" data-testid="landing-tax-note">{t("billing.taxNote")}</p>

      {data.referral?.enabled ? (
        <p className="mt-8 text-center text-[13px] text-[#8A8F97]" data-testid="landing-referral-note">
          {t("landing.pricing.referralNote", { referred: data.referral.referred_discount_month_pct, max: data.referral.max_reward_discount_pct })}
        </p>
      ) : null}
    </section>
  );
}
