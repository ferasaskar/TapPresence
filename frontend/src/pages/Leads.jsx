import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "@/lib/api";
import { OwnerNav } from "@/components/admin/OwnerNav";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Loader2, Search, Phone, Mail, MessageCircle, Sparkles, Trash2, User, CreditCard, Clock, Copy, X, ArrowLeft, CalendarDays } from "lucide-react";
import { toast } from "sonner";

const STAGES = ["new", "contacted", "meeting_booked", "qualified", "converted", "archived"];
const STAGE_LABEL = { new: "New", contacted: "Contacted", meeting_booked: "Meeting Booked", qualified: "Qualified", converted: "Converted", archived: "Archived" };
const STAGE_BADGE = {
  new: "text-[#D6A653] border-[#D6A653]/40 bg-[#D6A653]/10",
  contacted: "text-sky-300 border-sky-400/40 bg-sky-400/10",
  meeting_booked: "text-violet-300 border-violet-400/40 bg-violet-400/10",
  qualified: "text-amber-300 border-amber-400/40 bg-amber-400/10",
  converted: "text-emerald-300 border-emerald-400/40 bg-emerald-400/10",
  archived: "text-white/50 border-white/20 bg-white/5",
};
const MSTATUS_LABEL = { requested: "Pending", time_proposed: "New Time Proposed", scheduled: "Confirmed", confirmed: "Confirmed", rescheduled: "Confirmed", completed: "Completed", cancelled: "Cancelled", declined: "Declined", "no-show": "No-show" };
const EVENT_LABEL = { created: "Lead created", meeting_requested: "Meeting Requested", meeting_booked: "Meeting Booked", meeting_confirmed: "Meeting Confirmed", meeting_completed: "Meeting Completed", meeting_cancelled: "Meeting Cancelled", contact_exchanged: "Contact Exchanged", profile_viewed: "Profile Viewed" };

const norm = (s) => (s || "new").toLowerCase();
const digits = (p) => (p || "").replace(/[^\d+]/g, "").replace(/^\+/, "");
const fmt = (iso) => new Date(iso).toLocaleString([], { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });

export default function Leads() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const [leads, setLeads] = useState(null);
  const [cards, setCards] = useState([]);
  const [mByLead, setMByLead] = useState({});
  const [tab, setTab] = useState("all");
  const [q, setQ] = useState("");
  const [source, setSource] = useState("all");
  const [card, setCard] = useState("all");
  const [dateRange, setDateRange] = useState("all");
  const [openLead, setOpenLead] = useState(null);
  const [draft, setDraft] = useState("");
  const [gen, setGen] = useState(false);
  const [aiOpts, setAiOpts] = useState({ tone: "professional", channel: "email", language: "en" });

  const load = () => {
    api.get("/admin/leads").then(({ data }) => setLeads(data)).catch(() => setLeads([]));
    api.get("/admin/cards").then(({ data }) => setCards(data)).catch(() => {});
    Promise.all(["upcoming", "past", "cancelled"].map((f) => api.get("/admin/meetings", { params: { filter: f } }).then((r) => r.data).catch(() => [])))
      .then((lists) => {
        const map = {};
        lists.flat().forEach((m) => { if (m.lead_id) map[m.lead_id] = m; });
        setMByLead(map);
      });
  };
  useEffect(() => { load(); }, []);

  const stageOf = (l) => {
    const s = norm(l.status);
    if (s !== "new") return s;
    if (mByLead[l.id] || l.source === "meeting_booking") return "meeting_booked";
    return "new";
  };

  // open lead from ?lead=
  useEffect(() => {
    const id = params.get("lead");
    if (id && leads) { const l = leads.find((x) => x.id === id); if (l) openDetail(l); }
  }, [leads]); // eslint-disable-line

  const counts = useMemo(() => {
    const c = { all: 0 }; STAGES.forEach((s) => (c[s] = 0));
    (leads || []).forEach((l) => { c.all++; c[stageOf(l)]++; });
    return c;
  }, [leads, mByLead]);

  const filtered = useMemo(() => {
    let list = leads || [];
    if (tab !== "all") list = list.filter((l) => stageOf(l) === tab);
    if (source !== "all") list = list.filter((l) => (l.source || "inquiry") === source);
    if (card !== "all") list = list.filter((l) => l.cardSlug === card);
    if (dateRange !== "all") {
      const now = Date.now(); const days = dateRange === "today" ? 1 : dateRange === "7d" ? 7 : 30;
      list = list.filter((l) => now - new Date(l.created_at).getTime() <= days * 864e5);
    }
    if (q.trim()) { const s = q.toLowerCase(); list = list.filter((l) => [l.name, l.email, l.phone].some((v) => (v || "").toLowerCase().includes(s))); }
    return [...list].sort((a, b) => new Date(b.last_activity || b.created_at) - new Date(a.last_activity || a.created_at));
  }, [leads, tab, source, card, dateRange, q, mByLead]);

  const openDetail = async (l) => {
    setOpenLead(l); setDraft(""); 
    if (!l.read) { try { await api.patch(`/admin/leads/${l.id}`); setLeads((ls) => ls.map((x) => x.id === l.id ? { ...x, read: true } : x)); } catch (_) {} }
  };
  const closeDetail = () => { setOpenLead(null); if (params.get("lead")) { params.delete("lead"); setParams(params, { replace: true }); } };

  const changeStage = async (l, st) => {
    try { await api.patch(`/admin/leads/${l.id}/status`, { status: st }); toast.success(`Moved to ${STAGE_LABEL[st]}`); setLeads((ls) => ls.map((x) => x.id === l.id ? { ...x, status: st } : x)); setOpenLead((o) => o && o.id === l.id ? { ...o, status: st } : o); }
    catch { toast.error("Could not update"); }
  };
  const remove = async (l) => { if (!window.confirm("Delete this lead?")) return; try { await api.delete(`/admin/leads/${l.id}`); toast.success("Deleted"); closeDetail(); setLeads((ls) => ls.filter((x) => x.id !== l.id)); } catch { toast.error("Delete failed"); } };

  const genAI = async (l) => {
    setGen(true); setDraft("");
    try { const { data } = await api.post("/ai/followup", { lead_name: l.name, company: l.company || "", notes: l.message || l.interest || "", owner_name: "", tone: aiOpts.tone, channel: aiOpts.channel, language: aiOpts.language }); setDraft(data.draft); toast.success(`Draft ready (${data.provider})`); }
    catch { toast.error("Could not draft"); } finally { setGen(false); }
  };

  const multiCard = cards.length > 1;
  const QA = ({ icon: Icon, href, onClick, label, testId }) => {
    const cls = "flex h-9 w-9 items-center justify-center rounded-lg border border-white/12 bg-white/[0.02] text-white/70 transition-colors hover:border-[#D6A653]/50 hover:text-white";
    return href ? <a href={href} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()} className={cls} title={label} data-testid={testId}><Icon className="h-4 w-4" /></a>
      : <button onClick={(e) => { e.stopPropagation(); onClick(); }} className={cls} title={label} data-testid={testId}><Icon className="h-4 w-4" /></button>;
  };

  return (
    <div className="aria-dark relative min-h-screen bg-[#050607] text-white" style={{ fontFamily: "'Outfit', sans-serif" }} data-testid="leads-page">
      <div className="grain-overlay" style={{ opacity: 0.04 }} />
      <OwnerNav active="" />

      <main className="relative mx-auto max-w-5xl px-4 py-8 sm:px-8">
        <div className="mb-4 flex items-center gap-3">
          <button onClick={() => navigate("/dashboard")} className="text-white/50 hover:text-white" data-testid="leads-back"><ArrowLeft className="h-5 w-5" /></button>
          <div>
            <h2 className="text-2xl font-light tracking-tight text-white">Leads &amp; Inbox</h2>
            <p className="text-sm text-white/45">Your inquiries and booking contacts.</p>
          </div>
        </div>

        {/* pipeline tabs */}
        <div className="mb-4 flex gap-2 overflow-x-auto pb-1" data-testid="leads-pipeline">
          {["all", ...STAGES].map((s) => (
            <button key={s} onClick={() => setTab(s)} data-testid={`pipeline-${s}`}
              className={`flex shrink-0 items-center gap-1.5 rounded-full border px-3.5 py-1.5 text-sm transition-all ${tab === s ? "border-[#D6A653] bg-[#D6A653]/12 text-white" : "border-white/10 text-white/55 hover:border-white/25"}`}>
              {s === "all" ? "All" : STAGE_LABEL[s]}
              <span className="rounded-full bg-white/10 px-1.5 text-[10px] text-white/70">{counts[s] || 0}</span>
            </button>
          ))}
        </div>

        {/* filters */}
        <div className="mb-5 grid grid-cols-2 gap-2 sm:flex sm:flex-wrap sm:items-center">
          <div className="relative col-span-2 sm:w-56">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-white/35" />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search name, email, phone" className="h-9 w-full rounded-lg border border-white/12 bg-[#0A0B0D] pl-9 pr-3 text-sm text-white placeholder:text-white/30 focus:border-[#D6A653]/50 focus:outline-none" data-testid="leads-search" />
          </div>
          <Select value={source} onValueChange={setSource}><SelectTrigger className="h-9 text-xs" data-testid="leads-filter-source"><SelectValue placeholder="Source" /></SelectTrigger><SelectContent className="aria-pop"><SelectItem value="all">All sources</SelectItem><SelectItem value="inquiry">Inquiry</SelectItem><SelectItem value="meeting_booking">Meeting booking</SelectItem></SelectContent></Select>
          {multiCard ? <Select value={card} onValueChange={setCard}><SelectTrigger className="h-9 text-xs" data-testid="leads-filter-card"><SelectValue placeholder="Card" /></SelectTrigger><SelectContent className="aria-pop"><SelectItem value="all">All cards</SelectItem>{cards.map((c) => <SelectItem key={c.slug} value={c.slug}>/{c.slug}</SelectItem>)}</SelectContent></Select> : null}
          <Select value={dateRange} onValueChange={setDateRange}><SelectTrigger className="h-9 text-xs" data-testid="leads-filter-date"><SelectValue placeholder="Date" /></SelectTrigger><SelectContent className="aria-pop"><SelectItem value="all">Any time</SelectItem><SelectItem value="today">Last 24h</SelectItem><SelectItem value="7d">Last 7 days</SelectItem><SelectItem value="30d">Last 30 days</SelectItem></SelectContent></Select>
        </div>

        {leads === null ? (
          <div className="flex justify-center py-20"><Loader2 className="h-6 w-6 animate-spin text-[#D6A653]" /></div>
        ) : filtered.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-white/12 py-20 text-center text-white/50" data-testid="leads-empty">No leads here.</div>
        ) : (
          <div className="space-y-2.5">
            {filtered.map((l) => {
              const st = stageOf(l); const m = mByLead[l.id];
              const lastEv = (l.timeline || [])[l.timeline?.length - 1];
              return (
                <div key={l.id} onClick={() => openDetail(l)} data-testid={`lead-row-${l.id}`}
                  className={`cursor-pointer rounded-2xl border p-4 transition-colors ${l.read ? "border-white/10 bg-[#0A0B0D]" : "border-[#D6A653]/30 bg-[#D6A653]/[0.05]"} hover:border-white/25`}>
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-medium text-white">{l.name}</span>
                        {!l.read ? <span className="rounded-full bg-[#D6A653] px-1.5 py-0.5 text-[9px] font-semibold text-[#050607]">NEW</span> : null}
                        <span className={`rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-wider ${STAGE_BADGE[st]}`} data-testid={`lead-stage-${l.id}`}>{STAGE_LABEL[st]}</span>
                        {m ? <span className="rounded-full border border-white/15 bg-white/5 px-2 py-0.5 text-[10px] text-white/60">{MSTATUS_LABEL[m.status] || m.status}</span> : null}
                      </div>
                      <div className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-white/50">
                        {l.email ? <span className="flex items-center gap-1"><Mail className="h-3 w-3" />{l.email}</span> : null}
                        {l.phone ? <span className="flex items-center gap-1"><Phone className="h-3 w-3" />{l.phone}</span> : null}
                        <span className="text-white/35">/{l.cardSlug}</span>
                        <span className="text-white/30">· {(l.source || "inquiry").replace("_", " ")}</span>
                      </div>
                      <p className="mt-1 text-xs text-white/40">{lastEv ? `${EVENT_LABEL[lastEv.event] || lastEv.event}` : "Inquiry"} · {fmt(l.last_activity || l.created_at)}</p>
                    </div>
                    <div className="flex shrink-0 gap-1.5">
                      {l.phone ? <QA icon={Phone} href={`tel:${l.phone}`} label="Call" testId={`lead-call-${l.id}`} /> : null}
                      {l.phone ? <QA icon={MessageCircle} href={`https://wa.me/${digits(l.phone)}`} label="WhatsApp" testId={`lead-wa-${l.id}`} /> : null}
                      {l.email ? <QA icon={Mail} href={`mailto:${l.email}`} label="Email" testId={`lead-email-${l.id}`} /> : null}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>

      {/* lead detail */}
      <Dialog open={!!openLead} onOpenChange={(v) => !v && closeDetail()}>
        <DialogContent className="aria-dark max-h-[88vh] max-w-lg overflow-y-auto border-white/10 bg-[#0A0B0D] text-white" data-testid="lead-detail">
          {openLead ? (() => {
            const l = openLead; const st = stageOf(l); const m = mByLead[l.id];
            const timeline = [{ at: l.created_at, event: "created" }, ...(l.timeline || [])];
            return (
              <>
                <DialogHeader>
                  <DialogTitle className="flex items-center gap-2 text-white"><User className="h-5 w-5 text-[#D6A653]" /> {l.name}</DialogTitle>
                </DialogHeader>
                <div className="space-y-4 text-sm">
                  <div className="flex flex-wrap gap-2">
                    {l.phone ? <a href={`tel:${l.phone}`} className="flex items-center gap-1.5 rounded-lg border border-white/12 px-3 py-1.5 text-xs hover:border-[#D6A653]/50" data-testid="detail-call"><Phone className="h-3.5 w-3.5 text-[#D6A653]" /> Call</a> : null}
                    {l.phone ? <a href={`https://wa.me/${digits(l.phone)}`} target="_blank" rel="noreferrer" className="flex items-center gap-1.5 rounded-lg border border-white/12 px-3 py-1.5 text-xs hover:border-[#D6A653]/50" data-testid="detail-wa"><MessageCircle className="h-3.5 w-3.5 text-[#D6A653]" /> WhatsApp</a> : null}
                    {l.email ? <a href={`mailto:${l.email}`} className="flex items-center gap-1.5 rounded-lg border border-white/12 px-3 py-1.5 text-xs hover:border-[#D6A653]/50" data-testid="detail-email"><Mail className="h-3.5 w-3.5 text-[#D6A653]" /> Email</a> : null}
                  </div>

                  <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
                    <div className="grid grid-cols-2 gap-y-2 text-xs">
                      {l.email ? <><span className="text-white/45">Email</span><span className="text-right text-white/85">{l.email}</span></> : null}
                      {l.phone ? <><span className="text-white/45">Phone</span><span className="text-right text-white/85">{l.phone}</span></> : null}
                      <span className="text-white/45">Source</span><span className="text-right text-white/85">{(l.source || "inquiry").replace("_", " ")}</span>
                      <span className="flex items-center gap-1 text-white/45"><CreditCard className="h-3 w-3" /> Card</span><span className="text-right text-[#D6A653]">/{l.cardSlug}</span>
                    </div>
                    {l.message ? <p className="mt-3 border-t border-white/8 pt-3 text-white/75">“{l.message}”</p> : null}
                  </div>

                  {/* pipeline status */}
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-xs text-white/45">Pipeline stage</span>
                    <Select value={st} onValueChange={(v) => changeStage(l, v)}>
                      <SelectTrigger className="h-8 w-44 text-xs" data-testid="detail-stage"><SelectValue /></SelectTrigger>
                      <SelectContent className="aria-pop">{STAGES.map((s) => <SelectItem key={s} value={s}>{STAGE_LABEL[s]}</SelectItem>)}</SelectContent>
                    </Select>
                  </div>

                  {m ? (
                    <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4" data-testid="detail-meeting">
                      <p className="mb-1 text-xs uppercase tracking-wider text-[#D6A653]">Meeting</p>
                      <p className="text-white/85">{m.meeting_type_title} — {MSTATUS_LABEL[m.status] || m.status}</p>
                      <p className="mt-1 flex items-center gap-1 text-xs text-white/55"><Clock className="h-3 w-3" /> {new Date(m.start_utc).toLocaleString([], { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit", timeZone: m.owner_timezone })} ({m.owner_timezone})</p>
                      <button onClick={() => navigate("/meetings")} className="mt-2 text-xs text-[#D6A653] hover:underline" data-testid="detail-view-meeting"><CalendarDays className="mr-1 inline h-3 w-3" /> Open in Meetings</button>
                    </div>
                  ) : null}

                  {/* activity timeline */}
                  <div>
                    <p className="mb-2 text-xs uppercase tracking-wider text-[#D6A653]">Activity</p>
                    <ul className="space-y-2">
                      {timeline.map((e, i) => (
                        <li key={i} className="flex items-center gap-2 text-xs text-white/60" data-testid={`timeline-${i}`}>
                          <span className="h-1.5 w-1.5 rounded-full bg-[#D6A653]" />
                          <span className="text-white/80">{EVENT_LABEL[e.event] || e.event}</span>
                          {e.detail ? <span className="text-white/40">· {e.detail}</span> : null}
                          <span className="ml-auto text-white/35">{fmt(e.at)}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* AI follow-up */}
                  <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
                    <div className="mb-2 grid grid-cols-3 gap-2">
                      <Select value={aiOpts.channel} onValueChange={(v) => setAiOpts((o) => ({ ...o, channel: v }))}><SelectTrigger className="h-8 text-xs" data-testid="ai-channel"><SelectValue /></SelectTrigger><SelectContent className="aria-pop"><SelectItem value="email">Email</SelectItem><SelectItem value="whatsapp">WhatsApp</SelectItem><SelectItem value="sms">SMS</SelectItem></SelectContent></Select>
                      <Select value={aiOpts.tone} onValueChange={(v) => setAiOpts((o) => ({ ...o, tone: v }))}><SelectTrigger className="h-8 text-xs" data-testid="ai-tone"><SelectValue /></SelectTrigger><SelectContent className="aria-pop"><SelectItem value="professional">Professional</SelectItem><SelectItem value="warm">Warm</SelectItem><SelectItem value="short">Short</SelectItem></SelectContent></Select>
                      <Select value={aiOpts.language} onValueChange={(v) => setAiOpts((o) => ({ ...o, language: v }))}><SelectTrigger className="h-8 text-xs" data-testid="ai-language"><SelectValue /></SelectTrigger><SelectContent className="aria-pop"><SelectItem value="en">EN</SelectItem><SelectItem value="ar">AR</SelectItem><SelectItem value="es">ES</SelectItem></SelectContent></Select>
                    </div>
                    <button onClick={() => genAI(l)} disabled={gen} className="flex w-full items-center justify-center gap-1.5 rounded-lg bg-[#D6A653] py-2 text-sm font-medium text-[#050607] hover:bg-[#E8B764] disabled:opacity-60" data-testid="detail-ai-generate">{gen ? <Loader2 className="h-4 w-4 animate-spin" /> : <><Sparkles className="h-4 w-4" /> AI Follow-up</>}</button>
                    {draft ? (
                      <div className="mt-2">
                        <textarea value={draft} onChange={(e) => setDraft(e.target.value)} rows={5} className="w-full rounded-lg border border-white/10 bg-black/30 p-2 text-sm text-white/85 focus:outline-none" data-testid="detail-ai-draft" />
                        <button onClick={() => { navigator.clipboard.writeText(draft); toast.success("Copied"); }} className="mt-1 flex items-center gap-1 text-xs text-[#D6A653]" data-testid="detail-ai-copy"><Copy className="h-3 w-3" /> Copy · review before sending</button>
                      </div>
                    ) : null}
                  </div>

                  <button onClick={() => remove(l)} className="flex items-center gap-1.5 text-xs text-red-400/80 hover:text-red-400" data-testid="detail-delete"><Trash2 className="h-3.5 w-3.5" /> Delete lead</button>
                </div>
              </>
            );
          })() : null}
        </DialogContent>
      </Dialog>
    </div>
  );
}
