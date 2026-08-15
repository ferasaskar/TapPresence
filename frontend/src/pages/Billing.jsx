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
const fmtLong = (iso) => (iso ? new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" }) : "");
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
  const [featureUsage, setFeatureUsage] = useState([]);
  const [invoices, setInvoices] = useState(undefined);
  const [interval, setInterval] = useState("year");
  const [market, setMarket] = useState("USD");
  const [busy, setBusy] = useState("");

  const load = (mk) => {
    api.get(`/billing${mk ? `?market=${mk}` : ""}`).then(({ data }) => {
      setData(data);
      if (!mk && data?.commercial?.pricing?.market) setMarket(data.commercial.pricing.market);
    }).catch(() => setData(null));
  };
  useEffect(() => { load(); api.get("/referral").then(({ data }) => setRef(data)).catch(() => {}); api.get("/usage/me").then(({ data }) => setFeatureUsage(data.items || [])).catch(() => {}); api.get("/billing/invoices").then(({ data }) => setInvoices(data.invoices || [])).catch(() => setInvoices([])); /* eslint-disable-next-line */ }, []);
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
        features: ["Up to 3 cards", "Full analytics (12 months)", "100 AI follow-ups / month", "50 card scans / month", "Remove TapPresence branding", "Digital wallet passes"],
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
      const { data: res } = await api.post("/billing/checkout", { plan: planId, interval, seats, market, origin_url: window.location.origin });
      window.location.href = res.checkout_url;
    } catch (e) {
      const st = e?.response?.status;
      if (st === 503) toast.error("Payments are not available yet. Please try again shortly.");
      else if (st === 403) toast.error("Only the workspace owner can change the plan.");
      else toast.error(e?.response?.data?.detail || "Could not start checkout. Try again.");
      setBusy("");
    }
  };

  const cancel = async () => {
    if (!window.confirm("Cancel subscription at the end of the current period? Your data stays intact.")) return;
    setBusy("cancel");
    try { await api.post("/billing/cancel"); toast.success("Subscription set to cancel at period end."); load(market); }
    catch { toast.error("Could not cancel."); }
    finally { setBusy(""); }
  };

  const resume = async () => {
    setBusy("resume");
    try { await api.post("/billing/resume"); toast.success(t("billing.resumed")); load(market); }
    catch (e) { toast.error(e?.response?.data?.detail || "Could not resume subscription."); }
    finally { setBusy(""); }
  };

  const openPortal = async () => {
    setBusy("portal");
    try { const { data: res } = await api.post("/billing/portal"); window.location.href = res.url; }
    catch (e) { toast.error(e?.response?.data?.detail || t("billing.portalError")); setBusy(""); }
  };

  const ps = data?.payment_state;

  const isPaid = currentPlan === "pro" || currentPlan === "team";
  const cycleLabel = data?.interval === "year" ? t("billing.annual") : t("billing.monthly");
  const willCancel = data?.cancel_at_period_end;

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
            {/* failed-payment recovery banner */}
            {ps?.failed ? (
              <div className="mt-6 flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-red-500/40 bg-red-500/[0.08] p-5" data-testid="billing-payment-failed">
                <div className="flex items-start gap-3">
                  <CreditCard className="mt-0.5 h-6 w-6 shrink-0 text-red-400" />
                  <div>
                    <p className="text-sm font-medium text-red-200">{t("billing.paymentFailedTitle")}</p>
                    <p className="mt-1 text-xs text-white/60">
                      {t("billing.paymentFailedBody")}
                      {ps.amount_due ? ` (${ps.currency} ${(ps.amount_due / 100).toFixed(2)})` : ""}
                    </p>
                  </div>
                </div>
                <button onClick={openPortal} disabled={busy === "portal" || !ps.has_customer} data-testid="fix-payment-btn"
                  className="rounded-full bg-red-500 px-5 py-2 text-sm font-medium text-white transition-colors hover:bg-red-400 disabled:opacity-50">
                  {busy === "portal" ? <Loader2 className="h-4 w-4 animate-spin" /> : t("billing.fixPayment")}
                </button>
              </div>
            ) : ps?.recovered ? (
              <div className="mt-6 flex items-center gap-3 rounded-2xl border border-emerald-500/30 bg-emerald-500/[0.06] p-4" data-testid="billing-payment-recovered">
                <ShieldCheck className="h-5 w-5 text-emerald-400" />
                <p className="text-sm text-emerald-200">{t("billing.paymentRecovered")}</p>
              </div>
            ) : null}

            {/* current status banner */}
            <div className={`mt-6 flex flex-wrap items-center justify-between gap-4 rounded-2xl border p-5 ${locked ? "border-red-500/30 bg-red-500/[0.06]" : "border-[#D6A653]/25 bg-[#D6A653]/[0.06]"}`} data-testid="billing-status">
              <div className="flex items-center gap-3">
                <ShieldCheck className={`h-6 w-6 ${locked ? "text-red-400" : "text-[#D6A653]"}`} />
                <div>
                  <p className="text-sm text-white/55">{t("billing.currentPlan")}</p>
                  <p className="text-lg font-medium capitalize text-white" data-testid="billing-current-plan">
                    {currentPlan} · <span className={locked ? "text-red-400" : (willCancel ? "text-amber-400" : "text-[#D6A653]")}>{STATUS_LABEL[data.status] || data.status}</span>
                  </p>
                  {isPaid && data.provider === "stripe" ? (
                    <p className="mt-0.5 text-xs text-white/45" data-testid="billing-cycle">{t("billing.billingCycle")}: {cycleLabel}</p>
                  ) : null}
                </div>
              </div>
              <div className="text-right">
                {isTrial && data.trial_ends_at ? (
                  <p className="text-sm text-white/70" data-testid="billing-trial-days"><span className="text-xl font-light text-[#D6A653]">{daysLeft(data.trial_ends_at)}</span> {t("billing.daysLeft")}</p>
                ) : willCancel && data.current_period_end ? (
                  <p className="text-sm text-amber-300/90" data-testid="billing-access-until">{t("billing.remainsActiveUntil", { plan: (currentPlan || "").replace(/^\w/, (c) => c.toUpperCase()) })} <span className="font-medium">{fmtLong(data.current_period_end)}</span></p>
                ) : isPaid && data.current_period_end ? (
                  <p className="text-sm text-white/70" data-testid="billing-next-date">{t("billing.nextBilling")}: <span className="font-medium text-white">{fmtLong(data.current_period_end)}</span></p>
                ) : null}
                {data.active && isPaid && willCancel ? (
                  <button onClick={resume} disabled={busy === "resume"} data-testid="billing-resume" className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-[#D6A653] px-4 py-1.5 text-xs font-semibold text-black transition-all hover:brightness-110 disabled:opacity-50">
                    {busy === "resume" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}{t("billing.resume")}
                  </button>
                ) : data.active && isPaid && data.status !== "cancel_at_period_end" ? (
                  <button onClick={cancel} disabled={busy === "cancel"} data-testid="billing-cancel" className="mt-2 block text-xs text-white/45 underline underline-offset-2 hover:text-white/70">{t("billing.cancel")}</button>
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

            {/* feature usage allowances (only shown when a limit is active for this account) */}
            {featureUsage.length > 0 && (
              <div className="mt-4 space-y-2" data-testid="billing-feature-usage">
                {featureUsage.map((f) => (
                  <div key={f.key} className="rounded-xl border border-white/10 bg-white/[0.02] p-3" data-testid={`feature-usage-${f.key}`}>
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-white/80">{f.name}</span>
                      <span className={f.over ? "text-red-300" : f.warning ? "text-amber-300" : "text-white/50"}>{f.used} / {f.limit} used · {f.remaining} remaining</span>
                    </div>
                    <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-white/10">
                      <div className={`h-full rounded-full ${f.over ? "bg-red-400" : f.warning ? "bg-amber-400" : "bg-[#D6A653]"}`} style={{ width: `${Math.min(100, f.pct)}%` }} />
                    </div>
                    <p className="mt-1 text-[10px] text-white/40">{f.scope_label}{f.warning && !f.over ? ` — you've used ${f.pct}% of your allowance` : ""}{f.over ? " — allowance reached" : ""}</p>
                  </div>
                ))}
              </div>
            )}

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

            <p className="mt-3 text-center text-[12px] text-white/45" data-testid="billing-tax-note">{t("billing.taxNote")}</p>

            {/* plan comparison */}
            <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4" data-testid="billing-plans">
              {plans.filter((p) => !(p.id === "trial" && !data.trial_eligible)).map((p) => {
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
            {/* Invoice & receipt history (Stripe is the source of truth) */}
            <div className="mt-8 rounded-2xl border border-white/10 bg-[#0A0B0D] p-5" data-testid="billing-history">
              <div className="mb-4 flex items-center justify-between">
                <p className="flex items-center gap-2 text-sm font-medium text-white"><CreditCard className="h-4 w-4 text-[#D6A653]" /> {t("billing.historyTitle")}</p>
                {ps?.has_customer ? (
                  <button onClick={openPortal} disabled={busy === "portal"} data-testid="manage-billing-btn"
                    className="rounded-full border border-white/15 px-3.5 py-1.5 text-xs text-white/80 transition-colors hover:border-[#D6A653]/50">
                    {t("billing.manageBilling")}</button>
                ) : null}
              </div>
              {invoices === undefined ? (
                <div className="flex justify-center py-8"><Loader2 className="h-5 w-5 animate-spin text-[#D6A653]" /></div>
              ) : invoices.length === 0 ? (
                <p className="py-8 text-center text-sm text-white/40" data-testid="billing-history-empty">{t("billing.historyEmpty")}</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="text-[10px] uppercase tracking-wider text-white/40"><tr className="border-b border-white/8">
                      <th className="py-2 pr-3">{t("billing.colDate")}</th><th className="pr-3">{t("billing.colInvoice")}</th><th className="pr-3">{t("billing.colPlan")}</th>
                      <th className="pr-3 text-right">{t("billing.colSubtotal")}</th><th className="pr-3 text-right">{t("billing.colDiscount")}</th>
                      <th className="pr-3 text-right">{t("billing.colTax")}</th><th className="pr-3 text-right">{t("billing.colTotal")}</th>
                      <th className="pr-3">{t("billing.colStatus")}</th><th className="pr-3 text-right">{t("billing.colActions")}</th>
                    </tr></thead>
                    <tbody className="text-white/80">
                      {invoices.map((inv) => {
                        const cur = inv.currency;
                        const m = (v) => `${cur} ${((v || 0) / 100).toFixed(2)}`;
                        const stStyle = inv.status === "paid" ? "text-emerald-300" : inv.refunded ? "text-sky-300" : (inv.status === "open" || inv.status === "draft") ? "text-amber-300" : "text-red-300";
                        return (
                          <tr key={inv.id} className="border-b border-white/5" data-testid={`invoice-row-${inv.id}`}>
                            <td className="py-2 pr-3 text-white/70">{fmtLong(inv.date)}</td>
                            <td className="pr-3 text-white/60">{inv.number || "—"}</td>
                            <td className="pr-3 capitalize">{inv.plan || "—"}</td>
                            <td className="pr-3 text-right tabular-nums">{m(inv.subtotal)}</td>
                            <td className="pr-3 text-right tabular-nums text-white/50">{inv.discount ? `−${m(inv.discount)}` : "—"}</td>
                            <td className="pr-3 text-right tabular-nums text-white/60">{m(inv.tax)}</td>
                            <td className="pr-3 text-right tabular-nums text-white">{m(inv.total)}</td>
                            <td className={`pr-3 capitalize ${stStyle}`} data-testid={`invoice-status-${inv.id}`}>{inv.refunded ? t("billing.stRefunded") : (STATUS_LABEL[inv.status] || inv.status)}</td>
                            <td className="pr-3 text-right">
                              <div className="flex justify-end gap-2">
                                {inv.hosted_invoice_url ? <a href={inv.hosted_invoice_url} target="_blank" rel="noreferrer" data-testid={`invoice-view-${inv.id}`} className="text-[#D6A653] hover:underline">{t("billing.view")}</a> : null}
                                {inv.invoice_pdf ? <a href={inv.invoice_pdf} target="_blank" rel="noreferrer" data-testid={`invoice-pdf-${inv.id}`} className="text-white/60 hover:underline">PDF</a> : null}
                                {inv.receipt_url ? <a href={inv.receipt_url} target="_blank" rel="noreferrer" data-testid={`invoice-receipt-${inv.id}`} className="text-white/60 hover:underline">{t("billing.receipt")}</a> : null}
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {ref?.enabled ? (
              <div className="mt-8 rounded-2xl border border-white/10 bg-[#0A0B0D] p-5" data-testid="billing-referral">
                <div className="flex items-start gap-3">
                  <Zap className="mt-0.5 h-5 w-5 shrink-0 text-[#D6A653]" />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-white">{t("billing.referralTitle")}</p>
                    <p className="mt-1 text-xs text-white/50">{t("referralProgram.tagline", { count: ref.config.referrals_per_reward, months: ref.config.reward_months })}</p>
                    <div className="mt-4 flex flex-wrap items-center gap-2">
                      <code className="rounded-lg border border-[#D6A653]/30 bg-[#D6A653]/[0.08] px-3 py-1.5 text-sm font-medium tracking-wider text-[#D6A653]" data-testid="referral-code">{ref.code}</code>
                      <button data-testid="referral-copy" onClick={() => { navigator.clipboard.writeText(ref.share_url); toast.success(t("home.linkCopied")); }}
                        className="rounded-full border border-white/15 px-3.5 py-1.5 text-xs text-white/80 transition-colors hover:border-[#D6A653]/50">{t("billing.copyLink")}</button>
                      <button data-testid="referral-open" onClick={() => navigate("/referral")}
                        className="rounded-full border border-white/15 px-3.5 py-1.5 text-xs text-white/80 transition-colors hover:border-[#D6A653]/50">{t("referralProgram.viewProgress")}</button>
                    </div>
                    <p className="mt-3 text-xs text-[#D6A653]" data-testid="referral-reward">
                      {t("referralProgram.progressShort", { qualified: ref.reward?.progress || 0, per: ref.config.referrals_per_reward })}
                      {ref.reward?.free_months_earned > 0 ? ` · ${t("referralProgram.monthsEarned", { count: ref.reward.free_months_earned })}` : ""}
                    </p>
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
