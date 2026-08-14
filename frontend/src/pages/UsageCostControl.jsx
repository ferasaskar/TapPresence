import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { DateFilter, buildRange } from "@/components/admin/DateFilter";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { Gauge, Loader2, Download, Plus, Trash2, X, TrendingUp, AlertTriangle, CheckCircle2 } from "lucide-react";

const ug = (p, params) => api.get(`/admin/control/usage${p}`, { params }).then((r) => r.data);
const usd = (n) => `$${Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const num = (n) => Number(n || 0).toLocaleString();

const STATUS_STYLE = {
  normal: "bg-emerald-500/12 text-emerald-300",
  watch: "bg-sky-500/12 text-sky-300",
  high: "bg-amber-500/12 text-amber-300",
  critical: "bg-red-500/12 text-red-300",
};

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
const Kpi = ({ label, value, sub, estimated, testId }) => (
  <div className="rounded-xl border border-white/8 bg-white/[0.02] p-3" data-testid={testId}>
    <p className="text-[10px] uppercase tracking-wider text-white/40">{label}</p>
    <p className="mt-0.5 text-xl font-light tabular-nums text-white">{value}</p>
    {sub ? <p className="mt-0.5 text-[10px] text-white/40">{sub}</p> : null}
    {estimated ? <p className="mt-0.5 text-[9px] uppercase tracking-wide text-[#D6A653]/70">Estimated</p> : null}
  </div>
);
const Pill = ({ status }) => (
  <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] uppercase tracking-wide ${STATUS_STYLE[status] || STATUS_STYLE.normal}`} data-testid={`status-${status}`}>
    {status}
  </span>
);
const Loader = () => <div className="flex justify-center py-12"><Loader2 className="h-5 w-5 animate-spin text-[#D6A653]" /></div>;
const Toggle = ({ on, onClick, testId }) => (
  <button onClick={onClick} data-testid={testId} className={`relative h-5 w-9 rounded-full transition-colors ${on ? "bg-[#D6A653]" : "bg-white/15"}`}>
    <span className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-all ${on ? "left-[18px]" : "left-0.5"}`} />
  </button>
);

export default function UsageCostControl() {
  const [range, setRange] = useState(() => buildRange("month"));
  const [plan, setPlan] = useState("");
  const [feature, setFeature] = useState("");
  const [d, setD] = useState(null);
  const [tab, setTab] = useState("overview"); // overview | config | overrides
  const [detail, setDetail] = useState(null);
  const [sortUsers, setSortUsers] = useState("cost");
  const [sortWs, setSortWs] = useState("cost");

  const load = () => ug("/overview", { start: range.start, end: range.end, plan, feature }).then(setD).catch(() => setD(null));
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [range, plan, feature]);

  const exportCsv = async () => {
    try {
      const res = await api.get(`/admin/control/usage/export.csv`, { params: { start: range.start, end: range.end, feature }, responseType: "blob" });
      const url = URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a"); a.href = url; a.download = "usage_cost.csv"; a.click(); URL.revokeObjectURL(url);
    } catch { toast.error("Export failed"); }
  };

  const sortedUsers = useMemo(() => {
    if (!d) return [];
    const arr = [...d.top_users];
    arr.sort((a, b) => (b[sortUsers] || 0) - (a[sortUsers] || 0));
    return arr;
  }, [d, sortUsers]);
  const sortedWs = useMemo(() => {
    if (!d) return [];
    const arr = [...d.top_workspaces];
    arr.sort((a, b) => (b[sortWs] || 0) - (a[sortWs] || 0));
    return arr;
  }, [d, sortWs]);

  const k = d?.kpis;

  return (
    <div className="space-y-5" data-testid="ctrl-usage">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2 text-xl font-light text-white"><Gauge className="h-5 w-5 text-[#D6A653]" /> Usage &amp; Cost Control</h2>
          <p className="text-[11px] text-white/40">Global feature usage, estimated variable cost &amp; configurable limits. All costs are <span className="text-[#D6A653]/80">estimated</span> unless from an authoritative billing source.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <select value={plan} onChange={(e) => setPlan(e.target.value)} data-testid="usage-plan-filter" className="rounded-lg border border-white/12 bg-white/[0.03] px-2 py-1.5 text-xs text-white">
            <option value="">All plans</option>
            {["trial", "pro", "team", "enterprise"].map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
          <select value={feature} onChange={(e) => setFeature(e.target.value)} data-testid="usage-feature-filter" className="rounded-lg border border-white/12 bg-white/[0.03] px-2 py-1.5 text-xs text-white">
            <option value="">All features</option>
            {(d?.features || []).map((f) => <option key={f.key} value={f.key}>{f.name}</option>)}
          </select>
          <DateFilter value={range} onChange={setRange} testId="usage-range" />
        </div>
      </div>

      {/* tabs */}
      <div className="flex gap-2" data-testid="usage-tabs">
        {[["overview", "Overview"], ["config", "Cost & Limits"], ["overrides", "Overrides"]].map(([kk, lbl]) => (
          <button key={kk} onClick={() => setTab(kk)} data-testid={`usage-tab-${kk}`}
            className={`rounded-full border px-3 py-1.5 text-xs transition-colors ${tab === kk ? "border-[#D6A653] bg-[#D6A653]/12 text-[#D6A653]" : "border-white/12 text-white/55 hover:text-white"}`}>{lbl}</button>
        ))}
      </div>

      {tab === "overview" && (!d ? <Loader /> : (
        <>
          <Panel title="Platform KPIs (selected period)" testId="usage-kpis" actions={<button onClick={exportCsv} data-testid="usage-export-btn" className="flex items-center gap-1.5 rounded-lg border border-white/15 px-3 py-1.5 text-xs text-white/70 hover:bg-white/5"><Download className="h-3.5 w-3.5" /> Export CSV</button>}>
            <div className="grid grid-cols-2 gap-2.5 lg:grid-cols-4">
              <Kpi label="Active Users" value={num(k.active_users)} sub={`${num(k.total_users)} total`} testId="kpi-active-users" />
              <Kpi label="Active Workspaces" value={num(k.active_workspaces)} sub={`${num(k.total_workspaces)} total`} testId="kpi-active-ws" />
              <Kpi label="Tracked Usage" value={num(k.total_tracked_usage)} testId="kpi-usage" />
              <Kpi label="AI Operations" value={num(k.total_ai_operations)} testId="kpi-ai-ops" />
              <Kpi label="Est. AI Cost" value={usd(k.estimated_ai_cost)} estimated testId="kpi-ai-cost" />
              <Kpi label="Est. Total Variable Cost" value={usd(k.estimated_total_cost)} estimated testId="kpi-total-cost" />
              <Kpi label="Avg Cost / Active User" value={usd(k.avg_cost_per_user)} estimated testId="kpi-avg-user" />
              <Kpi label="Avg Cost / Active Workspace" value={usd(k.avg_cost_per_workspace)} estimated testId="kpi-avg-ws" />
              <Kpi label="Highest-Cost User" value={k.highest_cost_user ? usd(k.highest_cost_user.cost) : "—"} sub={k.highest_cost_user?.email || "no usage"} estimated testId="kpi-hi-user" />
              <Kpi label="Highest-Cost Workspace" value={k.highest_cost_workspace ? usd(k.highest_cost_workspace.cost) : "—"} sub={k.highest_cost_workspace?.name || "no usage"} estimated testId="kpi-hi-ws" />
            </div>
          </Panel>

          <Panel title="Feature usage & estimated cost" testId="usage-feature-table">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="text-[10px] uppercase tracking-wider text-white/40">
                  <tr className="border-b border-white/8">
                    <th className="py-2 pr-3">Feature</th><th className="pr-3">Cat</th><th className="pr-3 text-right">Today</th><th className="pr-3 text-right">Month</th>
                    <th className="pr-3 text-right">Avg/User</th><th className="pr-3 text-right">Avg/WS</th><th className="pr-3 text-right">Hi User</th><th className="pr-3 text-right">Hi WS</th>
                    <th className="pr-3 text-right">Unit</th><th className="pr-3 text-right">Est. Cost</th><th className="pr-3">Limit</th><th className="pr-3">Status</th>
                  </tr>
                </thead>
                <tbody className="text-white/80">
                  {d.features.map((f) => (
                    <tr key={f.key} className="border-b border-white/5" data-testid={`usage-row-${f.key}`}>
                      <td className="py-2 pr-3 text-white">{f.name}{f.placeholder ? <span className="ml-1.5 rounded bg-white/8 px-1 text-[9px] uppercase text-white/40">soon</span> : null}{!f.metered && !f.placeholder ? <span className="ml-1.5 rounded bg-white/8 px-1 text-[9px] uppercase text-white/40">info</span> : null}</td>
                      <td className="pr-3 text-white/50">{f.category}</td>
                      <td className="pr-3 text-right tabular-nums">{num(f.usage_today)}</td>
                      <td className="pr-3 text-right tabular-nums">{num(f.usage_month)}</td>
                      <td className="pr-3 text-right tabular-nums text-white/50">{f.avg_per_user}</td>
                      <td className="pr-3 text-right tabular-nums text-white/50">{f.avg_per_workspace}</td>
                      <td className="pr-3 text-right tabular-nums text-white/50">{num(f.highest_user_usage)}</td>
                      <td className="pr-3 text-right tabular-nums text-white/50">{num(f.highest_workspace_usage)}</td>
                      <td className="pr-3 text-right tabular-nums">{usd(f.unit_cost)}</td>
                      <td className="pr-3 text-right tabular-nums text-[#D6A653]">{usd(f.estimated_total_cost)}</td>
                      <td className="pr-3 text-[10px] text-white/50">{f.enforcement_enabled ? (f.limit_label || "Enabled") : "Unlimited"}</td>
                      <td className="pr-3"><Pill status={f.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-2 text-[10px] text-white/35">Costs are ESTIMATED from configured unit costs × usage. Informational features are not limited by default.</p>
          </Panel>

          <div className="grid gap-4 lg:grid-cols-2">
            <Panel title="Top cost users" testId="usage-top-users" actions={
              <select value={sortUsers} onChange={(e) => setSortUsers(e.target.value)} data-testid="sort-users" className="rounded-lg border border-white/12 bg-white/[0.03] px-2 py-1 text-[11px] text-white/70">
                <option value="cost">By cost</option><option value="ai_ops">By AI ops</option>
              </select>}>
              {sortedUsers.length === 0 ? <p className="py-6 text-center text-xs text-white/40" data-testid="top-users-empty">No metered usage in this period.</p> : (
                <div className="space-y-1.5">
                  {sortedUsers.map((u) => (
                    <button key={u.id} onClick={() => setDetail({ type: "user", id: u.id })} data-testid={`top-user-${u.id}`} className="flex w-full items-center justify-between gap-3 rounded-lg border border-white/8 px-3 py-2 text-left hover:bg-white/5">
                      <div className="min-w-0"><p className="truncate text-xs text-white">{u.email || u.name || u.id}</p><p className="text-[10px] text-white/40">{u.plan || "—"} · {u.workspace || "—"}</p></div>
                      <div className="text-right"><p className="text-xs text-[#D6A653] tabular-nums">{usd(u.cost)}</p><p className="text-[10px] text-white/40 tabular-nums">{num(u.ai_ops)} ops</p></div>
                    </button>
                  ))}
                </div>
              )}
            </Panel>
            <Panel title="Top cost workspaces" testId="usage-top-ws" actions={
              <select value={sortWs} onChange={(e) => setSortWs(e.target.value)} data-testid="sort-ws" className="rounded-lg border border-white/12 bg-white/[0.03] px-2 py-1 text-[11px] text-white/70">
                <option value="cost">By cost</option><option value="ai_ops">By AI ops</option>
              </select>}>
              {sortedWs.length === 0 ? <p className="py-6 text-center text-xs text-white/40" data-testid="top-ws-empty">No metered usage in this period.</p> : (
                <div className="space-y-1.5">
                  {sortedWs.map((w) => (
                    <button key={w.id} onClick={() => setDetail({ type: "workspace", id: w.id })} data-testid={`top-ws-${w.id}`} className="flex w-full items-center justify-between gap-3 rounded-lg border border-white/8 px-3 py-2 text-left hover:bg-white/5">
                      <div className="min-w-0"><p className="truncate text-xs text-white">{w.name || w.id}</p><p className="text-[10px] text-white/40">{w.plan || "—"}{w.seats ? ` · ${w.seats} seats` : ""}</p></div>
                      <div className="text-right"><p className="text-xs text-[#D6A653] tabular-nums">{usd(w.cost)}</p><p className="text-[10px] text-white/40 tabular-nums">{num(w.ai_ops)} ops</p></div>
                    </button>
                  ))}
                </div>
              )}
            </Panel>
          </div>

          <TimeSeries range={range} feature={feature} />
        </>
      ))}

      {tab === "config" && <CostLimitConfig onSaved={load} />}
      {tab === "overrides" && <Overrides />}

      {detail ? <DetailDrawer {...detail} range={range} onClose={() => setDetail(null)} /> : null}
    </div>
  );
}

// ---------------- Timeseries (CSS bar chart) ----------------
const TimeSeries = ({ range, feature }) => {
  const [s, setS] = useState(null);
  useEffect(() => { ug("/timeseries", { start: range.start, end: range.end, feature }).then((r) => setS(r.series)).catch(() => setS([])); }, [range, feature]);
  if (!s) return null;
  const max = Math.max(1, ...s.map((x) => x.usage));
  return (
    <Panel title="Usage over time" testId="usage-timeseries" actions={<TrendingUp className="h-4 w-4 text-white/40" />}>
      {s.length === 0 ? <p className="py-6 text-center text-xs text-white/40">No data in range.</p> : (
        <div className="flex items-end gap-1 overflow-x-auto" style={{ height: 120 }}>
          {s.map((x) => (
            <div key={x.date} className="flex min-w-[10px] flex-1 flex-col items-center gap-1" title={`${x.date}: ${x.usage} ops · $${x.cost}`}>
              <div className="w-full rounded-t bg-[#D6A653]/70" style={{ height: `${(x.usage / max) * 90}px` }} data-testid={`ts-bar-${x.date}`} />
              <span className="text-[8px] text-white/30">{x.date.slice(5)}</span>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
};

// ---------------- Cost & Limit configuration ----------------
const CostLimitConfig = ({ onSaved }) => {
  const [cfg, setCfg] = useState(null);
  const [edit, setEdit] = useState(null); // feature key being edited
  const load = () => ug("/config").then(setCfg).catch(() => setCfg(null));
  useEffect(() => { load(); }, []);
  if (!cfg) return <Loader />;
  return (
    <div className="space-y-3" data-testid="usage-config">
      <p className="text-[11px] text-white/40">Set unit costs (USD) and limits per feature. Enforcement is OFF by default — no customer is blocked until you enable a limit here. Existing plan allowances are unchanged.</p>
      {cfg.features.map((f) => (
        <div key={f.key} className="rounded-xl border border-white/8 bg-[#0B0D12] p-4" data-testid={`cfg-row-${f.key}`}>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm text-white">{f.name} <span className="ml-1.5 text-[10px] uppercase text-white/35">{f.category}</span>{f.placeholder ? <span className="ml-1.5 rounded bg-white/8 px-1 text-[9px] uppercase text-white/40">future</span> : null}</p>
              <p className="text-[11px] text-white/40">{usd(f.config.unit_cost)} {f.cost_unit} · scope {f.config.scope} · {f.config.enforcement_enabled ? <span className="text-emerald-300">enforcement ON ({f.config.hard_behavior})</span> : <span className="text-white/40">enforcement OFF</span>}</p>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-white/40">Enforce</span>
              <Toggle on={f.config.enforcement_enabled} testId={`cfg-enforce-${f.key}`} onClick={async () => {
                try { await api.put(`/admin/control/usage/config/${f.key}`, { enforcement_enabled: !f.config.enforcement_enabled }); toast.success("Saved"); load(); onSaved && onSaved(); } catch { toast.error("Failed"); }
              }} />
              <button onClick={() => setEdit(f.key)} data-testid={`cfg-edit-${f.key}`} className="rounded-lg border border-white/15 px-3 py-1.5 text-xs text-white/70 hover:bg-white/5">Configure</button>
            </div>
          </div>
        </div>
      ))}
      {edit ? <ConfigDialog feature={cfg.features.find((x) => x.key === edit)} onClose={() => setEdit(null)} onSaved={() => { setEdit(null); load(); onSaved && onSaved(); }} /> : null}
    </div>
  );
};

const ConfigDialog = ({ feature, onClose, onSaved }) => {
  const [f, setF] = useState(() => ({
    unit_cost: feature.config.unit_cost, scope: feature.config.scope, soft_pct: feature.config.soft_pct,
    hard_behavior: feature.config.hard_behavior, enforcement_enabled: feature.config.enforcement_enabled,
    plan_limits: JSON.parse(JSON.stringify(feature.config.plan_limits || {})),
  }));
  const [busy, setBusy] = useState(false);
  const setPlan = (p, k, v) => setF((s) => ({ ...s, plan_limits: { ...s.plan_limits, [p]: { ...s.plan_limits[p], [k]: v } } }));
  const save = async () => {
    setBusy(true);
    try {
      await api.put(`/admin/control/usage/config/${feature.key}`, {
        unit_cost: Number(f.unit_cost), scope: f.scope, soft_pct: Number(f.soft_pct),
        hard_behavior: f.hard_behavior, enforcement_enabled: f.enforcement_enabled, plan_limits: f.plan_limits,
      });
      toast.success("Configuration saved"); onSaved();
    } catch { toast.error("Save failed"); } finally { setBusy(false); }
  };
  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-lg border-white/10 bg-[#0B0D12] text-white" data-testid="cfg-dialog">
        <DialogHeader><DialogTitle>{feature.name}</DialogTitle><DialogDescription className="text-white/50">Configure unit cost (USD) and per-plan limits. Enforcement OFF keeps existing behavior.</DialogDescription></DialogHeader>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <label className="block"><span className="mb-1 block text-[11px] uppercase text-white/40">Unit cost (USD)</span>
              <Input type="number" step="0.001" value={f.unit_cost} onChange={(e) => setF({ ...f, unit_cost: e.target.value })} className="border-white/12 bg-white/[0.03] text-white" data-testid="cfg-unit-cost" /></label>
            <label className="block"><span className="mb-1 block text-[11px] uppercase text-white/40">Limit scope</span>
              <select value={f.scope} onChange={(e) => setF({ ...f, scope: e.target.value })} data-testid="cfg-scope" className="w-full rounded-lg border border-white/12 bg-white/[0.03] px-2 py-2 text-sm text-white">
                {["per_user", "per_workspace", "per_event", "unlimited"].map((s) => <option key={s} value={s}>{s}</option>)}</select></label>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <label className="block"><span className="mb-1 block text-[11px] uppercase text-white/40">Soft limit %</span>
              <Input type="number" value={f.soft_pct} onChange={(e) => setF({ ...f, soft_pct: e.target.value })} className="border-white/12 bg-white/[0.03] text-white" data-testid="cfg-soft" /></label>
            <label className="block"><span className="mb-1 block text-[11px] uppercase text-white/40">Hard limit behavior</span>
              <select value={f.hard_behavior} onChange={(e) => setF({ ...f, hard_behavior: e.target.value })} data-testid="cfg-hard" className="w-full rounded-lg border border-white/12 bg-white/[0.03] px-2 py-2 text-sm text-white">
                {["block", "flag", "overage"].map((s) => <option key={s} value={s}>{s}</option>)}</select></label>
          </div>
          <div className="rounded-lg border border-white/8 p-3">
            <p className="mb-2 text-[11px] uppercase text-white/40">Per-plan limits</p>
            {["trial", "pro", "team", "enterprise"].map((p) => (
              <div key={p} className="mb-2 flex items-center gap-2">
                <span className="w-20 text-xs text-white/60">{p}</span>
                <select value={f.plan_limits[p]?.mode || "unlimited"} onChange={(e) => setPlan(p, "mode", e.target.value)} data-testid={`cfg-plan-mode-${p}`} className="rounded-lg border border-white/12 bg-white/[0.03] px-2 py-1.5 text-xs text-white">
                  {["unlimited", "monthly", "disabled", "custom"].map((m) => <option key={m} value={m}>{m}</option>)}</select>
                {["monthly", "custom"].includes(f.plan_limits[p]?.mode) ? (
                  <Input type="number" value={f.plan_limits[p]?.limit ?? ""} onChange={(e) => setPlan(p, "limit", e.target.value === "" ? null : Number(e.target.value))} placeholder="limit" className="h-8 w-24 border-white/12 bg-white/[0.03] text-xs text-white" data-testid={`cfg-plan-limit-${p}`} />
                ) : null}
              </div>
            ))}
          </div>
          <label className="flex items-center justify-between rounded-lg border border-white/8 px-3 py-2.5">
            <span className="text-sm text-white/70">Enforcement enabled (activates the limit)</span>
            <Toggle on={f.enforcement_enabled} onClick={() => setF({ ...f, enforcement_enabled: !f.enforcement_enabled })} testId="cfg-enforce-toggle" />
          </label>
        </div>
        <DialogFooter>
          <button onClick={onClose} className="rounded-lg border border-white/15 px-4 py-2 text-sm text-white/70">Cancel</button>
          <button onClick={save} disabled={busy} data-testid="cfg-save-btn" className="rounded-lg bg-[#D6A653] px-4 py-2 text-sm font-medium text-[#050607] hover:bg-[#E8B764] disabled:opacity-50">{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Save"}</button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

// ---------------- Overrides ----------------
const Overrides = () => {
  const [items, setItems] = useState(null);
  const [features, setFeatures] = useState([]);
  const [form, setForm] = useState({ feature: "", scope_type: "workspace", scope_id: "", mode: "monthly", limit: 100, note: "" });
  const [busy, setBusy] = useState(false);
  const load = () => ug("/overrides").then((r) => setItems(r.items)).catch(() => setItems([]));
  useEffect(() => { load(); ug("/config").then((r) => setFeatures(r.features)).catch(() => {}); }, []);
  const create = async () => {
    if (!form.feature || !form.scope_id.trim()) { toast.error("Feature and target ID are required"); return; }
    setBusy(true);
    try { await api.post(`/admin/control/usage/overrides`, { ...form, limit: ["monthly", "custom"].includes(form.mode) ? Number(form.limit) : null }); toast.success("Override saved"); setForm({ ...form, scope_id: "", note: "" }); load(); }
    catch { toast.error("Failed"); } finally { setBusy(false); }
  };
  const del = async (id) => { try { await api.delete(`/admin/control/usage/overrides/${id}`); toast.success("Removed — back to plan default"); load(); } catch { toast.error("Failed"); } };
  return (
    <div className="space-y-4" data-testid="usage-overrides">
      <Panel title="Add customer override">
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block"><span className="mb-1 block text-[11px] uppercase text-white/40">Feature</span>
            <select value={form.feature} onChange={(e) => setForm({ ...form, feature: e.target.value })} data-testid="ov-feature" className="w-full rounded-lg border border-white/12 bg-white/[0.03] px-2 py-2 text-sm text-white">
              <option value="">Select…</option>{features.filter((f) => f.enforceable).map((f) => <option key={f.key} value={f.key}>{f.name}</option>)}</select></label>
          <label className="block"><span className="mb-1 block text-[11px] uppercase text-white/40">Scope</span>
            <select value={form.scope_type} onChange={(e) => setForm({ ...form, scope_type: e.target.value })} data-testid="ov-scope" className="w-full rounded-lg border border-white/12 bg-white/[0.03] px-2 py-2 text-sm text-white">
              {["user", "workspace", "event"].map((s) => <option key={s} value={s}>{s}</option>)}</select></label>
          <label className="block sm:col-span-2"><span className="mb-1 block text-[11px] uppercase text-white/40">Target ID ({form.scope_type} id)</span>
            <Input value={form.scope_id} onChange={(e) => setForm({ ...form, scope_id: e.target.value })} placeholder="paste user / workspace / event id" className="border-white/12 bg-white/[0.03] text-white" data-testid="ov-id" /></label>
          <label className="block"><span className="mb-1 block text-[11px] uppercase text-white/40">Mode</span>
            <select value={form.mode} onChange={(e) => setForm({ ...form, mode: e.target.value })} data-testid="ov-mode" className="w-full rounded-lg border border-white/12 bg-white/[0.03] px-2 py-2 text-sm text-white">
              {["unlimited", "monthly", "disabled", "custom"].map((m) => <option key={m} value={m}>{m}</option>)}</select></label>
          {["monthly", "custom"].includes(form.mode) ? (
            <label className="block"><span className="mb-1 block text-[11px] uppercase text-white/40">Limit</span>
              <Input type="number" value={form.limit} onChange={(e) => setForm({ ...form, limit: e.target.value })} className="border-white/12 bg-white/[0.03] text-white" data-testid="ov-limit" /></label>
          ) : <span />}
        </div>
        <button onClick={create} disabled={busy} data-testid="ov-create-btn" className="mt-3 flex items-center gap-1.5 rounded-lg bg-[#D6A653] px-4 py-2 text-sm font-medium text-[#050607] hover:bg-[#E8B764] disabled:opacity-50">{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <><Plus className="h-4 w-4" /> Add override</>}</button>
      </Panel>
      <Panel title="Active overrides">
        {items === null ? <Loader /> : items.length === 0 ? <p className="py-6 text-center text-xs text-white/40" data-testid="ov-empty">No overrides. All accounts use their plan default limit.</p> : (
          <div className="space-y-2">
            {items.map((o) => (
              <div key={o.id} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-white/8 px-4 py-3" data-testid={`ov-row-${o.id}`}>
                <div><p className="text-sm text-white">{o.feature} <span className="text-[#D6A653]">· {o.mode}{o.limit ? ` ${o.limit}` : ""}</span></p>
                  <p className="text-[11px] text-white/40">{o.scope_type}: {o.scope_label || o.scope_id}</p></div>
                <button onClick={() => del(o.id)} data-testid={`ov-del-${o.id}`} className="flex items-center gap-1 rounded-lg border border-red-500/40 px-3 py-1.5 text-xs text-red-300 hover:bg-red-500/10"><Trash2 className="h-3.5 w-3.5" /> Remove</button>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
};

// ---------------- Detail drawer ----------------
const DetailDrawer = ({ type, id, range, onClose }) => {
  const [d, setD] = useState(null);
  useEffect(() => { ug("/detail", { type, id, start: range.start, end: range.end }).then(setD).catch(() => setD(null)); }, [type, id, range]);
  return (
    <div className="fixed inset-0 z-50 flex justify-end" data-testid="usage-detail">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="relative z-10 flex h-full w-full max-w-md flex-col border-l border-white/10 bg-[#0B0D12] p-5">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-sm font-medium text-white">{type === "user" ? "User" : "Workspace"} cost detail</h3>
          <button onClick={onClose} data-testid="detail-close" className="p-1 text-white/60"><X className="h-5 w-5" /></button>
        </div>
        {!d ? <Loader /> : (
          <div className="space-y-4 overflow-y-auto">
            <div className="rounded-xl border border-white/8 p-3">
              <p className="text-white">{d.header.name || d.header.email || id}</p>
              <p className="text-[11px] text-white/40">{d.header.plan || "—"}{d.header.workspace ? ` · ${d.header.workspace}` : ""}{d.header.seats ? ` · ${d.header.seats} seats` : ""}</p>
            </div>
            <div className="space-y-1.5">
              {d.breakdown.length === 0 ? <p className="py-6 text-center text-xs text-white/40">No metered usage in period.</p> : d.breakdown.map((b) => (
                <div key={b.key} className="flex items-center justify-between rounded-lg border border-white/8 px-3 py-2" data-testid={`detail-${b.key}`}>
                  <div><p className="text-xs text-white">{b.name}</p><p className="text-[10px] text-white/40">{b.usage} × {usd(b.unit_cost)}</p></div>
                  <p className="text-xs text-[#D6A653] tabular-nums">{usd(b.estimated_cost)}</p>
                </div>
              ))}
            </div>
            <div className="rounded-xl border border-[#D6A653]/25 bg-[#D6A653]/[0.06] px-4 py-3">
              <p className="text-[11px] uppercase text-white/40">Total estimated variable cost</p>
              <p className="text-lg font-light text-[#D6A653]">{usd(d.total_estimated_cost)}</p>
              <p className="mt-1 text-[10px] text-white/40">Cost-to-revenue ratio: {d.cost_to_revenue_ratio != null ? d.cost_to_revenue_ratio : "n/a (revenue not authoritative)"}</p>
            </div>
            <p className="text-[10px] text-white/35">Internal cost data — Super Admin only. Never shown to customers.</p>
          </div>
        )}
      </div>
    </div>
  );
};
