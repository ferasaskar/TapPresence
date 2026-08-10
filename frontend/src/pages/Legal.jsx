import { useParams, Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { useLocale } from "@/i18n/useLocale";

export default function Legal() {
  const { doc } = useParams();
  const { t } = useLocale();
  const map = {
    privacy: { title: t("legal.privacyTitle"), body: t("legal.privacyBody") },
    terms: { title: t("legal.termsTitle"), body: t("legal.termsBody") },
  };
  const c = map[doc] || { title: t("legal.notFound"), body: "" };
  return (
    <div className="aria-dark relative min-h-screen overflow-hidden bg-[#0B0D12] text-white" style={{ fontFamily: "'Outfit', sans-serif" }}>
      <div className="grain-overlay" style={{ opacity: 0.05 }} />
      <div className="relative mx-auto max-w-2xl px-6 py-16">
        <Link to="/" className="inline-flex items-center gap-2 text-sm text-white/60 transition-colors hover:text-white" data-testid="legal-back">
          <ArrowLeft className="h-4 w-4" /> {t("legal.backHome")}
        </Link>
        <div className="mt-8 rounded-2xl border border-white/10 bg-white/[0.03] p-8">
          <div className="flex items-center gap-3">
            <img src="/tp-mark.png" alt="TapPresence" className="h-6 w-6 object-contain" />
            <span className="text-[15px] font-semibold tracking-tight">TapPresence</span>
          </div>
          <h1 className="mt-6 text-3xl font-medium tracking-tight text-white" data-testid="legal-title">{c.title}</h1>
          {c.body ? (
            <p className="mt-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#D4AF37]" data-testid="legal-placeholder-badge">{t("legal.placeholderBadge")}</p>
          ) : null}
          <p className="mt-6 leading-relaxed text-white/65">{c.body}</p>
          {c.body ? (
            <div className="mt-8 rounded-xl border border-white/10 bg-white/[0.02] p-5">
              <p className="text-sm font-medium text-white/85">{t("legal.dataRights")}</p>
              <p className="mt-1 text-sm text-white/55">{t("legal.dataRightsBody")}</p>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
