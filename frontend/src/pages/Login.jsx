import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2 } from "lucide-react";
import { useLocale } from "@/i18n/useLocale";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";

const fmtErr = (detail) => {
  if (detail == null) return null;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((e) => e?.msg || JSON.stringify(e)).join(" ");
  return String(detail);
};

export default function Login() {
  const { login } = useAuth();
  const { t } = useLocale();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      navigate("/dashboard");
    } catch (err) {
      setError(fmtErr(err.response?.data?.detail) || err.message || t("auth.genericError"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="aria-dark relative flex min-h-screen items-center justify-center overflow-hidden bg-[#050607] px-6" style={{ fontFamily: "'Outfit', sans-serif" }}>
      <div className="grain-overlay" style={{ opacity: 0.05 }} />
      <div className="aria-gold-radial pointer-events-none absolute inset-0" />
      <div className="absolute right-4 top-4 z-10"><LanguageSwitcher /></div>
      <div className="relative w-full max-w-sm rounded-2xl border border-white/10 bg-white/[0.04] p-8 backdrop-blur-xl shadow-[0_30px_80px_rgba(0,0,0,0.6)]">
        <Link to="/" className="text-lg font-semibold tracking-tight text-white">TapPresence</Link>
        <h1 className="mt-6 text-2xl font-medium tracking-tight text-white">{t("auth.welcomeBack")}</h1>
        <p className="mt-1 text-sm text-white/50">{t("auth.signInSub")}</p>
        <form onSubmit={submit} className="mt-7 space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="email">{t("auth.email")}</Label>
            <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} data-testid="login-email" required />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="password">{t("auth.password")}</Label>
            <Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} data-testid="login-password" required />
          </div>
          {error ? <p className="text-sm text-red-400" data-testid="login-error">{error}</p> : null}
          <Button type="submit" className="w-full rounded-full bg-[#D6A653] font-medium text-[#050607] transition-all hover:bg-[#E8B764] hover:shadow-[0_0_18px_rgba(214,166,83,0.35)] active:scale-[0.98]" disabled={loading} data-testid="login-submit">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : t("auth.signIn")}
          </Button>
        </form>
        <p className="mt-5 text-sm text-white/50">{t("auth.newHere")} <Link to="/register" className="text-[#D6A653] hover:underline">{t("auth.createYourId")}</Link></p>
      </div>
    </div>
  );
}
