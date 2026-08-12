import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { DateFilter, buildRange } from "@/components/admin/DateFilter";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import {
  LayoutDashboard, Users, Building2, CreditCard, TrendingUp, Tags, SlidersHorizontal, Gift,
  LayoutTemplate, Flag, Plug, Activity, ShieldAlert, ScrollText, Settings as SettingsIcon,
  ExternalLink, LogOut, ShieldCheck, Menu, X, Search, Loader2, CheckCircle2, XCircle, AlertTriangle, Ticket,
} from "lucide-react";

const cget = (p, params) => api.get(`/admin/control${p}`, { params }).then((r) => r.data);

const SECTIONS = [
  { key: "overview", label: "Overview", icon: LayoutDashboard },
  { key: "customers", label: "Customers", icon: Users },
  { key: "companies", label: "Workspaces", icon: Building2 },
  { key: "subscriptions", label: "Subscriptions", icon: CreditCard },
  { key: "revenue", label: "Revenue & Analytics", icon: TrendingUp },
  { key: "plans", label: "Plans & Pricing", icon: Tags },
  { key: "promotions", label: "Promotions", icon: Ticket },
  { key: "product", label: "Product & Entitlements", icon: SlidersHorizontal },
  { key: "referrals", label: "Referral Program", icon: Gift },
  { key: "templates", label: "Templates & Industries", icon: LayoutTemplate },
  { key: "flags", label: "Feature Flags", icon: Flag },
  { key: "integrations", label: "Integrations", icon: Plug },
  { key: "health", label: "System Health", icon: Activity },
  { key: "security", label: "Security & Abuse", icon: ShieldAlert },
  { key: "audit", label: "Audit Log", icon: ScrollText },
  { key: "settings", label: "Settings", icon: SettingsIcon },
];

// ---------- primitives ----------
const Panel = ({ title, actions, children, testId }) => (
  <div className="rounded-2xl border border-white/10 bg-[#0B0D12] p-5" data-testid={testId}>
    {(title || actions) && (
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        {title ? <h3 className="text-sm font-medium text-white">{title}</h3> : <span />}
        {actions}
      </div>
    )}
    {children}
  </div>
);

const Kpi = ({ label, value, sub, unavailable, testId }) => (
  <div className="rounded-xl border border-white/8 bg-white/[0.02] p-3" data-testid={testId}>
    <p className="text-[10px] uppercase tracking-wider text-white/40">{label}</p>
    {unavailable ? (
      <p className="mt-1 text-[11px] font-medium text-[#D6A653]/80">n/a until billing</p>
    ) : (
      <p className="mt-0.5 text-xl font-light tabular-nums text-white">{value}</p>
    )}
    {sub ? <p className="mt-0.5 text-[10px] text-emerald-300/80">{sub}</p> : null}
  </div>
);

const MoneyUnavailable = ({ testId = "money-unavailable" }) => (
  <div className="flex items-center gap-3 rounded-xl border border-[#D6A653]/25 bg-[#D6A653]/[0.06] px-4 py-3" data-testid={testId}>
    <CreditCard className="h-4 w-4 shrink-0 text-[#D6A653]" />
    <p className="text-xs text-[#F2E0C9]">MRR, ARR, revenue & churn are <b>not available until Stripe is connected</b>.</p>
  </div>
);

const StatePill = ({ ok, labelOk = "Connected", labelBad = "Not configured", warn }) => (
  <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] ${ok ? "bg-emerald-500/12 text-emerald-300" : warn ? "bg-amber-500/12 text-amber-300" : "bg-white/8 text-white/50"}`}>
    {ok ? <CheckCircle2 className="h-3 w-3" /> : warn ? <AlertTriangle className="h-3 w-3" /> : <XCircle className="h-3 w-3" />}
    {ok ? labelOk : warn ? "Degraded" : labelBad}
  </span>
);

const Grid = ({ children, cols = "grid-cols-2 lg:grid-cols-4" }) => (
  <div className={`grid gap-2.5 ${cols}`}>{children}</div>
);

const IncludeInternal = ({ on, onClick }) => (
  <label className="flex items-center gap-2 text-[11px] text-white/50" data-testid="include-internal">
    <Toggle on={on} onClick={onClick} testId="include-internal-toggle" /> Include internal / test data
  </label>
);

// ================================================================= sections
const Overview = () => {
  const [range, setRange] = useState(() => buildRange("month"));
  const [incInternal, setIncInternal] = useState(false);
  const [d, setD] = useState(null);
  const [showDist, setShowDist] = useState(false);
  useEffect(() => { cget("/overview", { start: range.start, end: range.end, include_internal: incInternal }).then(setD).catch(() => {}); }, [range, incInternal]);
  if (!d) return <Loader />;
  const a = d.accounts, u = d.usage, s = d.subscriptions;
  return (
    <div className="space-y-5" data-testid="ctrl-overview">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-light text-white">Platform Overview</h2>
          <p className="text-[11px] text-white/40" data-testid="users-line">{d.users.total} total users · {d.users.customers} customers · {d.users.internal} internal</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <IncludeInternal on={incInternal} onClick={() => setIncInternal(!incInternal)} />
          <DateFilter value={range} onChange={setRange} testId="ctrl-overview-range" />
        </div>
      </div>

      <Panel title="Business Summary" testId="ctrl-summary">
        <Grid>
          <Kpi label="Customer Accounts" value={a.total} sub={a.new_in_period ? `+${a.new_in_period} in period` : null} testId="kpi-total" />
          <Kpi label="Active Trials" value={s.active_trials} testId="kpi-trials" />
          <Kpi label="Paid Subscribers" value={s.active_paid} testId="kpi-paid" />
          <Kpi label="Companies" value={a.company + a.enterprise} testId="kpi-team" />
        </Grid>
        <p className="mt-2 text-[10px] text-white/35" data-testid="accounts-reconcile">{a.total} accounts = {a.individual} individual + {a.company} company + {a.enterprise} enterprise</p>
      </Panel>

      <Panel title="Growth (selected period)" testId="ctrl-growth">
        <Grid cols="grid-cols-2 lg:grid-cols-3">
          <Kpi label="New Accounts" value={a.new_in_period} testId="kpi-new" />
          <Kpi label="Trial → Paid" unavailable testId="kpi-t2p" />
          <Kpi label="Cancellations" value={s.cancellations_in_period} testId="kpi-cancel" />
        </Grid>
      </Panel>

      <Panel title="Product Usage (selected period)" testId="ctrl-usage">
        <Grid cols="grid-cols-2 sm:grid-cols-3 lg:grid-cols-4">
          <Kpi label="Published Cards" value={u.published_cards} testId="kpi-published" />
          <Kpi label="Card Views" value={u.views} testId="kpi-views" />
          <Kpi label="QR Scans" value={u.scans} testId="kpi-scans" />
          <Kpi label="NFC Taps" value={u.nfc_taps} testId="kpi-nfc" />
          <Kpi label="Leads" value={u.leads} testId="kpi-leads" />
          <Kpi label="Scanner Uses" value={u.scanner_uses} testId="kpi-scanuse" />
          <Kpi label="Meetings" value={u.meetings_booked} testId="kpi-meetings" />
          <Kpi label="Referrals (paid)" value={u.paid_referrals} testId="kpi-refs" />
        </Grid>
      </Panel>

      <Panel title="Revenue" testId="ctrl-money"><MoneyUnavailable /></Panel>

      <Panel title="Plan Distribution" testId="ctrl-plandist"
        actions={<button onClick={() => setShowDist(!showDist)} className="text-[11px] text-[#D6A653]" data-testid="plandist-toggle">{showDist ? "Hide" : "View details"}</button>}>
        {showDist ? (
          <div className="flex flex-wrap gap-2">
            {Object.entries(d.plan_distribution).map(([p, n]) => (
              <span key={p} className="rounded-full border border-white/12 bg-white/5 px-3 py-1 text-xs text-white/70">{p}: <b className="text-white">{n}</b></span>
            ))}
          </div>
        ) : <p className="text-[11px] text-white/40">Real customers only (internal/demo/test excluded).</p>}
      </Panel>
    </div>
  );
};

const ROLE_LABEL = { SUPER_ADMIN: "Super Admin", WORKSPACE_OWNER: "Owner", WORKSPACE_ADMIN: "Admin", MANAGER: "Manager", MEMBER: "Member" };
const roleLabel = (r) => ROLE_LABEL[r] || r;
const statusTone = (s) => s === "trialing" ? "text-[#D6A653]" : s === "active" ? "text-emerald-300" : s === "past_due" ? "text-amber-300" : "text-white/45";

const Customers = () => {
  const [q, setQ] = useState("");
  const [inc, setInc] = useState(false);
  const [rows, setRows] = useState([]);
  const [sel, setSel] = useState(null);
  const [detail, setDetail] = useState(null);
  const [busy, setBusy] = useState(false);
  const load = () => cget("/customers", { q, include_internal: inc }).then((d) => setRows(d.items || [])).catch(() => {});
  useEffect(() => { const t = setTimeout(load, 300); return () => clearTimeout(t); }, [q, inc]);
  const open = async (r) => { setSel(r); setDetail(null); try { setDetail(await cget(`/customers/${r.user_id}`)); } catch (_) {} };
  const act = async (action) => {
    setBusy(true);
    try {
      if (action === "suspend" || action === "unsuspend") await api.post(`/admin/platform/users/${sel.user_id}/suspend`, { suspended: action === "suspend" });
      else await api.post(`/admin/control/customers/${sel.user_id}/action`, { action });
      toast.success("Done"); await open(sel); load();
    } catch (e) { toast.error(e.response?.data?.detail || "Action failed"); } finally { setBusy(false); }
  };
  return (
    <div className="space-y-4" data-testid="ctrl-customers">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div><h2 className="text-xl font-light text-white">Customers</h2><p className="text-[11px] text-white/40">Customer accounts only — team members appear inside their account.</p></div>
        <IncludeInternal on={inc} onClick={() => setInc(!inc)} />
      </div>
      <div className="relative"><Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-white/40" /><Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search name, email…" className="border-white/12 bg-white/[0.03] pl-9 text-white" data-testid="customers-search" /></div>
      <div className="space-y-2">
        {rows.map((r) => (
          <button key={r.user_id} onClick={() => open(r)} data-testid={`customer-row-${r.user_id}`}
            className="flex w-full items-center justify-between gap-3 rounded-xl border border-white/8 bg-white/[0.02] p-3 text-left hover:bg-white/[0.04]">
            <div className="min-w-0">
              <p className="flex items-center gap-2 text-sm text-white">{r.name}
                {r.suspended ? <span className="rounded bg-red-500/15 px-1.5 text-[10px] text-red-300">suspended</span> : null}
                {!r.email_verified ? <span className="text-amber-400" title="unverified">•</span> : null}</p>
              <p className="truncate text-[11px] text-white/45">{r.email} · {r.workspace}</p>
            </div>
            <div className="shrink-0 text-right">
              <p className="text-xs text-white/80">{r.plan} <span className={statusTone(r.status)}>· {r.status}</span></p>
              <p className="text-[10px] text-white/40">{r.account_type} · {roleLabel(r.role)}</p>
            </div>
          </button>
        ))}
        {!rows.length ? <p className="py-8 text-center text-sm text-white/40">No customers</p> : null}
      </div>

      <Dialog open={!!sel} onOpenChange={(v) => !v && setSel(null)}>
        <DialogContent className="max-w-lg border-white/10 bg-[#0B0D12] text-white" data-testid="customer-detail">
          <DialogHeader><DialogTitle>{sel?.name}</DialogTitle><DialogDescription className="sr-only">Customer account details and support actions</DialogDescription></DialogHeader>
          {!detail ? <Loader /> : (
            <div className="space-y-3 text-sm">
              <div className="grid grid-cols-2 gap-2 text-white/70">
                <Field k="Email" v={detail.user.email} />
                <Field k="Verified" v={detail.user.email_verified ? "Yes" : "No"} />
                <Field k="Role" v={roleLabel(detail.user.role)} />
                <Field k="Plan" v={sel?.plan || "—"} />
                <Field k="Status" v={detail.status || sel?.status || "—"} />
                <Field k="Cards" v={detail.cards.length} />
                <Field k="Leads" v={detail.leads} />
                <Field k="Meetings" v={detail.meetings} />
                <Field k="Referrals" v={detail.referrals} />
                <Field k="Country" v={detail.user.country || "—"} />
                <Field k="Language" v={(detail.user.language || "—").toUpperCase()} />
                <Field k="Timezone" v={detail.user.timezone || "—"} />
                <Field k="Created" v={(detail.user.created_at || "").slice(0, 10)} />
                <Field k="Last activity" v={(detail.last_activity || "—").slice(0, 10)} />
              </div>
              <div className="flex flex-wrap gap-2 pt-2">
                <ActBtn onClick={() => act("resend_verification")} busy={busy} testId="cust-resend">Resend verification</ActBtn>
                <ActBtn onClick={() => act("revoke_sessions")} busy={busy} testId="cust-revoke">Revoke sessions</ActBtn>
                {sel?.role !== "SUPER_ADMIN" ? (
                  detail.user.suspended
                    ? <ActBtn onClick={() => act("unsuspend")} busy={busy} testId="cust-unsuspend" tone="ok">Unsuspend</ActBtn>
                    : <ActBtn onClick={() => act("suspend")} busy={busy} testId="cust-suspend" tone="danger">Suspend</ActBtn>
                ) : null}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

const Companies = () => {
  const [q, setQ] = useState("");
  const [inc, setInc] = useState(false);
  const [type, setType] = useState("all");
  const [rows, setRows] = useState([]);
  const [sel, setSel] = useState(null);
  const [detail, setDetail] = useState(null);
  useEffect(() => { const t = setTimeout(() => cget("/workspaces", { q, include_internal: inc, type }).then((d) => setRows(d.items || [])).catch(() => {}), 300); return () => clearTimeout(t); }, [q, inc, type]);
  const open = async (w) => { setSel(w); setDetail(null); try { setDetail(await cget(`/workspaces/${w.id}`)); } catch (_) {} };
  return (
    <div className="space-y-4" data-testid="ctrl-companies">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-xl font-light text-white">Workspaces</h2>
        <IncludeInternal on={inc} onClick={() => setInc(!inc)} />
      </div>
      <div className="flex flex-wrap gap-2">
        {[["all", "All"], ["company", "Companies"], ["individual", "Individuals"]].map(([k, l]) => <RadioPill key={k} on={type === k} onClick={() => setType(k)} testId={`ws-type-${k}`}>{l}</RadioPill>)}
      </div>
      <div className="relative"><Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-white/40" /><Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search workspaces…" className="border-white/12 bg-white/[0.03] pl-9 text-white" data-testid="companies-search" /></div>
      <div className="space-y-2">
        {rows.map((w) => (
          <button key={w.id} onClick={() => open(w)} data-testid={`company-row-${w.id}`}
            className="flex w-full items-center justify-between gap-3 rounded-xl border border-white/8 bg-white/[0.02] p-3 text-left hover:bg-white/[0.04]">
            <div className="min-w-0">
              <p className="text-sm text-white">{w.name}{w.environment !== "production_customer" ? <span className="ml-2 rounded bg-white/10 px-1.5 text-[10px] uppercase text-white/50">{w.environment}</span> : null}</p>
              <p className="text-[11px] text-white/45">{w.type === "company" || w.type === "team" ? "Company" : "Individual"} · {w.plan} <span className={statusTone(w.status)}>· {w.status}</span></p>
            </div>
            <div className="shrink-0 text-right text-[11px] text-white/50">
              <p>{w.members} member{w.members === 1 ? "" : "s"}</p><p>{w.cards} card{w.cards === 1 ? "" : "s"} · {w.leads} leads</p>
            </div>
          </button>
        ))}
        {!rows.length ? <p className="py-8 text-center text-sm text-white/40">No workspaces</p> : null}
      </div>
      <Dialog open={!!sel} onOpenChange={(v) => !v && setSel(null)}>
        <DialogContent className="max-w-lg border-white/10 bg-[#0B0D12] text-white" data-testid="company-detail">
          <DialogHeader><DialogTitle>{sel?.name}</DialogTitle><DialogDescription className="sr-only">Workspace details and members</DialogDescription></DialogHeader>
          {!detail ? <Loader /> : (
            <div className="space-y-3 text-sm">
              <div className="grid grid-cols-2 gap-2 text-white/70">
                <Field k="Owner" v={detail.owner?.email || "—"} />
                <Field k="Type" v={detail.workspace.type === "individual" ? "Individual" : "Company"} />
                <Field k="Plan" v={sel?.plan || "—"} />
                <Field k="Status" v={detail.status} />
                <Field k="Seats" v={detail.seats ?? "—"} />
                <Field k="Members" v={detail.members.length} />
                <Field k="Cards" v={detail.cards} />
                <Field k="Leads" v={detail.leads} />
                <Field k="Meetings" v={detail.meetings} />
                <Field k="Brand lock" v={detail.brand_lock ? "On" : "Off"} />
              </div>
              <div className="rounded-lg border border-white/8 p-3">
                <p className="mb-1.5 text-[11px] uppercase tracking-wider text-white/40">Members</p>
                {detail.members.map((m) => <div key={m.id} className="flex justify-between py-0.5 text-white/70"><span>{m.email || m.id}</span><span className="text-white/40">{roleLabel(m.role)}</span></div>)}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

const Subscriptions = () => {
  const [d, setD] = useState(null);
  const [incInternal, setIncInternal] = useState(false);
  const [q, setQ] = useState("");
  useEffect(() => { cget("/subscriptions", { include_internal: incInternal }).then(setD).catch(() => {}); }, [incInternal]);
  if (!d) return <Loader />;
  const buckets = [["active", "Active"], ["trialing", "Trialing"], ["past_due", "Past Due"], ["canceled", "Canceled"], ["inactive", "Inactive"]];
  const items = (d.items || []).filter((i) => !q.trim() || (i.name || "").toLowerCase().includes(q.toLowerCase()));
  const badge = (b) => b === "active" ? "text-emerald-300" : b === "trialing" ? "text-[#D6A653]" : b === "past_due" ? "text-amber-300" : "text-white/40";
  return (
    <div className="space-y-4" data-testid="ctrl-subscriptions">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-xl font-light text-white">Subscriptions</h2>
        <IncludeInternal on={incInternal} onClick={() => setIncInternal(!incInternal)} />
      </div>
      <Panel title="Summary" testId="subs-summary">
        <Grid cols="grid-cols-2 sm:grid-cols-3 lg:grid-cols-5">
          {buckets.map(([k, lbl]) => <Kpi key={k} label={lbl} value={d.summary?.[k] || 0} testId={`subs-count-${k}`} />)}
        </Grid>
        {!d.money_available ? <p className="mt-3 text-[11px] text-white/40">Billing values (renewal amounts, MRR) appear once Stripe is connected.</p> : null}
      </Panel>
      <div className="relative max-w-md"><Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-white/40" /><Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search customer…" className="border-white/12 bg-white/[0.03] pl-9 text-white" data-testid="subs-search" /></div>
      <Panel>
        <div className="divide-y divide-white/6">
          {items.map((i) => (
            <div key={i.id} className="flex items-center justify-between py-2.5" data-testid={`subs-row-${i.id}`}>
              <div><p className="text-sm text-white">{i.name}</p><p className="text-[11px] text-white/40">{i.type} · {i.plan}</p></div>
              <div className="text-right">
                <p className={`text-xs font-medium ${badge(i.bucket)}`}>{i.bucket}</p>
                <p className="text-[10px] text-white/35">{i.trial_ends_at ? `Trial ends ${i.trial_ends_at.slice(0, 10)}` : i.renewal ? `Renews ${i.renewal.slice(0, 10)}` : "—"}</p>
              </div>
            </div>
          ))}
          {!items.length ? <p className="py-6 text-center text-sm text-white/40">No subscriptions.</p> : null}
        </div>
      </Panel>
    </div>
  );
};

const Revenue = () => {
  const [range, setRange] = useState(() => buildRange("month"));
  const [d, setD] = useState(null);
  useEffect(() => { cget("/overview", { start: range.start, end: range.end }).then(setD).catch(() => {}); }, [range]);
  return (
    <div className="space-y-5" data-testid="ctrl-revenue">
      <div className="flex flex-wrap items-center justify-between gap-2"><h2 className="text-xl font-light text-white">Revenue & Analytics</h2><DateFilter value={range} onChange={setRange} testId="ctrl-rev-range" /></div>
      <Panel title="Revenue"><MoneyUnavailable /></Panel>
      {d ? <Panel title="Product analytics (real)"><Grid>
        <Kpi label="Views" value={d.usage.views} /><Kpi label="Scans" value={d.usage.scans} /><Kpi label="NFC Taps" value={d.usage.nfc_taps} /><Kpi label="Leads" value={d.usage.leads} />
      </Grid></Panel> : <Loader />}
    </div>
  );
};

const Plans = () => {
  const [cfg, setCfg] = useState(null);
  const [draft, setDraft] = useState(null);
  const [step, setStep] = useState(0); // 0 edit, 1 preview, 2 done
  const [preview, setPreview] = useState(null);
  const [applyTo, setApplyTo] = useState("new_only");
  const [reason, setReason] = useState("");
  const [versions, setVersions] = useState([]);
  const [resolved, setResolved] = useState({});
  const [resolvedDraft, setResolvedDraft] = useState({});
  const load = () => api.get("/admin/commercial").then((r) => { setCfg(r.data.config); setDraft(JSON.parse(JSON.stringify(r.data.config))); }).catch(() => {});
  const loadResolved = () => api.get("/commercial/pricing").then((r) => setResolved(r.data.resolved_all || {})).catch(() => {});
  useEffect(() => { load(); loadResolved(); cget("/pricing/versions").then((r) => setVersions(r.items || [])).catch(() => {}); }, []);
  const patch = () => {
    const rp = { USD: draft?.regional_pricing?.USD };
    (draft?.manual_price_markets || []).forEach((m) => { if (draft?.regional_pricing?.[m]) rp[m] = draft.regional_pricing[m]; });
    return {
      trial: { days: draft?.trial?.days, enabled: draft?.trial?.enabled },
      plans: { team: { min_seats: draft?.plans?.team?.min_seats } },
      regional_pricing: rp,
      fx_rates: draft?.fx_rates,
      manual_price_markets: draft?.manual_price_markets || [],
    };
  };
  // Live server-side resolve of the (unsaved) draft — no currency math in the frontend.
  useEffect(() => {
    if (!draft) return;
    const t = setTimeout(() => {
      api.post("/admin/control/pricing/resolve", { patch: patch() }).then((r) => setResolvedDraft(r.data.resolved_all || {})).catch(() => {});
    }, 350);
    return () => clearTimeout(t);
  }, [draft]); // eslint-disable-line
  if (!draft) return <Loader />;
  const setP = (path, val) => { const d = { ...draft }; let o = d; const keys = path.split("."); for (let i = 0; i < keys.length - 1; i++) { o[keys[i]] = { ...(o[keys[i]] || {}) }; o = o[keys[i]]; } o[keys[keys.length - 1]] = val; setDraft(d); };
  const isManual = (m) => (draft.manual_price_markets || []).includes(m);
  const toggleManual = (m, makeManual) => setDraft((prev) => {
    const d = JSON.parse(JSON.stringify(prev));
    const set = new Set(d.manual_price_markets || []);
    if (makeManual) {
      set.add(m);
      const r = resolvedDraft[m] || resolved[m] || {};
      d.regional_pricing[m] = { symbol: r.symbol, pro_month: r.pro_month, pro_year: r.pro_year, team_seat_month: r.team_seat_month, team_seat_year: r.team_seat_year };
    } else { set.delete(m); }
    d.manual_price_markets = [...set];
    return d;
  });
  const doPreview = async () => { try { setPreview(await api.post("/admin/control/pricing/preview", { patch: patch(), apply_to: applyTo }).then((r) => r.data)); setStep(1); } catch (e) { toast.error("Preview failed"); } };
  const doPublish = async () => { try { await api.post("/admin/control/pricing/publish", { patch: patch(), apply_to: applyTo, reason }); toast.success("Pricing published & live on public site"); setStep(2); load(); cget("/pricing/versions").then((r) => setVersions(r.items || [])); } catch (e) { toast.error("Publish failed"); } };
  const mk = draft.default_market || "USD";
  return (
    <div className="space-y-5" data-testid="ctrl-plans">
      <h2 className="text-xl font-light text-white">Plans & Pricing</h2>
      <p className="text-[11px] text-white/40">Published values drive the public Pricing page, checkout and entitlements — one source of truth. Editing base market: <b className="text-white/70">{mk}</b>.</p>
      <Panel title="Draft changes" testId="plans-editor">
        <div className="grid gap-4 sm:grid-cols-2">
          <NumField label="Trial days" value={draft.trial?.days} onChange={(v) => setP("trial.days", v)} testId="plan-trial-days" />
          <BoolField label="Trial enabled" value={draft.trial?.enabled} onChange={(v) => setP("trial.enabled", v)} testId="plan-trial-enabled" />
          <NumField label={`Pro / month (${mk})`} value={draft.regional_pricing?.[mk]?.pro_month} onChange={(v) => setP(`regional_pricing.${mk}.pro_month`, v)} testId="plan-pro-month" />
          <NumField label={`Pro / year (${mk})`} value={draft.regional_pricing?.[mk]?.pro_year} onChange={(v) => setP(`regional_pricing.${mk}.pro_year`, v)} testId="plan-pro-year" />
          <NumField label={`Team seat / month (${mk})`} value={draft.regional_pricing?.[mk]?.team_seat_month} onChange={(v) => setP(`regional_pricing.${mk}.team_seat_month`, v)} testId="plan-team-month" />
          <NumField label={`Team seat / year (${mk})`} value={draft.regional_pricing?.[mk]?.team_seat_year} onChange={(v) => setP(`regional_pricing.${mk}.team_seat_year`, v)} testId="plan-team-year" />
          <NumField label="Team minimum seats" value={draft.plans?.team?.min_seats} onChange={(v) => setP("plans.team.min_seats", v)} testId="plan-team-minseats" />
        </div>
        <div className="mt-4 flex items-center gap-2">
          <button onClick={doPreview} className="rounded-lg bg-[#D6A653] px-4 py-2 text-sm font-medium text-[#050607] hover:bg-[#E8B764]" data-testid="plans-preview-btn">Preview Impact</button>
          <button onClick={() => setDraft(JSON.parse(JSON.stringify(cfg)))} className="rounded-lg border border-white/12 px-4 py-2 text-sm text-white/60">Reset</button>
        </div>
      </Panel>
      <Panel title="Regional currencies" testId="plans-converted">
        <p className="mb-3 text-[11px] text-white/40">USD is the base. Non-base currencies are <b className="text-white/60">Auto</b> (convert from USD via an editable FX rate) or <b className="text-sky-300">Manual</b> (fixed local price). Switch Manual→Auto to resume converting from the current USD base. Prices below are resolved live from your unsaved draft; click <b className="text-[#D6A653]">Preview Impact</b> then Publish to go live.</p>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[860px] text-xs">
            <thead><tr className="text-left uppercase tracking-wide text-white/35">
              <th className="pb-2 pr-3">Market</th><th className="pb-2 pr-3">Source</th><th className="pb-2 pr-3">FX ×USD</th><th className="pb-2 pr-3">Pro mo / yr</th><th className="pb-2 pr-3">Pro save</th><th className="pb-2 pr-3">Team mo / yr</th><th className="pb-2">Team save</th>
            </tr></thead>
            <tbody>
              {(draft.fx_rates ? Object.keys({ USD: 1, ...draft.fx_rates }) : ["USD"]).map((m) => {
                const p = resolvedDraft[m] || resolved[m] || {};
                const base = m === "USD";
                const manual = !base && isManual(m);
                const sym = p.symbol || "";
                const inp = "w-16 rounded border border-white/12 bg-white/5 px-1.5 py-1 text-white outline-none focus:border-[#D6A653]/50";
                return (
                  <tr key={m} className="border-t border-white/6 text-white/70 align-middle" data-testid={`converted-${m}`}>
                    <td className="py-1.5 pr-3 font-medium text-white/85">{m}</td>
                    <td className="py-1.5 pr-3">
                      {base ? (
                        <span className="rounded-full bg-[#D6A653]/15 px-2 py-0.5 text-[10px] uppercase tracking-wider text-[#D6A653]" data-testid={`converted-src-${m}`}>BASE</span>
                      ) : (
                        <button onClick={() => toggleManual(m, !manual)} data-testid={`toggle-manual-${m}`}
                          className={`rounded-full px-2 py-0.5 text-[10px] uppercase tracking-wider ${manual ? "bg-sky-500/15 text-sky-300" : "bg-white/10 text-white/55"}`} title="Toggle Auto/Manual">
                          <span data-testid={`converted-src-${m}`}>{manual ? "MANUAL" : "AUTO"}</span>
                        </button>
                      )}
                    </td>
                    <td className="py-1.5 pr-3">
                      {base ? <span className="text-white/40">1.0</span> : (
                        <input type="number" step="0.0001" disabled={manual} value={draft.fx_rates?.[m] ?? ""} onChange={(e) => setP(`fx_rates.${m}`, Number(e.target.value))} data-testid={`fx-${m}`} className={`w-20 rounded border border-white/12 bg-white/5 px-1.5 py-1 text-white outline-none focus:border-[#D6A653]/50 disabled:opacity-40`} />
                      )}
                    </td>
                    <td className="py-1.5 pr-3 whitespace-nowrap">
                      {manual ? (
                        <span className="inline-flex items-center gap-1">{sym}<input type="number" step="0.01" value={draft.regional_pricing?.[m]?.pro_month ?? ""} onChange={(e) => setP(`regional_pricing.${m}.pro_month`, Number(e.target.value))} data-testid={`man-${m}-pro_month`} className={inp} /> / {sym}<input type="number" step="0.01" value={draft.regional_pricing?.[m]?.pro_year ?? ""} onChange={(e) => setP(`regional_pricing.${m}.pro_year`, Number(e.target.value))} data-testid={`man-${m}-pro_year`} className={inp} /></span>
                      ) : <span data-testid={`res-${m}-pro`}>{sym}{p.pro_month} / {sym}{p.pro_year}</span>}
                    </td>
                    <td className="py-1.5 pr-3" data-testid={`save-${m}-pro`}>{p.pro_annual_savings_pct}%</td>
                    <td className="py-1.5 pr-3 whitespace-nowrap">
                      {manual ? (
                        <span className="inline-flex items-center gap-1">{sym}<input type="number" step="0.01" value={draft.regional_pricing?.[m]?.team_seat_month ?? ""} onChange={(e) => setP(`regional_pricing.${m}.team_seat_month`, Number(e.target.value))} data-testid={`man-${m}-team_seat_month`} className={inp} /> / {sym}<input type="number" step="0.01" value={draft.regional_pricing?.[m]?.team_seat_year ?? ""} onChange={(e) => setP(`regional_pricing.${m}.team_seat_year`, Number(e.target.value))} data-testid={`man-${m}-team_seat_year`} className={inp} /></span>
                      ) : <span data-testid={`res-${m}-team`}>{sym}{p.team_seat_month} / {sym}{p.team_seat_year}</span>}
                    </td>
                    <td className="py-1.5" data-testid={`save-${m}-team`}>{p.team_annual_savings_pct}%</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Panel>
      <Panel title="Version history" testId="plans-versions">
        {!versions.length ? <p className="text-sm text-white/40">No published changes yet.</p> :
          versions.map((v) => <div key={v.id} className="flex justify-between border-t border-white/6 py-2 text-xs text-white/60"><span>{(v.created_at || "").slice(0, 16).replace("T", " ")} · {v.apply_to}</span><span className="text-white/40">{v.reason || "no reason"}</span></div>)}
      </Panel>

      <Dialog open={step === 1 || step === 2} onOpenChange={(o) => !o && setStep(0)}>
        <DialogContent className="max-w-lg border-white/10 bg-[#0B0D12] text-white" data-testid="plans-publish-dialog">
          {step === 1 && preview ? (<>
            <DialogHeader><DialogTitle>Impact Preview</DialogTitle><DialogDescription className="sr-only">Review the pricing change impact before publishing</DialogDescription></DialogHeader>
            <div className="space-y-3 text-sm">
              <p className="text-white/60">{preview.note}</p>
              <div className="rounded-lg border border-white/8 p-3 text-xs">
                {Object.keys(preview.diff || {}).length ? Object.entries(preview.diff).map(([k, v]) => (
                  <div key={k} className="flex justify-between py-0.5"><span className="text-white/70">{k}</span><span className="text-white/50">{String(v.before)} → <b className="text-[#D6A653]">{String(v.after)}</b></span></div>
                )) : <span className="text-white/40">No changes.</span>}
                <div className="mt-2 border-t border-white/8 pt-2 text-white/40">{(preview.impact?.[0]?.active_subscriptions) || 0} active paid customer(s) affected</div>
              </div>
              <div>
                <p className="mb-1 text-[11px] uppercase tracking-wider text-white/40">Apply to</p>
                <div className="flex gap-2">
                  <RadioPill on={applyTo === "new_only"} onClick={() => setApplyTo("new_only")} testId="apply-new">New customers only</RadioPill>
                  <RadioPill on={applyTo === "migrate"} onClick={() => setApplyTo("migrate")} testId="apply-migrate">Migrate existing</RadioPill>
                </div>
              </div>
              <Input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Reason (for audit log)" className="border-white/12 bg-white/[0.03] text-white" data-testid="plans-reason" />
            </div>
            <DialogFooter>
              <button onClick={() => setStep(0)} className="rounded-lg border border-white/12 px-4 py-2 text-sm text-white/60">Back</button>
              <button onClick={doPublish} className="rounded-lg bg-[#D6A653] px-4 py-2 text-sm font-medium text-[#050607]" data-testid="plans-confirm-publish">Confirm & Publish</button>
            </DialogFooter>
          </>) : (<>
            <DialogHeader><DialogTitle>Published</DialogTitle></DialogHeader>
            <p className="text-sm text-white/60">The pricing change has been versioned and recorded in the Audit Log. New prices apply to new customers{applyTo === "migrate" ? "; existing subscriptions flagged for migration when Stripe is connected." : "."}</p>
            <DialogFooter><button onClick={() => setStep(0)} className="rounded-lg bg-[#D6A653] px-4 py-2 text-sm font-medium text-[#050607]">Done</button></DialogFooter>
          </>)}
        </DialogContent>
      </Dialog>
    </div>
  );
};

const ENT_LABEL = { max_cards: "Max cards", premium_templates: "Premium templates", analytics: "Analytics level", analytics_months: "Analytics history (months)", leads: "Leads / CRM", wallet: "Mobile wallet passes", crm: "CRM", campaigns: "Campaigns", ai_followup: "AI follow-up", ai_limit: "AI monthly limit", ai_period: "AI reset period", scanner: "Card scanner", scanner_limit: "Scanner monthly limit", scanner_period: "Scanner reset period", team: "Team seats", remove_branding: "Remove branding", custom_domain: "Custom domain", api: "API access", integrations: "Integrations" };
const entLabel = (k) => ENT_LABEL[k] || k.replace(/_/g, " ");
const PROVIDER_KEY = { wallet: "wallet", ai_followup: "ai_followup", custom_domain: "custom_domain" };

const Product = () => {
  const [data, setData] = useState(null);
  const [plan, setPlan] = useState("pro");
  const [ov, setOv] = useState({});
  const [preview, setPreview] = useState(null);
  const [reason, setReason] = useState("");
  useEffect(() => { cget("/entitlements").then(setData).catch(() => {}); }, []);
  useEffect(() => { if (data) setOv({ ...(data.overrides?.[plan] || {}) }); }, [plan, data]);
  if (!data) return <Loader />;
  const defaults = data.defaults[plan] || {};
  const ps = data.provider_status || {};
  const doPreview = async () => { try { setPreview(await api.post("/admin/control/entitlements/preview", { plan, overrides: ov }).then((r) => r.data)); } catch { toast.error("Preview failed"); } };
  const publish = async () => { try { await api.put("/admin/control/entitlements", { plan, overrides: ov, reason }); toast.success("Entitlements published & audited"); setPreview(null); setReason(""); setData(await cget("/entitlements")); } catch { toast.error("Publish failed"); } };
  return (
    <div className="space-y-4" data-testid="ctrl-product">
      <h2 className="text-xl font-light text-white">Product & Entitlements</h2>
      <div className="flex flex-wrap gap-2">{data.plans.map((p) => <RadioPill key={p} on={plan === p} onClick={() => setPlan(p)} testId={`ent-plan-${p}`}>{p}</RadioPill>)}</div>
      <Panel title={`Overrides for "${plan}"`} testId="ent-editor"
        actions={<button onClick={doPreview} className="rounded-lg bg-[#D6A653] px-4 py-1.5 text-sm font-medium text-[#050607]" data-testid="ent-preview">Preview changes</button>}>
        <div className="grid gap-3 sm:grid-cols-2">
          {Object.entries(defaults).filter(([k]) => k !== "white_label").map(([k, dv]) => {
            const cur = ov[k] !== undefined ? ov[k] : dv;
            const provFeat = PROVIDER_KEY[k];
            const provOk = provFeat ? ps[provFeat] : null;
            const unavailable = provFeat && provOk === false;
            const label = entLabel(k);
            return (
              <div key={k} className="relative">
                {typeof dv === "boolean" ? <BoolField label={label} value={!!cur} onChange={(v) => setOv({ ...ov, [k]: v })} testId={`ent-${k}`} />
                  : typeof dv === "number" ? <NumField label={label} value={cur} onChange={(v) => setOv({ ...ov, [k]: v })} testId={`ent-${k}`} />
                    : <TextField label={label} value={String(cur ?? "")} onChange={(v) => setOv({ ...ov, [k]: v })} testId={`ent-${k}`} />}
                {unavailable ? <p className="mt-1 flex items-center gap-1 text-[10px] text-amber-300" data-testid={`ent-unavailable-${k}`}><AlertTriangle className="h-3 w-3" /> Provider not connected — feature unavailable even if enabled</p> : null}
              </div>
            );
          })}
        </div>
      </Panel>

      <Dialog open={!!preview} onOpenChange={(o) => !o && setPreview(null)}>
        <DialogContent className="max-w-lg border-white/10 bg-[#0B0D12] text-white" data-testid="ent-publish-dialog">
          <DialogHeader><DialogTitle>Impact Preview — {plan}</DialogTitle><DialogDescription className="sr-only">Review entitlement changes before publishing</DialogDescription></DialogHeader>
          {preview ? (
            <div className="space-y-3 text-sm">
              <p className="text-xs text-white/60">{preview.affected_customers} active customer(s) on this plan will be affected.</p>
              <div className="rounded-lg border border-white/8 p-3 text-xs">
                {Object.keys(preview.diff).length ? Object.entries(preview.diff).map(([k, v]) => (
                  <div key={k} className="flex justify-between py-0.5"><span className="text-white/70">{entLabel(k)}</span><span className="text-white/50">{String(v.before)} → <b className="text-[#D6A653]">{String(v.after)}</b></span></div>
                )) : <span className="text-white/40">No changes.</span>}
              </div>
              <Input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Reason (for audit log)" className="border-white/12 bg-white/[0.03] text-white" data-testid="ent-reason" />
            </div>
          ) : null}
          <DialogFooter>
            <button onClick={() => setPreview(null)} className="rounded-lg border border-white/12 px-4 py-2 text-sm text-white/60">Cancel</button>
            <button onClick={publish} disabled={!preview || !Object.keys(preview.diff).length} className="rounded-lg bg-[#D6A653] px-4 py-2 text-sm font-medium text-[#050607] disabled:opacity-50" data-testid="ent-confirm-publish">Confirm & Publish</button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

const Referrals = () => {
  const [d, setD] = useState(null);
  useEffect(() => { cget("/referrals").then(setD).catch(() => {}); }, []);
  if (!d) return <Loader />;
  const f = d.funnel;
  return (
    <div className="space-y-5" data-testid="ctrl-referrals">
      <h2 className="text-xl font-light text-white">Referral Program</h2>
      <p className="text-sm text-white/45">Invite {d.config?.referrals_per_reward || 5} paid qualifying referrals → {d.config?.reward_months || 1} month free.</p>
      <Panel title="Funnel"><Grid><Kpi label="Total" value={f.total} /><Kpi label="Signed Up" value={f.signed_up} /><Kpi label="Qualified (paid)" value={f.qualified} /><Kpi label="Revoked / Suspicious" value={f.revoked} /></Grid></Panel>
      <Panel title="Rewards"><Grid cols="sm:grid-cols-2"><Kpi label="Free months earned" value={d.months_earned} /></Grid></Panel>
      <Panel title="Top referrers">
        {!d.top_referrers.length ? <p className="text-sm text-white/40">No qualified referrals yet.</p> :
          d.top_referrers.map((r, i) => <div key={i} className="flex justify-between border-t border-white/6 py-2 text-sm text-white/70"><span>{r.workspace}</span><b className="text-white">{r.qualified}</b></div>)}
      </Panel>
    </div>
  );
};

const Templates = () => {
  const [rows, setRows] = useState([]);
  const load = () => api.get("/admin/industries").then((r) => setRows(r.data.industries || [])).catch(() => {});
  useEffect(() => { load(); }, []);
  const toggle = async (ind) => { try { await api.put(`/admin/industries/${ind.id}`, { active: !ind.active }); load(); } catch (_) { toast.error("Update failed"); } };
  return (
    <div className="space-y-4" data-testid="ctrl-templates">
      <h2 className="text-xl font-light text-white">Templates & Industries</h2>
      <Panel>
        <div className="grid gap-2 sm:grid-cols-2">
          {rows.map((ind) => (
            <div key={ind.id} className="flex items-center justify-between rounded-lg border border-white/8 px-3 py-2.5" data-testid={`industry-${ind.id}`}>
              <span className="text-sm text-white/80">{ind.name || ind.label || ind.id}</span>
              <Toggle on={ind.active !== false} onClick={() => toggle(ind)} testId={`industry-toggle-${ind.id}`} />
            </div>
          ))}
          {!rows.length ? <p className="text-sm text-white/40">No industries.</p> : null}
        </div>
      </Panel>
    </div>
  );
};

const Flags = () => {
  const [rows, setRows] = useState([]);
  const [key, setKey] = useState("");
  const load = () => cget("/flags").then((d) => setRows(d.items || [])).catch(() => {});
  useEffect(() => { load(); }, []);
  const setFlag = async (k, enabled, description = "") => { try { await api.put(`/admin/control/flags/${k}`, { enabled, description }); load(); } catch (_) { toast.error("Failed"); } };
  const add = async () => { if (!key.trim()) return; await setFlag(key.trim(), false); setKey(""); };
  return (
    <div className="space-y-4" data-testid="ctrl-flags">
      <h2 className="text-xl font-light text-white">Feature Flags</h2>
      <div className="flex max-w-md gap-2"><Input value={key} onChange={(e) => setKey(e.target.value)} placeholder="new_flag_key" className="border-white/12 bg-white/[0.03] text-white" data-testid="flag-key-input" /><button onClick={add} className="rounded-lg bg-[#D6A653] px-4 text-sm font-medium text-[#050607]" data-testid="flag-add">Add</button></div>
      <Panel>
        {!rows.length ? <p className="text-sm text-white/40">No flags yet.</p> : rows.map((fl) => (
          <div key={fl.key} className="flex items-center justify-between border-t border-white/6 py-2.5 first:border-t-0" data-testid={`flag-${fl.key}`}>
            <div><p className="text-sm text-white">{fl.key}</p>{fl.description ? <p className="text-xs text-white/40">{fl.description}</p> : null}</div>
            <Toggle on={fl.enabled} onClick={() => setFlag(fl.key, !fl.enabled, fl.description)} testId={`flag-toggle-${fl.key}`} />
          </div>
        ))}
      </Panel>
    </div>
  );
};

const Integrations = () => {
  const [d, setD] = useState(null);
  useEffect(() => { api.get("/integrations/status").then((r) => setD(r.data)).catch(() => {}); }, []);
  if (!d) return <Loader />;
  const cats = ["billing", "wallet", "crm"];
  return (
    <div className="space-y-4" data-testid="ctrl-integrations">
      <h2 className="text-xl font-light text-white">Integrations</h2>
      {cats.map((c) => (
        <Panel key={c} title={c.toUpperCase()} testId={`integr-${c}`}>
          <div className="flex flex-wrap gap-2">{Object.entries(d[c] || {}).map(([name, on]) => (
            <span key={name} className="inline-flex items-center gap-2 rounded-lg border border-white/8 bg-white/[0.02] px-3 py-2 text-sm text-white/70" data-testid={`integr-${name}`}>{name} <StatePill ok={!!on} /></span>
          ))}</div>
        </Panel>
      ))}
      <p className="text-xs text-white/40">{d.notes} Secrets are never displayed.</p>
    </div>
  );
};

const Health = () => {
  const [d, setD] = useState(null);
  useEffect(() => { cget("/health").then(setD).catch(() => {}); }, []);
  if (!d) return <Loader />;
  return (
    <div className="space-y-4" data-testid="ctrl-health">
      <h2 className="text-xl font-light text-white">System Health</h2>
      <Panel><div className="grid gap-3 sm:grid-cols-2">
        <HRow k="API" v={d.api} ok={d.api === "ok"} />
        <HRow k="Database" v={d.database} ok={d.database === "ok"} />
        <HRow k="AI Provider" v={d.ai_provider} ok={d.ai_provider === "ok"} />
        <HRow k="Billing" v={d.billing} ok={d.billing === "connected"} warn={d.billing === "demo"} />
        <HRow k="Email delivery" v={d.email_delivery} ok={d.email_delivery === "connected"} />
        <HRow k="Error monitoring (Sentry)" v={d.error_monitoring} ok={d.error_monitoring === "connected"} />
      </div>
      <p className="mt-4 text-xs text-white/40">Pending email verifications: {d.pending_email_verifications}. Deeper monitoring activates once Sentry is connected.</p>
      </Panel>
    </div>
  );
};

const Security = () => {
  const [d, setD] = useState(null);
  useEffect(() => { cget("/security").then(setD).catch(() => {}); }, []);
  if (!d) return <Loader />;
  return (
    <div className="space-y-4" data-testid="ctrl-security">
      <h2 className="text-xl font-light text-white">Security & Abuse</h2>
      <Panel title={`Suspended accounts (${d.suspended_accounts.length})`}>
        {!d.suspended_accounts.length ? <p className="text-sm text-white/40">None.</p> : d.suspended_accounts.map((u) => <div key={u.id} className="flex justify-between border-t border-white/6 py-2 text-sm text-white/70"><span>{u.name}</span><span className="text-white/40">{u.email}</span></div>)}
      </Panel>
      <Panel title={`Locked / throttled logins (${d.locked_or_throttled.length})`}>
        {!d.locked_or_throttled.length ? <p className="text-sm text-white/40">No throttled identifiers.</p> : d.locked_or_throttled.map((a, i) => <div key={i} className="flex justify-between border-t border-white/6 py-2 text-sm text-white/70"><span className="font-mono text-xs">{a.identifier}</span><span className="text-amber-300">{a.fails} fails</span></div>)}
      </Panel>
      <Panel title="Suspicious referrals"><p className="text-sm text-white/70">{d.suspicious_referrals} revoked referral(s).</p></Panel>
    </div>
  );
};

const Audit = () => {
  const [q, setQ] = useState("");
  const [rows, setRows] = useState([]);
  useEffect(() => { const t = setTimeout(() => cget("/audit", { q }).then((d) => setRows(d.items || [])).catch(() => {}), 300); return () => clearTimeout(t); }, [q]);
  return (
    <div className="space-y-4" data-testid="ctrl-audit">
      <h2 className="text-xl font-light text-white">Audit Log</h2>
      <div className="relative max-w-md"><Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-white/40" /><Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Filter by action…" className="border-white/12 bg-white/[0.03] pl-9 text-white" data-testid="audit-search" /></div>
      <Panel>
        <div className="max-h-[60vh] overflow-y-auto">
          {rows.map((lg) => (
            <div key={lg.id} className="border-t border-white/6 py-2.5 first:border-t-0" data-testid={`audit-${lg.id}`}>
              <div className="flex justify-between text-sm"><span className="text-white">{lg.action}</span><span className="text-white/40 text-xs">{(lg.created_at || "").slice(0, 16).replace("T", " ")}</span></div>
              <p className="text-xs text-white/40">{lg.actor_email || lg.actor_id || "system"} {lg.meta && Object.keys(lg.meta).length ? `· ${JSON.stringify(lg.meta).slice(0, 120)}` : ""}</p>
            </div>
          ))}
          {!rows.length ? <p className="py-6 text-center text-sm text-white/40">No audit entries.</p> : null}
        </div>
      </Panel>
    </div>
  );
};

const Promotions = () => {
  const [items, setItems] = useState(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({ code: "", discount_type: "percent", percent_off: 20, amount_off: 10, currency: "usd", duration: "once", duration_in_months: 3, max_redemptions: "" });
  const set = (k, v) => setForm((s) => ({ ...s, [k]: v }));

  const load = () => {
    setErr("");
    cget("/promotions").then((r) => setItems(r.items || [])).catch((e) => { setItems([]); setErr(e?.response?.data?.detail || "Could not load promotions"); });
  };
  useEffect(() => { load(); }, []);

  const create = async () => {
    if (!form.code.trim()) { toast.error("Enter a promo code"); return; }
    setBusy(true);
    try {
      const payload = { code: form.code.trim().toUpperCase(), discount_type: form.discount_type, duration: form.duration };
      if (form.discount_type === "percent") payload.percent_off = Number(form.percent_off);
      else { payload.amount_off = Number(form.amount_off); payload.currency = form.currency; }
      if (form.duration === "repeating") payload.duration_in_months = Number(form.duration_in_months);
      if (form.max_redemptions) payload.max_redemptions = Number(form.max_redemptions);
      await api.post("/admin/control/promotions", payload);
      toast.success(`Promo code ${payload.code} created`);
      setForm((s) => ({ ...s, code: "", max_redemptions: "" }));
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Create failed"); }
    finally { setBusy(false); }
  };

  const toggle = async (pc) => {
    try { await api.post(`/admin/control/promotions/${pc.id}/toggle`, { active: !pc.active }); load(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Update failed"); }
  };

  const fmtDiscount = (c) => c.percent_off ? `${c.percent_off}% off` : c.amount_off ? `${(c.amount_off / 100).toFixed(2)} ${(c.currency || "").toUpperCase()} off` : "—";

  return (
    <div className="space-y-5" data-testid="ctrl-promotions">
      <h2 className="text-xl font-light text-white">Promotions</h2>
      <p className="text-[11px] text-white/40">Create real Stripe promo codes. Customers enter them on the Stripe-hosted checkout page — pricing, trials and referrals are unaffected.</p>
      {err ? <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200" data-testid="promo-error">{err}</div> : null}

      <Panel title="Create promo code" testId="promo-editor">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <TextField label="Code (what customers type)" value={form.code} onChange={(v) => set("code", v.toUpperCase())} testId="promo-code" />
          <label className="block"><span className="mb-1 block text-[11px] uppercase tracking-wider text-white/40">Discount type</span>
            <div className="flex gap-2">
              <RadioPill on={form.discount_type === "percent"} onClick={() => set("discount_type", "percent")} testId="promo-type-percent">Percent</RadioPill>
              <RadioPill on={form.discount_type === "amount"} onClick={() => set("discount_type", "amount")} testId="promo-type-amount">Fixed amount</RadioPill>
            </div>
          </label>
          {form.discount_type === "percent" ? (
            <NumField label="Percent off (%)" value={form.percent_off} onChange={(v) => set("percent_off", v)} testId="promo-percent" />
          ) : (
            <>
              <NumField label="Amount off" value={form.amount_off} onChange={(v) => set("amount_off", v)} testId="promo-amount" />
              <TextField label="Currency" value={form.currency} onChange={(v) => set("currency", v.toLowerCase())} testId="promo-currency" />
            </>
          )}
          <label className="block"><span className="mb-1 block text-[11px] uppercase tracking-wider text-white/40">Duration</span>
            <div className="flex flex-wrap gap-2">
              {["once", "repeating", "forever"].map((d) => <RadioPill key={d} on={form.duration === d} onClick={() => set("duration", d)} testId={`promo-duration-${d}`}>{d}</RadioPill>)}
            </div>
          </label>
          {form.duration === "repeating" ? <NumField label="Months" value={form.duration_in_months} onChange={(v) => set("duration_in_months", v)} testId="promo-months" /> : <span />}
          <NumField label="Max redemptions (optional)" value={form.max_redemptions} onChange={(v) => set("max_redemptions", v)} testId="promo-max" />
        </div>
        <div className="mt-4">
          <button onClick={create} disabled={busy} className="rounded-lg bg-[#D6A653] px-4 py-2 text-sm font-medium text-[#050607] hover:bg-[#E8B764] disabled:opacity-50" data-testid="promo-create-btn">{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Create promo code"}</button>
        </div>
      </Panel>

      <Panel title="Active & past promo codes" testId="promo-list">
        {items === null ? <Loader /> : items.length === 0 ? (
          <p className="py-6 text-center text-sm text-white/40" data-testid="promo-empty">No promo codes yet.</p>
        ) : (
          <div className="space-y-2">
            {items.map((pc) => (
              <div key={pc.id} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-white/8 px-4 py-3" data-testid={`promo-row-${pc.code}`}>
                <div className="min-w-0">
                  <span className="font-mono text-sm font-medium text-white">{pc.code}</span>
                  <span className="ml-3 text-xs text-[#D6A653]">{fmtDiscount(pc.coupon)}</span>
                  <span className="ml-3 text-[11px] text-white/40">{pc.coupon.duration}{pc.coupon.duration === "repeating" ? ` · ${pc.coupon.duration_in_months}mo` : ""} · {pc.times_redeemed} used{pc.max_redemptions ? ` / ${pc.max_redemptions}` : ""}</span>
                </div>
                <div className="flex items-center gap-3">
                  <StatePill ok={pc.active} labelOk="Active" labelBad="Inactive" />
                  <ActBtn onClick={() => toggle(pc)} tone={pc.active ? "danger" : "ok"} testId={`promo-toggle-${pc.code}`}>{pc.active ? "Deactivate" : "Activate"}</ActBtn>
                </div>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
};


const ControlSettings = () => (
  <div className="space-y-4" data-testid="ctrl-settings">
    <h2 className="text-xl font-light text-white">Settings</h2>
    <Panel title="Control Center">
      <p className="text-sm text-white/60">This is the TapPresence platform operator console. Pricing, plans, entitlements, feature flags and referral configuration are managed in their dedicated sections and every sensitive change is recorded in the Audit Log.</p>
    </Panel>
  </div>
);

// ---------- small field helpers ----------
const Loader = () => <div className="flex justify-center py-12"><Loader2 className="h-5 w-5 animate-spin text-[#D6A653]" /></div>;
const Field = ({ k, v }) => <div><span className="block text-[10px] uppercase tracking-wider text-white/35">{k}</span><span className="text-white/80">{String(v)}</span></div>;
const NumField = ({ label, value, onChange, testId }) => <label className="block"><span className="mb-1 block text-[11px] uppercase tracking-wider text-white/40">{label}</span><Input type="number" value={value ?? ""} onChange={(e) => onChange(e.target.value === "" ? "" : Number(e.target.value))} className="border-white/12 bg-white/[0.03] text-white" data-testid={testId} /></label>;
const TextField = ({ label, value, onChange, testId }) => <label className="block"><span className="mb-1 block text-[11px] uppercase tracking-wider text-white/40">{label}</span><Input value={value} onChange={(e) => onChange(e.target.value)} className="border-white/12 bg-white/[0.03] text-white" data-testid={testId} /></label>;
const Toggle = ({ on, onClick, testId }) => <button onClick={onClick} data-testid={testId} className={`relative h-5 w-9 rounded-full transition-colors ${on ? "bg-[#D6A653]" : "bg-white/15"}`}><span className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-all ${on ? "left-[18px]" : "left-0.5"}`} /></button>;
const BoolField = ({ label, value, onChange, testId }) => <div className="flex items-center justify-between rounded-lg border border-white/8 px-3 py-2.5"><span className="text-sm text-white/70">{label}</span><Toggle on={!!value} onClick={() => onChange(!value)} testId={testId} /></div>;
const RadioPill = ({ on, onClick, children, testId }) => <button onClick={onClick} data-testid={testId} className={`rounded-full border px-3 py-1.5 text-xs transition-colors ${on ? "border-[#D6A653] bg-[#D6A653]/12 text-[#D6A653]" : "border-white/12 text-white/55 hover:text-white"}`}>{children}</button>;
const ActBtn = ({ onClick, busy, children, tone, testId }) => <button onClick={onClick} disabled={busy} data-testid={testId} className={`rounded-lg border px-3 py-1.5 text-sm disabled:opacity-50 ${tone === "danger" ? "border-red-500/40 text-red-300 hover:bg-red-500/10" : tone === "ok" ? "border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/10" : "border-white/15 text-white/70 hover:bg-white/5"}`}>{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : children}</button>;
const HRow = ({ k, v, ok, warn }) => <div className="flex items-center justify-between rounded-lg border border-white/8 px-3 py-2.5"><span className="text-sm text-white/70">{k}</span><StatePill ok={ok} warn={warn} labelOk={v} labelBad={v} /></div>;

const RENDER = { overview: Overview, customers: Customers, companies: Companies, subscriptions: Subscriptions, revenue: Revenue, plans: Plans, promotions: Promotions, product: Product, referrals: Referrals, templates: Templates, flags: Flags, integrations: Integrations, health: Health, security: Security, audit: Audit, settings: ControlSettings };

export default function ControlCenter() {
  const { section = "overview" } = useParams();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [drawer, setDrawer] = useState(false);
  const active = RENDER[section] ? section : "overview";
  const Body = RENDER[active];

  const Nav = () => (
    <>
      <div className="flex items-center gap-2.5 px-1 pb-4">
        <ShieldCheck className="h-6 w-6 text-[#D6A653]" />
        <div><p className="text-[10px] uppercase tracking-[0.25em] text-white/40">TapPresence</p><h1 className="text-[13px] font-medium text-white">Control Center</h1></div>
      </div>
      <nav className="flex-1 space-y-0.5 overflow-y-auto" data-testid="control-nav">
        {SECTIONS.map((s) => (
          <button key={s.key} onClick={() => { navigate(`/control/${s.key}`); setDrawer(false); }} data-testid={`control-nav-${s.key}`}
            className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-all ${active === s.key ? "bg-[#D6A653]/12 text-white" : "text-white/55 hover:bg-white/5 hover:text-white"}`}>
            <s.icon className={`h-4 w-4 shrink-0 ${active === s.key ? "text-[#D6A653]" : ""}`} /><span className="truncate">{s.label}</span>
          </button>
        ))}
      </nav>
      <div className="space-y-1 border-t border-white/8 pt-3">
        <button onClick={() => navigate("/dashboard")} className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-white/55 hover:bg-white/5 hover:text-white" data-testid="control-open-app"><ExternalLink className="h-4 w-4" /> Open TapPresence App</button>
        <button onClick={logout} className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-white/55 hover:bg-white/5 hover:text-white" data-testid="control-logout"><LogOut className="h-4 w-4" /> Log out</button>
      </div>
    </>
  );

  return (
    <div className="min-h-screen bg-[#050607]" data-testid="control-center">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 flex-col border-r border-white/8 bg-[#0B0D12] px-4 py-5 lg:flex"><Nav /></aside>
      {drawer ? <div className="fixed inset-0 z-40 bg-black/60 lg:hidden" onClick={() => setDrawer(false)} /> : null}
      <aside className={`fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-white/8 bg-[#0B0D12] px-4 py-5 transition-transform lg:hidden ${drawer ? "translate-x-0" : "-translate-x-full"}`}><div className="mb-1 flex justify-end"><button onClick={() => setDrawer(false)} className="p-1 text-white/60"><X className="h-5 w-5" /></button></div><Nav /></aside>

      <div className="lg:pl-64">
        <header className="sticky top-0 z-30 flex items-center justify-between border-b border-white/8 bg-[#0B0D12]/85 px-4 py-3 backdrop-blur-xl lg:px-8">
          <div className="flex items-center gap-2.5">
            <button onClick={() => setDrawer(true)} className="p-1.5 text-white/70 lg:hidden" data-testid="control-hamburger"><Menu className="h-5 w-5" /></button>
            <span className="flex items-center gap-2 text-sm font-medium text-white"><ShieldCheck className="h-4 w-4 text-[#D6A653]" /> TapPresence Admin Console</span>
          </div>
          <span className="text-xs text-white/50" data-testid="control-admin-identity">Super Admin</span>
        </header>
        <main className="mx-auto max-w-6xl px-4 py-8 lg:px-8">{Body ? <Body /> : null}</main>
      </div>
    </div>
  );
}
