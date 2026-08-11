import { useLocale } from "@/i18n/useLocale";
import { CalendarRange } from "lucide-react";

// One reusable period filter: Today | This Week | This Month | Custom.
// Emits { preset, start, end } (ISO). Consumers pass start/end to their APIs.
export const buildRange = (preset) => {
  const now = new Date();
  let start;
  const end = now;
  if (preset === "today") {
    start = new Date(now); start.setHours(0, 0, 0, 0);
  } else if (preset === "week") {
    start = new Date(now);
    const dow = (start.getDay() + 6) % 7; // Monday = 0
    start.setDate(start.getDate() - dow); start.setHours(0, 0, 0, 0);
  } else { // month
    start = new Date(now.getFullYear(), now.getMonth(), 1);
  }
  return { preset, start: start.toISOString(), end: end.toISOString() };
};

const toDayInput = (iso) => {
  try { const d = new Date(iso); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`; }
  catch { return ""; }
};

export const DateFilter = ({ value, onChange, testId = "date-filter", allowAll = false }) => {
  const { t } = useLocale();
  const preset = value?.preset || (allowAll ? "all" : "month");
  const presets = [
    ...(allowAll ? [["all", "dateFilter.all"]] : []),
    ["today", "dateFilter.today"], ["week", "dateFilter.week"], ["month", "dateFilter.month"], ["custom", "dateFilter.custom"],
  ];

  const pick = (p) => {
    if (p === "all") {
      onChange({ preset: "all", start: null, end: null });
    } else if (p === "custom") {
      onChange({ preset: "custom", start: value?.start || buildRange("month").start, end: value?.end || new Date().toISOString() });
    } else {
      onChange(buildRange(p));
    }
  };
  const setCustom = (which, v) => {
    if (!v) return;
    const iso = new Date(`${v}T${which === "end" ? "23:59:59" : "00:00:00"}`).toISOString();
    onChange({ preset: "custom", start: which === "start" ? iso : value.start, end: which === "end" ? iso : value.end });
  };

  return (
    <div className="flex flex-wrap items-center gap-2" data-testid={testId}>
      <div className="flex rounded-lg border border-white/10 p-0.5">
        {presets.map(([p, tk]) => (
          <button key={p} onClick={() => pick(p)} data-testid={`${testId}-${p}`}
            className={`rounded-md px-2.5 py-1 text-[11px] transition-colors ${preset === p ? "bg-[#D6A653] font-semibold text-[#050607]" : "text-white/55 hover:text-white"}`}>
            {t(tk)}
          </button>
        ))}
      </div>
      {preset === "custom" ? (
        <div className="flex items-center gap-1.5" data-testid={`${testId}-custom`}>
          <CalendarRange className="h-3.5 w-3.5 text-[#D6A653]" />
          <input type="date" value={toDayInput(value?.start)} onChange={(e) => setCustom("start", e.target.value)} data-testid={`${testId}-start`}
            className="rounded-md border border-white/12 bg-white/[0.03] px-2 py-1 text-[11px] text-white" />
          <span className="text-white/40">–</span>
          <input type="date" value={toDayInput(value?.end)} onChange={(e) => setCustom("end", e.target.value)} data-testid={`${testId}-end`}
            className="rounded-md border border-white/12 bg-white/[0.03] px-2 py-1 text-[11px] text-white" />
        </div>
      ) : null}
    </div>
  );
};
