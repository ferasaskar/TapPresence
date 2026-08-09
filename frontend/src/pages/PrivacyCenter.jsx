import { useState } from "react";
import { Link } from "react-router-dom";
import { ShieldCheck, Lock, BarChart3, ArrowLeft, ExternalLink } from "lucide-react";
import { toast } from "sonner";
import { useLocale } from "@/i18n/useLocale";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { getConsent, saveConsent } from "@/components/ConsentBanner";
import { detectMarket } from "@/lib/market";

// Additive privacy hub. Records cookie/analytics preferences only. Does NOT touch
// account deletion, data export, authentication or billing.
export default function PrivacyCenter() {
  const { t } = useLocale();
  const [analytics, setAnalytics] = useState(() => getConsent()?.analytics ?? false);
  const region = detectMarket() || "USD";

  const Toggle = ({ checked, onChange, disabled, testid }) => (
    <button onClick={() => !disabled && onChange(!checked)} disabled={disabled} data-testid={testid}
      className={`relative h-5 w-9 shrink-0 rounded-full transition-colors ${disabled ? "bg-[#D6A653]/60" : checked ? "bg-[#D6A653]" : "bg-white/15"}`}>
      <span className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-all ${checked ? "left-[18px]" : "left-0.5"}`} />
    </button>
  );

  const Row = ({ icon: Icon, title, desc, right, testid }) => (
    <div className="flex items-start justify-between gap-4 rounded-2xl border border-white/10 bg-[#0A0B0D] p-5" data-testid={testid}>
      <div className="flex items-start gap-3">
        <Icon className="mt-0.5 h-4 w-4 text-[#D6A653]" />
        <div><p className="text-sm font-medium text-white">{title}</p><p className="mt-1 text-xs text-white/50">{desc}</p></div>
      </div>
      {right}
    </div>
  );

  return (
    <div className="aria-dark relative min-h-screen bg-[#050607] text-white" style={{ fontFamily: "'Outfit', sans-serif" }} data-testid="privacy-center-page">
      <div className="grain-overlay" style={{ opacity: 0.04 }} />
      <div className="absolute right-4 top-4 z-10"><LanguageSwitcher /></div>
      <main className="relative mx-auto max-w-2xl px-4 py-10 sm:px-8">
        <Link to="/" className="mb-6 inline-flex items-center gap-1.5 text-sm text-white/50 hover:text-white"><ArrowLeft className="h-4 w-4" /> TapPresence</Link>
        <h1 className="flex items-center gap-2 text-2xl font-light tracking-tight text-white"><ShieldCheck className="h-5 w-5 text-[#D6A653]" /> {t("consent.centerTitle")}</h1>
        <p className="mt-1 text-sm text-white/45">{t("consent.centerSubtitle")}</p>
        <p className="mt-1 text-xs text-white/30">{t("consent.region")}: {region}</p>

        <div className="mt-6 space-y-3">
          <Row icon={Lock} testid="consent-row-necessary" title={t("consent.necessary")} desc={t("consent.necessaryDesc")}
            right={<span className="text-[11px] uppercase tracking-wide text-[#D6A653]">{t("consent.alwaysOn")}</span>} />
          <Row icon={BarChart3} testid="consent-row-analytics" title={t("consent.analytics")} desc={t("consent.analyticsDesc")}
            right={<Toggle checked={analytics} onChange={setAnalytics} testid="consent-toggle-analytics" />} />
        </div>

        <div className="mt-6 flex flex-wrap items-center gap-3">
          <button onClick={() => { saveConsent(analytics); toast.success(t("consent.saved")); }} data-testid="consent-save"
            className="rounded-full bg-[#D6A653] px-5 py-2.5 text-sm font-medium text-black hover:brightness-110">{t("consent.savePrefs")}</button>
          <Link to="/legal/privacy" data-testid="consent-view-policy" className="inline-flex items-center gap-1.5 text-sm text-white/60 hover:text-white">
            {t("consent.viewPolicy")} <ExternalLink className="h-3.5 w-3.5" />
          </Link>
        </div>
      </main>
    </div>
  );
}
