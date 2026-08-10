import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useLocale } from "@/i18n/useLocale";
import { OwnerNav } from "@/components/admin/OwnerNav";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Nfc, Loader2, ArrowLeft, ExternalLink, CheckCircle2, Ban } from "lucide-react";
import { toast } from "sonner";

const STATUS_STYLE = {
  ACTIVE: "text-emerald-300 border-emerald-400/40 bg-emerald-400/10",
  UNASSIGNED: "text-[#D4AF37] border-[#D4AF37]/40 bg-[#D4AF37]/10",
  DEACTIVATED: "text-white/50 border-white/20 bg-white/5",
  LOST: "text-red-300 border-red-400/40 bg-red-400/10",
  REPLACED: "text-white/50 border-white/20 bg-white/5",
};

export default function NfcCards() {
  const navigate = useNavigate();
  const { t } = useLocale();
  const [devices, setDevices] = useState(null);
  const [cards, setCards] = useState([]);
  const [busy, setBusy] = useState("");

  const load = () => {
    api.get("/nfc/devices").then(({ data }) => setDevices(data)).catch(() => setDevices([]));
    api.get("/admin/cards").then(({ data }) => setCards(data)).catch(() => {});
  };
  useEffect(() => { load(); }, []);

  const cardById = useMemo(() => Object.fromEntries(cards.map((c) => [c.id, c])), [cards]);

  const setDestination = async (dev, cardId) => {
    if (!cardId || cardId === dev.card_id) return;
    setBusy(dev.token);
    try {
      await api.post("/nfc/activate", { token: dev.token, card_id: cardId });
      toast.success(t("nfc.destinationUpdated"));
      setDevices((ds) => ds.map((d) => d.token === dev.token ? { ...d, card_id: cardId, status: "ACTIVE" } : d));
    } catch (e) {
      toast.error(e.response?.data?.detail || t("nfc.updateFailed"));
    } finally { setBusy(""); }
  };

  const setStatus = async (dev, status) => {
    setBusy(dev.token);
    try {
      await api.post(`/nfc/devices/${dev.token}/status`, { status });
      toast.success(t("nfc.statusUpdated"));
      setDevices((ds) => ds.map((d) => d.token === dev.token ? { ...d, status, card_id: ["DEACTIVATED", "LOST", "UNASSIGNED"].includes(status) ? null : d.card_id } : d));
    } catch (e) {
      toast.error(e.response?.data?.detail || t("nfc.updateFailed"));
    } finally { setBusy(""); }
  };

  return (
    <div className="aria-dark relative min-h-screen bg-[#0B0D12] text-white" style={{ fontFamily: "'Outfit', sans-serif" }} data-testid="nfc-page">
      <div className="grain-overlay" style={{ opacity: 0.04 }} />
      <OwnerNav active="" />

      <main className="relative mx-auto max-w-3xl px-4 py-8 sm:px-8">
        <div className="mb-4 flex items-center gap-3">
          <button onClick={() => navigate("/settings")} className="text-white/50 hover:text-white" data-testid="nfc-back"><ArrowLeft className="h-5 w-5" /></button>
          <div>
            <h2 className="flex items-center gap-2 text-2xl font-light tracking-tight text-white"><Nfc className="h-6 w-6 text-[#D4AF37]" /> {t("nfc.title")}</h2>
            <p className="text-sm text-white/45">{t("nfc.subtitle")}</p>
          </div>
        </div>

        {devices === null ? (
          <div className="flex justify-center py-20"><Loader2 className="h-6 w-6 animate-spin text-[#D4AF37]" /></div>
        ) : devices.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-white/12 py-16 text-center" data-testid="nfc-empty">
            <Nfc className="mx-auto mb-3 h-10 w-10 text-white/25" />
            <p className="text-white/60">{t("nfc.emptyTitle")}</p>
            <p className="mx-auto mt-1 max-w-sm text-sm text-white/40">{t("nfc.emptyDesc")}</p>
          </div>
        ) : (
          <div className="space-y-3" data-testid="nfc-devices">
            {devices.map((dev) => {
              const dest = dev.card_id ? cardById[dev.card_id] : null;
              const disabled = ["DEACTIVATED", "LOST"].includes(dev.status);
              return (
                <div key={dev.token} className="rounded-2xl border border-white/10 bg-[#11121A] p-5" data-testid={`nfc-device-${dev.token}`}>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-white">{dev.serial || dev.token}</span>
                      <span className={`rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-wider ${STATUS_STYLE[dev.status] || STATUS_STYLE.REPLACED}`} data-testid={`nfc-status-${dev.token}`}>{t(`nfc.st_${dev.status}`, { defaultValue: dev.status })}</span>
                    </div>
                    {dest ? (
                      <a href={`/${dest.slug}?src=nfc`} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-xs text-[#D4AF37] hover:underline" data-testid={`nfc-view-${dev.token}`}><ExternalLink className="h-3 w-3" /> /{dest.slug}</a>
                    ) : null}
                  </div>

                  <div className="mt-4">
                    <label className="text-xs text-white/45">{t("nfc.destinationCard")}</label>
                    <div className="mt-1.5 flex items-center gap-2">
                      <Select value={dev.card_id || ""} onValueChange={(v) => setDestination(dev, v)} disabled={disabled || busy === dev.token}>
                        <SelectTrigger className="h-10 flex-1 text-sm" data-testid={`nfc-select-${dev.token}`}><SelectValue placeholder={t("nfc.chooseCard")} /></SelectTrigger>
                        <SelectContent className="aria-pop">
                          {cards.map((c) => <SelectItem key={c.id} value={c.id}>{c.identity?.fullName || c.slug} · /{c.slug}</SelectItem>)}
                        </SelectContent>
                      </Select>
                      {busy === dev.token ? <Loader2 className="h-4 w-4 animate-spin text-[#D4AF37]" /> : null}
                    </div>
                    <p className="mt-1.5 text-[11px] text-white/35">{t("nfc.routeHint")}</p>
                  </div>

                  <div className="mt-3 flex flex-wrap gap-2 border-t border-white/8 pt-3">
                    {disabled ? (
                      <button onClick={() => setStatus(dev, "UNASSIGNED")} disabled={busy === dev.token} className="flex items-center gap-1.5 rounded-lg border border-emerald-400/30 bg-emerald-500/10 px-3 py-1.5 text-xs text-emerald-300 hover:bg-emerald-500/20 disabled:opacity-60" data-testid={`nfc-reactivate-${dev.token}`}><CheckCircle2 className="h-3.5 w-3.5" /> {t("nfc.reactivate")}</button>
                    ) : (
                      <button onClick={() => setStatus(dev, "LOST")} disabled={busy === dev.token} className="flex items-center gap-1.5 rounded-lg border border-red-400/30 bg-red-500/10 px-3 py-1.5 text-xs text-red-300 hover:bg-red-500/20 disabled:opacity-60" data-testid={`nfc-lost-${dev.token}`}><Ban className="h-3.5 w-3.5" /> {t("nfc.markLost")}</button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}
