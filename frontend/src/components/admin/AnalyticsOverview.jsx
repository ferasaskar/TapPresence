import { TrendingUp, Eye, MousePointerClick, Inbox, CalendarDays, CheckCircle2 } from "lucide-react";

const STEPS = [
  { key: "views", label: "Profile views", icon: Eye },
  { key: "engaged", label: "Engaged (taps)", icon: MousePointerClick },
  { key: "leads", label: "Leads captured", icon: Inbox },
  { key: "meetings_booked", label: "Meetings booked", icon: CalendarDays },
  { key: "meetings_completed", label: "Completed", icon: CheckCircle2 },
];

const ACTION_LABELS = {
  cta_exchange: "Exchange Contact",
  cta_book: "Book a Meeting",
  cta_message: "Send Message",
  call: "Call",
  whatsapp: "WhatsApp",
  email: "Email",
  message: "Message",
  booking_opened: "Booking opened",
  contact_exchanged: "Contact exchanged",
  wallet_apple: "Apple Wallet",
  wallet_google: "Google Wallet",
  other: "Other",
};

const Sparkline = ({ series }) => {
  if (!series || series.length < 2) return null;
  const max = Math.max(...series.map((p) => p.count), 1);
  const w = 100, h = 28;
  const pts = series.map((p, i) => {
    const x = (i / (series.length - 1)) * w;
    const y = h - (p.count / max) * (h - 3) - 1.5;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
  return (
    <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" className="h-8 w-full" data-testid="overview-sparkline">
      <polyline points={pts} fill="none" stroke="#D6A653" strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
    </svg>
  );
};

export const AnalyticsOverview = ({ data }) => {
  if (!data) return null;
  const f = data.funnel || {};
  const maxVal = Math.max(f.views || 0, 1);
  const pct = (num, den) => (den > 0 ? Math.round((num / den) * 100) : 0);

  return (
    <div className="rounded-2xl border border-white/10 bg-[#0A0B0D] p-5" data-testid="analytics-overview">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="flex items-center gap-2 text-sm font-medium text-white">
          <TrendingUp className="h-4 w-4 text-[#D6A653]" /> Conversion funnel
        </h3>
        <span className="text-[11px] uppercase tracking-wide text-white/40">Last {data.range_days} days</span>
      </div>

      <div className="space-y-2.5" data-testid="overview-funnel">
        {STEPS.map((s, i) => {
          const val = f[s.key] || 0;
          const prev = i === 0 ? null : f[STEPS[i - 1].key] || 0;
          const Icon = s.icon;
          return (
            <div key={s.key} data-testid={`funnel-${s.key}`}>
              <div className="mb-1 flex items-center justify-between text-xs">
                <span className="flex items-center gap-1.5 text-white/70"><Icon className="h-3.5 w-3.5 text-[#D6A653]" /> {s.label}</span>
                <span className="flex items-center gap-2">
                  <span className="font-semibold text-white">{val.toLocaleString()}</span>
                  {prev !== null && <span className="text-[10px] text-white/35">{pct(val, prev)}%</span>}
                </span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-white/[0.04]">
                <div className="h-full rounded-full" style={{ width: `${Math.max((val / maxVal) * 100, val > 0 ? 4 : 0)}%`, background: "linear-gradient(90deg,#8A6A2B,#D6A653,#E8B764)" }} />
              </div>
            </div>
          );
        })}
      </div>

      {data.series?.length >= 2 && (
        <div className="mt-5">
          <p className="mb-1 text-[11px] uppercase tracking-wide text-white/40">Views &amp; scans trend</p>
          <Sparkline series={data.series} />
        </div>
      )}

      {data.top_actions?.length > 0 && (
        <div className="mt-5" data-testid="overview-top-actions">
          <p className="mb-2 text-[11px] uppercase tracking-wide text-white/40">Top actions</p>
          <div className="flex flex-wrap gap-2">
            {data.top_actions.map((a) => (
              <span key={a.key} className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.03] px-2.5 py-1 text-[11px] text-white/70" data-testid={`top-action-${a.key}`}>
                {ACTION_LABELS[a.key] || a.key} <span className="font-semibold text-[#D6A653]">{a.count}</span>
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
