import { useState } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2 } from "lucide-react";
import { useLocale } from "@/i18n/useLocale";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";

const fmtErr = (d) => typeof d === "string" ? d : Array.isArray(d) ? d.map((e) => e?.msg || "").join(" ") : null;

export default function Register() {
  const { register } = useAuth();
  const { t } = useLocale();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const intent = params.get("intent");
  const refCode = params.get("ref") || "";
  const [f, setF] = useState({ name: "", email: "", password: "", workspace_name: "", referral_code: refCode });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const set = (k) => (e) => setF((s) => ({ ...s, [k]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      await register(f);
      navigate("/dashboard");
    } catch (err) {
      setError(fmtErr(err.response?.data?.detail) || err.message || t("auth.genericError"));
    } finally { setLoading(false); }
  };

  const sub = intent === "nfc" ? t("auth.createSubNfc")
    : intent === "team" ? t("auth.createSubTeam")
    : t("auth.createSubDefault");

  return (
    <div className="aria-dark relative flex min-h-screen items-center justify-center overflow-hidden bg-[#050607] px-6" style={{ fontFamily: "'Outfit', sans-serif" }}>
      <div className="grain-overlay" style={{ opacity: 0.05 }} />
      <div className="aria-gold-radial pointer-events-none absolute inset-0" />
      <div className="absolute right-4 top-4 z-10"><LanguageSwitcher /></div>
      <div className="relative w-full max-w-sm rounded-2xl border border-white/10 bg-white/[0.04] p-8 backdrop-blur-xl shadow-[0_30px_80px_rgba(0,0,0,0.6)]">
        <Link to="/" className="text-lg font-semibold tracking-tight text-white">ARIADNI <span className="text-[#D6A653]">ID</span></Link>
        <h1 className="mt-6 text-2xl font-medium tracking-tight text-white">{t("auth.createTitle")}</h1>
        <p className="mt-1 text-sm text-white/50">{sub}</p>
        <form onSubmit={submit} className="mt-7 space-y-4">
          <div className="space-y-1.5"><Label>{t("auth.fullName")}</Label><Input value={f.name} onChange={set("name")} data-testid="register-name" required /></div>
          <div className="space-y-1.5"><Label>{t("auth.workEmail")}</Label><Input type="email" value={f.email} onChange={set("email")} data-testid="register-email" required /></div>
          <div className="space-y-1.5"><Label>{t("auth.password")}</Label><Input type="password" value={f.password} onChange={set("password")} data-testid="register-password" required minLength={6} /></div>
          <div className="space-y-1.5"><Label>{t("auth.workspaceOptional")}</Label><Input value={f.workspace_name} onChange={set("workspace_name")} data-testid="register-workspace" /></div>
          {refCode ? (
            <div className="rounded-xl border border-[#D6A653]/30 bg-[#D6A653]/[0.07] px-3 py-2 text-xs text-[#D6A653]" data-testid="register-referral-banner">
              {t("auth.referralBanner")}
            </div>
          ) : null}
          {error ? <p className="text-sm text-red-400" data-testid="register-error">{error}</p> : null}
          <Button type="submit" className="w-full rounded-full bg-[#D6A653] font-medium text-[#050607] transition-all hover:bg-[#E8B764] hover:shadow-[0_0_18px_rgba(214,166,83,0.35)] active:scale-[0.98]" disabled={loading} data-testid="register-submit">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : t("auth.createAccount")}
          </Button>
        </form>
        <p className="mt-5 text-sm text-white/50">{t("auth.haveAccount")} <Link to="/login" className="text-[#D6A653] hover:underline">{t("auth.signInLink")}</Link></p>
      </div>
    </div>
  );
}
