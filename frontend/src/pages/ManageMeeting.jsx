import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { Loader2, CalendarDays, Clock, User, XCircle, RotateCw, Check, ArrowLeft, Hourglass, CalendarClock } from "lucide-react";
import { toast } from "sonner";

const guessTz = () => { try { return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC"; } catch { return "UTC"; } };
const fmt = (iso, tz) => new Date(iso).toLocaleString([], { weekday: "long", month: "long", day: "numeric", hour: "numeric", minute: "2-digit", timeZone: tz });
const fmtDay = (d) => new Date(d + "T12:00:00").toLocaleDateString([], { weekday: "short", month: "short", day: "numeric" });
const fmtTime = (iso, tz) => new Date(iso).toLocaleTimeString([], { hour: "numeric", minute: "2-digit", timeZone: tz });

export default function ManageMeeting() {
  const { token } = useParams();
  const navigate = useNavigate();
  const tz = guessTz();
  const [m, setM] = useState(null);
  const [err, setErr] = useState(false);
  const [mode, setMode] = useState(null); // "resched"
  const [date, setDate] = useState("");
  const [slots, setSlots] = useState([]);
  const [loadingSlots, setLoadingSlots] = useState(false);
  const [busy, setBusy] = useState(false);

  const load = () => api.get(`/meetings/manage/${token}`).then(({ data }) => setM(data)).catch(() => setErr(true));
  useEffect(() => { load(); }, [token]); // eslint-disable-line

  const days = Array.from({ length: 21 }, (_, i) => { const d = new Date(); d.setDate(d.getDate() + i); return d.toISOString().slice(0, 10); });

  const pickDate = async (d) => {
    setDate(d); setLoadingSlots(true); setSlots([]);
    try { const { data } = await api.get(`/cards/${m.cardSlug}/slots`, { params: { meeting_type_id: m.meeting_type_id, date: d } }); setSlots(data.slots || []); }
    catch { setSlots([]); } finally { setLoadingSlots(false); }
  };
  const exitReschedule = () => { setMode(null); setDate(""); setSlots([]); };
  const cancel = async () => {
    if (!window.confirm("Cancel this meeting? This can't be undone.")) return;
    setBusy(true);
    try { await api.post(`/meetings/manage/${token}/cancel`); toast.success("Meeting cancelled"); load(); }
    catch { toast.error("Could not cancel"); } finally { setBusy(false); }
  };
  const reschedule = async (start) => {
    setBusy(true);
    try { await api.post(`/meetings/manage/${token}/reschedule`, { start }); toast.success("Meeting rescheduled"); exitReschedule(); load(); }
    catch (e) { toast.error(e.response?.data?.detail || "Could not reschedule"); } finally { setBusy(false); }
  };
  const acceptProposal = async () => {
    setBusy(true);
    try { await api.post(`/meetings/manage/${token}/accept-proposal`); toast.success("New time accepted — confirmed"); load(); }
    catch (e) { toast.error(e.response?.data?.detail || "Could not accept"); } finally { setBusy(false); }
  };

  const goProfile = () => { if (m?.cardSlug) navigate(`/${m.cardSlug}`); else navigate("/"); };

  if (err) return <Screen onProfile={() => navigate("/")}><p className="text-white/60">Meeting not found.</p></Screen>;
  if (!m) return <Screen><Loader2 className="h-6 w-6 animate-spin text-[#D6A653]" /></Screen>;

  const status = m.status;
  const closed = status === "cancelled" || status === "declined";
  const pending = status === "requested";
  const confirmed = status === "confirmed";
  const proposed = status === "time_proposed";

  const headline = closed
    ? (status === "declined" ? "Request declined" : "Meeting cancelled")
    : pending ? "Meeting request sent"
    : confirmed ? "Your meeting is confirmed"
    : proposed ? "A new time was proposed"
    : "Your meeting";

  const Icon = closed ? XCircle : pending ? Hourglass : proposed ? CalendarClock : confirmed ? Check : CalendarDays;
  const iconColor = closed ? "text-red-400" : confirmed ? "text-emerald-400" : "text-[#D6A653]";

  return (
    <Screen onProfile={goProfile}>
      <div className="w-full max-w-md rounded-3xl border border-white/10 bg-white/[0.04] p-8 backdrop-blur-xl" data-testid="manage-meeting">
        <span className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full" style={{ background: "rgba(214,166,83,0.14)" }}>
          <Icon className={`h-7 w-7 ${iconColor}`} />
        </span>
        <h1 className="text-center text-2xl font-light" data-testid="manage-headline">{headline}</h1>
        {pending ? <p className="mt-1 text-center text-sm text-white/55" data-testid="manage-pending-note">Waiting for confirmation{m.owner_name ? ` from ${m.owner_name}` : ""}.</p> : null}

        <div className="mt-5 rounded-xl border border-white/10 bg-black/30 p-4 text-sm">
          <p className="font-medium text-white">{m.meeting_type_title}</p>
          <p className="mt-1 text-white/70"><Clock className="mr-1 inline h-3.5 w-3.5 text-[#D6A653]" />{fmt(m.start_utc, tz)} <span className="text-white/40">({tz})</span></p>
          {m.owner_name ? <p className="mt-1 text-white/55"><User className="mr-1 inline h-3.5 w-3.5" />with {m.owner_name}</p> : null}
        </div>

        {/* Owner proposed a new time */}
        {proposed && m.proposed_start_utc && (
          <div className="mt-4 rounded-xl border p-4 text-sm" style={{ borderColor: "rgba(214,166,83,0.4)", background: "rgba(214,166,83,0.08)" }} data-testid="manage-proposed">
            <p className="text-xs uppercase tracking-wider text-[#D6A653]">Proposed new time</p>
            <p className="mt-1 text-white/85">{fmt(m.proposed_start_utc, tz)} <span className="text-white/40">({tz})</span></p>
            <button onClick={acceptProposal} disabled={busy} className="mt-3 flex w-full items-center justify-center gap-1.5 rounded-full bg-[#D6A653] py-2.5 text-sm font-medium text-black hover:bg-[#E8B764]" data-testid="manage-accept-proposal">
              {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <><Check className="h-4 w-4" /> Accept new time</>}
            </button>
          </div>
        )}

        {/* Actions when active and not mid-reschedule */}
        {!closed && !mode && (
          <div className="mt-5 grid grid-cols-2 gap-3" data-testid="manage-actions">
            <button onClick={() => setMode("resched")} className="flex items-center justify-center gap-1.5 rounded-full border border-white/15 py-3 text-sm text-white hover:bg-white/5" data-testid="manage-reschedule"><RotateCw className="h-4 w-4" /> Reschedule</button>
            <button onClick={cancel} disabled={busy} className="flex items-center justify-center gap-1.5 rounded-full border border-red-400/40 py-3 text-sm text-red-300 hover:bg-red-500/10" data-testid="manage-cancel"><XCircle className="h-4 w-4" /> {pending ? "Withdraw" : "Cancel"}</button>
          </div>
        )}

        {/* Reschedule picker */}
        {mode === "resched" && !closed && (
          <div className="mt-5 space-y-3" data-testid="manage-resched">
            <div className="flex items-center justify-between">
              <p className="text-xs text-white/50">Pick a new day &amp; time</p>
              <button onClick={exitReschedule} className="flex items-center gap-1 text-xs text-white/60 hover:text-white" data-testid="manage-cancel-reschedule"><ArrowLeft className="h-3.5 w-3.5" /> Cancel rescheduling</button>
            </div>
            <div className="flex gap-2 overflow-x-auto pb-2">
              {days.map((d) => <button key={d} onClick={() => pickDate(d)} className={`shrink-0 rounded-xl border px-3 py-2 text-xs ${date === d ? "bg-[#D6A653] text-black" : "border-white/14 text-white/70"}`} style={date === d ? {} : { borderColor: "rgba(255,255,255,0.14)" }} data-testid={`manage-date-${d}`}>{fmtDay(d)}</button>)}
            </div>
            {loadingSlots ? <div className="flex justify-center py-4"><Loader2 className="h-5 w-5 animate-spin text-[#D6A653]" /></div> : date ? (
              slots.length === 0 ? <p className="py-3 text-center text-sm text-white/50">No times this day.</p> : (
                <div className="grid grid-cols-3 gap-2">
                  {slots.map((s) => <button key={s} onClick={() => reschedule(s)} disabled={busy} className="rounded-lg border border-[#D6A653]/50 bg-[#D6A653]/10 py-2 text-sm text-white" data-testid={`manage-slot-${s}`}>{fmtTime(s, tz)}</button>)}
                </div>
              )
            ) : <p className="text-center text-xs text-white/45">Pick a day to see times</p>}
            <button onClick={exitReschedule} className="w-full rounded-full border border-white/12 py-2.5 text-center text-xs text-white/70 hover:bg-white/5">Keep original time</button>
          </div>
        )}

        {/* Always-available exits — never trap the guest */}
        <div className="mt-6 flex items-center justify-center gap-4 border-t border-white/8 pt-4 text-xs">
          <button onClick={goProfile} className="flex items-center gap-1.5 text-white/60 hover:text-white" data-testid="manage-back-profile"><ArrowLeft className="h-3.5 w-3.5" /> Back to profile</button>
          <span className="text-white/15">·</span>
          <button onClick={() => window.close()} className="text-white/40 hover:text-white/70" data-testid="manage-close">Close</button>
        </div>
      </div>
    </Screen>
  );
}

const Screen = ({ children, onProfile }) => (
  <div className="aria-dark relative flex min-h-screen items-center justify-center overflow-hidden bg-[#050607] px-6 text-white" style={{ fontFamily: "'Outfit', sans-serif" }}>
    <div className="grain-overlay" style={{ opacity: 0.05 }} />
    <div className="aria-gold-radial pointer-events-none absolute inset-0" />
    {onProfile ? (
      <button onClick={onProfile} className="absolute left-5 top-5 z-10 flex items-center gap-1.5 text-xs text-white/55 hover:text-white" data-testid="manage-top-back"><ArrowLeft className="h-4 w-4" /> Back to profile</button>
    ) : null}
    <div className="relative flex items-center justify-center">{children}</div>
  </div>
);
