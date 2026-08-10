import { useEffect, useState } from "react";
import { api, API_BASE } from "@/lib/api";import { useLocale } from "@/i18n/useLocale";
import { OwnerNav } from "@/components/admin/OwnerNav";
import { toast } from "sonner";
import { Loader2, Gift, Copy, Users, Award, Clock, Share2, Download, MessageCircle, Mail } from "lucide-react";

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
  const downloadQr = async () => {
    try {
      const res = await fetch(`${API_BASE}/referral/qr?code=${encodeURIComponent(d.code)}`);
      const blob = await res.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `tappresence-referral-${d.code}.png`;
      a.click();
      URL.revokeObjectURL(a.href);
    } catch { toast.error(t("referral.qrError")); }
  };
  const share = async () => {
    if (navigator.share) { try { await navigator.share({ title: "TapPresence", url: d.share_url }); } catch {} }
    else copy(d.share_url, t("referral.copied"));
  };
  const shareWhatsApp = () => {
    const text = `${t("share.emailBody", { url: d.share_url })}`;
    window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, "_blank", "noopener");
  };
  const shareEmail = () => {
    const subject = encodeURIComponent(t("share.emailSubject"));
    const body = encodeURIComponent(t("share.emailBody", { url: d.share_url }));
    window.location.href = `mailto:?subject=${subject}&body=${body}`;
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
            <div className="mt-6 rounded-2xl border border-[#D4AF37]/25 bg-gradient-to-b from-[#D4AF37]/[0.08] to-transparent p-6" data-testid="referral-hero">
              {(() => {
                const per = d.config.referrals_per_reward || 5;
                const months = d.config.reward_months || 1;
                const qualified = d.reward?.qualified_count || 0;
                const earned = d.reward?.free_months_earned || 0;
                const progress = d.reward?.progress ?? (qualified % per);
                const remaining = (per - progress) % per || (progress === 0 && qualified === 0 ? per : per - progress);
                const justUnlocked = qualified > 0 && progress === 0;
                return (
                  <div data-testid="referral-progress">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#D4AF37]">{t("referralProgram.taglineShort", { count: per })}</p>
                    <h3 className="mt-2 text-xl font-light text-white" data-testid="referral-progress-title">
                      {justUnlocked ? t("referralProgram.unlocked", { count: earned }) : t("referralProgram.subscribedOf", { qualified: progress, per })}
                    </h3>
                    {/* dots */}
                    <div className="mt-4 flex items-center gap-2.5" data-testid="referral-dots">
                      {Array.from({ length: per }).map((_, i) => (
                        <span key={i} data-testid={`referral-dot-${i}`}
                          className={`h-4 w-4 rounded-full border transition-all ${i < progress ? "border-[#D4AF37] bg-[#D4AF37] shadow-[0_0_10px_rgba(212,175,55,0.5)]" : "border-white/20 bg-transparent"}`} />
                      ))}
                    </div>
                    <p className="mt-3 text-sm text-white/60" data-testid="referral-remaining">
                      {progress === 0 && qualified > 0
                        ? t("referralProgram.unlocked", { count: earned })
                        : t("referralProgram.moreToUnlock", { remaining, count: remaining })}
                    </p>
                    {(d.counts?.signed_up || 0) > 0 ? (
                      <p className="mt-1 text-xs text-white/40" data-testid="referral-pending">{t("referralProgram.pendingNote", { count: d.counts.signed_up })}</p>
                    ) : null}
                    <p className="mt-2 text-xs text-white/45" data-testid="referral-qualified-note">{t("referralProgram.qualifiedNote")}</p>
                  </div>
                );
              })()}

              <div className="mt-5 flex flex-col gap-3 border-t border-white/10 pt-5 sm:flex-row sm:items-center">
                <div className="flex items-center gap-2">
                  <span className="text-[11px] uppercase tracking-wide text-white/40">{t("referral.yourCode")}</span>
                  <code className="rounded-lg border border-[#D4AF37]/40 bg-[#D4AF37]/[0.08] px-3 py-1.5 text-lg font-medium tracking-[0.2em] text-[#D4AF37]" data-testid="referral-page-code">{d.code}</code>
                  <button onClick={() => copy(d.code, t("referral.codeCopied"))} data-testid="referral-copy-code" className="rounded-lg border border-white/15 p-1.5 text-white/70 hover:border-[#D4AF37]/50"><Copy className="h-3.5 w-3.5" /></button>
                </div>
                <div className="flex flex-1 items-center gap-2">
                  <input readOnly value={d.share_url} data-testid="referral-share-url" className="flex-1 rounded-lg border border-white/12 bg-white/5 px-3 py-2 text-sm text-white/70 outline-none" />
                  <button onClick={() => copy(d.share_url, t("referral.copied"))} data-testid="referral-copy-url" className="flex items-center gap-1.5 rounded-lg border border-white/15 px-3 py-2 text-sm text-white/80 hover:border-[#D4AF37]/50"><Copy className="h-4 w-4" /></button>
                  <button onClick={share} data-testid="referral-share" className="flex items-center gap-1.5 rounded-lg bg-[#D4AF37] px-3 py-2 text-sm font-medium text-black hover:brightness-110"><Share2 className="h-4 w-4" /></button>
                </div>
              </div>
              <div className="mt-3 flex flex-wrap gap-2" data-testid="referral-quick-share">
                <button onClick={shareWhatsApp} data-testid="referral-share-whatsapp" className="inline-flex items-center gap-1.5 rounded-full border border-[#25D366]/40 bg-[#25D366]/10 px-4 py-2 text-sm text-[#5cf29a] transition-colors hover:bg-[#25D366]/20"><MessageCircle className="h-4 w-4" /> {t("share.whatsapp")}</button>
                <button onClick={shareEmail} data-testid="referral-share-email" className="inline-flex items-center gap-1.5 rounded-full border border-white/15 bg-white/5 px-4 py-2 text-sm text-white/80 transition-colors hover:bg-white/10"><Mail className="h-4 w-4 text-[#D4AF37]" /> {t("share.email")}</button>
              </div>
              {/* QR of the invite link (reuses referral_code) */}
              <div className="mt-5 flex flex-col items-center gap-3 sm:flex-row sm:items-center" data-testid="referral-qr-block">
                <div className="rounded-2xl border border-white/12 bg-white p-2">
                  <img src={`${API_BASE}/referral/qr?code=${encodeURIComponent(d.code)}`} alt={t("referral.qrAlt")} width={132} height={132} className="block h-[132px] w-[132px]" data-testid="referral-qr-img" />
                </div>
                <div>
                  <p className="text-sm text-white/70">{t("referral.qrTitle")}</p>
                  <p className="mt-1 text-xs text-white/45">{t("referral.qrDesc")}</p>
                  <button onClick={downloadQr} data-testid="referral-qr-download" className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-white/15 px-3 py-1.5 text-xs text-white/80 hover:border-[#D4AF37]/50">
                    <Download className="h-3.5 w-3.5" /> {t("referral.qrDownload")}
                  </button>
                </div>
              </div>
            </div>

            <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Stat icon={Users} label={t("referralProgram.statTotal")} value={d.counts?.total || 0} testid="referral-stat-total" />
              <Stat icon={Award} label={t("referralProgram.statPaid")} value={d.reward?.qualified_count || 0} testid="referral-stat-paid" />
              <Stat icon={Gift} label={t("referralProgram.statMonths")} value={d.reward?.free_months_earned || 0} testid="referral-stat-months" />
              <Stat icon={Clock} label={t("referralProgram.statProgress")} value={`${d.reward?.progress || 0}/${d.config.referrals_per_reward}`} testid="referral-stat-progress" />
            </div>

            {d.config.referred_discount_month_pct > 0 ? (
              <div className="mt-4 rounded-xl border border-white/10 bg-[#0A0B0D] px-4 py-3 text-sm text-white/60" data-testid="referral-signup-discount">
                {t("referralProgram.signupDiscount", { pct: d.config.referred_discount_month_pct })}
              </div>
            ) : null}

            <div className="mt-8 rounded-2xl border border-white/10 bg-[#0A0B0D] p-6" data-testid="referral-how">
              <h3 className="text-sm font-medium text-white">{t("referralProgram.howTitle")}</h3>
              <ol className="mt-3 space-y-2 text-sm text-white/60">
                <li>1. {t("referralProgram.how1")}</li>
                <li>2. {t("referralProgram.how2")}</li>
                <li>3. {t("referralProgram.how3", { count: d.config.referrals_per_reward, months: d.config.reward_months })}</li>
              </ol>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
