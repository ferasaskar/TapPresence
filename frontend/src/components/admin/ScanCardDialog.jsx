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
import { Camera, Upload, ScanLine, Loader2, RefreshCw, Check } from "lucide-react";
import { toast } from "sonner";

const RTL = ["ar"];
const EMPTY = { name: "", title: "", company: "", email: "", phone: "", website: "",
  address: "", city: "", country: "", language: "en", notes: "" };

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
  const [source, setSource] = useState("business_card_scan");
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

  const reset = () => {
    setStep("capture"); setImage(""); setDraft(EMPTY); setScanning(false); setSaving(false);
    setCardSlug(scannableCards[0]?.slug || "");
  };

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
      setCamError("Camera unavailable — upload a photo instead.");
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
      const { data } = await api.post("/scan/card", { image_base64: image, source });
      if (data.configured === false) { toast.error(data.message || "Scanning not configured"); return; }
      setDraft({ ...EMPTY, ...data.draft });
      setStep("review");
      toast.success("Card read — review the details below");
    } catch (err) {
      const msg = err?.response?.data?.detail || "Could not read the card. Try a clearer photo.";
      toast.error(msg);
    } finally { setScanning(false); }
  };

  const save = async () => {
    if (!draft.name.trim()) { toast.error("A name is required"); return; }
    if (!cardSlug) { toast.error("Pick which card this lead belongs to"); return; }
    setSaving(true);
    try {
      await api.post("/scan/confirm", { ...draft, cardSlug, source });
      toast.success("Lead saved to your inbox");
      onSaved?.();
      onOpenChange(false);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Could not save lead");
    } finally { setSaving(false); }
  };

  const field = (key, label, opts = {}) => (
    <div className="space-y-1">
      <Label className="text-xs text-white/55">{label}</Label>
      <Input value={draft[key]} onChange={(e) => setDraft((d) => ({ ...d, [key]: e.target.value }))}
        dir={RTL.includes(draft.language) && ["name", "company"].includes(key) ? "rtl" : "ltr"}
        data-testid={`scan-field-${key}`} {...opts} />
    </div>
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="aria-dark max-h-[90vh] max-w-lg overflow-y-auto border-white/10 bg-[#0A0B0D] text-white" data-testid="scan-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-white">
            <ScanLine className="h-5 w-5 text-[#D6A653]" /> Scan a card
          </DialogTitle>
          <DialogDescription className="text-white/50">Capture or upload a business card or event badge, review the details, then save it as a lead.</DialogDescription>
        </DialogHeader>

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
            <div className="flex gap-2">
              <Select value={source} onValueChange={setSource}>
                <SelectTrigger className="h-9 text-sm" data-testid="scan-source"><SelectValue /></SelectTrigger>
                <SelectContent className="aria-pop">
                  <SelectItem value="business_card_scan">Business card</SelectItem>
                  <SelectItem value="badge_scan">Event badge</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex aspect-[4/3] items-center justify-center overflow-hidden rounded-xl border border-white/10 bg-black">
              {image ? (
                <img src={image} alt="captured card" className="h-full w-full object-contain" data-testid="scan-preview" />
              ) : camActive ? (
                <video ref={videoRef} playsInline muted className="h-full w-full object-cover" data-testid="scan-camera" />
              ) : (
                <div className="p-6 text-center text-sm text-white/50">{camError || "Point your camera at the card"}</div>
              )}
            </div>

            <div className="grid grid-cols-2 gap-2">
              {image ? (
                <Button onClick={() => { setImage(""); startCam(); }} className={ghostBtn} data-testid="scan-retake">
                  <RefreshCw className="mr-1 h-4 w-4" /> Retake
                </Button>
              ) : camActive ? (
                <Button onClick={capturePhoto} className={goldBtn} data-testid="scan-capture">
                  <Camera className="mr-1 h-4 w-4" /> Capture
                </Button>
              ) : (
                <Button onClick={startCam} className={ghostBtn} data-testid="scan-start-camera">
                  <Camera className="mr-1 h-4 w-4" /> Camera
                </Button>
              )}
              <Button onClick={() => fileRef.current?.click()} className={ghostBtn} data-testid="scan-upload">
                <Upload className="mr-1 h-4 w-4" /> Upload
              </Button>
              <input ref={fileRef} type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={onFile} data-testid="scan-file-input" />
            </div>

            <Button className={`w-full ${goldBtn}`} disabled={!image || scanning} onClick={runScan} data-testid="scan-run">
              {scanning ? <><Loader2 className="mr-1 h-4 w-4 animate-spin" /> Reading…</> : <><ScanLine className="mr-1 h-4 w-4" /> Scan card</>}
            </Button>
          </div>
        )}

        {step === "review" && (
          <div className="space-y-3">
            <p className="text-xs text-white/50">Review &amp; edit the extracted details, then save. Nothing is saved until you confirm.</p>
            {field("name", "Full name")}
            <div className="grid grid-cols-2 gap-3">
              {field("title", "Job title")}
              {field("company", "Company")}
            </div>
            <div className="grid grid-cols-2 gap-3">
              {field("email", "Email")}
              {field("phone", "Phone")}
            </div>
            {field("website", "Website")}
            {field("address", "Address")}
            <div className="grid grid-cols-2 gap-3">
              {field("city", "City")}
              {field("country", "Country")}
            </div>
            <div className="space-y-1">
              <Label className="text-xs text-white/55">Notes</Label>
              <Textarea rows={2} value={draft.notes} onChange={(e) => setDraft((d) => ({ ...d, notes: e.target.value }))} data-testid="scan-field-notes" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label className="text-xs text-white/55">Save to card</Label>
                <Select value={cardSlug} onValueChange={setCardSlug}>
                  <SelectTrigger className="h-9 text-sm" data-testid="scan-target-card"><SelectValue placeholder="Select a card" /></SelectTrigger>
                  <SelectContent className="aria-pop">
                    {scannableCards.map((c) => (
                      <SelectItem key={c.slug} value={c.slug}>{c.identity?.fullName || c.slug} (/{c.slug})</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label className="text-xs text-white/55">Language</Label>
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
                <RefreshCw className="mr-1 h-4 w-4" /> Rescan
              </Button>
              <Button className={`flex-1 ${goldBtn}`} disabled={saving} onClick={save} data-testid="scan-save">
                {saving ? <Loader2 className="mr-1 h-4 w-4 animate-spin" /> : <Check className="mr-1 h-4 w-4" />} Save lead
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
