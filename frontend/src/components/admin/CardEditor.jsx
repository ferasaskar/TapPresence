import { useState } from "react";
import { api } from "@/lib/api";
import { TemplateRenderer } from "@/components/templates/TemplateRenderer";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { ACCENT_OPTIONS } from "@/lib/accents";
import CardInfoTabs, { mergeCard } from "@/components/admin/CardInfoTabs";
import { Loader2, ArrowLeft, ExternalLink } from "lucide-react";
import { toast } from "sonner";
import { useLocale } from "@/i18n/useLocale";

const Field = ({ label, children }) => (
  <div className="space-y-1.5">
    <Label className="text-xs text-white/55">{label}</Label>
    {children}
  </div>
);

export default function CardEditor({ initial, onBack, onSaved }) {
  const { t } = useLocale();
  const [form, setForm] = useState(() => mergeCard(initial));
  const [saving, setSaving] = useState(false);
  const isNew = !initial?.id;

  const set = (path, value) => {
    setForm((f) => {
      const next = { ...f };
      if (path.includes(".")) { const [g, k] = path.split("."); next[g] = { ...next[g], [k]: value }; }
      else next[path] = value;
      return next;
    });
  };

  const save = async () => {
    if (!form.slug.trim()) { toast.error(t("createCard.ed_slugRequired")); return; }
    setSaving(true);
    try {
      const payload = { ...form, slug: form.slug.trim().toLowerCase().replace(/\s+/g, "-") };
      if (isNew) await api.post("/admin/cards", payload);
      else await api.put(`/admin/cards/${initial.id}`, payload);
      toast.success(t("createCard.ed_cardSaved"));
      onSaved();
    } catch (err) {
      toast.error(err.response?.data?.detail || t("createCard.ed_saveFailed"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="grid grid-cols-1 gap-8 lg:grid-cols-[1fr_400px]">
      {/* FORM */}
      <div>
        <div className="mb-6 flex items-center justify-between">
          <button onClick={onBack} className="flex items-center gap-2 text-sm text-white/55 transition-colors hover:text-white" data-testid="editor-back">
            <ArrowLeft className="h-4 w-4" /> {t("createCard.ed_back")}
          </button>
          <div className="flex items-center gap-4">
            {form.status === "published" && form.slug ? (
              <a href={`/${form.slug}`} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-sm text-white/55 transition-colors hover:text-white" data-testid="editor-view-live">
                {t("createCard.ed_viewLive")} <ExternalLink className="h-3.5 w-3.5" />
              </a>
            ) : null}
            <Button onClick={save} disabled={saving} className="rounded-full bg-[#D6A653] font-medium text-[#050607] transition-all hover:bg-[#E8B764] hover:shadow-[0_0_18px_rgba(214,166,83,0.35)] active:scale-95" data-testid="admin-save-button">
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : t("createCard.ed_saveCard")}
            </Button>
          </div>
        </div>

        <div className="mb-6 grid grid-cols-2 gap-4 rounded-xl border border-white/10 bg-white/[0.02] p-4 lg:grid-cols-3">
          <Field label={t("createCard.ed_slug")}>
            <Input value={form.slug} onChange={(e) => set("slug", e.target.value)} placeholder="feras-askar" data-testid="editor-slug" />
          </Field>
          <Field label={t("createCard.ed_accent")}>
            <Select value={form.accent} onValueChange={(v) => set("accent", v)}>
              <SelectTrigger data-testid="editor-accent"><SelectValue /></SelectTrigger>
              <SelectContent className="aria-pop">
                {ACCENT_OPTIONS.map((a) => <SelectItem key={a.id} value={a.id}>{a.label}</SelectItem>)}
              </SelectContent>
            </Select>
          </Field>
          <div className="flex items-center gap-3 pt-6">
            <Switch checked={form.status === "published"} onCheckedChange={(v) => set("status", v ? "published" : "draft")} data-testid="editor-published" />
            <span className="text-sm text-white/75">{form.status === "published" ? t("createCard.ed_published") : t("createCard.ed_draft")}</span>
          </div>
        </div>

        <CardInfoTabs form={form} setForm={setForm} cardId={initial?.id} />
      </div>

      {/* LIVE PREVIEW */}
      <div className="h-fit lg:sticky lg:top-6">
        <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#D6A653]">{t("createCard.ed_livePreview")}</p>
        <div className="mx-auto w-full max-w-[360px] overflow-hidden rounded-[2.2rem] border-[6px] border-[#141518] bg-[#050607] shadow-[0_30px_80px_rgba(0,0,0,0.6)] ring-1 ring-white/10">
          <div className="overflow-y-auto" style={{ height: "76vh" }} data-testid="editor-preview">
            <TemplateRenderer data={form} />
          </div>
        </div>
      </div>
    </div>
  );
}
