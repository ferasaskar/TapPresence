import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useLocale } from "@/i18n/useLocale";
import { toast } from "sonner";
import { Sparkles, Loader2, RefreshCw, AlertTriangle, Clock } from "lucide-react";

const PRIORITY_STYLE = {
  High: "bg-red-500/15 text-red-300 border-red-400/40",
  Medium: "bg-amber-500/15 text-amber-300 border-amber-400/40",
  Low: "bg-emerald-500/15 text-emerald-300 border-emerald-400/40",
};

const LEAD_FIELDS = [
  ["summary", "Lead Summary"], ["opportunity_assessment", "Opportunity Assessment"],
  ["why_matters", "Why This Lead Matters"], ["recommended_next_action", "Recommended Next Action"],
  ["followup_approach", "Suggested Follow-up Approach"], ["signals_risks", "Important Signals / Risks"],
];
const RECAP_FIELDS = [
  ["executive_summary", "Executive Summary"], ["event_performance", "Event Performance"],
  ["lead_quality", "Lead Quality Summary"], ["strongest_opportunities", "Strongest Opportunities"],
  ["key_patterns", "Key Patterns / Trends"], ["team_highlights", "Team Performance Highlights"],
  ["followup_priorities", "Follow-up Priorities"], ["next_actions", "Recommended Next Actions"],
  ["risks", "Risks / Missed Opportunities"], ["conclusion", "Management Conclusion"],
];

const Section = ({ label, value }) => {
  if (value == null || value === "") return null;
  return (
    <div className="border-t border-white/8 pt-2.5 first:border-t-0 first:pt-0">
      <p className="mb-1 text-[10px] font-medium uppercase tracking-wider text-[#D6A653]/80">{label}</p>
      {Array.isArray(value) ? (
        <ul className="list-disc space-y-0.5 ps-4 text-xs text-white/80">
          {value.map((v, i) => <li key={i}>{typeof v === "object" ? JSON.stringify(v) : String(v)}</li>)}
        </ul>
      ) : (
        <p className="whitespace-pre-line text-xs leading-relaxed text-white/80">{String(value)}</p>
      )}
    </div>
  );
};

function AIBlock({ kind, fetchUrl, postUrl, fields, testPrefix }) {
  const { t, lng, isRtl } = useLocale();
  const [data, setData] = useState(undefined); // undefined=loading, null=none
  const [stale, setStale] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let alive = true;
    api.get(fetchUrl).then(({ data }) => { if (alive) { setData(data.recap || data.insight || null); setStale(!!data.stale); } })
      .catch(() => { if (alive) setData(null); });
    return () => { alive = false; };
  }, [fetchUrl]);

  const generate = async (regenerate) => {
    setBusy(true);
    try {
      const { data: res } = await api.post(postUrl, { regenerate, language: lng });
      setData(res.recap || res.insight || null);
      setStale(!!res.stale);
      if (!res.cached) toast.success(t("ai.generated", "AI analysis ready"));
    } catch (e) {
      const s = e?.response?.status;
      if (s === 429) toast.error(e?.response?.data?.detail || t("ai.limitReached", "Usage limit reached"));
      else toast.error(e?.response?.data?.detail || t("ai.failed", "Could not generate. Please try again."));
    } finally { setBusy(false); }
  };

  const content = data?.content || {};
  const genAt = data?.generated_at ? new Date(data.generated_at).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }) : "";
  const title = kind === "recap" ? t("ai.recapTitle", "AI Event Recap") : t("ai.insightTitle", "AI Lead Insight");

  return (
    <div dir={isRtl ? "rtl" : "ltr"} className="rounded-xl border border-[#D6A653]/25 bg-[#D6A653]/[0.04] p-4" data-testid={`${testPrefix}-panel`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wider text-[#D6A653]">
          <Sparkles className="h-3.5 w-3.5" /> {title}
        </p>
        {data ? (
          <button onClick={() => generate(true)} disabled={busy} data-testid={`${testPrefix}-regenerate`}
            className="flex items-center gap-1.5 rounded-lg border border-white/15 px-2.5 py-1 text-[11px] text-white/70 hover:bg-white/5 disabled:opacity-50">
            {busy ? <Loader2 className="h-3 w-3 animate-spin" /> : <RefreshCw className="h-3 w-3" />} {t("ai.regenerate", "Regenerate")}
          </button>
        ) : null}
      </div>

      {data === undefined ? (
        <div className="flex justify-center py-6"><Loader2 className="h-4 w-4 animate-spin text-[#D6A653]" /></div>
      ) : data === null ? (
        <div className="mt-3">
          <p className="mb-3 text-xs text-white/55">{kind === "recap"
            ? t("ai.recapEmpty", "Generate an AI summary of this event's performance, lead quality and next actions.")
            : t("ai.insightEmpty", "Generate an AI analysis of this lead using your existing data — priority, next action and follow-up approach.")}</p>
          <button onClick={() => generate(false)} disabled={busy} data-testid={`${testPrefix}-generate`}
            className="flex items-center gap-1.5 rounded-lg bg-[#D6A653] px-3 py-1.5 text-xs font-medium text-[#050607] hover:bg-[#E8B764] disabled:opacity-50">
            {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
            {kind === "recap" ? t("ai.generateRecap", "Generate AI Event Recap") : t("ai.generateInsight", "Generate AI Insight")}
          </button>
        </div>
      ) : (
        <div className="mt-3 space-y-2.5">
          {stale ? (
            <div className="flex items-start gap-2 rounded-lg border border-amber-400/40 bg-amber-500/10 p-2.5 text-[11px] text-amber-200" data-testid={`${testPrefix}-stale`}>
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              <span>{kind === "recap"
                ? t("ai.recapStale", "Event data has changed since this recap was generated.")
                : t("ai.insightStale", "Lead information has changed since this AI Insight was generated.")}</span>
            </div>
          ) : null}

          {kind === "insight" && (content.priority || content.timing) ? (
            <div className="flex flex-wrap items-center gap-2">
              {content.priority ? (
                <span className={`rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase ${PRIORITY_STYLE[content.priority] || "border-white/20 text-white/60"}`} data-testid={`${testPrefix}-priority`}>
                  {t("ai.priority", "Priority")}: {content.priority}
                </span>
              ) : null}
              {content.timing ? (
                <span className="flex items-center gap-1 rounded-full border border-white/15 px-2 py-0.5 text-[10px] text-white/70" data-testid={`${testPrefix}-timing`}>
                  <Clock className="h-3 w-3" /> {content.timing}
                </span>
              ) : null}
            </div>
          ) : null}

          {fields.map(([key, label]) => <Section key={key} label={label} value={content[key]} />)}

          {genAt ? <p className="pt-1 text-[10px] text-white/35">{t("ai.generatedAt", "Generated")} {genAt}</p> : null}
        </div>
      )}
    </div>
  );
}

export const LeadAIInsight = ({ leadId }) => (
  <AIBlock kind="insight" testPrefix="lead-insight" fields={LEAD_FIELDS}
    fetchUrl={`/crm/leads/${leadId}/ai-insight`} postUrl={`/crm/leads/${leadId}/ai-insight`} />
);

export const EventAIRecap = ({ eventId }) => (
  <AIBlock kind="recap" testPrefix="event-recap" fields={RECAP_FIELDS}
    fetchUrl={`/events/${eventId}/ai-recap`} postUrl={`/events/${eventId}/ai-recap`} />
);
