import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useLocale } from "@/i18n/useLocale";
import { OwnerNav } from "@/components/admin/OwnerNav";
import { toast } from "sonner";
import { Loader2, Check, Crown, Users, Sparkles, ScanLine, CreditCard, Zap, Building2, ShieldCheck } from "lucide-react";

const GOLD = "#D6A653";

const STATUS_LABEL = {
  trialing: "Trial active",
  active: "Active",
  cancel_at_period_end: "Cancels at period end",
  past_due: "Payment past due",
  cancelled: "Cancelled",
  trial_expired: "Trial ended",
};

const fmtMoney = (sym, n) => `${sym}${Number(n).toFixed(2).replace(/\.00$/, "")}`;
const daysLeft = (iso) => {
  if (!iso) return null;
  const ms = new Date(iso).getTime() - Date.now();
  return Math.max(0, Math.ceil(ms / 86400000));
};

const UsageMeter = ({ icon: Icon, label, used, limit, testid }) => {
  const unlimited = limit == null || limit >= 100000;
  const pct = unlimited ? 0 : Math.min(100, Math.round((used / Math.max(1, limit)) * 100));
  const over = !unlimited && used >= limit;
  return (
    <div className="rounded-2xl border border-white/10 bg-[#0A0B0D] p-4" data-testid={testid}>
      <div className="mb-2 flex items-center justify-between">
        <span className="flex items-center gap-2 text-xs text-white/55"><Icon className="h-4 w-4 text-[#D6A653]" /> {label}</span>
        <span className={`text-xs font-medium ${over ? "text-red-400" : "text-white/70"}`}>{used}{unlimited ? "" : ` / ${limit}`}</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-white/[0.06]">
        <div className="h-full rounded-full transition-all" style={{ width: unlimited ? "12%" : `${pct}%`, background: over ? "#ef4444" : "linear-gradient(90deg,#8A6A2B,#D6A653)" }} />
      </div>
      {unlimited ? <p className="mt-1.5 text-[10px] uppercase tracking-wide text-white/30">Unlimited</p> : null}
    </div>
  );
};

export default function Billing() {
  const { user } = useAuth();
  const { t } = useLocale();
  const navigate = useNavigate();
  const [data, setData] = useState(undefined);
  const [ref, setRef] = useState(null);
  const [interval, setInterval] = useState("year");
  const [market, setMarket] = useState("USD");
  const [busy, setBusy] = useState("");

  const load = (mk) => {
    api.get(`/billing${mk ? `?market=${mk}` : ""}`).then(({ data }) => {
      setData(data);
      if (!mk && data?.commercial?.pricing?.market) setMarket(data.commercial.pricing.market);
    }).catch(() => setData(null));
  };
  useEffect(() => { load(); api.get("/referral").then(({ data }) => setRef(data)).catch(() => {}); /* eslint-disable-next-line */ }, []);
  useEffect(() => { if (data) load(market); /* eslint-disable-next-line */ }, [market]);

  const c = data?.commercial;
  const pricing = c?.pricing;
  const sym = pricing?.symbol || "$";
  const currentPlan = data?.plan;
  const isTrial = data?.status === "trialing";
  const locked = data && !data.active;
  const canManage = user?.role === "SUPER_ADMIN" || currentPlan; // ws owners land here; server enforces

  const plans = useMemo(() => {
    if (!c) return [];
    const yr = interval === "year";
    const team = c.plans.team;
    const proPrice = yr ? pricing.pro_year : pricing.pro_month;
    const teamPrice = yr ? pricing.team_seat_year : pricing.team_seat_month;
    return [
      {
        id: "trial", name: "Trial", icon: Sparkles, tagline: `${c.trial.days}-day free trial · no card required`,        price: fmtMoney(sym, 0), unit: "", features: ["1 profile card", "Full analytics (1 month)", "10 AI follow-ups (total)", "10 card scans (total)", "Lead capture & CRM"],
      },
      {
        id: "pro", name: "Pro", icon: Crown, popular: true, tagline: "For professionals",
        price: fmtMoney(sym, proPrice), unit: yr ? "/year" : "/month",
        save: yr ? `Save ${pricing.pro_annual_savings_pct}%` : null,
        features: ["Up to 3 cards", "Full analytics (12 months)", "100 AI follow-ups / month", "50 card scans / month", "Remove ARIADNI branding", "Digital wallet passes"],
      },
      {
        id: "team", name: "Team", icon: Users, tagline: `Min ${team.min_seats} seats`,
        price: fmtMoney(sym, teamPrice), unit: yr ? "/seat / year" : "/seat / month",
        save: yr ? `Save ${pricing.team_annual_savings_pct}%` : null,
        features: ["Unlimited cards", "Team dashboard & roles", "Locked company branding", "100 AI / user / month", "100 scans / user / month", "API access & custom domain"],
      },
      {
        id: "enterprise", name: "Enterprise", icon: Building2, tagline: "For organizations",
        price: "Custom", unit: "", features: ["Everything in Team", "White-label", "SSO / SAML (roadmap)", "Dedicated support", "Custom contracts & invoicing"],
        custom: true,
      },
    ];
  }, [c, interval, pricing, sym]);

  const subscribe = async (planId) => {
    if (planId === "enterprise") {
      window.location.href = "mailto:sales@tappresence.com?subject=Enterprise%20plan%20enquiry";
      return;
    }
    setBusy(planId);
    try {
      const seats = planId === "team" ? (c.plans.team.min_seats || 3) : 1;
      const { data: res } = await api.post("/billing/subscribe", { plan: planId, interval, seats, market });
      toast.success(`You're on ${res.subscription.plan.toUpperCase()} — activated`);
      load(market);
    } catch (e) {
      const st = e?.response?.status;
      if (st === 402) toast.error(e?.response?.data?.detail || "Payment provider not connected yet.");
      else if (st === 403) toast.error("Only the workspace owner can change the plan.");
      else toast.error("Could not update plan. Try again.");
    } finally { setBusy(""); }
  };

  const cancel = async () => {
    if (!window.confirm("Cancel subscription at the end of the current period? Your data stays intact.")) return;
    setBusy("cancel");
    try { await api.post("/billing/cancel"); toast.success("Subscription set to cancel at period end."); load(market); }
    catch { toast.error("Could not cancel."); }
    finally { setBusy(""); }
  };

  return (
    <div className="aria-dark relative min-h-screen bg-[#050607] text-white" style={{ fontFamily: "'Outfit', sans-serif" }} data-testid="billing-page">
      <div className="grain-overlay" style={{ opacity: 0.04 }} />
      <OwnerNav active="billing" />
      <main className="relative mx-auto max-w-6xl px-4 py-8 sm:px-8">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="flex items-center gap-2 text-2xl font-light tracking-tight text-white"><CreditCard className="h-5 w-5 text-[#D6A653]" /> {t("billing.title")}</h2>
            <p className="mt-1 text-sm text-white/45">{t("billing.subtitle")}</p>
          </div>
          {/* market selector */}
          {c ? (
            <select value={market} onChange={(e) => setMarket(e.target.value)} data-testid="billing-market" className="rounded-full border border-white/12 bg-white/5 px-3 py-1.5 text-sm text-white/80">
              {c.markets.map((m) => <option key={m} value={m} className="bg-[#0A0B0D]">{m}</option>)}
            </select>
          ) : null}
        </div>

        {data === undefined ? (
          <div className="flex justify-center py-24"><Loader2 className="h-6 w-6 animate-spin text-[#D6A653]" /></div>
        ) : data === null ? (
          <div className="mt-8 rounded-2xl border border-dashed border-white/12 py-24 text-center text-white/55">{t("billing.loadError")}</div>
        ) : (
          <>
            {/* current status banner */}
            <div className={`mt-6 flex flex-wrap items-center justify-between gap-4 rounded-2xl border p-5 ${locked ? "border-red-500/30 bg-red-500/[0.06]" : "border-[#D6A653]/25 bg-[#D6A653]/[0.06]"}`} data-testid="billing-status">
              <div className="flex items-center gap-3">
                <ShieldCheck className={`h-6 w-6 ${locked ? "text-red-400" : "text-[#D6A653]"}`} />
                <div>
                  <p className="text-sm text-white/55">{t("billing.currentPlan")}</p>
                  <p className="text-lg font-medium capitalize text-white" data-testid="billing-current-plan">
                    {currentPlan} · <span className={locked ? "text-red-400" : "text-[#D6A653]"}>{STATUS_LABEL[data.status] || data.status}</span>
                  </p>
                </div>
              </div>
              <div className="text-right">
                {isTrial && data.trial_ends_at ? (
                  <p className="text-sm text-white/70" data-testid="billing-trial-days"><span className="text-xl font-light text-[#D6A653]">{daysLeft(data.trial_ends_at)}</span> {t("billing.daysLeft")}</p>
                ) : data.current_period_end ? (
                  <p className="text-xs text-white/45">{t("billing.renews")} {new Date(data.current_period_end).toLocaleDateString()}</p>
                ) : null}
                {data.active && (currentPlan === "pro" || currentPlan === "team") && data.status !== "cancel_at_period_end" ? (
                  <button onClick={cancel} disabled={busy === "cancel"} data-testid="billing-cancel" className="mt-2 text-xs text-white/45 underline underline-offset-2 hover:text-white/70">{t("billing.cancel")}</button>
                ) : null}
              </div>
            </div>

            {locked ? (
              <div className="mt-3 rounded-xl border border-red-500/20 bg-red-500/[0.04] px-4 py-3 text-sm text-red-200/80" data-testid="billing-locked-note">
                {t("billing.lockedNote")}
              </div>
            ) : null}

            {/* usage */}
            <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-3" data-testid="billing-usage">
              <UsageMeter icon={CreditCard} label={t("billing.usageCards")} used={data.usage.cards.used} limit={data.usage.cards.limit} testid="usage-cards" />
              <UsageMeter icon={Sparkles} label={t("billing.usageAi")} used={data.usage.ai.used} limit={data.usage.ai.limit} testid="usage-ai" />
              <UsageMeter icon={ScanLine} label={t("billing.usageScanner")} used={data.usage.scanner.used} limit={data.usage.scanner.limit} testid="usage-scanner" />
            </div>

            {/* interval toggle */}
            <div className="mt-8 flex items-center justify-center gap-2">
              <div className="inline-flex rounded-full border border-white/12 bg-white/5 p-1" data-testid="billing-interval-toggle">
                {["month", "year"].map((iv) => (
                  <button key={iv} onClick={() => setInterval(iv)} data-testid={`interval-${iv}`}
                    className={`rounded-full px-4 py-1.5 text-sm transition-all ${interval === iv ? "bg-[#D6A653] font-medium text-black" : "text-white/60 hover:text-white"}`}>
                    {iv === "month" ? t("billing.monthly") : t("billing.annual")}
                  </button>
                ))}
              </div>
              {interval === "year" ? <span className="text-xs text-[#D6A653]">{t("billing.saveBadge", { pct: pricing.pro_annual_savings_pct })}</span> : null}
            </div>

            {/* plan comparison */}
            <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4" data-testid="billing-plans">
              {plans.map((p) => {
                const isCurrent = currentPlan === p.id && data.active;
                const Icon = p.icon;
                return (
                  <div key={p.id} data-testid={`plan-${p.id}`}
                    className={`relative flex flex-col rounded-2xl border p-5 transition-all ${p.popular ? "border-[#D6A653]/50 bg-[#D6A653]/[0.05]" : "border-white/10 bg-[#0A0B0D]"} ${isCurrent ? "ring-1 ring-[#D6A653]/60" : ""}`}>
                    {p.popular ? <span className="absolute -top-2.5 left-5 rounded-full bg-[#D6A653] px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-black">{t("billing.popular")}</span> : null}
                    <div className="flex items-center gap-2"><Icon className="h-4 w-4 text-[#D6A653]" /><h3 className="text-base font-medium text-white">{p.name}</h3></div>
                    <p className="mt-1 text-xs text-white/40">{p.tagline}</p>
                    <div className="mt-4 flex items-end gap-1">
                      <span className="text-3xl font-light text-white" data-testid={`plan-${p.id}-price`}>{p.price}</span>
                      {p.unit ? <span className="mb-1 text-xs text-white/45">{p.unit}</span> : null}
                    </div>
                    {p.save ? <span className="mt-1 text-[11px] font-medium text-[#D6A653]">{p.save}</span> : <span className="mt-1 h-[15px]" />}
                    <ul className="mt-4 flex-1 space-y-2">
                      {p.features.map((f, i) => (
                        <li key={i} className="flex items-start gap-2 text-[13px] text-white/65"><Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#D6A653]" /> {f}</li>
                      ))}
                    </ul>
                    <button
                      disabled={isCurrent || busy === p.id || p.id === "trial"}
                      onClick={() => subscribe(p.id)}
                      data-testid={`plan-${p.id}-cta`}
                      className={`mt-5 flex items-center justify-center gap-2 rounded-full px-4 py-2.5 text-sm font-medium transition-all disabled:opacity-40 ${p.popular || (locked && p.id === "pro") ? "bg-[#D6A653] text-black hover:brightness-110" : "border border-white/15 text-white hover:border-[#D6A653]/50"}`}>
                      {busy === p.id ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                      {isCurrent ? t("billing.currentPlanBtn") : p.id === "trial" ? t("billing.trialBtn") : p.custom ? t("billing.contactSales") : locked ? t("billing.reactivate") : t("billing.upgradeTo", { plan: p.name })}
                    </button>
                  </div>
                );
              })}
            </div>

            {/* referral engine */}
            {ref?.enabled ? (
              <div className="mt-8 rounded-2xl border border-white/10 bg-[#0A0B0D] p-5" data-testid="billing-referral">
                <div className="flex items-start gap-3">
                  <Zap className="mt-0.5 h-5 w-5 shrink-0 text-[#D6A653]" />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-white">{t("billing.referralTitle")}</p>
                    <p className="mt-1 text-xs text-white/50">{t("billing.referralDesc", { referred: ref.config.referred_discount_month_pct, reward: ref.config.referrer_reward_pct, max: ref.config.max_reward_discount_pct })}</p>
                    <div className="mt-4 flex flex-wrap items-center gap-2">
                      <code className="rounded-lg border border-[#D6A653]/30 bg-[#D6A653]/[0.08] px-3 py-1.5 text-sm font-medium tracking-wider text-[#D6A653]" data-testid="referral-code">{ref.code}</code>
                      <button data-testid="referral-copy" onClick={() => { navigator.clipboard.writeText(ref.share_url); toast.success(t("home.linkCopied")); }}
                        className="rounded-full border border-white/15 px-3.5 py-1.5 text-xs text-white/80 transition-colors hover:border-[#D6A653]/50">{t("billing.copyLink")}</button>
                      <span className="text-xs text-white/40" data-testid="referral-count">{t("billing.referredCount", { count: ref.referred_count })}</span>
                    </div>
                    {ref.reward && (ref.reward.applied_pct > 0 || ref.reward.queued_pct > 0) ? (
                      <p className="mt-3 text-xs text-[#D6A653]" data-testid="referral-reward">
                        {t("billing.rewardApplied", { pct: ref.reward.applied_pct })}
                        {ref.reward.queued_pct > 0 ? ` · ${t("billing.rewardQueued", { pct: ref.reward.queued_pct })}` : ""}
                      </p>
                    ) : null}
                    {data.discount && (data.discount.referred_month_pct > 0) ? (
                      <p className="mt-2 text-xs text-white/55" data-testid="referral-referred-discount">{t("billing.referredYou", { pct: data.discount.referred_month_pct })}</p>
                    ) : null}
                  </div>
                </div>
              </div>
            ) : null}

            {data.demo_billing ? (
              <p className="mt-6 text-center text-[11px] text-white/30" data-testid="billing-demo-note">{t("billing.demoNote")}</p>
            ) : null}
          </>
        )}
      </main>
    </div>
  );
}
