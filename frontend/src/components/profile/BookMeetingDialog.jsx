import { useEffect, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { api } from "@/lib/api";
import { Loader2, Clock, Video, MapPin, Phone, ChevronRight, ArrowLeft, CalendarCheck, PartyPopper, Copy } from "lucide-react";
import { toast } from "sonner";

const LOC = { in_person: MapPin, phone: Phone, video: Video, custom: MapPin };
const guessTz = () => { try { return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC"; } catch { return "UTC"; } };

const fmtTime = (iso, tz) => new Date(iso).toLocaleTimeString([], { hour: "numeric", minute: "2-digit", timeZone: tz });
const fmtDay = (d) => new Date(d + "T12:00:00").toLocaleDateString([], { weekday: "short", month: "short", day: "numeric" });

export function BookMeetingDialog({ open, onOpenChange, slug, accent = "#D6A653", ownerName = "" }) {
  const ac = accent;
  const visitorTz = guessTz();
  const [step, setStep] = useState("type");
  const [types, setTypes] = useState([]);
  const [ownerTz, setOwnerTz] = useState("UTC");
  const [mt, setMt] = useState(null);
  const [date, setDate] = useState("");
  const [slots, setSlots] = useState([]);
  const [loadingSlots, setLoadingSlots] = useState(false);
  const [slot, setSlot] = useState("");
  const [f, setF] = useState({ name: "", email: "", phone: "", note: "" });
  const [saving, setSaving] = useState(false);
  const [done, setDone] = useState(null);

  useEffect(() => {
    if (!open) return;
    setStep("type"); setSlot(""); setDone(null); setF({ name: "", email: "", phone: "", note: "" });
    api.get(`/cards/${slug}/booking`).then(({ data }) => {
      setTypes(data.meeting_types || []); setOwnerTz(data.owner_timezone || "UTC");
    }).catch(() => {});
    api.post(`/cards/${slug}/track`, { type: "tap", key: "booking_opened" }).catch(() => {});
  }, [open, slug]);

  const days = Array.from({ length: 21 }, (_, i) => {
    const d = new Date(); d.setDate(d.getDate() + i);
    return d.toISOString().slice(0, 10);
  });

  const chooseType = (m) => { setMt(m); setStep("date"); setDate(""); setSlots([]); };
  const chooseDate = async (d) => {
    setDate(d); setLoadingSlots(true); setSlots([]);
    api.post(`/cards/${slug}/track`, { type: "tap", key: "date_selected" }).catch(() => {});
    try {
      const { data } = await api.get(`/cards/${slug}/slots`, { params: { meeting_type_id: mt.id, date: d } });
      setSlots(data.slots || []);
    } catch { setSlots([]); }
    finally { setLoadingSlots(false); }
  };
  const chooseSlot = (s) => { setSlot(s); setStep("details"); api.post(`/cards/${slug}/track`, { type: "tap", key: "slot_selected" }).catch(() => {}); };

  const confirm = async () => {
    if (!f.name.trim() || !(f.email.trim() || f.phone.trim())) { toast.error("Name and email or phone required"); return; }
    setSaving(true);
    try {
      const { data } = await api.post(`/cards/${slug}/book`, { meeting_type_id: mt.id, start: slot, ...f, visitor_tz: visitorTz });
      setDone(data); setStep("done");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not book");
    } finally { setSaving(false); }
  };

  const LocIcon = mt ? (LOC[mt.location_type] || Video) : Video;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[88vh] max-w-md overflow-y-auto border text-white" style={{ background: "#0B0B0D", borderColor: `${ac}59` }} data-testid="book-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-white">
            {step !== "type" && step !== "done" ? (
              <button onClick={() => setStep(step === "date" ? "type" : step === "details" ? "date" : "type")} data-testid="book-back"><ArrowLeft className="h-4 w-4" style={{ color: ac }} /></button>
            ) : null}
            <CalendarCheck className="h-5 w-5" style={{ color: ac }} /> Book a Meeting
          </DialogTitle>
        </DialogHeader>

        {step === "type" && (
          <div className="space-y-2" data-testid="book-types">
            {types.length === 0 ? <p className="py-8 text-center text-sm text-white/50">No meeting types available.</p> : null}
            {types.map((m) => {
              const I = LOC[m.location_type] || Video;
              return (
                <button key={m.id} onClick={() => chooseType(m)} className="flex w-full items-center gap-3 rounded-xl border p-4 text-left transition-all hover:-translate-y-0.5" style={{ borderColor: `${ac}40`, background: `${ac}0f` }} data-testid={`book-type-${m.id}`}>
                  <span className="flex h-10 w-10 items-center justify-center rounded-full border" style={{ borderColor: `${ac}66` }}><I className="h-4 w-4" style={{ color: ac }} /></span>
                  <span className="min-w-0 flex-1">
                    <span className="block font-medium text-white">{m.title}</span>
                    <span className="block text-xs text-white/50"><Clock className="mr-1 inline h-3 w-3" />{m.duration} min{m.description ? ` · ${m.description}` : ""}</span>
                  </span>
                  <ChevronRight className="h-4 w-4 text-white/40" />
                </button>
              );
            })}
          </div>
        )}

        {step === "date" && (
          <div className="space-y-4">
            <p className="text-xs uppercase tracking-wide" style={{ color: ac }}>{mt?.title} · {mt?.duration} min</p>
            <div className="flex gap-2 overflow-x-auto pb-2" data-testid="book-dates">
              {days.map((d) => (
                <button key={d} onClick={() => chooseDate(d)} className={`shrink-0 rounded-xl border px-3 py-2 text-center text-xs ${date === d ? "text-black" : "text-white/70"}`} style={date === d ? { background: ac, borderColor: ac } : { borderColor: "rgba(255,255,255,0.14)" }} data-testid={`book-date-${d}`}>
                  {fmtDay(d)}
                </button>
              ))}
            </div>
            {date ? (
              loadingSlots ? <div className="flex justify-center py-6"><Loader2 className="h-5 w-5 animate-spin" style={{ color: ac }} /></div> : (
                <div>
                  <p className="mb-2 text-xs text-white/45">Times in {ownerTz} · shown in your zone ({visitorTz})</p>
                  {slots.length === 0 ? <p className="py-6 text-center text-sm text-white/50" data-testid="book-noslots">No available times this day.</p> : (
                    <div className="grid grid-cols-3 gap-2" data-testid="book-slots">
                      {slots.map((s) => (
                        <button key={s} onClick={() => chooseSlot(s)} className="rounded-lg border py-2 text-sm text-white transition-colors" style={{ borderColor: `${ac}55`, background: `${ac}0d` }} data-testid={`book-slot-${s}`}>
                          {fmtTime(s, visitorTz)}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )
            ) : null}
          </div>
        )}

        {step === "details" && (
          <div className="space-y-3" data-testid="book-details">
            <div className="rounded-xl border p-3 text-sm" style={{ borderColor: `${ac}40`, background: `${ac}0f` }}>
              <p className="font-medium text-white">{mt?.title}</p>
              <p className="text-white/60"><Clock className="mr-1 inline h-3 w-3" />{fmtDay(date)} · {fmtTime(slot, visitorTz)} ({visitorTz})</p>
            </div>
            {["name", "email", "phone"].map((k) => (
              <input key={k} value={f[k]} onChange={(e) => setF((s) => ({ ...s, [k]: e.target.value }))} placeholder={k === "name" ? "Full name" : k === "email" ? "Email" : "Phone (optional)"} className="w-full rounded-lg border bg-transparent px-3 py-2.5 text-sm text-white placeholder:text-white/35 focus:outline-none" style={{ borderColor: `${ac}40` }} data-testid={`book-${k}`} />
            ))}
            <textarea value={f.note} onChange={(e) => setF((s) => ({ ...s, note: e.target.value }))} placeholder="Note (optional)" rows={2} className="w-full rounded-lg border bg-transparent px-3 py-2.5 text-sm text-white placeholder:text-white/35 focus:outline-none" style={{ borderColor: `${ac}40` }} data-testid="book-note" />
            <button onClick={confirm} disabled={saving} className="w-full rounded-full py-3 text-sm font-medium text-black" style={{ background: ac }} data-testid="book-confirm">
              {saving ? <Loader2 className="mx-auto h-4 w-4 animate-spin" /> : "Confirm Meeting"}
            </button>
          </div>
        )}

        {step === "done" && done && (
          <div className="py-4 text-center" data-testid="book-success">
            <span className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-full" style={{ background: `${ac}22` }}><PartyPopper className="h-7 w-7" style={{ color: ac }} /></span>
            <h3 className="text-2xl font-light">{done.meeting.status === "requested" ? "Meeting request sent" : "You're booked"}</h3>
            {done.meeting.status === "requested" ? (
              <p className="mx-auto mt-1 max-w-xs text-sm text-white/60" data-testid="book-pending-note">Waiting for confirmation{ownerName ? ` from ${ownerName}` : ""}. You'll be notified once it's confirmed.</p>
            ) : null}
            <div className="mx-auto mt-4 max-w-xs rounded-xl border p-4 text-left text-sm" style={{ borderColor: `${ac}40`, background: `${ac}0f` }}>
              <p className="font-medium text-white">{done.meeting.meeting_type_title}</p>
              <p className="text-white/70">{fmtDay(date)} · {fmtTime(done.meeting.start_utc, visitorTz)} ({visitorTz})</p>
              <p className="text-white/50">{ownerName ? `with ${ownerName}` : ""}</p>
            </div>
            <div className="mt-4 flex items-center justify-center gap-2 text-xs">
              <span className="text-white/45">Manage link:</span>
              <button onClick={() => { navigator.clipboard.writeText(`${window.location.origin}/m/${done.manage_token}`); toast.success("Manage link copied"); }} className="flex items-center gap-1" style={{ color: ac }} data-testid="book-copy-manage"><Copy className="h-3 w-3" /> Copy</button>
            </div>
            <a href={`/m/${done.manage_token}`} className="mt-3 inline-block text-xs text-white/50 underline" data-testid="book-manage-link">Reschedule or cancel</a>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
