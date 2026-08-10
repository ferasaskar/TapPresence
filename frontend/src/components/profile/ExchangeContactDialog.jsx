import { useState, useRef } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { api, vcardUrl, newIdemKey, idem } from "@/lib/api";
import { Loader2, Check, UserPlus, Download } from "lucide-react";
import { toast } from "sonner";
import { useLocale } from "@/i18n/useLocale";

// Exchange Contact: visitor shares their details (creates a CRM lead) and then
// receives the owner's contact card back — a true mutual exchange.
export function ExchangeContactDialog({ open, onOpenChange, slug, accent = "#D6A653", ownerName = "" }) {
  const ac = accent;
  const { t } = useLocale();
  const [f, setF] = useState({ name: "", email: "", phone: "", message: "" });
  const [saving, setSaving] = useState(false);
  const [done, setDone] = useState(false);
  const idemRef = useRef(null);
  const firstName = ownerName ? ownerName.split(" ")[0] : "";

  const submit = async () => {
    if (!f.name.trim() || !(f.email.trim() || f.phone.trim())) { toast.error(t("exchange.required")); return; }
    setSaving(true);
    if (!idemRef.current) idemRef.current = newIdemKey();
    try {
      await api.post(`/cards/${slug}/leads`, { name: f.name, email: f.email, phone: f.phone, message: f.message }, idem(idemRef.current));
      api.post(`/cards/${slug}/track`, { type: "tap", key: "contact_exchanged" }).catch(() => {});
      idemRef.current = null;
      setDone(true);
    } catch (err) {
      toast.error(err.response?.data?.detail || t("exchange.failed"));
    } finally { setSaving(false); }
  };

  const ph = { name: t("exchange.fullName"), email: t("exchange.email"), phone: t("exchange.phoneOptional") };

  return (
    <Dialog open={open} onOpenChange={(v) => { onOpenChange(v); if (!v) { setDone(false); setF({ name: "", email: "", phone: "", message: "" }); } }}>
      <DialogContent className="max-w-md border text-white" style={{ background: "#0B0B0D", borderColor: `${ac}59` }} data-testid="exchange-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-white"><UserPlus className="h-5 w-5" style={{ color: ac }} /> {t("exchange.title")}</DialogTitle>
        </DialogHeader>
        {done ? (
          <div className="py-4 text-center" data-testid="exchange-success">
            <span className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-full" style={{ background: `${ac}22` }}><Check className="h-7 w-7" style={{ color: ac }} /></span>
            <h3 className="text-xl font-light">{t("exchange.detailsShared")}</h3>
            <p className="mt-1 text-sm text-white/55">{ownerName ? `${ownerName} ${t("exchange.willBeInTouch")}` : t("exchange.willBeInTouchGeneric")}</p>
            <a href={vcardUrl(slug)} className="mt-5 inline-flex items-center gap-2 rounded-full px-6 py-3 text-sm font-medium text-black" style={{ background: ac }} data-testid="exchange-savecontact"><Download className="h-4 w-4" /> {firstName ? t("exchange.saveContact", { name: firstName }) : t("exchange.saveContactGeneric")}</a>
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-sm text-white/55">{ownerName ? t("exchange.shareToConnectWith", { name: ownerName }) : t("exchange.shareToConnect")}</p>
            {["name", "email", "phone"].map((k) => (
              <input key={k} value={f[k]} onChange={(e) => setF((s) => ({ ...s, [k]: e.target.value }))} placeholder={ph[k]} className="w-full rounded-lg border bg-transparent px-3 py-2.5 text-sm text-white placeholder:text-white/35 focus:outline-none" style={{ borderColor: `${ac}40` }} data-testid={`exchange-${k}`} />
            ))}
            <textarea value={f.message} onChange={(e) => setF((s) => ({ ...s, message: e.target.value }))} placeholder={t("exchange.messageOptional")} rows={2} className="w-full rounded-lg border bg-transparent px-3 py-2.5 text-sm text-white placeholder:text-white/35 focus:outline-none" style={{ borderColor: `${ac}40` }} data-testid="exchange-message" />
            <button onClick={submit} disabled={saving} className="w-full rounded-full py-3 text-sm font-medium text-black" style={{ background: ac }} data-testid="exchange-submit">
              {saving ? <Loader2 className="mx-auto h-4 w-4 animate-spin" /> : t("exchange.cta")}
            </button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
