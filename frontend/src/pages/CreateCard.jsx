import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { TemplateRenderer } from "@/components/templates/TemplateRenderer";
import { IndustryCard } from "@/components/landing/IndustryCard";
import { INDUSTRY_CARDS } from "@/lib/industryCards";
import { industryById } from "@/lib/industries";
import IndustryCustomizer from "@/components/admin/IndustryCustomizer";
import CardInfoTabs, { emptyCard } from "@/components/admin/CardInfoTabs";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { ArrowLeft, ArrowRight, Loader2, Check } from "lucide-react";
import { toast } from "sonner";

const AriadniMark = ({ className = "" }) => (
  <svg viewBox="0 0 24 24" className={className} fill="none" aria-hidden>
    <path d="M12 3 L21 20 L15.6 20 L12 12 L8.4 20 L3 20 Z" fill="currentColor" />
  </svg>
);

const STEPS = [
  { n: 1, label: "Choose Your Industry" },
  { n: 2, label: "Customize Your Style" },
  { n: 3, label: "Your Information" },
];

export default function CreateCard() {
  const navigate = useNavigate();
  const [form, setForm] = useState(() => ({ ...emptyCard }));
  const [step, setStep] = useState(1);
  const [saving, setSaving] = useState(false);

  const set = (path, value) => {
    setForm((f) => {
      const next = { ...f };
      if (path.includes(".")) { const [g, k] = path.split("."); next[g] = { ...next[g], [k]: value }; }
      else next[path] = value;
      return next;
    });
  };

  const pickIndustry = (id) => {
    const card = INDUSTRY_CARDS.find((c) => c.id === id);
    const ind = industryById(id);
    setForm((f) => ({
      ...f,
      industry: id,
      accent: card?.accentId || "gold",
      custom_accent_color: "",
      background_style: ind?.styles?.[0]?.id || "",
      background_opacity: ind?.defaultOpacity ?? 0.14,
    }));
    setStep(2);
  };

  const save = async (publish) => {
    const name = form.identity.fullName?.trim();
    if (!name) { toast.error("Add your full name first"); setStep(3); return; }
    const slug = (form.slug.trim() || name).toLowerCase().replace(/[^a-z0-9\s-]/g, "").replace(/\s+/g, "-");
    setSaving(true);
    try {
      await api.post("/admin/cards", { ...form, slug, status: publish ? "published" : "draft" });
      toast.success(publish ? "Card published" : "Draft saved");
      navigate("/admin");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not save card");
    } finally { setSaving(false); }
  };

  const industryChosen = !!form.industry;

  return (
    <div className="aria-dark relative min-h-screen bg-[#050607] text-white" style={{ fontFamily: "'Outfit', sans-serif" }} data-testid="create-card-studio">
      <div className="grain-overlay" style={{ opacity: 0.04 }} />

      {/* header */}
      <header className="sticky top-0 z-40 border-b border-white/8 bg-[#050607]/85 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-2 px-4 py-4 sm:px-8">
          <button onClick={() => navigate("/admin")} className="flex items-center gap-2 text-sm text-white/60 transition-colors hover:text-white" data-testid="create-back">
            <ArrowLeft className="h-4 w-4" /> <span className="hidden sm:inline">Card Manager</span>
          </button>
          <div className="hidden items-center gap-2.5 md:flex">
            <AriadniMark className="h-5 w-5 text-[#D6A653]" />
            <span className="text-[15px] font-medium">Create Your Card</span>
          </div>
          <div className="flex items-center gap-2">
            <Button onClick={() => save(false)} disabled={saving || !industryChosen} className="rounded-full border border-white/15 bg-transparent px-3 text-white hover:bg-white/5 sm:px-4" data-testid="save-draft-button">
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : "Save Draft"}
            </Button>
            <Button onClick={() => save(true)} disabled={saving || !industryChosen} className="rounded-full bg-[#D6A653] px-3 font-medium text-[#050607] transition-all hover:bg-[#E8B764] hover:shadow-[0_0_18px_rgba(214,166,83,0.35)] active:scale-95 sm:px-4" data-testid="publish-button">
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : "Publish Card"}
            </Button>
          </div>
        </div>
      </header>

      <main className="relative mx-auto max-w-7xl px-4 pb-20 pt-8 sm:px-8">
        {/* stepper */}
        <div className="mb-8 flex flex-wrap items-center gap-2">
          {STEPS.map((s, i) => {
            const active = step === s.n;
            const done = step > s.n;
            const disabled = s.n > 1 && !industryChosen;
            return (
              <button key={s.n} onClick={() => !disabled && setStep(s.n)} disabled={disabled}
                className={`flex items-center gap-2 rounded-full border px-4 py-2 text-sm transition-all ${active ? "border-[#D6A653] bg-[#D6A653]/12 text-white" : done ? "border-[#D6A653]/30 text-[#D6A653]" : "border-white/12 text-white/45"} ${disabled ? "cursor-not-allowed opacity-40" : "hover:border-white/30"}`}
                data-testid={`step-${s.n}`}>
                <span className={`flex h-5 w-5 items-center justify-center rounded-full text-[11px] ${active || done ? "bg-[#D6A653] text-[#050607]" : "bg-white/10 text-white/60"}`}>{done ? <Check className="h-3 w-3" /> : s.n}</span>
                {s.label}
                {i < STEPS.length - 1 && <ArrowRight className="ml-1 hidden h-3.5 w-3.5 text-white/25 sm:block" />}
              </button>
            );
          })}
        </div>

        <div className="grid gap-8 lg:grid-cols-[1fr_400px]">
          {/* step content */}
          <div>
            {step === 1 && (
              <div>
                <h1 className="text-3xl font-light tracking-tight text-white">Create Your Card</h1>
                <p className="mt-2 text-white/55">Choose your industry and personalize your professional identity.</p>
                <p className="mt-8 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#D6A653]">Choose Your Industry</p>
                <div className="mt-5 grid grid-cols-1 gap-x-6 gap-y-10 sm:grid-cols-2 xl:grid-cols-3">
                  {INDUSTRY_CARDS.map((c) => (
                    <button key={c.id} onClick={() => pickIndustry(c.id)} className="group text-left focus:outline-none" data-testid={`choose-industry-${c.id}`}>
                      <div className={`rounded-[30px] transition-all ${form.industry === c.id ? "ring-2 ring-[#D6A653] ring-offset-4 ring-offset-[#050607]" : "opacity-90 group-hover:opacity-100 group-hover:-translate-y-1"}`}>
                        <IndustryCard c={c} />
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {step === 2 && (
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#D6A653]">Customize Your Style</p>
                <h2 className="mt-2 text-2xl font-light tracking-tight text-white">Make it yours</h2>
                <p className="mt-1 text-sm text-white/50">Adjust the accent, background and atmosphere — the preview updates instantly.</p>
                <div className="mt-6">
                  <IndustryCustomizer form={form} set={set} />
                </div>
                <div className="mt-6 flex items-center justify-between">
                  <Button onClick={() => setStep(1)} className="rounded-full border border-white/15 bg-transparent text-white hover:bg-white/5"><ArrowLeft className="mr-1 h-4 w-4" /> Industry</Button>
                  <Button onClick={() => setStep(3)} className="rounded-full bg-[#D6A653] font-medium text-[#050607] hover:bg-[#E8B764]" data-testid="to-information">Continue <ArrowRight className="ml-1 h-4 w-4" /></Button>
                </div>
              </div>
            )}

            {step === 3 && (
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#D6A653]">Your Information</p>
                <h2 className="mt-2 text-2xl font-light tracking-tight text-white">Fill in your details</h2>
                <div className="mt-5 mb-4 max-w-xs">
                  <Label className="text-xs text-white/55">Card link (slug)</Label>
                  <Input value={form.slug} onChange={(e) => set("slug", e.target.value)} placeholder="auto from your name" data-testid="editor-slug" />
                </div>
                <CardInfoTabs form={form} setForm={setForm} showIndustry={false} />
                <div className="mt-6 flex items-center justify-between">
                  <Button onClick={() => setStep(2)} className="rounded-full border border-white/15 bg-transparent text-white hover:bg-white/5"><ArrowLeft className="mr-1 h-4 w-4" /> Style</Button>
                  <Button onClick={() => save(true)} disabled={saving} className="rounded-full bg-[#D6A653] font-medium text-[#050607] hover:bg-[#E8B764]" data-testid="publish-button-bottom">
                    {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : "Preview & Publish"}
                  </Button>
                </div>
              </div>
            )}
          </div>

          {/* persistent live preview */}
          <div className="h-fit lg:sticky lg:top-24">
            <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#D6A653]">Live Preview</p>
            <div className="mx-auto w-full max-w-[360px] overflow-hidden rounded-[2.2rem] border-[6px] border-[#141518] bg-[#050607] shadow-[0_30px_80px_rgba(0,0,0,0.6)] ring-1 ring-white/10">
              <div className="overflow-y-auto" style={{ height: "72vh" }} data-testid="create-preview">
                <TemplateRenderer data={form} />
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
