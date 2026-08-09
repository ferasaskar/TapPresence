import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import en from "./locales/en.json";
import ar from "./locales/ar.json";
import es from "./locales/es.json";

export const SUPPORTED_LANGS = [
  { code: "en", label: "English", locale: "en-US", dir: "ltr" },
  { code: "ar", label: "العربية", locale: "ar-AE", dir: "rtl" },
  { code: "es", label: "Español", locale: "es-ES", dir: "ltr" },
];

export const RTL_LANGS = ["ar"];

// Keep <html dir/lang> in sync so RTL is a true layout change, not only translated text.
export const applyDocumentDir = (lng) => {
  const dir = RTL_LANGS.includes(lng) ? "rtl" : "ltr";
  const el = document.documentElement;
  el.setAttribute("lang", lng);
  el.setAttribute("dir", dir);
};

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: { en: { translation: en }, ar: { translation: ar }, es: { translation: es } },
    fallbackLng: "en",
    supportedLngs: SUPPORTED_LANGS.map((l) => l.code),
    nonExplicitSupportedLngs: true,
    interpolation: { escapeValue: false },
    detection: {
      order: ["localStorage", "navigator", "htmlTag"],
      lookupLocalStorage: "ariadni_lang",
      caches: ["localStorage"],
    },
  });

applyDocumentDir(i18n.resolvedLanguage || "en");
i18n.on("languageChanged", applyDocumentDir);

export default i18n;
