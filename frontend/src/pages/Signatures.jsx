import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { useLocale } from "@/i18n/useLocale";
import { OwnerNav } from "@/components/admin/OwnerNav";
import { buildSignatureHtml } from "@/lib/signature";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Mail, Copy, Code, Lock, Loader2 } from "lucide-react";
import { toast } from "sonner";

const BACKEND = process.env.REACT_APP_BACKEND_URL;
const FIELDS = [
  { key: "photo", tkey: "signatures.photo", brand: "logo" },
  { key: "qr", tkey: "signatures.qr" },
  { key: "title", tkey: "signatures.titleField" },
  { key: "company", tkey: "signatures.company", brand: "company" },
  { key: "phone", tkey: "signatures.phone" },
  { key: "email", tkey: "signatures.email" },
  { key: "link", tkey: "signatures.link" },
];

export default function Signatures() {
  const { t } = useLocale();
  const [cards, setCards] = useState(undefined);
  const [locked, setLocked] = useState([]);
  const [sel, setSel] = useState("");
  const [opts, setOpts] = useState({ photo: true, qr: true, title: true, company: true, phone: true, email: true, link: true, template: "classic" });

  useEffect(() => {
    api.get("/admin/cards").then(({ data }) => { setCards(data); if (data[0]) setSel(data[0].id); }).catch(() => setCards([]));
    api.get("/workspaces/me").then(({ data }) => setLocked((data?.[0]?.locked_fields) || [])).catch(() => {});
  }, []);

  const card = useMemo(() => (cards || []).find((c) => c.id === sel), [cards, sel]);
  const urls = useMemo(() => card ? {
    profile: `${window.location.origin}/${card.slug}`,
    qr: `${BACKEND}/api/cards/${card.slug}/qr`,
    photo: card.identity?.profilePhoto || "",
  } : {}, [card]);

  const html = useMemo(() => card ? buildSignatureHtml(card, { ...opts, accent: card.accent }, urls) : "", [card, opts, urls]);

  const isLocked = (f) => f.brand && locked.includes(f.brand);
  const toggle = (f) => { if (isLocked(f)) return; setOpts((o) => ({ ...o, [f.key]: !o[f.key] })); };

  const copyHtml = async () => { try { await navigator.clipboard.writeText(html); toast.success(t("signatures.copied")); } catch { toast.error("Copy failed"); } };
  const copyRich = async () => {
    try {
      const blob = new Blob([html], { type: "text/html" });
      const plain = new Blob([html.replace(/<[^>]+>/g, "")], { type: "text/plain" });
      await navigator.clipboard.write([new window.ClipboardItem({ "text/html": blob, "text/plain": plain })]);
      toast.success(t("signatures.copied"));
    } catch { copyHtml(); }
  };

  return (
    <div className="aria-dark relative min-h-screen bg-[#050607] text-white" style={{ fontFamily: "'Outfit', sans-serif" }} data-testid="signatures-page">
      <div className="grain-overlay" style={{ opacity: 0.04 }} />
      <OwnerNav active="signatures" />
      <main className="relative mx-auto max-w-5xl px-4 py-8 sm:px-8">
        <h2 className="flex items-center gap-2 text-2xl font-light tracking-tight text-white"><Mail className="h-5 w-5 text-[#D6A653]" /> {t("signatures.title")}</h2>
        <p className="mt-1 text-sm text-white/45">{t("signatures.subtitle")}</p>

        {cards === undefined ? (
          <div className="flex justify-center py-24"><Loader2 className="h-6 w-6 animate-spin text-[#D6A653]" /></div>
        ) : !cards.length ? (
          <div className="mt-8 rounded-2xl border border-dashed border-white/12 py-24 text-center text-white/55" data-testid="signatures-empty">{t("signatures.noCards")}</div>
        ) : (
          <div className="mt-6 grid gap-5 lg:grid-cols-2">
            {/* Controls */}
            <div className="space-y-4">
              <div className="rounded-2xl border border-white/10 bg-[#0A0B0D] p-4">
                <label className="mb-1 block text-[11px] uppercase tracking-wide text-white/40">{t("signatures.card")}</label>
                <Select value={sel} onValueChange={setSel}>
                  <SelectTrigger className="border-white/12 bg-white/[0.03] text-sm text-white" data-testid="sig-card-select"><SelectValue /></SelectTrigger>
                  <SelectContent className="aria-pop border-white/10 bg-[#0A0B0D] text-white">{cards.map((c) => <SelectItem key={c.id} value={c.id}>{c.identity?.fullName || c.slug}</SelectItem>)}</SelectContent>
                </Select>

                <label className="mb-1 mt-4 block text-[11px] uppercase tracking-wide text-white/40">{t("signatures.template")}</label>
                <div className="grid grid-cols-3 gap-2" data-testid="sig-templates">
                  {["classic", "compact", "modern"].map((tpl) => (
                    <button key={tpl} onClick={() => setOpts((o) => ({ ...o, template: tpl }))} data-testid={`sig-template-${tpl}`}
                      className={`rounded-lg border px-2 py-2 text-xs capitalize transition-colors ${opts.template === tpl ? "border-[#D6A653] bg-[#D6A653]/10 text-[#D6A653]" : "border-white/12 text-white/60 hover:text-white"}`}>
                      {t(`signatures.${tpl}`)}
                    </button>
                  ))}
                </div>

                <label className="mb-2 mt-4 block text-[11px] uppercase tracking-wide text-white/40">{t("signatures.fields")}</label>
                <div className="grid grid-cols-2 gap-2" data-testid="sig-fields">
                  {FIELDS.map((f) => {
                    const lockedField = isLocked(f);
                    return (
                      <button key={f.key} onClick={() => toggle(f)} disabled={lockedField} data-testid={`sig-field-${f.key}`}
                        className={`flex items-center justify-between rounded-lg border px-3 py-2 text-xs transition-colors ${opts[f.key] ? "border-[#D6A653]/40 bg-[#D6A653]/[0.06] text-white" : "border-white/10 text-white/50"} ${lockedField ? "opacity-60" : "hover:border-white/20"}`}>
                        <span>{t(f.tkey)}</span>
                        {lockedField ? <Lock className="h-3 w-3 text-[#D6A653]" title={t("signatures.locked")} /> : <span className={`h-3 w-3 rounded-full ${opts[f.key] ? "bg-[#D6A653]" : "border border-white/25"}`} />}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="flex gap-2">
                <button onClick={copyRich} data-testid="sig-copy-rich" className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-[#D6A653] py-2.5 text-sm font-medium text-[#050607] hover:bg-[#E8B764]"><Copy className="h-4 w-4" /> {t("signatures.copyRich")}</button>
                <button onClick={copyHtml} data-testid="sig-copy-html" className="flex items-center justify-center gap-2 rounded-lg border border-white/12 px-4 py-2.5 text-sm text-white/70 hover:text-white"><Code className="h-4 w-4" /> {t("signatures.copyHtml")}</button>
              </div>
            </div>

            {/* Preview */}
            <div>
              <p className="mb-2 text-[11px] uppercase tracking-wide text-white/40">{t("signatures.preview")}</p>
              <div className="rounded-2xl border border-white/10 bg-white p-6" data-testid="sig-preview">
                <div dangerouslySetInnerHTML={{ __html: html }} />
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
