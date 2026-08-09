import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { Loader2, ArrowLeft, Clock, User, Mail, Phone, CalendarDays, Sparkles, Copy } from "lucide-react";
import { toast } from "sonner";

const TABS = ["today", "upcoming", "past", "cancelled"];
const STATUS_OPTS = ["scheduled", "confirmed", "completed", "cancelled", "no-show"];
const badge = (s) => ({
  scheduled: "text-[#D6A653] border-[#D6A653]/40 bg-[#D6A653]/10",
  confirmed: "text-emerald-300 border-emerald-400/40 bg-emerald-400/10",
  completed: "text-sky-300 border-sky-400/40 bg-sky-400/10",
  cancelled: "text-red-300 border-red-400/40 bg-red-400/10",
  "no-show": "text-orange-300 border-orange-400/40 bg-orange-400/10",
  rescheduled: "text-violet-300 border-violet-400/40 bg-violet-400/10",
}[s] || "text-white/60 border-white/20 bg-white/5");

const fmt = (iso, tz) => new Date(iso).toLocaleString([], { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit", timeZone: tz });

export default function Meetings() {
  const navigate = useNavigate();
  const [tab, setTab] = useState("upcoming");
  const [items, setItems] = useState(null);
  const [draft, setDraft] = useState({});

  const load = () => {
    setItems(null);
    api.get("/admin/meetings", { params: { filter: tab } }).then(({ data }) => setItems(data)).catch(() => setItems([]));
  };
  useEffect(() => { load(); }, [tab]); // eslint-disable-line

  const setStatus = async (m, status) => {
    try { await api.patch(`/admin/meetings/${m.id}/status`, { status }); toast.success(`Marked ${status}`); load(); }
    catch { toast.error("Could not update"); }
  };

  const aiFollowup = async (m) => {
    setDraft((d) => ({ ...d, [m.id]: "…" }));
    try {
      const { data } = await api.post("/ai/followup", { lead_name: m.visitor_name, company: "", notes: `${m.meeting_type_title} meeting on ${fmt(m.start_utc, m.owner_timezone)}`, owner_name: m.owner_name, tone: "professional", channel: "email", language: "en" });
      setDraft((d) => ({ ...d, [m.id]: data.draft }));
    } catch { setDraft((d) => ({ ...d, [m.id]: "" })); toast.error("Could not draft"); }
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
                      <span className={`rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-wider ${badge(m.status)}`}>{m.status}</span>
                    </div>
                    <p className="mt-1 text-sm text-white/70"><Clock className="mr-1 inline h-3.5 w-3.5 text-[#D6A653]" />{fmt(m.start_utc, m.owner_timezone)} <span className="text-white/40">({m.owner_timezone})</span></p>
                    <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-white/55">
                      <span className="flex items-center gap-1"><User className="h-3 w-3" /> {m.visitor_name}</span>
                      {m.visitor_email ? <span className="flex items-center gap-1"><Mail className="h-3 w-3" /> {m.visitor_email}</span> : null}
                      {m.visitor_phone ? <span className="flex items-center gap-1"><Phone className="h-3 w-3" /> {m.visitor_phone}</span> : null}
                      <span className="text-white/35">via /{m.cardSlug}</span>
                    </div>
                    {m.note ? <p className="mt-2 text-sm text-white/60">“{m.note}”</p> : null}
                  </div>
                  <div className="flex flex-col items-end gap-2">
                    <select value={m.status} onChange={(e) => setStatus(m, e.target.value)} className="rounded-lg border border-white/12 bg-[#0A0B0D] px-2 py-1.5 text-xs text-white" data-testid={`meeting-status-${m.id}`}>
                      {STATUS_OPTS.map((s) => <option key={s} value={s}>{s}</option>)}
                    </select>
                    {m.status === "completed" ? (
                      <button onClick={() => aiFollowup(m)} className="flex items-center gap-1 rounded-lg border border-white/15 px-3 py-1.5 text-xs text-white hover:bg-white/5" data-testid={`meeting-ai-${m.id}`}><Sparkles className="h-3.5 w-3.5 text-[#D6A653]" /> Draft follow-up</button>
                    ) : null}
                  </div>
                </div>
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
