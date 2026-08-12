import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { OwnerNav } from "@/components/admin/OwnerNav";
import { toast } from "sonner";
import { Loader2, DollarSign, Sparkles, Users, Gift, Globe, Save, Crown } from "lucide-react";

const Field = ({ label, value, onChange, type = "number", step = "0.01", suffix, testid, min }) => (
  <label className="block">
    <span className="mb-1 block text-[11px] uppercase tracking-wide text-white/40">{label}</span>
    <div className="flex items-center rounded-xl border border-white/12 bg-white/5 px-3">
      <input type={type} step={step} min={min} value={value ?? ""} onChange={(e) => onChange(type === "number" ? e.target.value : e.target.value)}
        data-testid={testid} className="w-full bg-transparent py-2 text-sm text-white outline-none" />
      {suffix ? <span className="pl-2 text-xs text-white/40">{suffix}</span> : null}
    </div>
  </label>
);

const Toggle = ({ label, checked, onChange, testid }) => (
  <button onClick={() => onChange(!checked)} data-testid={testid} className="flex items-center gap-2.5">
    <span className={`relative h-5 w-9 rounded-full transition-colors ${checked ? "bg-[#D6A653]" : "bg-white/15"}`}>
      <span className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-all ${checked ? "left-[18px]" : "left-0.5"}`} />
    </span>
    <span className="text-sm text-white/75">{label}</span>
  </button>
);

const Card = ({ icon: Icon, title, children, testid }) => (
  <section className="rounded-2xl border border-white/10 bg-[#0A0B0D] p-5" data-testid={testid}>
    <h3 className="mb-4 flex items-center gap-2 text-sm font-medium text-white"><Icon className="h-4 w-4 text-[#D6A653]" /> {title}</h3>
    {children}
  </section>
);

export default function CommercialSettings() {
  const { user } = useAuth();
  const isSuper = user?.role === "SUPER_ADMIN";
  const [cfg, setCfg] = useState(undefined);
  const [markets, setMarkets] = useState([]);
  const [resolved, setResolved] = useState({});
  const [demo, setDemo] = useState(false);
  const [saving, setSaving] = useState(false);

  const loadResolved = () => api.get("/commercial/pricing").then(({ data }) => setResolved(data.resolved_all || {})).catch(() => {});

  useEffect(() => {
    if (!isSuper) { setCfg(null); return; }
    api.get("/admin/commercial").then(({ data }) => { setCfg(data.config); setMarkets(data.markets); setDemo(data.demo_billing); }).catch(() => setCfg(null));
    loadResolved();
  }, [isSuper]);

  const isManual = (m) => (cfg?.manual_price_markets || []).includes(m);
  const setManual = (m, on) => setPath((n) => {
    const cur = new Set(n.manual_price_markets || []);
    if (on) { cur.add(m); n.regional_pricing[m] = { ...(resolved[m] || n.regional_pricing[m] || {}) }; }
    else cur.delete(m);
    n.manual_price_markets = [...cur];
  });

  const setPath = (fn) => setCfg((prev) => { const next = structuredClone(prev); fn(next); return next; });
  const num = (v) => (v === "" || v == null ? 0 : Number(v));

  const save = async () => {
    setSaving(true);
    try {
      const payload = {
        trial: { enabled: !!cfg.trial.enabled, days: parseInt(cfg.trial.days) || 0 },
        plans: {
          pro: { price_month: num(cfg.plans.pro.price_month), price_year: num(cfg.plans.pro.price_year), annual_discount_pct: num(cfg.plans.pro.annual_discount_pct) },
          team: { price_seat_month: num(cfg.plans.team.price_seat_month), price_seat_year: num(cfg.plans.team.price_seat_year), min_seats: parseInt(cfg.plans.team.min_seats) || 1, annual_discount_pct: num(cfg.plans.team.annual_discount_pct) },
        },
        referral: {
          enabled: !!cfg.referral.enabled,
          referred_discount_month_pct: num(cfg.referral.referred_discount_month_pct),
          referred_discount_year_pct: num(cfg.referral.referred_discount_year_pct),
          referrals_per_reward: parseInt(cfg.referral.referrals_per_reward) || 5,
          reward_months: parseInt(cfg.referral.reward_months) || 1,
        },
        default_market: cfg.default_market,
        regional_pricing: cfg.regional_pricing,
        fx_rates: cfg.fx_rates,
        manual_price_markets: cfg.manual_price_markets || [],
      };
      const { data } = await api.put("/admin/commercial", payload);
      setCfg(data.config);
      await loadResolved();
      toast.success("Commercial configuration saved");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Could not save configuration");
    } finally { setSaving(false); }
  };

  return (
    <div className="aria-dark relative min-h-screen bg-[#050607] text-white" style={{ fontFamily: "'Outfit', sans-serif" }} data-testid="commercial-settings-page">
      <div className="grain-overlay" style={{ opacity: 0.04 }} />
      <OwnerNav active="command" />
      <main className="relative mx-auto max-w-5xl px-4 py-8 sm:px-8">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="flex items-center gap-2 text-2xl font-light tracking-tight text-white"><DollarSign className="h-5 w-5 text-[#D6A653]" /> Commercial & Pricing</h2>
            <p className="mt-1 text-sm text-white/45">Manage pricing, trial, referral and regional configuration — no code changes.</p>
          </div>
          {cfg ? (
            <button onClick={save} disabled={saving} data-testid="commercial-save" className="flex items-center gap-2 rounded-full bg-[#D6A653] px-5 py-2.5 text-sm font-medium text-black transition-all hover:brightness-110 disabled:opacity-50">
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />} Save changes
            </button>
          ) : null}
        </div>

        {!isSuper ? (
          <div className="mt-8 rounded-2xl border border-dashed border-white/12 py-24 text-center text-white/55" data-testid="commercial-denied">Super admin only.</div>
        ) : cfg === undefined ? (
          <div className="flex justify-center py-24"><Loader2 className="h-6 w-6 animate-spin text-[#D6A653]" /></div>
        ) : cfg === null ? (
          <div className="mt-8 rounded-2xl border border-dashed border-white/12 py-24 text-center text-white/55">Could not load configuration.</div>
        ) : (
          <div className="mt-6 space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <Card icon={Sparkles} title="Trial" testid="cfg-trial">
                <div className="space-y-4">
                  <Toggle label="Trial enabled (no card required)" checked={cfg.trial.enabled} onChange={(v) => setPath((n) => { n.trial.enabled = v; })} testid="cfg-trial-enabled" />
                  <Field label="Trial duration (days)" type="number" step="1" min="0" value={cfg.trial.days} onChange={(v) => setPath((n) => { n.trial.days = v; })} suffix="days" testid="cfg-trial-days" />
                </div>
              </Card>

              <Card icon={Crown} title="Pro plan" testid="cfg-pro">
                <div className="grid grid-cols-2 gap-3">
                  <Field label="Monthly price" value={cfg.plans.pro.price_month} onChange={(v) => setPath((n) => { n.plans.pro.price_month = v; })} testid="cfg-pro-month" />
                  <Field label="Annual price" value={cfg.plans.pro.price_year} onChange={(v) => setPath((n) => { n.plans.pro.price_year = v; })} testid="cfg-pro-year" />
                  <Field label="Annual saving" step="1" value={cfg.plans.pro.annual_discount_pct} onChange={(v) => setPath((n) => { n.plans.pro.annual_discount_pct = v; })} suffix="%" testid="cfg-pro-discount" />
                </div>
              </Card>

              <Card icon={Users} title="Team plan" testid="cfg-team">
                <div className="grid grid-cols-2 gap-3">
                  <Field label="Monthly / seat" value={cfg.plans.team.price_seat_month} onChange={(v) => setPath((n) => { n.plans.team.price_seat_month = v; })} testid="cfg-team-month" />
                  <Field label="Annual / seat" value={cfg.plans.team.price_seat_year} onChange={(v) => setPath((n) => { n.plans.team.price_seat_year = v; })} testid="cfg-team-year" />
                  <Field label="Minimum seats" step="1" min="1" value={cfg.plans.team.min_seats} onChange={(v) => setPath((n) => { n.plans.team.min_seats = v; })} testid="cfg-team-minseats" />
                  <Field label="Annual saving" step="1" value={cfg.plans.team.annual_discount_pct} onChange={(v) => setPath((n) => { n.plans.team.annual_discount_pct = v; })} suffix="%" testid="cfg-team-discount" />
                </div>
              </Card>

              <Card icon={Gift} title="Referral program" testid="cfg-referral">
                <div className="space-y-3">
                  <Toggle label="Referral program enabled" checked={cfg.referral.enabled} onChange={(v) => setPath((n) => { n.referral.enabled = v; })} testid="cfg-referral-enabled" />
                  <div className="grid grid-cols-2 gap-3">
                    <Field label="Referred discount (monthly)" step="1" value={cfg.referral.referred_discount_month_pct} onChange={(v) => setPath((n) => { n.referral.referred_discount_month_pct = v; })} suffix="%" testid="cfg-ref-referred-month" />
                    <Field label="Referred discount (annual)" step="1" value={cfg.referral.referred_discount_year_pct} onChange={(v) => setPath((n) => { n.referral.referred_discount_year_pct = v; })} suffix="%" testid="cfg-ref-referred-year" />
                    <Field label="Qualified paid referrals per reward" step="1" value={cfg.referral.referrals_per_reward} onChange={(v) => setPath((n) => { n.referral.referrals_per_reward = v; })} testid="cfg-ref-per-reward" />
                    <Field label="Free months per reward" step="1" value={cfg.referral.reward_months} onChange={(v) => setPath((n) => { n.referral.reward_months = v; })} testid="cfg-ref-reward-months" />
                  </div>
                </div>
              </Card>
            </div>

            <Card icon={Globe} title="Regional pricing" testid="cfg-regional">
              <div className="mb-4 flex flex-wrap items-center gap-3">
                <span className="text-xs text-white/45">Default market</span>
                <select value={cfg.default_market} onChange={(e) => setPath((n) => { n.default_market = e.target.value; })} data-testid="cfg-default-market" className="rounded-full border border-white/12 bg-white/5 px-3 py-1.5 text-sm text-white/80">
                  {markets.map((m) => <option key={m} value={m} className="bg-[#0A0B0D]">{m}</option>)}
                </select>
                <span className="text-[11px] text-white/30">USD is the base. Other currencies auto-convert via FX unless marked Manual.</span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[720px] text-sm">
                  <thead><tr className="text-left text-[11px] uppercase tracking-wide text-white/35">
                    <th className="pb-2 pr-3">Market</th><th className="pb-2 pr-3">Source</th><th className="pb-2 pr-3">FX ×USD</th><th className="pb-2 pr-3">Pro / mo</th><th className="pb-2 pr-3">Pro / yr</th><th className="pb-2 pr-3">Team seat / mo</th><th className="pb-2">Team seat / yr</th>
                  </tr></thead>
                  <tbody>
                    {markets.map((m) => {
                      const base = m === "USD";
                      const manual = base || isManual(m);
                      const editable = base || isManual(m);
                      const stored = cfg.regional_pricing[m] || {};
                      const shown = editable ? stored : (resolved[m] || {});
                      const upd = (k, v) => setPath((n) => { n.regional_pricing[m] = { ...(n.regional_pricing[m] || {}), [k]: v }; });
                      const updFx = (v) => setPath((n) => { n.fx_rates = { ...(n.fx_rates || {}), [m]: Number(v) }; });
                      return (
                        <tr key={m} className="border-t border-white/[0.06]" data-testid={`cfg-region-${m}`}>
                          <td className="py-2 pr-3 font-medium text-white/80">{m}</td>
                          <td className="py-2 pr-3">
                            {base ? (
                              <span className="rounded-full bg-[#D6A653]/15 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-[#D6A653]" data-testid={`cfg-src-${m}`}>Base</span>
                            ) : (
                              <button onClick={() => setManual(m, !isManual(m))} data-testid={`cfg-manual-toggle-${m}`}
                                className={`rounded-full px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider ${isManual(m) ? "bg-sky-500/15 text-sky-300" : "bg-white/10 text-white/55"}`}>
                                {isManual(m) ? "Manual" : "Auto"}
                              </button>
                            )}
                          </td>
                          <td className="py-2 pr-3">
                            <input type="number" step="0.0001" disabled={base} value={base ? 1 : (cfg.fx_rates?.[m] ?? "")} onChange={(e) => updFx(e.target.value)} data-testid={`cfg-fx-${m}`}
                              className="w-20 rounded-lg border border-white/12 bg-white/5 px-2 py-1.5 text-sm text-white outline-none focus:border-[#D6A653]/50 disabled:opacity-40" />
                          </td>
                          {["pro_month", "pro_year", "team_seat_month", "team_seat_year"].map((k) => (
                            <td key={k} className="py-2 pr-3">
                              <input type="number" step="0.01" disabled={!editable} value={shown[k] ?? ""} onChange={(e) => upd(k, Number(e.target.value))} data-testid={`cfg-${m}-${k}`}
                                className="w-24 rounded-lg border border-white/12 bg-white/5 px-2 py-1.5 text-sm text-white outline-none focus:border-[#D6A653]/50 disabled:opacity-40" />
                            </td>
                          ))}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              <p className="mt-3 text-[11px] text-white/30">Auto markets recompute from USD whenever you change the USD base or their FX rate. Switch a market to Manual to set a fixed local price (e.g. AED 369.99); manual prices are preserved when USD changes.</p>
            </Card>

            <p className="text-center text-[11px] text-white/30" data-testid="cfg-demo-note">
              {demo ? "Demo activation is ENABLED (ALLOW_DEMO_BILLING). Upgrades activate without a real payment. Disable and connect a provider before production." : "Demo activation is disabled — a payment provider is authoritative."}
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
