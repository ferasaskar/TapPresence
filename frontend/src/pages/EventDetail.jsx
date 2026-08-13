import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { OwnerNav } from "@/components/admin/OwnerNav";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Loader2, ArrowLeft, CalendarDays, MapPin, Users, User, Search, TrendingUp, UserPlus, RefreshCw, CalendarCheck, Trophy, Coins, Pencil, Check } from "lucide-react";
import { toast } from "sonner";
import { useLocale } from "@/i18n/useLocale";

const fmtDate = (d) => (d ? new Date(d + "T00:00:00").toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" }) : "");
const fmtDT = (iso) => (iso ? new Date(iso).toLocaleString([], { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }) : "");
const STAGES = ["new", "contacted", "qualified", "meeting", "opportunity", "customer", "not_interested"];
const ALIAS = { meeting_booked: "meeting", converted: "customer", archived: "not_interested", won: "customer", lost: "not_interested", follow_up: "contacted" };
const stageOf = (l) => { const s = ALIAS[(l.status || "new").toLowerCase()] || (l.status || "new").toLowerCase(); return STAGES.includes(s) ? s : "new"; };
const STAGE_BADGE = {
  new: "text-[#D6A653] border-[#D6A653]/40 bg-[#D6A653]/10", contacted: "text-sky-300 border-sky-400/40 bg-sky-400/10",
  qualified: "text-amber-300 border-amber-400/40 bg-amber-400/10", meeting: "text-violet-300 border-violet-400/40 bg-violet-400/10",
  opportunity: "text-fuchsia-300 border-fuchsia-400/40 bg-fuchsia-400/10", customer: "text-emerald-300 border-emerald-400/40 bg-emerald-400/10",
  not_interested: "text-white/50 border-white/20 bg-white/5",
};

const Kpi = ({ icon: Icon, label, value, sub, testid }) => (
  <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-4" data-testid={testid}>
    <div className="flex items-center gap-2 text-xs text-white/45">{Icon ? <Icon className="h-3.5 w-3.5 text-[#D6A653]" /> : null} {label}</div>
    <div className="mt-1.5 text-2xl font-light text-white">{value}</div>
    {sub ? <div className="mt-0.5 text-[11px] text-white/40">{sub}</div> : null}
  </div>
);

export default function EventDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { t } = useLocale();
  const sLabel = (st) => t(`leads.stage_${st}`, { defaultValue: st });
  const capLabel = (k) => t(`leads.source_${k}`, { defaultValue: (k || "").replace(/_/g, " ") });
  const [dash, setDash] = useState(null);
  const [leads, setLeads] = useState([]);
  const [err, setErr] = useState(false);
  const [q, setQ] = useState("");
  const [stage, setStage] = useState("all");
  const [method, setMethod] = useState("all");
  const [nr, setNr] = useState("all");
  const [lbSort, setLbSort] = useState("leads");
  const [editCost, setEditCost] = useState(false);
  const [costForm, setCostForm] = useState({ event_cost: "", event_cost_currency: "AED" });

  const load = () => {
    api.get(`/events/${id}/dashboard`).then(({ data }) => {
      setDash(data);
      setCostForm({ event_cost: data.cost.event_cost ?? "", event_cost_currency: data.cost.currency || "AED" });
    }).catch(() => setErr(true));
    api.get(`/events/${id}`).then(({ data }) => setLeads(data.leads || [])).catch(() => {});
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [id]);

  const saveCost = async () => {
    try {
      await api.patch(`/events/${id}`, { event_cost: costForm.event_cost === "" ? null : Number(costForm.event_cost), event_cost_currency: costForm.event_cost_currency });
      toast.success(t("eventDash.costSaved")); setEditCost(false); load();
    } catch { toast.error(t("events.createFailed")); }
  };

  const filtered = useMemo(() => {
    let list = leads;
    if (stage !== "all") list = list.filter((l) => stageOf(l) === stage);
    if (method !== "all") list = list.filter((l) => (l.source || "inquiry") === method);
    if (nr !== "all") list = list.filter((l) => (l.new_returning || "new") === nr);
    if (q.trim()) { const s = q.toLowerCase(); list = list.filter((l) => [l.name, l.email, l.company, l.title].some((v) => (v || "").toLowerCase().includes(s))); }
    return list;
  }, [leads, stage, method, nr, q]);

  const leaderboard = useMemo(() => {
    if (!dash) return [];
    const arr = [...dash.leaderboard];
    arr.sort((a, b) => (b[lbSort] || 0) - (a[lbSort] || 0));
    return arr;
  }, [dash, lbSort]);

  const maxDaily = dash ? Math.max(1, ...dash.daily_trend.map((d) => d.leads)) : 1;
  const maxPipe = dash ? Math.max(1, ...dash.pipeline.map((p) => p.count)) : 1;

  return (
    <div className="aria-dark relative min-h-screen bg-[#050607] text-white" style={{ fontFamily: "'Outfit', sans-serif" }} data-testid="event-detail-page">
      <div className="grain-overlay" style={{ opacity: 0.04 }} />
      <OwnerNav active="events" />
      <main className="relative mx-auto max-w-6xl px-4 py-8 sm:px-8">
        <button onClick={() => navigate("/events")} className="mb-5 flex items-center gap-2 text-sm text-white/50 hover:text-white" data-testid="event-detail-back"><ArrowLeft className="h-4 w-4" /> {t("events.backToEvents")}</button>

        {err ? (
          <div className="rounded-2xl border border-dashed border-white/12 py-20 text-center text-white/50" data-testid="event-detail-error">{t("events.notFound")}</div>
        ) : !dash ? (
          <div className="flex justify-center py-20"><Loader2 className="h-6 w-6 animate-spin text-[#D6A653]" /></div>
        ) : (() => {
          const ev = dash.event; const k = dash.kpis; const total = k.total_leads;
          return (
          <>
            {/* Header */}
            <div className="mb-5 rounded-2xl border border-white/10 bg-white/[0.02] p-5" data-testid="event-detail-header">
              <div className="flex items-center gap-2">
                <h2 className="text-2xl font-light tracking-tight text-white">{ev.name}</h2>
                <span className={`rounded-full border px-2 py-0.5 text-[11px] ${ev.status === "active" ? "border-emerald-400/40 bg-emerald-400/10 text-emerald-300" : "border-white/20 bg-white/5 text-white/50"}`}>{t(`eventDash.status_${ev.status}`, { defaultValue: ev.status })}</span>
              </div>
              <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-white/55">
                {ev.location ? <span className="flex items-center gap-1.5"><MapPin className="h-4 w-4 text-[#D6A653]" /> {ev.location}</span> : null}
                {ev.start_date ? <span className="flex items-center gap-1.5"><CalendarDays className="h-4 w-4 text-[#D6A653]" /> {fmtDate(ev.start_date)}{ev.end_date ? ` – ${fmtDate(ev.end_date)}` : ""}</span> : null}
                {ev.days ? <span>{t("eventDash.days", { count: ev.days })}</span> : null}
                {ev.created_by_name ? <span className="flex items-center gap-1.5"><User className="h-4 w-4 text-white/40" /> {ev.created_by_name}</span> : null}
                <span className="text-white/35">{dash.timezone}</span>
              </div>
            </div>

            {/* KPI cards */}
            <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4" data-testid="event-kpis">
              <Kpi icon={Users} label={t("eventDash.totalLeads")} value={k.total_leads} testid="kpi-total" />
              <Kpi icon={UserPlus} label={t("eventDash.newContacts")} value={k.new_contacts} sub={dash.new_vs_returning.new_pct + "%"} testid="kpi-new" />
              <Kpi icon={RefreshCw} label={t("eventDash.returning")} value={k.returning_contacts} sub={dash.new_vs_returning.returning_pct + "%"} testid="kpi-returning" />
              <Kpi icon={CalendarCheck} label={t("eventDash.meetings")} value={k.meetings_booked} sub={t("eventDash.meetingRate", { rate: dash.conversion.meeting_rate })} testid="kpi-meetings" />
              <Kpi icon={TrendingUp} label={t("eventDash.customers")} value={k.customers} testid="kpi-customers" />
              <Kpi icon={TrendingUp} label={t("eventDash.conversion")} value={k.conversion_rate + "%"} testid="kpi-conversion" />
              <Kpi label={t("eventDash.followupsDue")} value={k.followups_due + k.followups_overdue} sub={k.followups_overdue ? t("eventDash.overdue", { count: k.followups_overdue }) : ""} testid="kpi-followups-due" />
              <Kpi label={t("eventDash.followupsCompleted")} value={k.followups_completed} testid="kpi-followups-done" />
            </div>

            <div className="grid gap-6 lg:grid-cols-2">
              {/* Pipeline distribution */}
              <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5" data-testid="event-pipeline">
                <p className="mb-3 text-xs uppercase tracking-wider text-[#D6A653]">{t("eventDash.pipeline")}</p>
                <div className="space-y-2">
                  {dash.pipeline.map((p) => (
                    <button key={p.stage} onClick={() => setStage(stage === p.stage ? "all" : p.stage)} data-testid={`pipe-${p.stage}`}
                      className={`flex w-full items-center gap-3 rounded-lg px-2 py-1.5 text-left transition-colors ${stage === p.stage ? "bg-[#D6A653]/10" : "hover:bg-white/5"}`}>
                      <span className="w-24 shrink-0 text-xs text-white/70">{sLabel(p.stage)}</span>
                      <span className="h-2 flex-1 overflow-hidden rounded-full bg-white/8"><span className="block h-full rounded-full bg-[#D6A653]" style={{ width: `${(p.count / maxPipe) * 100}%` }} /></span>
                      <span className="w-8 shrink-0 text-right text-xs text-white/70">{p.count}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Capture methods */}
              <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5" data-testid="event-capture-methods">
                <p className="mb-3 text-xs uppercase tracking-wider text-[#D6A653]">{t("eventDash.captureMethods")}</p>
                {dash.capture_methods.length === 0 ? <p className="text-sm text-white/40">{t("eventDash.noData")}</p> : (
                  <div className="space-y-2">
                    {dash.capture_methods.map((c) => (
                      <div key={c.key} className="flex items-center gap-3" data-testid={`cap-${c.key}`}>
                        <span className="w-28 shrink-0 truncate text-xs text-white/70">{capLabel(c.key)}</span>
                        <span className="h-2 flex-1 overflow-hidden rounded-full bg-white/8"><span className="block h-full rounded-full bg-sky-400/70" style={{ width: `${c.pct}%` }} /></span>
                        <span className="w-16 shrink-0 text-right text-xs text-white/60">{c.count} · {c.pct}%</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Daily trend */}
              <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5" data-testid="event-daily-trend">
                <p className="mb-3 text-xs uppercase tracking-wider text-[#D6A653]">{t("eventDash.dailyTrend")}</p>
                {dash.daily_trend.length === 0 ? <p className="text-sm text-white/40">{t("eventDash.noData")}</p> : (
                  <div className="flex items-end gap-2 overflow-x-auto pb-1" style={{ minHeight: 120 }}>
                    {dash.daily_trend.map((d) => (
                      <div key={d.date} className="flex min-w-[36px] flex-1 flex-col items-center gap-1" data-testid={`day-${d.date}`}>
                        <span className="text-[11px] text-white/60">{d.leads}</span>
                        <span className="w-full rounded-t bg-[#D6A653]/70" style={{ height: `${Math.max(6, (d.leads / maxDaily) * 90)}px` }} />
                        <span className="text-[10px] text-white/40">{new Date(d.date + "T00:00:00").toLocaleDateString([], { month: "short", day: "numeric" })}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Cost & ROI */}
              <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5" data-testid="event-cost">
                <div className="mb-3 flex items-center justify-between">
                  <p className="text-xs uppercase tracking-wider text-[#D6A653]">{t("eventDash.costRoi")}</p>
                  <button onClick={() => setEditCost(!editCost)} className="text-white/40 hover:text-white" data-testid="event-cost-edit"><Pencil className="h-3.5 w-3.5" /></button>
                </div>
                {editCost ? (
                  <div className="flex items-center gap-2">
                    <input type="number" value={costForm.event_cost} onChange={(e) => setCostForm((f) => ({ ...f, event_cost: e.target.value }))} placeholder="25000" className="h-9 w-32 rounded-lg border border-white/12 bg-[#0A0B0D] px-2 text-sm text-white focus:border-[#D6A653]/50 focus:outline-none" data-testid="event-cost-input" />
                    <Select value={costForm.event_cost_currency} onValueChange={(v) => setCostForm((f) => ({ ...f, event_cost_currency: v }))}>
                      <SelectTrigger className="h-9 w-24 text-sm" data-testid="event-cost-currency"><SelectValue /></SelectTrigger>
                      <SelectContent className="aria-pop">{["AED", "USD", "EUR", "GBP", "SAR"].map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
                    </Select>
                    <button onClick={saveCost} className="rounded-lg bg-[#D6A653] px-3 py-2 text-xs font-medium text-black" data-testid="event-cost-save"><Check className="h-4 w-4" /></button>
                  </div>
                ) : (
                  <div className="grid grid-cols-2 gap-y-2 text-sm">
                    <span className="text-white/45">{t("eventDash.eventCost")}</span>
                    <span className="text-right text-white/85" data-testid="event-cost-value">{dash.cost.event_cost ? `${dash.cost.currency} ${Number(dash.cost.event_cost).toLocaleString()}` : t("eventDash.notSet")}</span>
                    <span className="text-white/45">{t("eventDash.attributedRevenue")}</span>
                    <span className="text-right text-white/40">{t("eventDash.notAvailable")}</span>
                    <span className="text-white/45">{t("eventDash.roi")}</span>
                    <span className="text-right text-white/40">{t("eventDash.notAvailable")}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Team leaderboard */}
            <div className="mt-6 rounded-2xl border border-white/10 bg-white/[0.02] p-5" data-testid="event-leaderboard">
              <div className="mb-3 flex items-center justify-between">
                <p className="flex items-center gap-1.5 text-xs uppercase tracking-wider text-[#D6A653]"><Trophy className="h-3.5 w-3.5" /> {t("eventDash.teamPerformance")}</p>
                <Select value={lbSort} onValueChange={setLbSort}>
                  <SelectTrigger className="h-8 w-36 text-xs" data-testid="lb-sort"><SelectValue /></SelectTrigger>
                  <SelectContent className="aria-pop">
                    <SelectItem value="leads">{t("eventDash.sortLeads")}</SelectItem>
                    <SelectItem value="meetings">{t("eventDash.sortMeetings")}</SelectItem>
                    <SelectItem value="customers">{t("eventDash.sortCustomers")}</SelectItem>
                    <SelectItem value="conversion_rate">{t("eventDash.sortConversion")}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              {leaderboard.length === 0 ? <p className="text-sm text-white/40">{t("eventDash.noTeamData")}</p> : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead><tr className="text-left text-[11px] uppercase tracking-wider text-white/40">
                      <th className="py-2 pr-3">{t("eventDash.member")}</th><th className="px-2">{t("eventDash.leads")}</th>
                      <th className="px-2">{t("eventDash.new")}</th><th className="px-2">{t("eventDash.returning")}</th>
                      <th className="px-2">{t("eventDash.meetings")}</th><th className="px-2">{t("eventDash.customers")}</th><th className="px-2">{t("eventDash.conv")}</th>
                    </tr></thead>
                    <tbody>
                      {leaderboard.map((r) => (
                        <tr key={r.user_id} className="border-t border-white/6 text-white/80" data-testid={`lb-row-${r.user_id}`}>
                          <td className="py-2 pr-3 text-white">{r.name}</td><td className="px-2">{r.leads}</td>
                          <td className="px-2">{r.new}</td><td className="px-2">{r.returning}</td>
                          <td className="px-2">{r.meetings}</td><td className="px-2">{r.customers}</td><td className="px-2">{r.conversion_rate}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Lead table */}
            <div className="mt-6" data-testid="event-leads-section">
              <p className="mb-3 text-xs uppercase tracking-wider text-white/45">{t("events.capturedLeads")}</p>
              <div className="mb-3 grid grid-cols-2 gap-2 sm:flex sm:flex-wrap">
                <div className="relative col-span-2 sm:w-48"><Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-white/35" /><input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("leads.search")} className="h-9 w-full rounded-lg border border-white/12 bg-[#0A0B0D] pl-9 pr-3 text-sm text-white placeholder:text-white/30 focus:border-[#D6A653]/50 focus:outline-none" data-testid="event-lead-search" /></div>
                <Select value={stage} onValueChange={setStage}><SelectTrigger className="h-9 text-xs" data-testid="event-lead-filter-stage"><SelectValue placeholder={t("leads.pipelineStage")} /></SelectTrigger><SelectContent className="aria-pop"><SelectItem value="all">{t("eventDash.allStages")}</SelectItem>{STAGES.map((s) => <SelectItem key={s} value={s}>{sLabel(s)}</SelectItem>)}</SelectContent></Select>
                <Select value={method} onValueChange={setMethod}><SelectTrigger className="h-9 text-xs" data-testid="event-lead-filter-method"><SelectValue placeholder={t("leads.source")} /></SelectTrigger><SelectContent className="aria-pop"><SelectItem value="all">{t("leads.allSources")}</SelectItem>{dash.capture_methods.map((c) => <SelectItem key={c.key} value={c.key}>{capLabel(c.key)}</SelectItem>)}</SelectContent></Select>
                <Select value={nr} onValueChange={setNr}><SelectTrigger className="h-9 text-xs" data-testid="event-lead-filter-nr"><SelectValue placeholder={t("eventDash.newReturning")} /></SelectTrigger><SelectContent className="aria-pop"><SelectItem value="all">{t("eventDash.allContacts")}</SelectItem><SelectItem value="new">{t("eventDash.newContacts")}</SelectItem><SelectItem value="returning">{t("eventDash.returning")}</SelectItem></SelectContent></Select>
              </div>
              {filtered.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-white/12 py-14 text-center text-white/50" data-testid="event-leads-empty">{t("events.noLeads")}</div>
              ) : (
                <div className="space-y-2" data-testid="event-leads-list">
                  {filtered.map((l) => {
                    const st = stageOf(l);
                    return (
                      <button key={l.id} onClick={() => navigate(`/leads?lead=${l.id}`)} data-testid={`event-lead-${l.id}`}
                        className="flex w-full items-center justify-between gap-3 rounded-xl border border-white/10 bg-white/[0.02] p-3.5 text-left transition-all hover:border-[#D6A653]/40">
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <p className="truncate font-medium text-white">{l.name}</p>
                            <span className={`shrink-0 rounded-full border px-1.5 py-0.5 text-[10px] ${l.new_returning === "returning" ? "border-sky-400/40 bg-sky-400/10 text-sky-300" : "border-emerald-400/40 bg-emerald-400/10 text-emerald-300"}`}>{l.new_returning === "returning" ? t("eventDash.returning") : t("eventDash.new")}</span>
                          </div>
                          <p className="truncate text-xs text-white/50">{[l.title, l.company].filter(Boolean).join(" · ") || l.email || l.phone}</p>
                          <p className="mt-1 flex flex-wrap items-center gap-x-3 text-[11px] text-white/40">
                            {l.captured_by_name ? <span className="flex items-center gap-1"><User className="h-3 w-3" /> {l.captured_by_name}</span> : null}
                            <span>{capLabel(l.source || "inquiry")}</span>
                            <span>{fmtDT(l.captured_at || l.created_at)}</span>
                            {l.has_meeting ? <span className="text-violet-300">{t("eventDash.hasMeeting")}</span> : null}
                            {l.follow_up_completed_at ? <span className="text-emerald-300">{t("eventDash.followedUp")}</span> : l.next_follow_up ? <span className="text-amber-300">{t("eventDash.followUpSet")}</span> : null}
                          </p>
                        </div>
                        <span className={`shrink-0 rounded-full border px-2.5 py-0.5 text-[11px] ${STAGE_BADGE[st]}`}>{sLabel(st)}</span>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          </>
          );
        })()}
      </main>
    </div>
  );
}
