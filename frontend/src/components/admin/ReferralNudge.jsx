import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useLocale } from "@/i18n/useLocale";
import { Gift, ArrowRight } from "lucide-react";

// Subtle, premium dashboard nudge. Reuses the EXISTING /referral progress + config
// (never hardcodes the threshold). Links to the existing Referral page. Not a popup,
// not a second referral system — pure presentation of existing state.
export function ReferralNudge() {
  const { t } = useLocale();
  const navigate = useNavigate();
  const [d, setD] = useState(null);

  useEffect(() => { api.get("/referral").then((r) => setD(r.data)).catch(() => {}); }, []);
  if (!d || !d.enabled) return null;

  const per = d.config.referrals_per_reward || 5;
  const qualified = d.reward?.qualified_count || 0;
  const earned = d.reward?.free_months_earned || 0;
  const progress = d.reward?.progress ?? (qualified % per);
  const remaining = per - progress;

  let msg;
  if (qualified === 0) msg = t("referralProgram.nudgeStart", { count: per });
  else if (earned > 0 && progress === 0) msg = t("referralProgram.nudgeUnlocked", { count: earned });
  else msg = t("referralProgram.nudgeProgress", { remaining, count: remaining });

  return (
    <button
      onClick={() => navigate("/referral")}
      data-testid="dashboard-referral-nudge"
      className="group flex w-full items-center gap-3 rounded-2xl border border-[#D4AF37]/25 bg-gradient-to-r from-[#D4AF37]/[0.08] to-transparent px-4 py-3.5 text-left transition-colors hover:border-[#D4AF37]/45"
    >
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#D4AF37]/15">
        <Gift className="h-4.5 w-4.5 text-[#D4AF37]" />
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-white" data-testid="dashboard-referral-nudge-msg">{msg}</p>
        {qualified > 0 ? (
          <div className="mt-1.5 flex items-center gap-1" aria-hidden>
            {Array.from({ length: per }).map((_, i) => (
              <span key={i} className={`h-1.5 rounded-full transition-all ${i < progress ? "w-5 bg-[#D4AF37]" : "w-3 bg-white/15"}`} />
            ))}
          </div>
        ) : null}
      </div>
      <span className="flex shrink-0 items-center gap-1 text-xs font-medium text-[#D4AF37]">
        {t("referralProgram.nudgeCta")} <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
      </span>
    </button>
  );
}
