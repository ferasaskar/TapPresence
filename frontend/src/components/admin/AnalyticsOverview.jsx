import { TrendingUp, Eye, MousePointerClick, Inbox, CalendarDays, CheckCircle2, QrCode, Nfc, Link2, Tag, Megaphone, Users, CreditCard, ScanLine } from "lucide-react";
import { useLocale } from "@/i18n/useLocale";

const STEP_KEYS = [
  { key: "views", tkey: "funnel.views", icon: Eye },
  { key: "engaged", tkey: "funnel.engaged", icon: MousePointerClick },
  { key: "leads", tkey: "funnel.leads", icon: Inbox },
  { key: "meetings_booked", tkey: "funnel.booked", icon: CalendarDays },
  { key: "meetings_completed", tkey: "funnel.completed", icon: CheckCircle2 },
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
  const { t, formatNumber } = useLocale();
  if (!data) return null;
  const f = data.funnel || {};
  const maxVal = Math.max(f.views || 0, 1);
  const pct = (num, den) => (den > 0 ? Math.round((num / den) * 100) : 0);
  const STEPS = STEP_KEYS.map((s) => ({ ...s, label: t(s.tkey) }));

  return (
    <div className="rounded-2xl border border-white/10 bg-[#0A0B0D] p-5" data-testid="analytics-overview">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="flex items-center gap-2 text-sm font-medium text-white">
          <TrendingUp className="h-4 w-4 text-[#D6A653]" /> {t("funnel.title")}
        </h3>
        <span className="text-[11px] uppercase tracking-wide text-white/40">{t("funnel.range", { days: data.range_days })}</span>
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
                  <span className="font-semibold text-white">{formatNumber(val)}</span>
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
          <p className="mb-1 text-[11px] uppercase tracking-wide text-white/40">{t("funnel.trend")}</p>
          <Sparkline series={data.series} />
        </div>
      )}

      {data.top_actions?.length > 0 && (
        <div className="mt-5" data-testid="overview-top-actions">
          <p className="mb-2 text-[11px] uppercase tracking-wide text-white/40">{t("funnel.topActions")}</p>
          <div className="flex flex-wrap gap-2">
            {data.top_actions.map((a) => (
              <span key={a.key} className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.03] px-2.5 py-1 text-[11px] text-white/70" data-testid={`top-action-${a.key}`}>
                {ACTION_LABELS[a.key] || a.key} <span className="font-semibold text-[#D6A653]">{a.count}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      <AnalyticsBreakdowns data={data} t={t} formatNumber={formatNumber} />
    </div>
  );
};

const Chip = ({ label, value, testId }) => (
  <span className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.03] px-2.5 py-1 text-[11px] text-white/70" data-testid={testId}>
    {label} <span className="font-semibold text-[#D6A653]">{value}</span>
  </span>
);

const Section = ({ icon: Icon, title, testId, children }) => (
  <div className="mt-5" data-testid={testId}>
    <p className="mb-2 flex items-center gap-1.5 text-[11px] uppercase tracking-wide text-white/40"><Icon className="h-3.5 w-3.5 text-[#D6A653]" /> {title}</p>
    {children}
  </div>
);

const AnalyticsBreakdowns = ({ data, t, formatNumber }) => {
  const ch = data.channels || {};
  const b = data.breakdowns || {};
  const anyChannel = (ch.direct || 0) + (ch.qr || 0) + (ch.nfc || 0) > 0;
  return (
    <>
      {anyChannel && (
        <Section icon={Link2} title={t("analytics.byChannel", { defaultValue: "Traffic by channel" })} testId="breakdown-channels">
          <div className="flex flex-wrap gap-2">
            <Chip label={<><Link2 className="mr-1 inline h-3 w-3" />{t("analytics.direct", { defaultValue: "Direct / link" })}</>} value={formatNumber(ch.direct || 0)} testId="channel-direct" />
            <Chip label={<><QrCode className="mr-1 inline h-3 w-3" />{t("analytics.qr", { defaultValue: "QR" })}</>} value={formatNumber(ch.qr || 0)} testId="channel-qr" />
            <Chip label={<><Nfc className="mr-1 inline h-3 w-3" />{t("analytics.nfc", { defaultValue: "NFC" })}</>} value={formatNumber(ch.nfc || 0)} testId="channel-nfc" />
            <Chip label={<><ScanLine className="mr-1 inline h-3 w-3" />{t("analytics.scanner", { defaultValue: "Scanner leads" })}</>} value={formatNumber(b.scanner_leads || 0)} testId="channel-scanner" />
          </div>
        </Section>
      )}

      {b.by_card?.length > 1 && (
        <Section icon={CreditCard} title={t("analytics.byCard", { defaultValue: "By card" })} testId="breakdown-cards">
          <div className="space-y-1.5">
            {b.by_card.map((c) => (
              <div key={c.slug} className="flex items-center justify-between rounded-lg border border-white/8 bg-white/[0.02] px-3 py-1.5 text-xs" data-testid={`bd-card-${c.slug}`}>
                <span className="min-w-0 truncate text-white/75">{c.name} <span className="text-white/30">/{c.slug}</span></span>
                <span className="flex shrink-0 gap-3 text-[11px] text-white/50">
                  <span title={t("analytics.views", { defaultValue: "Views" })}><Eye className="mr-0.5 inline h-3 w-3" />{formatNumber(c.views)}</span>
                  <span title={t("analytics.leads", { defaultValue: "Leads" })}><Inbox className="mr-0.5 inline h-3 w-3" />{formatNumber(c.leads)}</span>
                  <span title={t("analytics.meetings", { defaultValue: "Meetings" })}><CalendarDays className="mr-0.5 inline h-3 w-3" />{formatNumber(c.meetings)}</span>
                </span>
              </div>
            ))}
          </div>
        </Section>
      )}

      {b.by_source?.length > 0 && (
        <Section icon={Tag} title={t("analytics.bySource", { defaultValue: "Leads by source" })} testId="breakdown-source">
          <div className="flex flex-wrap gap-2">
            {b.by_source.map((s) => <Chip key={s.key} label={t(`leads.source_${s.key}`, { defaultValue: (s.key || "inquiry").replace(/_/g, " ") })} value={s.count} testId={`bd-source-${s.key}`} />)}
          </div>
        </Section>
      )}

      {b.by_event?.length > 0 && (
        <Section icon={Megaphone} title={t("analytics.byEvent", { defaultValue: "Leads by event" })} testId="breakdown-event">
          <div className="flex flex-wrap gap-2">
            {b.by_event.map((s) => <Chip key={s.key} label={s.key} value={s.count} testId={`bd-event-${s.key}`} />)}
          </div>
        </Section>
      )}

      {b.by_campaign?.length > 0 && (
        <Section icon={Megaphone} title={t("analytics.byCampaign", { defaultValue: "Leads by campaign" })} testId="breakdown-campaign">
          <div className="flex flex-wrap gap-2">
            {b.by_campaign.map((s) => <Chip key={s.key} label={s.key} value={s.count} testId={`bd-campaign-${s.key}`} />)}
          </div>
        </Section>
      )}

      {b.by_member?.length > 0 && (
        <Section icon={Users} title={t("analytics.byMember", { defaultValue: "Captured by team member" })} testId="breakdown-member">
          <div className="flex flex-wrap gap-2">
            {b.by_member.map((s) => <Chip key={s.key} label={s.name} value={s.count} testId={`bd-member-${s.key}`} />)}
          </div>
        </Section>
      )}
    </>
  );
};
