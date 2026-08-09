import { useTranslation } from "react-i18next";
import { SUPPORTED_LANGS } from "./index";

// Locale-aware formatters + language helpers. One shared source for dates/numbers/currency.
export const useLocale = () => {
  const { t, i18n } = useTranslation();
  const lng = i18n.resolvedLanguage || "en";
  const meta = SUPPORTED_LANGS.find((l) => l.code === lng) || SUPPORTED_LANGS[0];
  const locale = meta.locale;

  const setLanguage = (code) => i18n.changeLanguage(code);

  const formatNumber = (n, opts = {}) => new Intl.NumberFormat(locale, opts).format(n ?? 0);
  const formatCurrency = (n, currency = "USD") =>
    new Intl.NumberFormat(locale, { style: "currency", currency }).format(n ?? 0);
  const formatDate = (iso, opts = { dateStyle: "medium" }, tz) =>
    new Intl.DateTimeFormat(locale, tz ? { ...opts, timeZone: tz } : opts).format(new Date(iso));
  const formatDateTime = (iso, tz) =>
    new Intl.DateTimeFormat(locale, {
      weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit",
      ...(tz ? { timeZone: tz } : {}),
    }).format(new Date(iso));

  return { t, lng, locale, dir: meta.dir, isRtl: meta.dir === "rtl", langs: SUPPORTED_LANGS, setLanguage,
    formatNumber, formatCurrency, formatDate, formatDateTime };
};
