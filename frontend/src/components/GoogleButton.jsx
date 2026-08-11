import { useLocale } from "@/i18n/useLocale";

const GoogleG = () => (
  <svg viewBox="0 0 24 24" className="h-4 w-4" aria-hidden="true">
    <path fill="#EA4335" d="M12 10.2v3.9h5.5c-.24 1.4-1.66 4.1-5.5 4.1-3.3 0-6-2.7-6-6.1s2.7-6.1 6-6.1c1.9 0 3.1.8 3.8 1.5l2.6-2.5C16.9 2.9 14.7 2 12 2 6.9 2 2.8 6.1 2.8 11.5S6.9 21 12 21c5.9 0 8.6-4.1 8.6-7.4 0-.5-.06-.9-.13-1.3H12z" />
  </svg>
);

// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
export const GoogleButton = ({ label }) => {
  const { t } = useLocale();
  const go = () => { window.location.href = `${process.env.REACT_APP_BACKEND_URL}/api/auth/google/start`; };
  return (
    <button type="button" onClick={go} data-testid="google-signin"
      className="flex w-full items-center justify-center gap-2.5 rounded-full border border-white/15 bg-white px-5 py-2.5 text-sm font-medium text-[#1f2328] transition-all hover:bg-white/90 active:scale-[0.98]">
      <GoogleG /> {label || t("auth.continueGoogle")}
    </button>
  );
};

export const AuthDivider = () => {
  const { t } = useLocale();
  return (
    <div className="my-5 flex items-center gap-3">
      <span className="h-px flex-1 bg-white/10" />
      <span className="text-xs uppercase tracking-wide text-white/35">{t("auth.orDivider")}</span>
      <span className="h-px flex-1 bg-white/10" />
    </div>
  );
};
