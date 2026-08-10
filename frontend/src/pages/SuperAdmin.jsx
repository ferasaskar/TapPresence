import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useLocale } from "@/i18n/useLocale";
import { OwnerNav } from "@/components/admin/OwnerNav";
import { Loader2, Building2, Users, CreditCard, Inbox, CalendarDays, Eye, Palette, ShieldCheck, Search, Ban, CheckCircle2 } from "lucide-react";

const UserSupport = () => {
  const [q, setQ] = useState("");
  const [rows, setRows] = useState(null);
  const [busy, setBusy] = useState("");
  const search = async () => {
    setRows(null);
    try { const { data } = await api.get("/admin/platform/users", { params: { q } }); setRows(data.items || []); }
    catch { setRows([]); }
  };
  useEffect(() => { search(); }, []); // eslint-disable-line
  const toggle = async (u) => {
    setBusy(u.id);
    try { await api.post(`/admin/platform/users/${u.id}/suspend`, { suspended: !u.suspended }); setRows((rs) => rs.map((x) => x.id === u.id ? { ...x, suspended: !x.suspended } : x)); }
    catch (_) {} finally { setBusy(""); }
  };
  return (
    <div className="mt-6 rounded-2xl border border-white/10 bg-[#0A0B0D] p-5" data-testid="user-support">
      <h3 className="mb-3 flex items-center gap-2 text-sm font-medium text-white"><Users className="h-4 w-4 text-[#D6A653]" /> Users &amp; Support</h3>
      <div className="mb-4 flex gap-2">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-white/30" />
          <input value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && search()} placeholder="Search by name or email…" className="h-10 w-full rounded-lg border border-white/12 bg-[#050607] pl-9 pr-3 text-sm text-white placeholder:text-white/30 focus:border-[#D6A653]/50 focus:outline-none" data-testid="user-search-input" />
        </div>
        <button onClick={search} className="rounded-lg bg-[#D6A653] px-4 text-sm font-medium text-[#050607] hover:bg-[#E8B764]" data-testid="user-search-btn">Search</button>
      </div>
      {rows === null ? <div className="py-8 text-center"><Loader2 className="mx-auto h-5 w-5 animate-spin text-[#D6A653]" /></div>
        : rows.length === 0 ? <p className="py-6 text-center text-sm text-white/45">No users found.</p>
        : (
          <div className="space-y-2">
            {rows.map((u) => (
              <div key={u.id} className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-white/8 bg-[#050607] px-4 py-2.5" data-testid={`user-row-${u.id}`}>
                <div className="min-w-0">
                  <p className="truncate text-sm text-white">{u.name} {u.role === "SUPER_ADMIN" ? <span className="ml-1 rounded bg-[#D6A653]/15 px-1.5 py-0.5 text-[9px] uppercase text-[#D6A653]">admin</span> : null} {u.suspended ? <span className="ml-1 rounded bg-red-500/15 px-1.5 py-0.5 text-[9px] uppercase text-red-300">suspended</span> : null}</p>
                  <p className="truncate text-xs text-white/45">{u.email} · {u.workspace || "—"} · {u.plan || "—"} · {u.status || "—"} · {u.email_verified ? "verified" : "unverified"}</p>
                </div>
                {u.role !== "SUPER_ADMIN" ? (
                  <button onClick={() => toggle(u)} disabled={busy === u.id} className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs disabled:opacity-60 ${u.suspended ? "border-emerald-400/30 bg-emerald-500/10 text-emerald-300" : "border-red-400/30 bg-red-500/10 text-red-300"}`} data-testid={`user-suspend-${u.id}`}>
                    {u.suspended ? <><CheckCircle2 className="h-3.5 w-3.5" /> Reinstate</> : <><Ban className="h-3.5 w-3.5" /> Suspend</>}
                  </button>
                ) : null}
              </div>
            ))}
          </div>
        )}
    </div>
  );
};

const Metric = ({ icon: Icon, label, value, sub }) => (
  <div className="rounded-2xl border border-white/10 bg-[#0A0B0D] p-4" data-testid={`metric-${label.toLowerCase().replace(/ /g, "-")}`}>
    <Icon className="mb-2 h-4 w-4 text-[#D6A653]" />
    <p className="text-2xl font-light text-white">{value ?? "—"}</p>
    <p className="text-xs text-white/45">{label}{sub ? <span className="text-white/30"> · {sub}</span> : null}</p>
  </div>
);

export default function SuperAdmin() {
  const { user } = useAuth();
  const { formatNumber } = useLocale();
  const navigate = useNavigate();
  const [d, setD] = useState(undefined);
  const isSuper = user?.role === "SUPER_ADMIN";

  useEffect(() => {
    if (!isSuper) { setD(null); return; }
    api.get("/admin/platform/overview").then(({ data }) => setD(data)).catch(() => setD(null));
  }, [isSuper]);

  return (
    <div className="aria-dark relative min-h-screen bg-[#050607] text-white" style={{ fontFamily: "'Outfit', sans-serif" }} data-testid="superadmin-page">
      <div className="grain-overlay" style={{ opacity: 0.04 }} />
      <OwnerNav active="command" />
      <main className="relative mx-auto max-w-5xl px-4 py-8 sm:px-8">
        <h2 className="flex items-center gap-2 text-2xl font-light tracking-tight text-white"><ShieldCheck className="h-5 w-5 text-[#D6A653]" /> Command Center</h2>
        <p className="mt-1 text-sm text-white/45">Platform-wide business metrics · live data.</p>

        {!isSuper ? (
          <div className="mt-8 rounded-2xl border border-dashed border-white/12 py-24 text-center text-white/55" data-testid="superadmin-denied">Super admin only.</div>
        ) : d === undefined ? (
          <div className="flex justify-center py-24"><Loader2 className="h-6 w-6 animate-spin text-[#D6A653]" /></div>
        ) : d === null ? (
          <div className="mt-8 rounded-2xl border border-dashed border-white/12 py-24 text-center text-white/55">Could not load metrics.</div>
        ) : (
          <>
            <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4" data-testid="platform-metrics">
              <Metric icon={Building2} label="Workspaces" value={formatNumber(d.workspaces)} />
              <Metric icon={Users} label="Users" value={formatNumber(d.users)} sub={`${formatNumber(d.memberships)} memberships`} />
              <Metric icon={CreditCard} label="Cards" value={formatNumber(d.cards)} sub={`${formatNumber(d.cards_published)} published`} />
              <Metric icon={Inbox} label="Leads" value={formatNumber(d.leads)} />
              <Metric icon={CalendarDays} label="Meetings" value={formatNumber(d.meetings)} />
              <Metric icon={Eye} label="Views 30d" value={formatNumber(d.views_30d)} />
            </div>

            <div className="mt-6 grid gap-4 lg:grid-cols-2">
              <div className="rounded-2xl border border-white/10 bg-[#0A0B0D] p-5" data-testid="plan-distribution">
                <h3 className="mb-4 text-sm font-medium text-white">Plan distribution</h3>
                <div className="space-y-2">
                  {Object.entries(d.plan_distribution || {}).map(([plan, n]) => {
                    const total = Object.values(d.plan_distribution).reduce((a, b) => a + b, 0) || 1;
                    return (
                      <div key={plan}>
                        <div className="mb-1 flex justify-between text-xs"><span className="capitalize text-white/70">{plan}</span><span className="text-white/50">{n}</span></div>
                        <div className="h-2 overflow-hidden rounded-full bg-white/[0.04]"><div className="h-full rounded-full" style={{ width: `${(n / total) * 100}%`, background: "linear-gradient(90deg,#8A6A2B,#D6A653)" }} /></div>
                      </div>
                    );
                  })}
                </div>
              </div>
              <div className="rounded-2xl border border-white/10 bg-[#0A0B0D] p-5" data-testid="meetings-by-status">
                <h3 className="mb-4 text-sm font-medium text-white">Meetings by status</h3>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(d.meetings_by_status || {}).map(([s, n]) => (
                    <span key={s} className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.03] px-2.5 py-1 text-xs text-white/70"><span className="capitalize">{s.replace(/_/g, " ")}</span><span className="font-semibold text-[#D6A653]">{n}</span></span>
                  ))}
                </div>
              </div>
            </div>

            <button onClick={() => navigate("/admin/commercial")} data-testid="goto-commercial" className="mt-6 flex w-full items-center justify-between rounded-2xl border border-white/10 bg-[#0A0B0D] p-5 text-left transition-colors hover:border-[#D6A653]/40">
              <span className="flex items-center gap-3"><CreditCard className="h-5 w-5 text-[#D6A653]" /><span><span className="block text-sm font-medium text-white">Commercial &amp; Pricing</span><span className="block text-xs text-white/45">Manage plans, trial, referral and regional pricing</span></span></span>
              <span className="text-[#D6A653]">→</span>
            </button>

            <button onClick={() => navigate("/industry-studio")} data-testid="goto-industry-studio" className="mt-6 flex w-full items-center justify-between rounded-2xl border border-white/10 bg-[#0A0B0D] p-5 text-left transition-colors hover:border-[#D6A653]/40">
              <span className="flex items-center gap-3"><Palette className="h-5 w-5 text-[#D6A653]" /><span><span className="block text-sm font-medium text-white">Industry Studio</span><span className="block text-xs text-white/45">Customize industry visual presets across the platform</span></span></span>
              <span className="text-[#D6A653]">→</span>
            </button>

            <UserSupport />
          </>
        )}
      </main>
    </div>
  );
}
