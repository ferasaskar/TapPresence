import { useEffect, useState } from "react";
import { api } from "@/lib/api";import { useLocale } from "@/i18n/useLocale";
import { OwnerNav } from "@/components/admin/OwnerNav";
import { toast } from "sonner";
import { Loader2, Gift, Copy, Users, Award, Clock, Share2 } from "lucide-react";

const Stat = ({ icon: Icon, label, value, sub, testid }) => (
  <div className="rounded-2xl border border-white/10 bg-[#0A0B0D] p-5" data-testid={testid}>
    <Icon className="mb-2 h-4 w-4 text-[#D6A653]" />
    <p className="text-2xl font-light text-white">{value}</p>
    <p className="text-xs text-white/45">{label}{sub ? <span className="text-white/30"> · {sub}</span> : null}</p>
  </div>
);

export default function Referral() {
  const { t } = useLocale();
  const [d, setD] = useState(undefined);

  useEffect(() => { api.get("/referral").then(({ data }) => setD(data)).catch(() => setD(null)); }, []);

  const copy = (text, msg) => { navigator.clipboard.writeText(text); toast.success(msg); };
  const share = async () => {
    if (navigator.share) { try { await navigator.share({ title: "TapPresence", url: d.share_url }); } catch {} }
    else copy(d.share_url, t("referral.copied"));
  };

  return (
    <div className="aria-dark relative min-h-screen bg-[#050607] text-white" style={{ fontFamily: "'Outfit', sans-serif" }} data-testid="referral-page">
      <div className="grain-overlay" style={{ opacity: 0.04 }} />
      <OwnerNav active="referral" />
      <main className="relative mx-auto max-w-3xl px-4 py-8 sm:px-8">
        <h2 className="flex items-center gap-2 text-2xl font-light tracking-tight text-white"><Gift className="h-5 w-5 text-[#D6A653]" /> {t("referral.title")}</h2>
        <p className="mt-1 text-sm text-white/45">{t("referral.subtitle")}</p>

        {d === undefined ? (
          <div className="flex justify-center py-24"><Loader2 className="h-6 w-6 animate-spin text-[#D6A653]" /></div>
        ) : d === null ? (
          <div className="mt-8 rounded-2xl border border-dashed border-white/12 py-24 text-center text-white/55">{t("referral.loadError")}</div>
        ) : !d.enabled ? (
          <div className="mt-8 rounded-2xl border border-dashed border-white/12 py-24 text-center text-white/55" data-testid="referral-disabled">{t("referral.disabled")}</div>
        ) : (
          <>
            <div className="mt-6 rounded-2xl border border-[#D6A653]/25 bg-[#D6A653]/[0.06] p-6" data-testid="referral-hero">
              <p className="text-sm text-white/70">{t("referral.headline", { referred: d.config.referred_discount_month_pct, reward: d.config.referrer_reward_pct, max: d.config.max_reward_discount_pct })}</p>
              <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center">
                <div className="flex items-center gap-2">
                  <span className="text-[11px] uppercase tracking-wide text-white/40">{t("referral.yourCode")}</span>
                  <code className="rounded-lg border border-[#D6A653]/40 bg-[#D6A653]/[0.08] px-3 py-1.5 text-lg font-medium tracking-[0.2em] text-[#D6A653]" data-testid="referral-page-code">{d.code}</code>
                </div>
                <div className="flex flex-1 items-center gap-2">
                  <input readOnly value={d.share_url} data-testid="referral-share-url" className="flex-1 rounded-lg border border-white/12 bg-white/5 px-3 py-2 text-sm text-white/70 outline-none" />
                  <button onClick={() => copy(d.share_url, t("referral.copied"))} data-testid="referral-copy-url" className="flex items-center gap-1.5 rounded-lg border border-white/15 px-3 py-2 text-sm text-white/80 hover:border-[#D6A653]/50"><Copy className="h-4 w-4" /></button>
                  <button onClick={share} data-testid="referral-share" className="flex items-center gap-1.5 rounded-lg bg-[#D6A653] px-3 py-2 text-sm font-medium text-black hover:brightness-110"><Share2 className="h-4 w-4" /></button>
                </div>
              </div>
            </div>

            <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-3">
              <Stat icon={Users} label={t("referral.referred")} value={d.referred_count} testid="referral-stat-count" />
              <Stat icon={Award} label={t("referral.rewardApplied")} value={`${d.reward?.applied_pct || 0}%`} sub={`${t("referral.cap")} ${d.config.max_reward_discount_pct}%`} testid="referral-stat-reward" />
              <Stat icon={Clock} label={t("referral.rewardQueued")} value={`${d.reward?.queued_pct || 0}%`} testid="referral-stat-queued" />
            </div>

            {d.referred_as ? (
              <div className="mt-4 rounded-xl border border-white/10 bg-[#0A0B0D] px-4 py-3 text-sm text-white/60" data-testid="referral-referred-as">
                {t("referral.youWereReferred", { pct: d.referred_as.discount_month_pct })}
              </div>
            ) : null}

            <div className="mt-8 rounded-2xl border border-white/10 bg-[#0A0B0D] p-6" data-testid="referral-how">
              <h3 className="text-sm font-medium text-white">{t("referral.howTitle")}</h3>
              <ol className="mt-3 space-y-2 text-sm text-white/60">
                <li>1. {t("referral.step1")}</li>
                <li>2. {t("referral.step2", { referred: d.config.referred_discount_month_pct })}</li>
                <li>3. {t("referral.step3", { reward: d.config.referrer_reward_pct, max: d.config.max_reward_discount_pct })}</li>
              </ol>
              <div className="mt-5 flex items-center gap-4">
                <p className="text-xs text-white/35">{t("referral.fairUse")}</p>
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
