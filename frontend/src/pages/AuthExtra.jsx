import { useState, useEffect } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2, CheckCircle2, XCircle, MailCheck } from "lucide-react";
import { useLocale } from "@/i18n/useLocale";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";

const Shell = ({ children }) => (
  <div className="aria-dark relative flex min-h-screen items-center justify-center overflow-hidden bg-[#050607] px-6" style={{ fontFamily: "'Outfit', sans-serif" }}>
    <div className="grain-overlay" style={{ opacity: 0.05 }} />
    <div className="aria-gold-radial pointer-events-none absolute inset-0" />
    <div className="absolute right-4 top-4 z-10"><LanguageSwitcher /></div>
    <div className="relative w-full max-w-sm rounded-2xl border border-white/10 bg-white/[0.04] p-8 backdrop-blur-xl shadow-[0_30px_80px_rgba(0,0,0,0.6)]">
      <Link to="/" className="text-lg font-semibold tracking-tight text-white">TapPresence</Link>
      {children}
    </div>
  </div>
);

export function ForgotPassword() {
  const { t } = useLocale();
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const submit = async (e) => {
    e.preventDefault(); setLoading(true);
    try { await api.post("/auth/forgot-password", { email }); setSent(true); }
    catch { setSent(true); } finally { setLoading(false); }
  };
  return (
    <Shell>
      <h1 className="mt-6 text-2xl font-medium tracking-tight text-white">{t("auth.forgotTitle")}</h1>
      {sent ? (
        <p className="mt-4 text-sm text-white/70" data-testid="forgot-sent">{t("auth.forgotSent")}</p>
      ) : (
        <>
          <p className="mt-1 text-sm text-white/50">{t("auth.forgotSub")}</p>
          <form onSubmit={submit} className="mt-7 space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="email">{t("auth.email")}</Label>
              <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} data-testid="forgot-email" required />
            </div>
            <Button type="submit" className="w-full rounded-full bg-[#D6A653] font-medium text-[#050607] hover:bg-[#E8B764]" disabled={loading} data-testid="forgot-submit">
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : t("auth.forgotSend")}
            </Button>
          </form>
        </>
      )}
      <p className="mt-5 text-sm text-white/50"><Link to="/login" className="text-[#D6A653] hover:underline">{t("auth.backToLogin")}</Link></p>
    </Shell>
  );
}

export function ResetPassword() {
  const { t } = useLocale();
  const navigate = useNavigate();
  const [sp] = useSearchParams();
  const token = sp.get("token") || "";
  const [pw, setPw] = useState("");
  const [pw2, setPw2] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const submit = async (e) => {
    e.preventDefault(); setError("");
    if (pw.length < 8) { setError(t("auth.pwTooShort")); return; }
    if (pw !== pw2) { setError(t("auth.pwMismatch")); return; }
    setLoading(true);
    try { await api.post("/auth/reset-password", { token, password: pw }); navigate("/login?reset=1"); }
    catch (err) { setError(err.response?.data?.detail || t("auth.resetInvalid")); } finally { setLoading(false); }
  };
  return (
    <Shell>
      <h1 className="mt-6 text-2xl font-medium tracking-tight text-white">{t("auth.resetTitle")}</h1>
      {!token ? (
        <p className="mt-4 text-sm text-red-400" data-testid="reset-notoken">{t("auth.resetInvalid")}</p>
      ) : (
        <form onSubmit={submit} className="mt-7 space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="pw">{t("auth.newPassword")}</Label>
            <Input id="pw" type="password" value={pw} onChange={(e) => setPw(e.target.value)} data-testid="reset-pw" required />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="pw2">{t("auth.confirmPassword")}</Label>
            <Input id="pw2" type="password" value={pw2} onChange={(e) => setPw2(e.target.value)} data-testid="reset-pw2" required />
          </div>
          {error ? <p className="text-sm text-red-400" data-testid="reset-error">{error}</p> : null}
          <Button type="submit" className="w-full rounded-full bg-[#D6A653] font-medium text-[#050607] hover:bg-[#E8B764]" disabled={loading} data-testid="reset-submit">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : t("auth.resetSubmit")}
          </Button>
        </form>
      )}
    </Shell>
  );
}

export function VerifyEmail() {
  const { t } = useLocale();
  const [sp] = useSearchParams();
  const token = sp.get("token") || "";
  const [state, setState] = useState("loading");
  useEffect(() => {
    if (!token) { setState("error"); return; }
    api.post("/auth/verify-email", { token }).then(() => setState("ok")).catch(() => setState("error"));
  }, [token]);
  return (
    <Shell>
      <div className="mt-8 flex flex-col items-center text-center">
        {state === "loading" && <Loader2 className="h-10 w-10 animate-spin text-[#D6A653]" />}
        {state === "ok" && <CheckCircle2 className="h-12 w-12 text-emerald-400" data-testid="verify-ok" />}
        {state === "error" && <XCircle className="h-12 w-12 text-red-400" data-testid="verify-error" />}
        <h1 className="mt-4 text-xl font-medium text-white">{state === "ok" ? t("auth.verifyOk") : state === "error" ? t("auth.verifyFail") : t("auth.verifying")}</h1>
        <Link to="/login" className="mt-6 text-sm text-[#D6A653] hover:underline">{t("auth.backToLogin")}</Link>
      </div>
    </Shell>
  );
}
