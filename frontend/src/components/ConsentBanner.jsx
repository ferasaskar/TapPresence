import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ShieldCheck } from "lucide-react";
import { useLocale } from "@/i18n/useLocale";
import { detectMarket } from "@/lib/market";

const KEY = "tp_consent";
// GDPR-style opt-in regions (EU + UK). Region derived from the same safe locale/market signal.
const GDPR_MARKETS = new Set(["EUR", "GBP"]);

export function saveConsent(analytics) {
  try {
    localStorage.setItem(KEY, JSON.stringify({ necessary: true, analytics: !!analytics, ts: Date.now(), v: 1 }));
    window.dispatchEvent(new Event("tp-consent-changed"));
  } catch { /* ignore */ }
}
export function getConsent() {
  try { return JSON.parse(localStorage.getItem(KEY) || "null"); } catch { return null; }
}

// Region-aware, additive cookie consent. Records the visitor's choice only — it does NOT
// modify existing analytics/tracking, auth, billing, deletion or export behavior.
export default function ConsentBanner() {
  const { t } = useLocale();
  const [show, setShow] = useState(false);
  useEffect(() => { if (!getConsent()) setShow(true); }, []);
  if (!show) return null;

  const gdpr = GDPR_MARKETS.has(detectMarket() || "USD");
  const done = () => setShow(false);

  return (
    <div className="fixed inset-x-0 bottom-0 z-[60] p-3 sm:p-4" data-testid="consent-banner">
      <div className="mx-auto flex max-w-3xl flex-col gap-3 rounded-2xl border border-white/12 bg-[#0A0B0D]/95 p-4 shadow-[0_20px_60px_rgba(0,0,0,0.6)] backdrop-blur-xl sm:flex-row sm:items-center">
        <ShieldCheck className="h-5 w-5 shrink-0 text-[#D6A653]" />
        <p className="flex-1 text-xs leading-relaxed text-white/70">
          {gdpr ? t("consent.messageGdpr") : t("consent.message")}
        </p>
        <div className="flex flex-wrap items-center gap-2">
          <Link to="/privacy-center" onClick={done} data-testid="consent-manage" className="rounded-lg border border-white/15 px-3 py-1.5 text-xs text-white/80 hover:border-[#D6A653]/50">{t("consent.manage")}</Link>
          {gdpr ? (
            <button onClick={() => { saveConsent(false); done(); }} data-testid="consent-reject" className="rounded-lg border border-white/15 px-3 py-1.5 text-xs text-white/80 hover:border-[#D6A653]/50">{t("consent.rejectNonEssential")}</button>
          ) : null}
          <button onClick={() => { saveConsent(true); done(); }} data-testid="consent-accept" className="rounded-lg bg-[#D6A653] px-4 py-1.5 text-xs font-medium text-black hover:brightness-110">{gdpr ? t("consent.acceptAll") : t("consent.accept")}</button>
        </div>
      </div>
    </div>
  );
}
