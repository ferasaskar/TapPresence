import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useLocale } from "@/i18n/useLocale";
import { OwnerNav } from "@/components/admin/OwnerNav";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Loader2, Clock, User, Mail, Phone, Sparkles, Copy, Check, X, RotateCw, CalendarClock, CheckCircle2, UserX, Eye, List as ListIcon, CalendarDays, ChevronLeft, ChevronRight, Bell, ExternalLink } from "lucide-react";
import { toast } from "sonner";

const LABEL = { requested: "Pending Approval", time_proposed: "New Time Proposed", scheduled: "Confirmed", confirmed: "Confirmed", rescheduled: "Confirmed", completed: "Completed", cancelled: "Cancelled", declined: "Declined", "no-show": "No-show" };
const STATUS_KEY = { requested: "requested", time_proposed: "time_proposed", scheduled: "confirmed", confirmed: "confirmed", rescheduled: "confirmed", completed: "completed", cancelled: "cancelled", declined: "declined", "no-show": "noshow" };
const STATUS_OPTS = [["Pending Approval", "requested"], ["New Time Proposed", "time_proposed"], ["Confirmed", "confirmed"], ["Completed", "completed"], ["Cancelled", "cancelled"], ["Declined", "declined"], ["No-show", "noshow"]];
const badge = (s) => ({
  requested: "text-[#D6A653] border-[#D6A653]/40 bg-[#D6A653]/10", time_proposed: "text-violet-300 border-violet-400/40 bg-violet-400/10",
  scheduled: "text-emerald-300 border-emerald-400/40 bg-emerald-400/10", confirmed: "text-emerald-300 border-emerald-400/40 bg-emerald-400/10", rescheduled: "text-emerald-300 border-emerald-400/40 bg-emerald-400/10",
  completed: "text-sky-300 border-sky-400/40 bg-sky-400/10", cancelled: "text-red-300 border-red-400/40 bg-red-400/10", declined: "text-red-300 border-red-400/40 bg-red-400/10", "no-show": "text-orange-300 border-orange-400/40 bg-orange-400/10",
}[s] || "text-white/60 border-white/20 bg-white/5");
const ACTIVE = ["scheduled", "confirmed", "rescheduled"];
const PENDING = ["requested", "time_proposed"];
const fmt = (iso, tz) => new Date(iso).toLocaleString([], { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit", timeZone: tz });
const fmtDay = (d) => new Date(d + "T12:00:00").toLocaleDateString([], { weekday: "short", month: "short", day: "numeric" });
const fmtTime = (iso, tz) => new Date(iso).toLocaleTimeString([], { hour: "numeric", minute: "2-digit", timeZone: tz });
const dayKey = (iso, tz) => new Date(iso).toLocaleDateString("en-CA", { timeZone: tz || "UTC" });

const Act = ({ children, onClick, testId, tone = "default", disabled }) => {
  const tones = { default: "border-white/15 text-white hover:bg-white/5", ok: "border-emerald-400/40 text-emerald-300 hover:bg-emerald-400/10", danger: "border-red-400/40 text-red-300 hover:bg-red-500/10", gold: "border-[#D6A653]/50 text-[#D6A653] hover:bg-[#D6A653]/10" };
  return <button onClick={(e) => { e.stopPropagation(); onClick(); }} disabled={disabled} data-testid={testId} className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs transition-colors disabled:opacity-50 ${tones[tone]}`}>{children}</button>;
};

export default function Meetings() {
  const navigate = useNavigate();
  const { t } = useLocale();
  const sLabel = (s) => t(`meetings.status_${STATUS_KEY[s] || "requested"}`, { defaultValue: LABEL[s] || s });
  const [all, setAll] = useState(null);
  const [cards, setCards] = useState([]);
  const [tab, setTab] = useState("upcoming");
  const [view, setView] = useState("list");
  const [fType, setFType] = useState("all");
  const [fStatus, setFStatus] = useState("all");
  const [fCard, setFCard] = useState("all");
  const [month, setMonth] = useState(() => { const d = new Date(); return new Date(d.getFullYear(), d.getMonth(), 1); });
  const [selDay, setSelDay] = useState(null);
  const [detail, setDetail] = useState(null);
  const [picker, setPicker] = useState(null);
  const [busy, setBusy] = useState("");
  const [draft, setDraft] = useState({});

  const load = () => {
    setAll(null);
    Promise.all(["upcoming", "past", "cancelled"].map((f) => api.get("/admin/meetings", { params: { filter: f } }).then((r) => r.data).catch(() => [])))
      .then((lists) => { const map = {}; lists.flat().forEach((m) => (map[m.id] = m)); setAll(Object.values(map)); });
    api.get("/admin/cards").then(({ data }) => setCards(data)).catch(() => {});
  };
  useEffect(() => { load(); }, []);

  const isToday = (m) => dayKey(m.start_utc, m.owner_timezone) === new Date().toLocaleDateString("en-CA", { timeZone: m.owner_timezone || "UTC" });
  const buckets = useMemo(() => {
    const a = all || []; const now = Date.now();
    return {
      today: a.filter((m) => isToday(m) && ![...PENDING, "cancelled", "declined", "completed", "no-show"].includes(m.status)),
      upcoming: a.filter((m) => new Date(m.start_utc).getTime() >= now && ACTIVE.includes(m.status)),
      pending: a.filter((m) => PENDING.includes(m.status)),
      completed: a.filter((m) => m.status === "completed"),
    };
  }, [all]);

  const tabList = buckets[tab] || [];
  const types = useMemo(() => [...new Set((all || []).map((m) => m.meeting_type_title))], [all]);
  const multiCard = cards.length > 1;
  const filtered = useMemo(() => {
    let l = tabList;
    if (fType !== "all") l = l.filter((m) => m.meeting_type_title === fType);
    if (fStatus !== "all") l = l.filter((m) => (LABEL[m.status] || m.status) === fStatus);
    if (fCard !== "all") l = l.filter((m) => m.cardSlug === fCard);
    if (selDay && view === "calendar") l = (all || []).filter((m) => dayKey(m.start_utc, m.owner_timezone) === selDay);
    return [...l].sort((a, b) => new Date(a.start_utc) - new Date(b.start_utc));
  }, [tabList, fType, fStatus, fCard, selDay, view, all]);

  const setStatus = async (m, status) => {
    setBusy(m.id);
    try { await api.patch(`/admin/meetings/${m.id}/status`, { status }); toast.success(sLabel(status)); setDetail(null); load(); }
    catch (e) { toast.error(e.response?.data?.detail || "Could not update"); } finally { setBusy(""); }
  };
  const openPicker = (m, kind) => setPicker({ id: m.id, kind, slug: m.cardSlug, mtId: m.meeting_type_id, tz: m.owner_timezone, date: "", slots: [], loading: false });
  const pickDate = async (d) => {
    setPicker((p) => ({ ...p, date: d, slots: [], loading: true }));
    try { const { data } = await api.get(`/cards/${picker.slug}/slots`, { params: { meeting_type_id: picker.mtId, date: d } }); setPicker((p) => ({ ...p, slots: data.slots || [], loading: false })); }
    catch { setPicker((p) => ({ ...p, slots: [], loading: false })); }
  };
  const submitSlot = async (start) => {
    const { id, kind } = picker; setBusy(id);
    try { await api.post(kind === "propose" ? `/admin/meetings/${id}/propose` : `/admin/meetings/${id}/reschedule`, { start }); toast.success(kind === "propose" ? "New time proposed" : "Rescheduled"); setPicker(null); setDetail(null); load(); }
    catch (e) { toast.error(e.response?.data?.detail || "Could not update"); } finally { setBusy(""); }
  };
  const aiFollowup = async (m) => {
    setDraft((d) => ({ ...d, [m.id]: "…" }));
    try { const { data } = await api.post("/ai/followup", { lead_name: m.visitor_name, company: "", notes: `${m.meeting_type_title} meeting`, owner_name: m.owner_name, tone: "professional", channel: "email", language: "en" }); setDraft((d) => ({ ...d, [m.id]: data.draft })); }
    catch { setDraft((d) => ({ ...d, [m.id]: "" })); toast.error("Could not draft"); }
  };

  const days = Array.from({ length: 21 }, (_, i) => { const d = new Date(); d.setDate(d.getDate() + i); return d.toISOString().slice(0, 10); });

  const actionsFor = (m, compact) => {
    const s = m.status;
    if (s === "requested" || s === "time_proposed") {
      return (<>
        {s === "requested" && <Act tone="ok" onClick={() => setStatus(m, "confirmed")} testId={`meeting-accept-${m.id}`} disabled={busy === m.id}><Check className="h-3.5 w-3.5" /> {t("meetings.accept")}</Act>}
        {s === "requested" && <Act tone="danger" onClick={() => setStatus(m, "declined")} testId={`meeting-decline-${m.id}`} disabled={busy === m.id}><X className="h-3.5 w-3.5" /> {t("meetings.decline")}</Act>}
        <Act tone="gold" onClick={() => openPicker(m, "propose")} testId={`meeting-propose-${m.id}`}><CalendarClock className="h-3.5 w-3.5" /> {s === "time_proposed" ? t("meetings.revise") : t("meetings.proposeNew")}</Act>
        {s === "time_proposed" && <Act tone="danger" onClick={() => setStatus(m, "cancelled")} testId={`meeting-cancel-${m.id}`} disabled={busy === m.id}><X className="h-3.5 w-3.5" /> {t("meetings.cancel")}</Act>}
      </>);
    }
    if (ACTIVE.includes(s)) {
      const startMs = new Date(m.start_utc).getTime(); const endMs = startMs + (Number(m.duration) || 30) * 60000; const now = Date.now();
      return (<>
        <Act onClick={() => openPicker(m, "reschedule")} testId={`meeting-reschedule-${m.id}`}><RotateCw className="h-3.5 w-3.5" /> {t("meetings.reschedule")}</Act>
        {now >= endMs && <Act tone="ok" onClick={() => setStatus(m, "completed")} testId={`meeting-complete-${m.id}`} disabled={busy === m.id}><CheckCircle2 className="h-3.5 w-3.5" /> {t("meetings.completedBtn")}</Act>}
        {now >= startMs + 15 * 60000 && <Act onClick={() => setStatus(m, "no-show")} testId={`meeting-noshow-${m.id}`} disabled={busy === m.id}><UserX className="h-3.5 w-3.5" /> {t("meetings.noShow")}</Act>}
        <Act tone="danger" onClick={() => setStatus(m, "cancelled")} testId={`meeting-cancel-${m.id}`} disabled={busy === m.id}><X className="h-3.5 w-3.5" /> {t("meetings.cancel")}</Act>
      </>);
    }
    if (s === "completed") return (<>
      {m.lead_id && <Act onClick={() => navigate(`/leads?lead=${m.lead_id}`)} testId={`meeting-viewlead-${m.id}`}><Eye className="h-3.5 w-3.5" /> {t("meetings.viewLead")}</Act>}
      <Act tone="gold" onClick={() => aiFollowup(m)} testId={`meeting-ai-${m.id}`}><Sparkles className="h-3.5 w-3.5" /> {t("meetings.aiFollowup")}</Act>
    </>);
    return m.lead_id ? <Act onClick={() => navigate(`/leads?lead=${m.lead_id}`)} testId={`meeting-viewlead-${m.id}`}><Eye className="h-3.5 w-3.5" /> {t("meetings.viewLead")}</Act> : <span className="text-xs text-white/35">{t("meetings.readOnly")}</span>;
  };

  const summary = [
    { key: "today", label: t("meetings.today"), count: buckets.today?.length || 0 },
    { key: "upcoming", label: t("meetings.upcoming"), count: buckets.upcoming?.length || 0 },
    { key: "pending", label: t("meetings.pending"), count: buckets.pending?.length || 0 },
    { key: "completed", label: t("meetings.completed"), count: buckets.completed?.length || 0 },
  ];

  // calendar grid
  const grid = useMemo(() => {
    const first = new Date(month.getFullYear(), month.getMonth(), 1);
    const start = new Date(first); start.setDate(1 - first.getDay());
    return Array.from({ length: 42 }, (_, i) => { const d = new Date(start); d.setDate(start.getDate() + i); return d; });
  }, [month]);
  const countByDay = useMemo(() => { const c = {}; (all || []).forEach((m) => { const k = dayKey(m.start_utc, m.owner_timezone); c[k] = (c[k] || 0) + 1; }); return c; }, [all]);

  return (
    <div className="aria-dark relative min-h-screen bg-[#050607] text-white" style={{ fontFamily: "'Outfit', sans-serif" }} data-testid="meetings-page">
      <div className="grain-overlay" style={{ opacity: 0.04 }} />
      <OwnerNav active="meetings" />

      <main className="relative mx-auto max-w-5xl px-4 py-8 sm:px-8">
        <div className="mb-5 flex items-center justify-between">
          <div><h2 className="text-2xl font-light tracking-tight text-white">{t("meetings.title")}</h2><p className="text-sm text-white/45">{t("meetings.subtitle")}</p></div>
          <div className="flex rounded-full border border-white/12 p-0.5">
            <button onClick={() => { setView("list"); setSelDay(null); }} className={`flex items-center gap-1 rounded-full px-3 py-1.5 text-xs ${view === "list" ? "bg-[#D6A653] text-black" : "text-white/60"}`} data-testid="view-list"><ListIcon className="h-3.5 w-3.5" /> {t("meetings.list")}</button>
            <button onClick={() => setView("calendar")} className={`flex items-center gap-1 rounded-full px-3 py-1.5 text-xs ${view === "calendar" ? "bg-[#D6A653] text-black" : "text-white/60"}`} data-testid="view-calendar"><CalendarDays className="h-3.5 w-3.5" /> {t("meetings.calendar")}</button>
          </div>
        </div>

        {/* summary */}
        <div className="mb-5 grid grid-cols-2 gap-2 sm:grid-cols-4" data-testid="meetings-summary">
          {summary.map((s) => (
            <button key={s.key} onClick={() => { setTab(s.key); setView("list"); setSelDay(null); }} data-testid={`summary-${s.key}`}
              className={`rounded-2xl border p-4 text-left transition-all ${tab === s.key && view === "list" ? "border-[#D6A653] bg-[#D6A653]/10" : "border-white/10 bg-[#0A0B0D] hover:border-white/25"}`}>
              <p className="text-2xl font-semibold text-white">{s.count}</p>
              <p className="text-[11px] uppercase tracking-wide text-white/50">{s.label}</p>
            </button>
          ))}
        </div>

        {/* filters */}
        <div className="mb-5 flex flex-wrap gap-2">
          <Select value={fType} onValueChange={setFType}><SelectTrigger className="h-9 w-40 text-xs" data-testid="filter-type"><SelectValue placeholder={t("meetings.type")} /></SelectTrigger><SelectContent className="aria-pop"><SelectItem value="all">{t("meetings.allTypes")}</SelectItem>{types.map((ty) => <SelectItem key={ty} value={ty}>{ty}</SelectItem>)}</SelectContent></Select>
          <Select value={fStatus} onValueChange={setFStatus}><SelectTrigger className="h-9 w-40 text-xs" data-testid="filter-status"><SelectValue placeholder={t("meetings.status")} /></SelectTrigger><SelectContent className="aria-pop"><SelectItem value="all">{t("meetings.allStatuses")}</SelectItem>{STATUS_OPTS.map(([val, key]) => <SelectItem key={val} value={val}>{t(`meetings.status_${key}`)}</SelectItem>)}</SelectContent></Select>
          {multiCard ? <Select value={fCard} onValueChange={setFCard}><SelectTrigger className="h-9 w-40 text-xs" data-testid="filter-card"><SelectValue placeholder={t("meetings.card")} /></SelectTrigger><SelectContent className="aria-pop"><SelectItem value="all">{t("meetings.allCards")}</SelectItem>{cards.map((c) => <SelectItem key={c.slug} value={c.slug}>/{c.slug}</SelectItem>)}</SelectContent></Select> : null}
        </div>

        {all === null ? (
          <div className="flex justify-center py-20"><Loader2 className="h-6 w-6 animate-spin text-[#D6A653]" /></div>
        ) : view === "calendar" ? (
          <div className="rounded-2xl border border-white/10 bg-[#0A0B0D] p-4" data-testid="calendar-view">
            <div className="mb-3 flex items-center justify-between">
              <button onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() - 1, 1))} className="rounded-lg p-1.5 text-white/60 hover:bg-white/5" data-testid="cal-prev"><ChevronLeft className="h-4 w-4" /></button>
              <span className="text-sm font-medium">{month.toLocaleDateString([], { month: "long", year: "numeric" })}</span>
              <button onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() + 1, 1))} className="rounded-lg p-1.5 text-white/60 hover:bg-white/5" data-testid="cal-next"><ChevronRight className="h-4 w-4" /></button>
            </div>
            <div className="grid grid-cols-7 gap-1 text-center text-[10px] uppercase text-white/35">{["S", "M", "T", "W", "T", "F", "S"].map((d, i) => <div key={i}>{d}</div>)}</div>
            <div className="mt-1 grid grid-cols-7 gap-1">
              {grid.map((d, i) => {
                const k = d.toLocaleDateString("en-CA"); const n = countByDay[k] || 0; const inMonth = d.getMonth() === month.getMonth();
                return (
                  <button key={i} onClick={() => setSelDay(k)} className={`flex aspect-square flex-col items-center justify-center rounded-lg border text-xs ${selDay === k ? "border-[#D6A653] bg-[#D6A653]/15" : "border-white/6"} ${inMonth ? "text-white/80" : "text-white/25"}`} data-testid={`cal-day-${k}`}>
                    {d.getDate()}
                    {n > 0 ? <span className="mt-0.5 h-1.5 w-1.5 rounded-full bg-[#D6A653]" /> : null}
                  </button>
                );
              })}
            </div>
            <div className="mt-4 space-y-2">
              {selDay ? (filtered.length ? filtered.map((m) => <Row key={m.id} m={m} onOpen={() => setDetail(m)} actions={actionsFor} badge={badge} sLabel={sLabel} />) : <p className="py-4 text-center text-sm text-white/45">{t("meetings.noMeetingsDay", { day: selDay })}</p>) : <p className="py-4 text-center text-sm text-white/45">{t("meetings.selectDay")}</p>}
            </div>
          </div>
        ) : filtered.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-white/12 py-20 text-center text-white/50" data-testid="meetings-empty">{t("meetings.noMeetings", { tab: t(`meetings.${tab}`) })}</div>
        ) : (
          <div className="space-y-3">
            {filtered.map((m) => (
              <div key={m.id}>
                <Row m={m} onOpen={() => setDetail(m)} actions={actionsFor} badge={badge} sLabel={sLabel} />
                {picker && picker.id === m.id && (
                  <div className="mt-2 rounded-xl border border-white/10 bg-white/[0.03] p-4" data-testid={`meeting-picker-${m.id}`}>
                    <div className="mb-2 flex items-center justify-between"><p className="text-xs text-white/60">{picker.kind === "propose" ? t("meetings.proposeTitle") : t("meetings.pickTitle")} ({m.owner_timezone})</p><button onClick={() => setPicker(null)} className="text-xs text-white/50 hover:text-white">{t("meetings.cancel")}</button></div>
                    <div className="flex gap-2 overflow-x-auto pb-2">{days.map((d) => <button key={d} onClick={() => pickDate(d)} className={`shrink-0 rounded-xl border px-3 py-2 text-xs ${picker.date === d ? "bg-[#D6A653] text-black" : "border-white/14 text-white/70"}`}>{fmtDay(d)}</button>)}</div>
                    {picker.loading ? <div className="flex justify-center py-3"><Loader2 className="h-5 w-5 animate-spin text-[#D6A653]" /></div> : picker.date ? (picker.slots.length === 0 ? <p className="py-2 text-center text-xs text-white/50">{t("meetings.noTimes")}</p> : <div className="grid grid-cols-4 gap-2 sm:grid-cols-6">{picker.slots.map((sl) => <button key={sl} onClick={() => submitSlot(sl)} disabled={busy === m.id} className="rounded-lg border border-[#D6A653]/50 bg-[#D6A653]/10 py-2 text-xs text-white">{fmtTime(sl, m.owner_timezone)}</button>)}</div>) : <p className="text-center text-xs text-white/45">{t("meetings.pickDay")}</p>}
                  </div>
                )}
                {draft[m.id] !== undefined ? (draft[m.id] === "…" ? <div className="mt-2 flex items-center gap-2 text-xs text-white/50"><Loader2 className="h-3.5 w-3.5 animate-spin" /> {t("meetings.drafting")}</div> : draft[m.id] ? (
                  <div className="mt-2 rounded-lg border border-white/10 bg-white/[0.03] p-3"><textarea readOnly value={draft[m.id]} rows={5} className="w-full resize-none bg-transparent text-sm text-white/85 focus:outline-none" data-testid={`meeting-draft-${m.id}`} /><button onClick={() => { navigator.clipboard.writeText(draft[m.id]); toast.success(t("meetings.copied")); }} className="mt-1 flex items-center gap-1 text-xs text-[#D6A653]"><Copy className="h-3 w-3" /> {t("meetings.copyReview")}</button></div>
                ) : null) : null}
              </div>
            ))}
          </div>
        )}
      </main>

      {/* detail modal */}
      <Dialog open={!!detail} onOpenChange={(v) => !v && setDetail(null)}>
        <DialogContent className="aria-dark max-h-[88vh] max-w-md overflow-y-auto border-white/10 bg-[#0A0B0D] text-white" data-testid="meeting-detail">
          {detail ? (<>
            <DialogHeader><DialogTitle className="flex items-center gap-2 text-white">{detail.meeting_type_title} <span className={`rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-wider ${badge(detail.status)}`}>{sLabel(detail.status)}</span></DialogTitle></DialogHeader>
            <div className="space-y-4 text-sm">
              <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
                <p className="flex items-center gap-1.5 text-white/85"><User className="h-3.5 w-3.5 text-[#D6A653]" /> {detail.visitor_name}</p>
                {detail.visitor_email ? <p className="mt-1 flex items-center gap-1.5 text-xs text-white/60"><Mail className="h-3 w-3" /> {detail.visitor_email}</p> : null}
                {detail.visitor_phone ? <p className="mt-1 flex items-center gap-1.5 text-xs text-white/60"><Phone className="h-3 w-3" /> {detail.visitor_phone}</p> : null}
              </div>
              <div className="grid grid-cols-2 gap-y-2 rounded-xl border border-white/10 bg-white/[0.02] p-4 text-xs">
                <span className="text-white/45">{t("meetings.when")}</span><span className="text-right text-white/85">{fmt(detail.start_utc, detail.owner_timezone)}</span>
                <span className="text-white/45">{t("meetings.timezone")}</span><span className="text-right text-white/85">{detail.owner_timezone}</span>
                <span className="text-white/45">{t("meetings.sourceCard")}</span><span className="text-right text-[#D6A653]">/{detail.cardSlug}</span>
                {detail.proposed_start_utc ? <><span className="text-white/45">{t("meetings.proposed")}</span><span className="text-right text-violet-300">{fmt(detail.proposed_start_utc, detail.owner_timezone)}</span></> : null}
              </div>
              {detail.note ? <p className="rounded-xl border border-white/10 bg-white/[0.02] p-3 text-white/70">“{detail.note}”</p> : null}
              <div className="flex flex-wrap gap-2">{actionsFor(detail)}</div>
              {Array.isArray(detail.reminders) && detail.reminders.length ? (
                <div className="text-xs text-white/45"><p className="mb-1 flex items-center gap-1"><Bell className="h-3 w-3 text-[#D6A653]" /> {t("meetings.reminders")}</p>{detail.reminders.map((r, i) => <span key={i} className="mr-2">{r.offset_hours}h: {r.provider === "NOT_CONFIGURED" ? t("meetings.notConfigured") : r.status}</span>)}</div>
              ) : null}
              {detail.lead_id ? <button onClick={() => navigate(`/leads?lead=${detail.lead_id}`)} className="flex items-center gap-1.5 text-xs text-[#D6A653] hover:underline" data-testid="detail-lead-link"><ExternalLink className="h-3.5 w-3.5" /> {t("meetings.openLead")}</button> : null}
              {Array.isArray(detail.history) && detail.history.length ? (
                <div><p className="mb-1 text-xs uppercase tracking-wider text-[#D6A653]">{t("meetings.history")}</p><ul className="space-y-0.5 text-xs text-white/55">{detail.history.map((h, i) => <li key={i}>{(h.event || "").replace("status:", "")} · {new Date(h.at).toLocaleString([], { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })}{h.by ? ` · ${h.by}` : ""}</li>)}</ul></div>
              ) : null}
            </div>
          </>) : null}
        </DialogContent>
      </Dialog>
    </div>
  );
}

const Row = ({ m, onOpen, actions, badge, sLabel }) => (
  <div onClick={onOpen} className="cursor-pointer rounded-2xl border border-white/10 bg-[#0A0B0D] p-5 transition-colors hover:border-white/25" data-testid={`meeting-${m.id}`}>
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-medium text-white">{m.meeting_type_title}</span>
          <span className={`rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-wider ${badge(m.status)}`} data-testid={`meeting-statuslabel-${m.id}`}>{sLabel(m.status)}</span>
        </div>
        <p className="mt-1 text-sm text-white/70"><Clock className="mr-1 inline h-3.5 w-3.5 text-[#D6A653]" />{fmt(m.start_utc, m.owner_timezone)} <span className="text-white/40">({m.owner_timezone})</span></p>
        <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-white/50">
          <span className="flex items-center gap-1"><User className="h-3 w-3" /> {m.visitor_name}</span>
          {m.visitor_email ? <span className="flex items-center gap-1"><Mail className="h-3 w-3" /> {m.visitor_email}</span> : null}
          <span className="text-white/30">/{m.cardSlug}</span>
        </div>
      </div>
      <div className="flex flex-wrap justify-end gap-2" data-testid={`meeting-actions-${m.id}`}>{actions(m)}</div>
    </div>
  </div>
);
