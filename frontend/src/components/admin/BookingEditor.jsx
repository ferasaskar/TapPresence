import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Plus, Trash2, Loader2, CalendarClock } from "lucide-react";
import { toast } from "sonner";

const TZ = ["Asia/Dubai", "Asia/Riyadh", "Asia/Qatar", "Europe/London", "Europe/Paris", "America/New_York", "America/Los_Angeles", "Asia/Kolkata", "Asia/Singapore", "Australia/Sydney", "UTC"];
const DAYS = [["1", "Mon"], ["2", "Tue"], ["3", "Wed"], ["4", "Thu"], ["5", "Fri"], ["6", "Sat"], ["7", "Sun"]];
const LOCS = [["video", "Google Meet / Video"], ["in_person", "In Person"], ["phone", "Phone Call"], ["custom", "Custom Location"]];
const panel = "rounded-xl border border-white/10 bg-white/[0.02] p-4";
const F = ({ label, children }) => <div className="space-y-1"><Label className="text-xs text-white/55">{label}</Label>{children}</div>;

export default function BookingEditor({ form, set, cardId }) {
  const b = form.booking || {};
  const [mts, setMts] = useState(null);
  const [avail, setAvail] = useState(null);
  const [savingA, setSavingA] = useState(false);

  useEffect(() => {
    if (!cardId) return;
    api.get(`/admin/cards/${cardId}/meeting-types`).then(({ data }) => setMts(data)).catch(() => setMts([]));
    api.get(`/admin/cards/${cardId}/availability`).then(({ data }) => setAvail(data)).catch(() => setAvail(null));
  }, [cardId]);

  const addMt = async () => {
    const { data } = await api.post(`/admin/cards/${cardId}/meeting-types`, { title: "New Meeting", duration: 30, location_type: "video", enabled: true, order: (mts?.length || 0) });
    setMts((m) => [...(m || []), data]);
  };
  const saveMt = async (mt) => { await api.put(`/admin/cards/${cardId}/meeting-types/${mt.id}`, mt); toast.success("Meeting type saved"); };
  const delMt = async (id) => { await api.delete(`/admin/cards/${cardId}/meeting-types/${id}`); setMts((m) => m.filter((x) => x.id !== id)); };
  const upMt = (i, k, v) => setMts((m) => { const c = [...m]; c[i] = { ...c[i], [k]: v }; return c; });

  const saveAvail = async () => {
    setSavingA(true);
    try { await api.put(`/admin/cards/${cardId}/availability`, avail); toast.success("Availability saved"); }
    catch { toast.error("Could not save"); } finally { setSavingA(false); }
  };
  const toggleDay = (d) => setAvail((a) => ({ ...a, days: a.days.includes(+d) ? a.days.filter((x) => x !== +d) : [...a.days, +d].sort() }));

  return (
    <div className="space-y-5">
      <div className={`${panel} flex items-center justify-between`}>
        <div>
          <p className="flex items-center gap-2 font-medium text-white"><CalendarClock className="h-4 w-4 text-[#D6A653]" /> Native ARIADNI Booking</p>
          <p className="text-xs text-white/50">Let visitors book meetings directly on your card — no external tool.</p>
        </div>
        <Switch checked={!!b.nativeEnabled} onCheckedChange={(v) => set("booking.nativeEnabled", v)} data-testid="booking-native-toggle" />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <F label="Your timezone">
          <Select value={b.timezone || "Asia/Dubai"} onValueChange={(v) => set("booking.timezone", v)}>
            <SelectTrigger data-testid="booking-timezone"><SelectValue /></SelectTrigger>
            <SelectContent className="aria-pop">{TZ.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent>
          </Select>
        </F>
        <F label="External booking URL (fallback)">
          <Input value={b.bookingUrl || ""} onChange={(e) => set("booking.bookingUrl", e.target.value)} placeholder="Calendly / Cal.com" data-testid="editor-booking" />
        </F>
      </div>
      <p className="text-xs text-white/40">When native booking is ON, your card uses the ARIADNI calendar. When OFF, it falls back to the external URL if set.</p>

      {!cardId ? (
        <div className={`${panel} text-sm text-white/55`}>Save/publish this card first, then return here to add meeting types and set your working hours. Sensible defaults (Mon–Fri, 9–6, 15/30/45-min meetings) are created automatically.</div>
      ) : (
        <>
          <div>
            <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#D6A653]">Meeting Types</p>
            {mts === null ? <Loader2 className="h-5 w-5 animate-spin text-[#D6A653]" /> : (
              <div className="space-y-3">
                {mts.map((mt, i) => (
                  <div key={mt.id} className={`${panel} space-y-3`} data-testid={`mt-${i}`}>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2"><Switch checked={!!mt.enabled} onCheckedChange={(v) => upMt(i, "enabled", v)} /><span className="text-xs text-white/50">{mt.enabled ? "Public" : "Hidden"}</span></div>
                      <button onClick={() => delMt(mt.id)} className="text-red-400/80 hover:text-red-400" data-testid={`mt-del-${i}`}><Trash2 className="h-4 w-4" /></button>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <F label="Title"><Input value={mt.title} onChange={(e) => upMt(i, "title", e.target.value)} data-testid={`mt-title-${i}`} /></F>
                      <F label="Duration (min)"><Input type="number" value={mt.duration} onChange={(e) => upMt(i, "duration", parseInt(e.target.value) || 0)} data-testid={`mt-duration-${i}`} /></F>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <F label="Location">
                        <Select value={mt.location_type} onValueChange={(v) => upMt(i, "location_type", v)}>
                          <SelectTrigger><SelectValue /></SelectTrigger>
                          <SelectContent className="aria-pop">{LOCS.map(([v, l]) => <SelectItem key={v} value={v}>{l}</SelectItem>)}</SelectContent>
                        </Select>
                      </F>
                      <F label="Location detail / link"><Input value={mt.location_detail || ""} onChange={(e) => upMt(i, "location_detail", e.target.value)} /></F>
                    </div>
                    <F label="Description"><Input value={mt.description || ""} onChange={(e) => upMt(i, "description", e.target.value)} /></F>
                    <div className="flex items-center justify-between rounded-lg border border-white/10 bg-white/[0.02] px-3 py-2">
                      <div>
                        <p className="text-xs font-medium text-white">Requires approval</p>
                        <p className="text-[11px] text-white/45">Guests send a request; you Accept, Decline or Propose a new time. Off = auto-confirm.</p>
                      </div>
                      <Switch checked={mt.confirmation_mode === "approval"} onCheckedChange={(v) => upMt(i, "confirmation_mode", v ? "approval" : "auto")} data-testid={`mt-approval-${i}`} />
                    </div>
                    <Button size="sm" onClick={() => saveMt(mts[i])} className="rounded-lg bg-[#D6A653] text-[#050607] hover:bg-[#E8B764]" data-testid={`mt-save-${i}`}>Save type</Button>
                  </div>
                ))}
                <Button onClick={addMt} className="rounded-lg border border-white/15 bg-transparent text-white hover:bg-white/5" data-testid="mt-add"><Plus className="mr-1 h-4 w-4" /> Add meeting type</Button>
              </div>
            )}
          </div>

          {avail && (
            <div className={panel} data-testid="availability-editor">
              <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#D6A653]">Availability</p>
              <div className="mb-3 flex flex-wrap gap-2">
                {DAYS.map(([d, l]) => <button key={d} onClick={() => toggleDay(d)} className={`rounded-lg border px-3 py-1.5 text-xs ${avail.days.includes(+d) ? "border-[#D6A653] bg-[#D6A653]/12 text-white" : "border-white/12 text-white/45"}`} data-testid={`avail-day-${d}`}>{l}</button>)}
              </div>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                <F label="Start"><Input type="time" value={avail.start} onChange={(e) => setAvail((a) => ({ ...a, start: e.target.value }))} data-testid="avail-start" /></F>
                <F label="End"><Input type="time" value={avail.end} onChange={(e) => setAvail((a) => ({ ...a, end: e.target.value }))} data-testid="avail-end" /></F>
                <F label="Slot interval (min)"><Input type="number" value={avail.slot_interval} onChange={(e) => setAvail((a) => ({ ...a, slot_interval: parseInt(e.target.value) || 30 }))} /></F>
                <F label="Buffer after (min)"><Input type="number" value={avail.buffer_after} onChange={(e) => setAvail((a) => ({ ...a, buffer_after: parseInt(e.target.value) || 0 }))} /></F>
                <F label="Min notice (hours)"><Input type="number" value={avail.min_notice_hours} onChange={(e) => setAvail((a) => ({ ...a, min_notice_hours: parseInt(e.target.value) || 0 }))} /></F>
                <F label="Book up to (days)"><Input type="number" value={avail.max_days} onChange={(e) => setAvail((a) => ({ ...a, max_days: parseInt(e.target.value) || 60 }))} /></F>
              </div>
              <Button size="sm" onClick={saveAvail} disabled={savingA} className="mt-3 rounded-lg bg-[#D6A653] text-[#050607] hover:bg-[#E8B764]" data-testid="avail-save">{savingA ? <Loader2 className="h-4 w-4 animate-spin" /> : "Save availability"}</Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
