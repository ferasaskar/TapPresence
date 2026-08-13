import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { OwnerNav } from "@/components/admin/OwnerNav";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Loader2, ArrowLeft, CalendarDays, MapPin, Plus, Users, ChevronRight } from "lucide-react";
import { toast } from "sonner";
import { useLocale } from "@/i18n/useLocale";

const goldBtn = "rounded-lg bg-[#D6A653] font-medium text-[#050607] transition-all hover:bg-[#E8B764] active:scale-[0.98]";
const fmtDate = (d) => (d ? new Date(d + "T00:00:00").toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" }) : "");

export default function Events() {
  const navigate = useNavigate();
  const { t } = useLocale();
  const [events, setEvents] = useState(null);
  const [seg, setSeg] = useState("all");
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", location: "", start_date: "", end_date: "", notes: "" });
  const [saving, setSaving] = useState(false);

  const load = () => api.get("/events").then(({ data }) => setEvents(data)).catch(() => setEvents([]));
  useEffect(() => { load(); }, []);

  const create = async () => {
    if (!form.name.trim()) { toast.error(t("events.nameRequired")); return; }
    setSaving(true);
    try {
      await api.post("/events", form);
      toast.success(t("events.created"));
      setOpen(false);
      setForm({ name: "", location: "", start_date: "", end_date: "", notes: "" });
      load();
    } catch (err) {
      toast.error(err?.response?.data?.detail || t("events.createFailed"));
    } finally { setSaving(false); }
  };

  return (
    <div className="aria-dark relative min-h-screen bg-[#050607] text-white" style={{ fontFamily: "'Outfit', sans-serif" }} data-testid="events-page">
      <div className="grain-overlay" style={{ opacity: 0.04 }} />
      <OwnerNav active="events" />

      <main className="relative mx-auto max-w-5xl px-4 py-8 sm:px-8">
        <div className="mb-6 flex items-center gap-3">
          <button onClick={() => navigate("/dashboard")} className="text-white/50 hover:text-white" data-testid="events-back"><ArrowLeft className="h-5 w-5" /></button>
          <div className="flex-1">
            <h2 className="text-2xl font-light tracking-tight text-white">{t("events.title")}</h2>
            <p className="text-sm text-white/45">{t("events.subtitle")}</p>
          </div>
          <Button className={goldBtn} onClick={() => setOpen(true)} data-testid="events-new"><Plus className="mr-1 h-4 w-4" /> {t("events.new")}</Button>
        </div>

        {events === null ? (
          <div className="flex justify-center py-20"><Loader2 className="h-6 w-6 animate-spin text-[#D6A653]" /></div>
        ) : events.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-white/12 py-20 text-center text-white/50" data-testid="events-empty">
            <CalendarDays className="mx-auto mb-3 h-8 w-8 text-white/25" />
            {t("events.empty")}
          </div>
        ) : (
          <>
          <div className="mb-4 flex gap-2" data-testid="events-segments">
            {["all", "active", "archived"].map((s) => (
              <button key={s} onClick={() => setSeg(s)} data-testid={`events-seg-${s}`}
                className={`rounded-full border px-3.5 py-1.5 text-sm transition-all ${seg === s ? "border-[#D6A653] bg-[#D6A653]/12 text-white" : "border-white/10 text-white/55 hover:border-white/25"}`}>
                {t(`events.seg_${s}`)}
              </button>
            ))}
          </div>
          <div className="grid gap-3 sm:grid-cols-2" data-testid="events-list">
            {events.filter((e) => seg === "all" || (e.status || "active") === seg).map((e) => (
              <button key={e.id} onClick={() => navigate(`/events/${e.id}`)} data-testid={`event-card-${e.id}`}
                className="group flex items-center justify-between gap-3 rounded-2xl border border-white/10 bg-white/[0.02] p-4 text-left transition-all hover:border-[#D6A653]/40">
                <div className="min-w-0">
                  <p className="truncate font-medium text-white">{e.name}</p>
                  <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs text-white/50">
                    {e.location ? <span className="flex items-center gap-1"><MapPin className="h-3 w-3" /> {e.location}</span> : null}
                    {e.start_date ? <span className="flex items-center gap-1"><CalendarDays className="h-3 w-3" /> {fmtDate(e.start_date)}{e.end_date ? ` – ${fmtDate(e.end_date)}` : ""}</span> : null}
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    <span className="inline-flex items-center gap-1 rounded-full border border-[#D6A653]/30 bg-[#D6A653]/10 px-2 py-0.5 text-[11px] text-[#D6A653]"><Users className="h-3 w-3" /> {t("events.leadsCount", { count: e.lead_count || 0 })}</span>
                    <span className="inline-flex items-center gap-1 rounded-full border border-violet-400/30 bg-violet-400/10 px-2 py-0.5 text-[11px] text-violet-300">{t("events.meetingsCount", { count: e.meeting_count || 0 })}</span>
                    <span className="inline-flex items-center gap-1 rounded-full border border-emerald-400/30 bg-emerald-400/10 px-2 py-0.5 text-[11px] text-emerald-300">{t("events.customersCount", { count: e.customer_count || 0 })}</span>
                  </div>
                </div>
                <ChevronRight className="h-5 w-5 shrink-0 text-white/30 transition-colors group-hover:text-[#D6A653]" />
              </button>
            ))}
          </div>
          </>
        )}
      </main>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="aria-dark max-w-md border-white/10 bg-[#0A0B0D] text-white" data-testid="event-create-dialog">
          <DialogHeader><DialogTitle className="text-white">{t("events.new")}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <Input value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} placeholder={t("events.namePlaceholder")} data-testid="event-form-name" />
            <Input value={form.location} onChange={(e) => setForm((f) => ({ ...f, location: e.target.value }))} placeholder={t("events.locationPlaceholder")} data-testid="event-form-location" />
            <div className="grid grid-cols-2 gap-2">
              <div><label className="text-xs text-white/50">{t("events.startDate")}</label><Input type="date" value={form.start_date} onChange={(e) => setForm((f) => ({ ...f, start_date: e.target.value }))} data-testid="event-form-start" /></div>
              <div><label className="text-xs text-white/50">{t("events.endDate")}</label><Input type="date" value={form.end_date} onChange={(e) => setForm((f) => ({ ...f, end_date: e.target.value }))} data-testid="event-form-end" /></div>
            </div>
            <Input value={form.notes} onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))} placeholder={t("events.notesPlaceholder")} data-testid="event-form-notes" />
            <Button className={`w-full ${goldBtn}`} onClick={create} disabled={saving} data-testid="event-form-save">{saving ? <Loader2 className="h-4 w-4 animate-spin" /> : t("events.create")}</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
