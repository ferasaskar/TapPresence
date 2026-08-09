import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { Loader2, ArrowLeft, Clock, User, Mail, Phone, CalendarDays, Sparkles, Copy, Check, X, RotateCw, CalendarClock, CheckCircle2, UserX, Eye } from "lucide-react";
import { toast } from "sonner";

const TABS = ["today", "upcoming", "past", "cancelled"];

// internal status -> human-readable label (never expose raw enums)
const LABEL = {
  requested: "Pending Approval",
  time_proposed: "New Time Proposed",
  scheduled: "Confirmed",
  confirmed: "Confirmed",
  rescheduled: "Confirmed",
  completed: "Completed",
  cancelled: "Cancelled",
  declined: "Declined",
  "no-show": "No-show",
};
const badge = (s) => ({
  requested: "text-[#D6A653] border-[#D6A653]/40 bg-[#D6A653]/10",
  time_proposed: "text-violet-300 border-violet-400/40 bg-violet-400/10",
  scheduled: "text-emerald-300 border-emerald-400/40 bg-emerald-400/10",
  confirmed: "text-emerald-300 border-emerald-400/40 bg-emerald-400/10",
  rescheduled: "text-emerald-300 border-emerald-400/40 bg-emerald-400/10",
  completed: "text-sky-300 border-sky-400/40 bg-sky-400/10",
  cancelled: "text-red-300 border-red-400/40 bg-red-400/10",
  declined: "text-red-300 border-red-400/40 bg-red-400/10",
  "no-show": "text-orange-300 border-orange-400/40 bg-orange-400/10",
}[s] || "text-white/60 border-white/20 bg-white/5");

const ACTIVE = ["scheduled", "confirmed", "rescheduled"];
const fmt = (iso, tz) => new Date(iso).toLocaleString([], { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit", timeZone: tz });
const fmtDay = (d) => new Date(d + "T12:00:00").toLocaleDateString([], { weekday: "short", month: "short", day: "numeric" });
const fmtTime = (iso, tz) => new Date(iso).toLocaleTimeString([], { hour: "numeric", minute: "2-digit", timeZone: tz });

const Act = ({ children, onClick, testId, tone = "default", disabled }) => {
  const tones = {
    default: "border-white/15 text-white hover:bg-white/5",
    ok: "border-emerald-400/40 text-emerald-300 hover:bg-emerald-400/10",
    danger: "border-red-400/40 text-red-300 hover:bg-red-500/10",
    gold: "border-[#D6A653]/50 text-[#D6A653] hover:bg-[#D6A653]/10",
  };
  return <button onClick={onClick} disabled={disabled} data-testid={testId} className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs transition-colors disabled:opacity-50 ${tones[tone]}`}>{children}</button>;
};

export default function Meetings() {
  const navigate = useNavigate();
  const [tab, setTab] = useState("upcoming");
  const [items, setItems] = useState(null);
  const [draft, setDraft] = useState({});
  const [details, setDetails] = useState({});     // meetingId -> bool (expanded)
  const [picker, setPicker] = useState(null);      // { id, kind: 'propose'|'reschedule', slug, mtId, date, slots, loading }
  const [busy, setBusy] = useState("");

  const load = () => {
    setItems(null);
    api.get("/admin/meetings", { params: { filter: tab } }).then(({ data }) => setItems(data)).catch(() => setItems([]));
  };
  useEffect(() => { load(); setPicker(null); }, [tab]); // eslint-disable-line

  const setStatus = async (m, status) => {
    setBusy(m.id);
    try { await api.patch(`/admin/meetings/${m.id}/status`, { status }); toast.success(LABEL[status] ? `Marked ${LABEL[status]}` : "Updated"); load(); }
    catch (e) { toast.error(e.response?.data?.detail || "Could not update"); }
    finally { setBusy(""); }
  };

  const openPicker = (m, kind) => setPicker({ id: m.id, kind, slug: m.cardSlug, mtId: m.meeting_type_id, tz: m.owner_timezone, date: "", slots: [], loading: false });
  const pickDate = async (d) => {
    setPicker((p) => ({ ...p, date: d, slots: [], loading: true }));
    try { const { data } = await api.get(`/cards/${picker.slug}/slots`, { params: { meeting_type_id: picker.mtId, date: d } }); setPicker((p) => ({ ...p, slots: data.slots || [], loading: false })); }
    catch { setPicker((p) => ({ ...p, slots: [], loading: false })); }
  };
  const submitSlot = async (start) => {
    const { id, kind } = picker;
    setBusy(id);
    try {
      const url = kind === "propose" ? `/admin/meetings/${id}/propose` : `/admin/meetings/${id}/reschedule`;
      await api.post(url, { start });
      toast.success(kind === "propose" ? "New time proposed — guest will be asked to accept" : "Meeting rescheduled");
      setPicker(null); load();
    } catch (e) { toast.error(e.response?.data?.detail || "Could not update"); }
    finally { setBusy(""); }
  };

  const aiFollowup = async (m) => {
    setDraft((d) => ({ ...d, [m.id]: "…" }));
    try {
      const { data } = await api.post("/ai/followup", { lead_name: m.visitor_name, company: "", notes: `${m.meeting_type_title} meeting on ${fmt(m.start_utc, m.owner_timezone)}`, owner_name: m.owner_name, tone: "professional", channel: "email", language: "en" });
      setDraft((d) => ({ ...d, [m.id]: data.draft }));
    } catch { setDraft((d) => ({ ...d, [m.id]: "" })); toast.error("Could not draft"); }
  };

  const days = Array.from({ length: 21 }, (_, i) => { const d = new Date(); d.setDate(d.getDate() + i); return d.toISOString().slice(0, 10); });

  const renderActions = (m) => {
    const s = m.status;
    if (s === "requested") return (
      <div className="flex flex-wrap justify-end gap-2" data-testid={`meeting-actions-${m.id}`}>
        <Act tone="ok" onClick={() => setStatus(m, "confirmed")} testId={`meeting-accept-${m.id}`} disabled={busy === m.id}><Check className="h-3.5 w-3.5" /> Accept</Act>
        <Act tone="danger" onClick={() => setStatus(m, "declined")} testId={`meeting-decline-${m.id}`} disabled={busy === m.id}><X className="h-3.5 w-3.5" /> Decline</Act>
        <Act tone="gold" onClick={() => openPicker(m, "propose")} testId={`meeting-propose-${m.id}`}><CalendarClock className="h-3.5 w-3.5" /> Propose New Time</Act>
      </div>
    );
    if (s === "time_proposed") return (
      <div className="flex flex-wrap justify-end gap-2" data-testid={`meeting-actions-${m.id}`}>
        <Act tone="gold" onClick={() => openPicker(m, "propose")} testId={`meeting-revise-${m.id}`}><CalendarClock className="h-3.5 w-3.5" /> Revise proposal</Act>
        <Act tone="danger" onClick={() => setStatus(m, "cancelled")} testId={`meeting-cancel-${m.id}`} disabled={busy === m.id}><X className="h-3.5 w-3.5" /> Cancel</Act>
      </div>
    );
    if (ACTIVE.includes(s)) {
      const startMs = new Date(m.start_utc).getTime();
      const endMs = startMs + (Number(m.duration) || 30) * 60000;
      const nowMs = Date.now();
      const canComplete = nowMs >= endMs;             // only after scheduled end
      const canNoShow = nowMs >= startMs + 15 * 60000; // after start + 15m grace
      return (
        <div className="flex flex-wrap justify-end gap-2" data-testid={`meeting-actions-${m.id}`}>
          <Act onClick={() => openPicker(m, "reschedule")} testId={`meeting-reschedule-${m.id}`}><RotateCw className="h-3.5 w-3.5" /> Reschedule</Act>
          {canComplete ? <Act tone="ok" onClick={() => setStatus(m, "completed")} testId={`meeting-complete-${m.id}`} disabled={busy === m.id}><CheckCircle2 className="h-3.5 w-3.5" /> Mark Completed</Act> : null}
          {canNoShow ? <Act onClick={() => setStatus(m, "no-show")} testId={`meeting-noshow-${m.id}`} disabled={busy === m.id}><UserX className="h-3.5 w-3.5" /> No-show</Act> : null}
          <Act tone="danger" onClick={() => setStatus(m, "cancelled")} testId={`meeting-cancel-${m.id}`} disabled={busy === m.id}><X className="h-3.5 w-3.5" /> Cancel</Act>
        </div>
      );
    }
    if (s === "completed") return (
      <div className="flex flex-wrap justify-end gap-2" data-testid={`meeting-actions-${m.id}`}>
        <Act onClick={() => setDetails((d) => ({ ...d, [m.id]: !d[m.id] }))} testId={`meeting-viewlead-${m.id}`}><Eye className="h-3.5 w-3.5" /> View Lead</Act>
        <Act tone="gold" onClick={() => aiFollowup(m)} testId={`meeting-ai-${m.id}`}><Sparkles className="h-3.5 w-3.5" /> AI Follow-up</Act>
      </div>
    );
    // cancelled / declined / no-show -> read-only, view details only
    return (
      <div className="flex flex-wrap justify-end gap-2" data-testid={`meeting-actions-${m.id}`}>
        <Act onClick={() => setDetails((d) => ({ ...d, [m.id]: !d[m.id] }))} testId={`meeting-viewdetails-${m.id}`}><Eye className="h-3.5 w-3.5" /> View details</Act>
      </div>
    );
  };

  return (
    <div className="aria-dark relative min-h-screen bg-[#050607] text-white" style={{ fontFamily: "'Outfit', sans-serif" }} data-testid="meetings-page">
      <div className="grain-overlay" style={{ opacity: 0.04 }} />
      <header className="sticky top-0 z-40 border-b border-white/8 bg-[#050607]/85 backdrop-blur-xl">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4 sm:px-8">
          <button onClick={() => navigate("/admin")} className="flex items-center gap-2 text-sm text-white/60 hover:text-white" data-testid="meetings-back"><ArrowLeft className="h-4 w-4" /> Card Manager</button>
          <span className="flex items-center gap-2 text-[15px] font-medium"><CalendarDays className="h-5 w-5 text-[#D6A653]" /> Meetings</span>
          <span className="w-24" />
        </div>
      </header>

      <main className="relative mx-auto max-w-5xl px-4 py-8 sm:px-8">
        <div className="mb-6 flex flex-wrap gap-2">
          {TABS.map((t) => (
            <button key={t} onClick={() => setTab(t)} className={`rounded-full border px-4 py-2 text-sm capitalize transition-colors ${tab === t ? "border-[#D6A653] bg-[#D6A653]/12 text-white" : "border-white/12 text-white/50 hover:border-white/30"}`} data-testid={`meetings-tab-${t}`}>{t}</button>
          ))}
        </div>

        {items === null ? (
          <div className="flex justify-center py-20"><Loader2 className="h-6 w-6 animate-spin text-[#D6A653]" /></div>
        ) : items.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-white/12 py-20 text-center text-white/50" data-testid="meetings-empty">No {tab} meetings.</div>
        ) : (
          <div className="space-y-3">
            {items.map((m) => (
              <div key={m.id} className="rounded-2xl border border-white/10 bg-[#0A0B0D] p-5" data-testid={`meeting-${m.id}`}>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium text-white">{m.meeting_type_title}</span>
                      <span className={`rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-wider ${badge(m.status)}`} data-testid={`meeting-statuslabel-${m.id}`}>{LABEL[m.status] || m.status}</span>
                    </div>
                    <p className="mt-1 text-sm text-white/70"><Clock className="mr-1 inline h-3.5 w-3.5 text-[#D6A653]" />{fmt(m.start_utc, m.owner_timezone)} <span className="text-white/40">({m.owner_timezone})</span></p>
                    <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-white/55">
                      <span className="flex items-center gap-1"><User className="h-3 w-3" /> {m.visitor_name}</span>
                      {m.visitor_email ? <span className="flex items-center gap-1"><Mail className="h-3 w-3" /> {m.visitor_email}</span> : null}
                      {m.visitor_phone ? <span className="flex items-center gap-1"><Phone className="h-3 w-3" /> {m.visitor_phone}</span> : null}
                      <span className="text-white/35">via /{m.cardSlug}</span>
                    </div>
                    {m.status === "time_proposed" && m.proposed_start_utc ? (
                      <p className="mt-2 rounded-lg border border-violet-400/30 bg-violet-400/10 px-3 py-1.5 text-xs text-violet-200" data-testid={`meeting-proposed-${m.id}`}>Proposed new time: {fmt(m.proposed_start_utc, m.owner_timezone)} — awaiting guest acceptance</p>
                    ) : null}
                    {m.note ? <p className="mt-2 text-sm text-white/60">“{m.note}”</p> : null}
                  </div>
                  <div className="flex flex-col items-end gap-2">{renderActions(m)}</div>
                </div>

                {/* inline reschedule / propose picker */}
                {picker && picker.id === m.id && (
                  <div className="mt-4 rounded-xl border border-white/10 bg-white/[0.03] p-4" data-testid={`meeting-picker-${m.id}`}>
                    <div className="mb-2 flex items-center justify-between">
                      <p className="text-xs text-white/60">{picker.kind === "propose" ? "Propose a new time" : "Pick a new time"} (in {m.owner_timezone})</p>
                      <button onClick={() => setPicker(null)} className="text-xs text-white/50 hover:text-white" data-testid={`meeting-picker-cancel-${m.id}`}>Cancel</button>
                    </div>
                    <div className="flex gap-2 overflow-x-auto pb-2">
                      {days.map((d) => <button key={d} onClick={() => pickDate(d)} className={`shrink-0 rounded-xl border px-3 py-2 text-xs ${picker.date === d ? "bg-[#D6A653] text-black" : "border-white/14 text-white/70"}`} data-testid={`meeting-pdate-${d}`}>{fmtDay(d)}</button>)}
                    </div>
                    {picker.loading ? <div className="flex justify-center py-3"><Loader2 className="h-5 w-5 animate-spin text-[#D6A653]" /></div> : picker.date ? (
                      picker.slots.length === 0 ? <p className="py-2 text-center text-xs text-white/50">No times this day.</p> : (
                        <div className="grid grid-cols-4 gap-2 sm:grid-cols-6">
                          {picker.slots.map((sl) => <button key={sl} onClick={() => submitSlot(sl)} disabled={busy === m.id} className="rounded-lg border border-[#D6A653]/50 bg-[#D6A653]/10 py-2 text-xs text-white" data-testid={`meeting-pslot-${sl}`}>{fmtTime(sl, m.owner_timezone)}</button>)}
                        </div>
                      )
                    ) : <p className="text-center text-xs text-white/45">Pick a day to see times</p>}
                  </div>
                )}

                {/* view details / lead */}
                {details[m.id] && (
                  <div className="mt-4 rounded-xl border border-white/10 bg-white/[0.03] p-4 text-sm text-white/70" data-testid={`meeting-details-${m.id}`}>
                    <p className="mb-1 text-xs uppercase tracking-wider text-[#D6A653]">Guest</p>
                    <p>{m.visitor_name}{m.visitor_email ? ` · ${m.visitor_email}` : ""}{m.visitor_phone ? ` · ${m.visitor_phone}` : ""}</p>
                    {m.note ? <p className="mt-2 text-white/60">Note: “{m.note}”</p> : null}
                    {Array.isArray(m.history) && m.history.length ? (
                      <>
                        <p className="mb-1 mt-3 text-xs uppercase tracking-wider text-[#D6A653]">Status history</p>
                        <ul className="space-y-0.5 text-xs text-white/55">
                          {m.history.map((h, i) => <li key={i}>{(h.event || "").replace("status:", "")} · {new Date(h.at).toLocaleString([], { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })}{h.by ? ` · ${h.by}` : ""}</li>)}
                        </ul>
                      </>
                    ) : null}
                  </div>
                )}

                {draft[m.id] !== undefined ? (
                  draft[m.id] === "…" ? <div className="mt-3 flex items-center gap-2 text-xs text-white/50"><Loader2 className="h-3.5 w-3.5 animate-spin" /> Drafting…</div> : draft[m.id] ? (
                    <div className="mt-3 rounded-lg border border-white/10 bg-white/[0.03] p-3">
                      <textarea readOnly value={draft[m.id]} rows={5} className="w-full resize-none bg-transparent text-sm text-white/85 focus:outline-none" data-testid={`meeting-draft-${m.id}`} />
                      <button onClick={() => { navigator.clipboard.writeText(draft[m.id]); toast.success("Copied"); }} className="mt-1 flex items-center gap-1 text-xs text-[#D6A653]"><Copy className="h-3 w-3" /> Copy · review before sending</button>
                    </div>
                  ) : null
                ) : null}
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
