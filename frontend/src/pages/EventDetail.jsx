import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { OwnerNav } from "@/components/admin/OwnerNav";
import { Loader2, ArrowLeft, CalendarDays, MapPin, Users, User } from "lucide-react";
import { useLocale } from "@/i18n/useLocale";

const fmtDate = (d) => (d ? new Date(d + "T00:00:00").toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" }) : "");
const norm = (s) => (s || "new").toLowerCase();
const STAGE_BADGE = {
  new: "text-[#D6A653] border-[#D6A653]/40 bg-[#D6A653]/10",
  contacted: "text-sky-300 border-sky-400/40 bg-sky-400/10",
  qualified: "text-amber-300 border-amber-400/40 bg-amber-400/10",
  meeting: "text-violet-300 border-violet-400/40 bg-violet-400/10",
  opportunity: "text-fuchsia-300 border-fuchsia-400/40 bg-fuchsia-400/10",
  customer: "text-emerald-300 border-emerald-400/40 bg-emerald-400/10",
  not_interested: "text-white/50 border-white/20 bg-white/5",
};

export default function EventDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { t } = useLocale();
  const sLabel = (st) => t(`leads.stage_${st}`, { defaultValue: st });
  const [data, setData] = useState(null);
  const [err, setErr] = useState(false);

  useEffect(() => {
    api.get(`/events/${id}`).then(({ data }) => setData(data)).catch(() => setErr(true));
  }, [id]);

  return (
    <div className="aria-dark relative min-h-screen bg-[#050607] text-white" style={{ fontFamily: "'Outfit', sans-serif" }} data-testid="event-detail-page">
      <div className="grain-overlay" style={{ opacity: 0.04 }} />
      <OwnerNav active="events" />

      <main className="relative mx-auto max-w-4xl px-4 py-8 sm:px-8">
        <button onClick={() => navigate("/events")} className="mb-5 flex items-center gap-2 text-sm text-white/50 hover:text-white" data-testid="event-detail-back"><ArrowLeft className="h-4 w-4" /> {t("events.backToEvents")}</button>

        {err ? (
          <div className="rounded-2xl border border-dashed border-white/12 py-20 text-center text-white/50" data-testid="event-detail-error">{t("events.notFound")}</div>
        ) : data === null ? (
          <div className="flex justify-center py-20"><Loader2 className="h-6 w-6 animate-spin text-[#D6A653]" /></div>
        ) : (
          <>
            <div className="mb-6 rounded-2xl border border-white/10 bg-white/[0.02] p-5" data-testid="event-detail-header">
              <h2 className="text-2xl font-light tracking-tight text-white">{data.event.name}</h2>
              <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-white/55">
                {data.event.location ? <span className="flex items-center gap-1.5"><MapPin className="h-4 w-4 text-[#D6A653]" /> {data.event.location}</span> : null}
                {data.event.start_date ? <span className="flex items-center gap-1.5"><CalendarDays className="h-4 w-4 text-[#D6A653]" /> {fmtDate(data.event.start_date)}{data.event.end_date ? ` – ${fmtDate(data.event.end_date)}` : ""}</span> : null}
                <span className="flex items-center gap-1.5"><Users className="h-4 w-4 text-[#D6A653]" /> {t("events.leadsCount", { count: data.lead_count })}</span>
              </div>
              {data.event.notes ? <p className="mt-3 text-sm text-white/60">{data.event.notes}</p> : null}
            </div>

            <p className="mb-3 text-xs uppercase tracking-wider text-white/45">{t("events.capturedLeads")}</p>
            {data.leads.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-white/12 py-16 text-center text-white/50" data-testid="event-leads-empty">{t("events.noLeads")}</div>
            ) : (
              <div className="space-y-2" data-testid="event-leads-list">
                {data.leads.map((l) => {
                  const st = norm(l.status);
                  return (
                    <button key={l.id} onClick={() => navigate(`/leads?lead=${l.id}`)} data-testid={`event-lead-${l.id}`}
                      className="flex w-full items-center justify-between gap-3 rounded-xl border border-white/10 bg-white/[0.02] p-3.5 text-left transition-all hover:border-[#D6A653]/40">
                      <div className="min-w-0">
                        <p className="truncate font-medium text-white">{l.name}</p>
                        <p className="truncate text-xs text-white/50">{[l.title, l.company].filter(Boolean).join(" · ") || l.email || l.phone}</p>
                        {l.captured_by_name ? <p className="mt-1 flex items-center gap-1 text-[11px] text-white/40"><User className="h-3 w-3" /> {t("events.capturedBy", { name: l.captured_by_name })}</p> : null}
                      </div>
                      <span className={`shrink-0 rounded-full border px-2.5 py-0.5 text-[11px] ${STAGE_BADGE[st] || STAGE_BADGE.new}`}>{sLabel(st)}</span>
                    </button>
                  );
                })}
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
