import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useLocale } from "@/i18n/useLocale";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Camera, Upload, ScanLine, Loader2, RefreshCw, Check, QrCode, CalendarDays, Plus, MapPin, CreditCard, Phone, Mail, MessageCircle, ArrowRight, Bell } from "lucide-react";
import { toast } from "sonner";
import { decodeQrFromDataUrl, parseContact } from "@/lib/qrContact";

const RTL = ["ar"];
const EMPTY = { name: "", first_name: "", last_name: "", title: "", company: "", email: "", phone: "", website: "",
  linkedin: "", badge_id: "", booth: "", address: "", city: "", country: "", language: "en", notes: "" };
const digits = (p) => (p || "").replace(/[^\d+]/g, "").replace(/^\+/, "");

const goldBtn = "rounded-lg bg-[#D6A653] font-medium text-[#050607] transition-all hover:bg-[#E8B764] active:scale-[0.98]";
const ghostBtn = "rounded-lg border border-white/15 bg-transparent text-white hover:bg-white/5";

function shrink(dataUrl, max = 1600, quality = 0.85) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      let { width, height } = img;
      const scale = Math.min(1, max / Math.max(width, height));
      width = Math.round(width * scale); height = Math.round(height * scale);
      const c = document.createElement("canvas");
      c.width = width; c.height = height;
      c.getContext("2d").drawImage(img, 0, 0, width, height);
      resolve(c.toDataURL("image/jpeg", quality));
    };
    img.onerror = () => resolve(dataUrl);
    img.src = dataUrl;
  });
}

export default function ScanCardDialog({ open, onOpenChange, cards = [], onSaved }) {
  const navigate = useNavigate();
  const { t } = useLocale();
  const scannableCards = cards.filter((c) => c.slug);
  const [sc, setSc] = useState(null);
  useEffect(() => { if (open) api.get("/billing").then(({ data }) => setSc(data.usage?.scanner ? { ...data.usage.scanner, active: data.active } : null)).catch(() => {}); }, [open]);
  const [step, setStep] = useState("capture");
  const [mode, setMode] = useState("event_badge_scan"); // event_badge_scan | business_card_scan
  const [source, setSource] = useState("event_badge_scan");
  const [image, setImage] = useState("");
  const [scanning, setScanning] = useState(false);
  const [saving, setSaving] = useState(false);
  const [draft, setDraft] = useState(EMPTY);
  const [cardSlug, setCardSlug] = useState("");
  const [camActive, setCamActive] = useState(false);
  const [camError, setCamError] = useState("");
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const fileRef = useRef(null);

  // ---- Events
  const [events, setEvents] = useState([]);
  const [eventId, setEventId] = useState(() => localStorage.getItem("tp_active_event") || "");
  const [creatingEvent, setCreatingEvent] = useState(false);
  const [evForm, setEvForm] = useState({ name: "", location: "", start_date: "", end_date: "" });
  const [savingEvent, setSavingEvent] = useState(false);
  const [savedLead, setSavedLead] = useState(null);

  const loadEvents = () => api.get("/events").then(({ data }) => setEvents(data || [])).catch(() => {});
  useEffect(() => { if (open) loadEvents(); }, [open]);
  const activeEvent = events.find((e) => e.id === eventId) || null;
  const setActiveEvent = (id) => { setEventId(id); try { id ? localStorage.setItem("tp_active_event", id) : localStorage.removeItem("tp_active_event"); } catch (_) {} };

  const createEvent = async () => {
    if (!evForm.name.trim()) { toast.error(t("events.nameRequired")); return; }
    setSavingEvent(true);
    try {
      const { data } = await api.post("/events", { ...evForm });
      await loadEvents();
      setActiveEvent(data.id);
      setCreatingEvent(false);
      setEvForm({ name: "", location: "", start_date: "", end_date: "" });
      toast.success(t("events.created"));
    } catch (err) {
      toast.error(err?.response?.data?.detail || t("events.createFailed"));
    } finally { setSavingEvent(false); }
  };

  const reset = () => {
    setStep("capture"); setImage(""); setDraft(EMPTY); setScanning(false); setSaving(false);
    setSavedLead(null); setDupLead(null);
    setCardSlug(scannableCards[0]?.slug || "");
  };

  const isBadge = mode === "event_badge_scan";
  useEffect(() => { setSource(mode); }, [mode]);

  const stopCam = () => {
    if (streamRef.current) { streamRef.current.getTracks().forEach((t) => t.stop()); streamRef.current = null; }
    setCamActive(false);
  };

  const startCam = async () => {
    setCamError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" } }, audio: false });
      streamRef.current = stream;
      setCamActive(true);
      setTimeout(() => { if (videoRef.current) { videoRef.current.srcObject = stream; videoRef.current.play?.(); } }, 50);
    } catch (e) {
      setCamError(t("scan.cameraUnavailable"));
    }
  };

  useEffect(() => {
    if (open) { reset(); startCam(); } else { stopCam(); }
    return () => stopCam();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const capturePhoto = async () => {
    const v = videoRef.current;
    if (!v) return;
    const c = document.createElement("canvas");
    c.width = v.videoWidth || 1280; c.height = v.videoHeight || 720;
    c.getContext("2d").drawImage(v, 0, 0, c.width, c.height);
    const raw = c.toDataURL("image/jpeg", 0.9);
    stopCam();
    setImage(await shrink(raw));
  };

  const onFile = async (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    const reader = new FileReader();
    reader.onload = async () => { stopCam(); setImage(await shrink(reader.result)); };
    reader.readAsDataURL(f);
  };

  const runScan = async () => {
    if (!image) return;
    setScanning(true);
    try {
      // Universal: try a contact QR locally first (offline, free, private).
      const qrText = await decodeQrFromDataUrl(image);
      if (qrText) {
        const parsed = parseContact(qrText);
        if (parsed) {
          setDraft({ ...EMPTY, ...parsed, language: "en" });
          setSource("qr_scan");
          setStep("review");
          toast.success(t("scan.qrRead"));
          return;
        }
      }
      const { data } = await api.post("/scan/card", { image_base64: image, source: mode });
      if (data.configured === false) { toast.error(data.message || t("scan.notConfigured")); return; }
      setDraft({ ...EMPTY, ...data.draft });
      setSource(mode);
      setStep("review");
      toast.success(isBadge ? t("scan.badgeRead") : t("scan.cardRead"));
    } catch (err) {
      const msg = err?.response?.data?.detail || t("scan.couldNotRead");
      toast.error(msg);
    } finally { setScanning(false); }
  };

  const [dupLead, setDupLead] = useState(null);

  const scannerType = () => (source === "event_badge_scan" ? "event_badge" : source === "business_card_scan" ? "business_card" : "");

  const doSave = async (force) => {
    setSaving(true);
    try {
      const { data } = await api.post("/scan/confirm", {
        ...draft, cardSlug, source, scanner_type: scannerType(),
        event_id: isBadge ? eventId : "", force: !!force,
      });
      if (data.ok === false && data.duplicate) { setDupLead(data.duplicate); return; }
      setSavedLead(data.lead);
      setStep("saved");
      toast.success(t("scan.leadSaved"));
      onSaved?.();
    } catch (err) {
      toast.error(err?.response?.data?.detail || t("scan.couldNotSave"));
    } finally { setSaving(false); }
  };

  const save = async () => {
    if (!draft.name.trim()) { toast.error(t("scan.nameRequired")); return; }
    if (!cardSlug) { toast.error(t("scan.pickCard")); return; }
    setDupLead(null);
    await doSave(false);
  };

  const updateExisting = async () => {
    if (!dupLead) return;
    setSaving(true);
    try {
      const { data } = await api.post("/scan/confirm", {
        ...draft, cardSlug, source, scanner_type: scannerType(),
        event_id: isBadge ? eventId : "", update_lead_id: dupLead.id,
      });
      setSavedLead(data.lead);
      setStep("saved");
      setDupLead(null);
      toast.success(t("scan.dupUpdated"));
      onSaved?.();
    } catch (err) {
      toast.error(err?.response?.data?.detail || t("scan.couldNotSave"));
    } finally { setSaving(false); }
  };

  const field = (key, label, opts = {}) => (
    <div className="space-y-1">
      <Label className="text-xs text-white/55">{label}{key === "name" ? <span className="text-[#D6A653]"> *</span> : null}</Label>
      <Input value={draft[key] || ""} onChange={(e) => setDraft((d) => ({ ...d, [key]: e.target.value }))}
        dir={RTL.includes(draft.language) && ["name", "company"].includes(key) ? "rtl" : "ltr"}
        aria-invalid={key === "name" && !draft.name.trim() ? true : undefined}
        className={key === "name" && !draft.name.trim() ? "border-red-500/50" : undefined}
        data-testid={`scan-field-${key}`} {...opts} />
    </div>
  );

  const EventPicker = () => (
    <div className="space-y-2" data-testid="scan-event-picker">
      <div className="flex items-center justify-between">
        <Label className="flex items-center gap-1.5 text-xs text-white/70"><CalendarDays className="h-3.5 w-3.5 text-[#D6A653]" /> {t("scan.eventLabel")}</Label>
        {!creatingEvent ? (
          <button onClick={() => setCreatingEvent(true)} className="flex items-center gap-1 text-[11px] text-[#D6A653] hover:underline" data-testid="scan-event-new"><Plus className="h-3 w-3" /> {t("scan.newEvent")}</button>
        ) : null}
      </div>
      {creatingEvent ? (
        <div className="space-y-2 rounded-xl border border-[#D6A653]/25 bg-[#D6A653]/[0.05] p-3" data-testid="scan-event-create">
          <Input value={evForm.name} onChange={(e) => setEvForm((f) => ({ ...f, name: e.target.value }))} placeholder={t("events.namePlaceholder")} className="h-9 text-sm" data-testid="scan-event-name" />
          <Input value={evForm.location} onChange={(e) => setEvForm((f) => ({ ...f, location: e.target.value }))} placeholder={t("events.locationPlaceholder")} className="h-9 text-sm" data-testid="scan-event-location" />
          <div className="grid grid-cols-2 gap-2">
            <Input type="date" value={evForm.start_date} onChange={(e) => setEvForm((f) => ({ ...f, start_date: e.target.value }))} className="h-9 text-sm" data-testid="scan-event-start" />
            <Input type="date" value={evForm.end_date} onChange={(e) => setEvForm((f) => ({ ...f, end_date: e.target.value }))} className="h-9 text-sm" data-testid="scan-event-end" />
          </div>
          <div className="flex gap-2">
            <Button className={`flex-1 ${goldBtn}`} onClick={createEvent} disabled={savingEvent} data-testid="scan-event-save">{savingEvent ? <Loader2 className="h-4 w-4 animate-spin" /> : t("events.create")}</Button>
            <Button className={ghostBtn} onClick={() => setCreatingEvent(false)} data-testid="scan-event-cancel">{t("scan.cancel")}</Button>
          </div>
        </div>
      ) : (
        <Select value={eventId || "__none"} onValueChange={(v) => setActiveEvent(v === "__none" ? "" : v)}>
          <SelectTrigger className="h-9 text-sm" data-testid="scan-event-select"><SelectValue placeholder={t("scan.selectEvent")} /></SelectTrigger>
          <SelectContent className="aria-pop">
            <SelectItem value="__none">{t("scan.noEvent")}</SelectItem>
            {events.map((e) => <SelectItem key={e.id} value={e.id}>{e.name}{e.location ? ` · ${e.location}` : ""}</SelectItem>)}
          </SelectContent>
        </Select>
      )}
    </div>
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="aria-dark max-h-[90vh] max-w-lg overflow-y-auto border-white/10 bg-[#0A0B0D] text-white" data-testid="scan-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-white">
            <ScanLine className="h-5 w-5 text-[#D6A653]" /> {t("scan.title")}
          </DialogTitle>
          <DialogDescription className="text-white/50">{t("scan.desc")}</DialogDescription>
        </DialogHeader>

        {dupLead ? (
          <div className="space-y-4" data-testid="scan-duplicate">
            <div className="rounded-xl border border-amber-400/30 bg-amber-400/[0.07] p-4">
              <p className="text-sm font-medium text-amber-200">{t("scan.dupTitle")}</p>
              <p className="mt-1 text-xs text-white/60">{t("scan.dupBody")}</p>
              <div className="mt-3 rounded-lg border border-white/10 bg-[#0A0B0D] p-3 text-sm">
                <p className="text-white">{dupLead.name}</p>
                <p className="text-xs text-white/50">{[dupLead.title, dupLead.company].filter(Boolean).join(" · ")}</p>
                <p className="text-xs text-white/50">{[dupLead.email, dupLead.phone].filter(Boolean).join(" · ")}</p>
                {dupLead.event ? <p className="mt-1 text-xs text-[#D6A653]">{t("scan.dupPrevEvent", { event: dupLead.event })}</p> : null}
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button className={`flex-1 ${goldBtn}`} onClick={updateExisting} disabled={saving} data-testid="scan-dup-update">{saving ? <Loader2 className="h-4 w-4 animate-spin" /> : t("scan.dupUpdate")}</Button>
              <Button className={ghostBtn} onClick={() => doSave(true)} disabled={saving} data-testid="scan-dup-createanyway">{t("scan.dupCreateAnyway")}</Button>
              <Button className={ghostBtn} onClick={() => setDupLead(null)} disabled={saving} data-testid="scan-dup-cancel">{t("scan.cancel")}</Button>
            </div>
          </div>
        ) : null}

        {!dupLead && step !== "saved" && (<>

        {sc ? (
          (!sc.active || sc.limit === 0) ? (
            <div className="flex items-center justify-between gap-3 rounded-xl border border-red-500/30 bg-red-500/[0.06] px-4 py-2.5" data-testid="scan-entitlement">
              <span className="flex items-center gap-2 text-xs text-red-200/80"><ScanLine className="h-4 w-4" /> {t("scan.unavailable")}</span>
              <button onClick={() => { onOpenChange(false); navigate("/billing"); }} data-testid="scan-upgrade" className="rounded-lg bg-[#D6A653] px-3 py-1.5 text-xs font-medium text-black hover:brightness-110">{t("scan.upgrade")}</button>
            </div>
          ) : (
            <div className="rounded-xl border border-[#D6A653]/25 bg-[#D6A653]/[0.06] px-4 py-2.5" data-testid="scan-entitlement">
              <span className="flex items-center gap-2 text-xs text-white/70"><ScanLine className="h-4 w-4 text-[#D6A653]" />
                {sc.limit >= 100000 ? t("scan.unlimited") : t("scan.included", { used: sc.used, limit: sc.limit, period: t(sc.period === "total" ? "scan.period_total" : "scan.period_month") })}
              </span>
            </div>
          )
        ) : null}

        {step === "capture" && (
          <div className="space-y-4">
            {/* Mode selection — fast tap targets */}
            <div className="grid grid-cols-2 gap-2" data-testid="scan-mode">
              <button onClick={() => setMode("event_badge_scan")} data-testid="scan-mode-badge"
                className={`rounded-xl border px-3 py-2.5 text-sm font-medium transition-all ${isBadge ? "border-[#D6A653] bg-[#D6A653]/15 text-white" : "border-white/12 bg-white/[0.02] text-white/60 hover:text-white"}`}>
                <CreditCard className="mx-auto mb-1 h-4 w-4" /> {t("scan.modeBadge")}
              </button>
              <button onClick={() => setMode("business_card_scan")} data-testid="scan-mode-card"
                className={`rounded-xl border px-3 py-2.5 text-sm font-medium transition-all ${!isBadge ? "border-[#D6A653] bg-[#D6A653]/15 text-white" : "border-white/12 bg-white/[0.02] text-white/60 hover:text-white"}`}>
                <ScanLine className="mx-auto mb-1 h-4 w-4" /> {t("scan.modeCard")}
              </button>
            </div>

            <p className="flex items-center gap-1.5 text-xs text-white/45" data-testid="scan-universal-hint">
              <QrCode className="h-3.5 w-3.5 text-[#D6A653]" /> {t("scan.universalHint")}
            </p>

            {isBadge ? <EventPicker /> : null}

            <div className="flex aspect-[4/3] items-center justify-center overflow-hidden rounded-xl border border-white/10 bg-black">
              {image ? (
                <img src={image} alt="captured" className="h-full w-full object-contain" data-testid="scan-preview" />
              ) : camActive ? (
                <video ref={videoRef} playsInline muted className="h-full w-full object-cover" data-testid="scan-camera" />
              ) : (
                <div className="p-6 text-center text-sm text-white/50">{camError || t("scan.cameraPrompt")}</div>
              )}
            </div>

            <div className="grid grid-cols-2 gap-2">
              {image ? (
                <Button onClick={() => { setImage(""); startCam(); }} className={ghostBtn} data-testid="scan-retake">
                  <RefreshCw className="mr-1 h-4 w-4" /> {t("scan.retake")}
                </Button>
              ) : camActive ? (
                <Button onClick={capturePhoto} className={goldBtn} data-testid="scan-capture">
                  <Camera className="mr-1 h-4 w-4" /> {t("scan.capture")}
                </Button>
              ) : (
                <Button onClick={startCam} className={ghostBtn} data-testid="scan-start-camera">
                  <Camera className="mr-1 h-4 w-4" /> {t("scan.camera")}
                </Button>
              )}
              <Button onClick={() => fileRef.current?.click()} className={ghostBtn} data-testid="scan-upload">
                <Upload className="mr-1 h-4 w-4" /> {t("scan.upload")}
              </Button>
              <input ref={fileRef} type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={onFile} data-testid="scan-file-input" />
            </div>

            <Button className={`w-full ${goldBtn}`} disabled={!image || scanning} onClick={runScan} data-testid="scan-run">
              {scanning ? <><Loader2 className="mr-1 h-4 w-4 animate-spin" /> {t("scan.reading")}</> : <><ScanLine className="mr-1 h-4 w-4" /> {isBadge ? t("scan.scanBadge") : t("scan.scanCard")}</>}
            </Button>
          </div>
        )}

        {step === "review" && (
          <div className="space-y-3">
            <p className="text-xs text-white/50">{source === "qr_scan" ? t("scan.qrReviewIntro") : isBadge ? t("scan.badgeReviewIntro") : t("scan.reviewIntro")}</p>
            {field("name", t("scan.fFullName"))}
            <div className="grid grid-cols-2 gap-3">
              {field("title", t("scan.fJobTitle"))}
              {field("company", t("scan.fCompany"))}
            </div>
            <div className="grid grid-cols-2 gap-3">
              {field("email", t("scan.fEmail"))}
              {field("phone", t("scan.fPhone"))}
            </div>
            {field("website", t("scan.fWebsite"))}
            {isBadge ? (
              <div className="grid grid-cols-2 gap-3">
                {field("linkedin", t("scan.fLinkedin"))}
                {field("badge_id", t("scan.fBadgeId"))}
              </div>
            ) : null}
            {isBadge ? <EventPicker /> : null}
            <div className="space-y-1">
              <Label className="text-xs text-white/55">{t("scan.fNotes")}</Label>
              <Textarea rows={2} value={draft.notes} onChange={(e) => setDraft((d) => ({ ...d, notes: e.target.value }))} data-testid="scan-field-notes" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label className="text-xs text-white/55">{t("scan.saveToCard")}</Label>
                <Select value={cardSlug} onValueChange={setCardSlug}>
                  <SelectTrigger className="h-9 text-sm" data-testid="scan-target-card"><SelectValue placeholder={t("scan.selectCard")} /></SelectTrigger>
                  <SelectContent className="aria-pop">
                    {scannableCards.map((c) => (
                      <SelectItem key={c.slug} value={c.slug}>{c.identity?.fullName || c.slug} (/{c.slug})</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label className="text-xs text-white/55">{t("scan.language")}</Label>
                <Select value={draft.language} onValueChange={(v) => setDraft((d) => ({ ...d, language: v }))}>
                  <SelectTrigger className="h-9 text-sm" data-testid="scan-language"><SelectValue /></SelectTrigger>
                  <SelectContent className="aria-pop">
                    <SelectItem value="en">English</SelectItem>
                    <SelectItem value="ar">العربية</SelectItem>
                    <SelectItem value="es">Español</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="flex gap-2 pt-1">
              <Button className={`flex-1 ${ghostBtn}`} onClick={() => { setStep("capture"); setImage(""); startCam(); }} data-testid="scan-back">
                <RefreshCw className="mr-1 h-4 w-4" /> {t("scan.rescan")}
              </Button>
              <Button className={`flex-1 ${goldBtn}`} disabled={saving || !draft.name.trim()} onClick={save} data-testid="scan-save">
                {saving ? <Loader2 className="mr-1 h-4 w-4 animate-spin" /> : <Check className="mr-1 h-4 w-4" />} {t("scan.saveLead")}
              </Button>
            </div>
          </div>
        )}
        </>)}

        {/* Saved — immediate follow-up actions (reuses existing lead management) */}
        {step === "saved" && savedLead ? (
          <div className="space-y-4" data-testid="scan-saved">
            <div className="rounded-xl border border-emerald-400/30 bg-emerald-500/[0.07] p-4 text-center">
              <Check className="mx-auto mb-1 h-6 w-6 text-emerald-300" />
              <p className="text-sm font-medium text-white">{t("scan.savedTitle")}</p>
              <p className="mt-0.5 text-xs text-white/60">{savedLead.name}{savedLead.company ? ` · ${savedLead.company}` : ""}</p>
              {savedLead.event ? <p className="mt-1 flex items-center justify-center gap-1 text-xs text-[#D6A653]"><CalendarDays className="h-3 w-3" /> {savedLead.event}</p> : null}
            </div>
            <p className="text-xs uppercase tracking-wider text-white/45">{t("scan.followUpNow")}</p>
            <div className="grid grid-cols-3 gap-2">
              {savedLead.phone ? <a href={`tel:${savedLead.phone}`} className={`flex flex-col items-center gap-1 rounded-lg border border-white/12 py-2.5 text-xs text-white hover:border-[#D6A653]/50`} data-testid="saved-call"><Phone className="h-4 w-4 text-[#D6A653]" /> {t("leads.call")}</a> : null}
              {savedLead.phone ? <a href={`https://wa.me/${digits(savedLead.phone)}`} target="_blank" rel="noreferrer" className="flex flex-col items-center gap-1 rounded-lg border border-white/12 py-2.5 text-xs text-white hover:border-[#D6A653]/50" data-testid="saved-wa"><MessageCircle className="h-4 w-4 text-[#D6A653]" /> {t("leads.whatsapp")}</a> : null}
              {savedLead.email ? <a href={`mailto:${savedLead.email}`} className="flex flex-col items-center gap-1 rounded-lg border border-white/12 py-2.5 text-xs text-white hover:border-[#D6A653]/50" data-testid="saved-email"><Mail className="h-4 w-4 text-[#D6A653]" /> {t("leads.email")}</a> : null}
            </div>
            <button onClick={() => { onOpenChange(false); navigate(`/leads?lead=${savedLead.id}`); }} className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-[#D6A653]/50 bg-[#D6A653]/10 py-2.5 text-sm font-medium text-[#D6A653] hover:bg-[#D6A653]/20" data-testid="saved-view-lead">
              <Bell className="h-4 w-4" /> {t("scan.openLeadFollowUp")}
            </button>
            <Button className={`w-full ${goldBtn}`} onClick={() => { reset(); startCam(); }} data-testid="saved-scan-next">
              <ArrowRight className="mr-1 h-4 w-4" /> {t("scan.scanNext")}
            </Button>
          </div>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
