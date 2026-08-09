import { ImageUploadField } from "@/components/admin/ImageUploadField";
import { ACCENT_OPTIONS, accentHex } from "@/lib/accents";
import { INDUSTRIES, industryById, patternLayer } from "@/lib/industries";
import { Building2, Briefcase, TrendingUp, Cpu, HeartPulse, Scale, GraduationCap, Hotel, Car, Flower2, LineChart, Plus, Check } from "lucide-react";

const ICONS = { Building2, Briefcase, TrendingUp, Cpu, HeartPulse, Scale, GraduationCap, Hotel, Car, Flower2, LineChart, Plus };
const INTENSITIES = ["soft", "medium", "rich"];
const POSITIONS = ["left", "center", "right", "full"];

const Section = ({ title, children }) => (
  <div className="space-y-3">
    <p className="text-[11px] font-medium uppercase tracking-[0.15em] text-[#C9A24B]">{title}</p>
    {children}
  </div>
);

export default function IndustryCustomizer({ form, set }) {
  const ind = industryById(form.industry);
  const ac = accentHex(form.templateId, form.accent, form.custom_accent_color);

  const pickIndustry = (id) => {
    const it = industryById(id);
    set("industry", id);
    set("background_style", it?.styles[0]?.id || "");
    set("background_opacity", it?.defaultOpacity ?? 0.14);
  };

  const opacityPct = Math.round((form.background_opacity ?? 0.14) * 100);

  const styleThumbStyle = (style) => {
    if (style.type === "custom") return { background: "repeating-linear-gradient(45deg,#1a1a1a,#1a1a1a 6px,#222 6px,#222 12px)" };
    if (style.type === "pattern") {
      const p = patternLayer(style.pattern, ac);
      return { backgroundColor: "#0c0d10", backgroundImage: p.css, backgroundSize: p.size, backgroundRepeat: p.repeat };
    }
    return { backgroundImage: `url("${ind?.image}")`, backgroundSize: "cover", backgroundPosition: "center" };
  };

  return (
    <div className="rounded-2xl border border-white/10 bg-[#0a0b0d] p-5 text-neutral-200" data-testid="industry-customizer">
      <h3 className="mb-1 text-[15px] font-semibold text-white">Industry Personalization</h3>
      <p className="mb-5 text-[12px] text-neutral-500">Choose your industry, brand color and visual atmosphere. The preview updates live.</p>

      <div className="space-y-6">
        {/* INDUSTRY */}
        <Section title="Industry">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {INDUSTRIES.map((it) => {
              const Icon = ICONS[it.icon] || Building2;
              const active = form.industry === it.id;
              return (
                <button key={it.id} type="button" onClick={() => pickIndustry(it.id)}
                  className={`group relative flex flex-col items-start gap-2 overflow-hidden rounded-xl border p-3 text-left transition-all duration-200 hover:-translate-y-0.5 ${active ? "border-[#C9A24B] bg-[#C9A24B]/10 shadow-[0_0_20px_rgba(201,162,75,0.2)]" : "border-white/10 bg-[#111214] hover:border-white/25"}`}
                  data-testid={`industry-${it.id}`}>
                  <span className="flex h-8 w-8 items-center justify-center rounded-lg border border-white/10 bg-black/40">
                    <Icon className="h-4 w-4" style={{ color: active ? "#E7C56B" : "#9aa0a8" }} strokeWidth={1.6} />
                  </span>
                  <span className="text-[12px] font-medium leading-tight text-white">{it.name}</span>
                  {active && <Check className="absolute right-2 top-2 h-3.5 w-3.5 text-[#E7C56B]" />}
                </button>
              );
            })}
          </div>
        </Section>

        {/* ACCENT */}
        <Section title="Accent Color">
          <div className="flex flex-wrap items-center gap-2.5">
            {ACCENT_OPTIONS.map((a) => (
              <button key={a.id} type="button" title={a.label}
                onClick={() => set("accent", a.id)}
                className={`h-8 w-8 rounded-full border transition-transform hover:scale-110 ${form.accent === a.id ? "ring-2 ring-white/70 ring-offset-2 ring-offset-[#0a0b0d]" : "border-white/20"}`}
                style={{ backgroundColor: a.hex }} data-testid={`accent-${a.id}`} />
            ))}
            <label className={`flex h-8 items-center gap-2 rounded-full border px-3 text-[11px] ${form.accent === "custom" ? "border-white/70 text-white" : "border-white/20 text-neutral-400"}`}>
              <input type="color" value={form.custom_accent_color || "#C9A24B"}
                onChange={(e) => { set("custom_accent_color", e.target.value); set("accent", "custom"); }}
                className="h-5 w-5 cursor-pointer rounded border-0 bg-transparent p-0" data-testid="accent-custom" />
              Custom
            </label>
          </div>
        </Section>

        {/* BACKGROUND STYLE */}
        {ind && ind.id !== "custom" && (
          <Section title="Background Style">
            <div className="flex gap-2.5 overflow-x-auto pb-1">
              {ind.styles.map((st) => {
                const active = (form.background_style || ind.styles[0].id) === st.id;
                return (
                  <button key={st.id} type="button" onClick={() => set("background_style", st.id)}
                    className={`shrink-0 overflow-hidden rounded-xl border p-1 transition-all hover:-translate-y-0.5 ${active ? "border-[#C9A24B] shadow-[0_0_16px_rgba(201,162,75,0.25)]" : "border-white/10"}`}
                    data-testid={`bgstyle-${st.id}`}>
                    <div className="h-14 w-24 rounded-lg" style={styleThumbStyle(st)} />
                    <span className="mt-1 block px-1 text-center text-[10px] text-neutral-400">{st.label}</span>
                  </button>
                );
              })}
            </div>
          </Section>
        )}

        {/* CUSTOM BACKGROUND */}
        <Section title={ind?.id === "custom" ? "Custom Background" : "Custom Background (optional)"}>
          <div className="rounded-xl border border-white/10 bg-[#111214] p-3">
            <ImageUploadField label="" value={form.custom_background} onChange={(v) => set("custom_background", v)} testId="upload-custom-bg" />
            {form.custom_background && (
              <button type="button" onClick={() => set("custom_background", "")} className="mt-2 text-[11px] text-neutral-500 hover:text-white" data-testid="clear-custom-bg">Remove custom image</button>
            )}
          </div>
        </Section>

        {/* OPACITY */}
        <Section title="Background Opacity">
          <div className="flex items-center gap-3">
            <input type="range" min="0" max="30" value={opacityPct}
              onChange={(e) => set("background_opacity", Number(e.target.value) / 100)}
              className="h-1.5 w-full cursor-pointer appearance-none rounded-full bg-white/15 accent-[#C9A24B]" data-testid="bg-opacity" />
            <span className="w-10 text-right text-[13px] font-semibold text-[#E7C56B]" data-testid="bg-opacity-value">{opacityPct}%</span>
          </div>
        </Section>

        {/* INTENSITY */}
        <Section title="Background Intensity">
          <div className="grid grid-cols-3 gap-2">
            {INTENSITIES.map((v) => (
              <button key={v} type="button" onClick={() => set("background_intensity", v)}
                className={`rounded-lg border py-2 text-[12px] capitalize transition-colors ${form.background_intensity === v ? "border-[#C9A24B] bg-[#C9A24B]/12 text-white" : "border-white/10 text-neutral-400 hover:border-white/25"}`}
                data-testid={`intensity-${v}`}>{v}</button>
            ))}
          </div>
        </Section>

        {/* POSITION */}
        <Section title="Background Position">
          <div className="grid grid-cols-4 gap-2">
            {POSITIONS.map((v) => (
              <button key={v} type="button" onClick={() => set("background_position", v)}
                className={`rounded-lg border py-2 text-[12px] capitalize transition-colors ${(form.background_position || "center") === v ? "border-[#C9A24B] bg-[#C9A24B]/12 text-white" : "border-white/10 text-neutral-400 hover:border-white/25"}`}
                data-testid={`position-${v}`}>{v}</button>
            ))}
          </div>
        </Section>
      </div>
    </div>
  );
}
