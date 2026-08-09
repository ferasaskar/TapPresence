import { useEffect } from "react";
import { toast } from "sonner";
import { useLocale } from "@/i18n/useLocale";
import { detectMarket } from "@/lib/market";

// One-time, subtle notice shown ONLY when TapPresence auto-selects a non-default
// language or market on a visitor's first visit. Never after a manual choice.
// Language and market remain independent — this only informs, it never changes anything.
const LANG_LABEL = { en: "English", ar: "العربية", es: "Español" };

export default function LocaleToast() {
  const { t, lng } = useLocale();
  useEffect(() => {
    let shown, langManual, marketManual;
    try {
      shown = localStorage.getItem("tp_locale_toast_shown");
      langManual = localStorage.getItem("tp_lang_manual") === "1";
      marketManual = !!localStorage.getItem("tp_market");
    } catch { return; }
    if (shown) return;

    const autoLang = !langManual && lng && lng !== "en";
    const detected = detectMarket();
    const autoMarket = !marketManual && detected && detected !== "USD";
    if (!autoLang && !autoMarket) return;

    const market = (!marketManual && detected) ? detected : "USD";
    const id = setTimeout(() => {
      toast(t("common.localeToast", { lang: LANG_LABEL[lng] || "English", market }), { duration: 6000 });
      try { localStorage.setItem("tp_locale_toast_shown", "1"); } catch {}
    }, 1200);
    return () => clearTimeout(id);
  }, [lng, t]);

  return null;
}
