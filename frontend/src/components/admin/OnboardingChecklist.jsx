import { useMemo } from "react";
import { CheckCircle2, Circle, Rocket } from "lucide-react";

// Activation checklist for the core journey: Create → Personalize → Publish → Share → First lead.
// Pure presentation over data the owner already has access to. Hidden once complete.
export const OnboardingChecklist = ({ primary, overview, newLeads, onNavigate }) => {
  const steps = useMemo(() => {
    const views = overview?.funnel?.views || 0;
    const leads = (overview?.funnel?.leads || 0) + (overview?.totals?.leads_all_time || 0) + (newLeads || 0);
    return [
      { key: "create", label: "Create your card", done: !!primary, go: () => onNavigate("/templates") },
      { key: "photo", label: "Add your profile photo", done: !!primary?.identity?.profilePhoto, go: () => onNavigate("/admin") },
      { key: "publish", label: "Publish your card", done: primary?.status === "published", go: () => onNavigate("/admin") },
      { key: "share", label: "Share it & get your first view", done: views > 0, go: () => primary && window.open(`/${primary.slug}`, "_blank") },
      { key: "lead", label: "Capture your first lead", done: leads > 0, go: () => onNavigate("/leads") },
    ];
  }, [primary, overview, newLeads, onNavigate]);

  const doneCount = steps.filter((s) => s.done).length;
  if (doneCount === steps.length) return null;
  const pct = Math.round((doneCount / steps.length) * 100);

  return (
    <div className="rounded-2xl border border-[#D6A653]/25 bg-gradient-to-br from-[#D6A653]/[0.07] to-transparent p-5" data-testid="onboarding-checklist">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="flex items-center gap-2 text-sm font-medium text-white"><Rocket className="h-4 w-4 text-[#D6A653]" /> Get set up</h3>
        <span className="text-[11px] uppercase tracking-wide text-white/45" data-testid="onboarding-progress">{doneCount}/{steps.length} done</span>
      </div>
      <div className="mb-4 h-1.5 overflow-hidden rounded-full bg-white/[0.06]">
        <div className="h-full rounded-full transition-all duration-500" style={{ width: `${pct}%`, background: "linear-gradient(90deg,#8A6A2B,#D6A653,#E8B764)" }} />
      </div>
      <ul className="space-y-1.5">
        {steps.map((s) => (
          <li key={s.key}>
            <button
              onClick={s.done ? undefined : s.go}
              disabled={s.done}
              data-testid={`onboarding-step-${s.key}`}
              className={`flex w-full items-center gap-2.5 rounded-lg px-2 py-2 text-left text-sm transition-colors ${s.done ? "text-white/45" : "text-white/85 hover:bg-white/[0.04]"}`}
            >
              {s.done
                ? <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
                : <Circle className="h-4 w-4 shrink-0 text-[#D6A653]" />}
              <span className={s.done ? "line-through decoration-white/25" : ""}>{s.label}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
};
