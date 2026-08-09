import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useLocale } from "@/i18n/useLocale";
import { OwnerNav } from "@/components/admin/OwnerNav";
import { Loader2, Building2, Users, CreditCard, Inbox, CalendarDays, Eye, Palette, ShieldCheck } from "lucide-react";

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

            <button onClick={() => navigate("/industry-studio")} data-testid="goto-industry-studio" className="mt-6 flex w-full items-center justify-between rounded-2xl border border-white/10 bg-[#0A0B0D] p-5 text-left transition-colors hover:border-[#D6A653]/40">
              <span className="flex items-center gap-3"><Palette className="h-5 w-5 text-[#D6A653]" /><span><span className="block text-sm font-medium text-white">Industry Studio</span><span className="block text-xs text-white/45">Customize industry visual presets across the platform</span></span></span>
              <span className="text-[#D6A653]">→</span>
            </button>
          </>
        )}
      </main>
    </div>
  );
}
