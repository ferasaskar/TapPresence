import { useState, useEffect, useMemo } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2, ArrowLeft, User, Building2, Minus, Plus } from "lucide-react";
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
  const [refInfo, setRefInfo] = useState(null);
  const [pricing, setPricing] = useState(null);
  const [acct, setAcct] = useState(intent === "team" ? "team" : "individual");
  const [interval, setInterval] = useState("month");
  const [seats, setSeats] = useState(3);

  useEffect(() => {
    api.get("/commercial/pricing").then(({ data }) => {
      setPricing(data);
      const min = data?.plans?.team?.min_seats || 3;
      setSeats((s) => Math.max(s, min));
      if (refCode && data?.referral?.enabled) setRefInfo({ pct: data.referral.referred_discount_month_pct });
    }).catch(() => {});
  }, [refCode]);

  const minSeats = pricing?.plans?.team?.min_seats || 3;
  const p = pricing?.pricing || {};
  const seatPrice = interval === "year" ? p.team_seat_year : p.team_seat_month;
  const sym = p.symbol || "$";
  const total = useMemo(() => (Number(seatPrice) || 0) * seats, [seatPrice, seats]);
  const trialDays = pricing?.trial?.days ?? 14;

  const [f, setF] = useState({ name: "", email: "", password: "", workspace_name: "", company_name: "", referral_code: refCode });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const set = (k) => (e) => setF((s) => ({ ...s, [k]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || "";
      const payload = { ...f, timezone: tz, account_type: acct };
      if (acct === "team") { payload.seats = Math.max(seats, minSeats); payload.billing_interval = interval; }
      const u = await register(payload);
      navigate(u?.role === "SUPER_ADMIN" ? "/control" : "/dashboard");
    } catch (err) {
      setError(fmtErr(err.response?.data?.detail) || err.message || t("auth.genericError"));
    } finally { setLoading(false); }
  };

  return (
    <div className="aria-dark relative flex min-h-screen items-center justify-center overflow-hidden bg-[#050607] px-6 py-16" style={{ fontFamily: "'Outfit', sans-serif" }}>
      <div className="grain-overlay" style={{ opacity: 0.05 }} />
      <div className="aria-gold-radial pointer-events-none absolute inset-0" />
      <Link to="/" className="absolute left-4 top-4 z-10 flex items-center gap-1.5 text-sm text-white/60 transition-colors hover:text-[#D6A653]" data-testid="back-to-home"><ArrowLeft className="h-4 w-4" /> {t("auth.backToHome")}</Link>
      <div className="absolute right-4 top-4 z-10"><LanguageSwitcher /></div>
      <div className="relative w-full max-w-md rounded-2xl border border-white/10 bg-white/[0.04] p-8 backdrop-blur-xl shadow-[0_30px_80px_rgba(0,0,0,0.6)]">
        <Link to="/" className="flex items-center gap-2.5" data-testid="brand-lockup">
          <img src="/tp-mark.png" alt="TapPresence" className="h-9 w-9 object-contain" />
          <span className="text-lg font-semibold tracking-tight text-white">TapPresence</span>
        </Link>
        <h1 className="mt-6 text-2xl font-medium tracking-tight text-white">{t("auth.createTitle")}</h1>
        <p className="mt-1 text-sm text-white/50">{t("auth.chooseUse")}</p>

        {/* Account type */}
        <div className="mt-4 grid grid-cols-2 gap-2" data-testid="account-type">
          <button type="button" onClick={() => setAcct("individual")} data-testid="acct-individual"
            className={`flex flex-col items-start gap-1 rounded-xl border p-3 text-left transition-all ${acct === "individual" ? "border-[#D6A653] bg-[#D6A653]/10" : "border-white/12 hover:border-white/25"}`}>
            <User className={`h-4 w-4 ${acct === "individual" ? "text-[#D6A653]" : "text-white/50"}`} />
            <span className="text-sm font-medium text-white">{t("auth.typeIndividual")}</span>
            <span className="text-[11px] text-white/45">{t("auth.typeIndividualSub")}</span>
          </button>
          <button type="button" onClick={() => setAcct("team")} data-testid="acct-team"
            className={`flex flex-col items-start gap-1 rounded-xl border p-3 text-left transition-all ${acct === "team" ? "border-[#D6A653] bg-[#D6A653]/10" : "border-white/12 hover:border-white/25"}`}>
            <Building2 className={`h-4 w-4 ${acct === "team" ? "text-[#D6A653]" : "text-white/50"}`} />
            <span className="text-sm font-medium text-white">{t("auth.typeTeam")}</span>
            <span className="text-[11px] text-white/45">{t("auth.typeTeamSub")}</span>
          </button>
        </div>

        <form onSubmit={submit} className="mt-5 space-y-4">
          <div className="space-y-1.5"><Label>{t("auth.fullName")}</Label><Input value={f.name} onChange={set("name")} data-testid="register-name" required /></div>
          <div className="space-y-1.5"><Label>{t("auth.workEmail")}</Label><Input type="email" value={f.email} onChange={set("email")} data-testid="register-email" required /></div>
          <div className="space-y-1.5"><Label>{t("auth.password")}</Label><Input type="password" value={f.password} onChange={set("password")} data-testid="register-password" required minLength={6} /></div>

          {acct === "team" ? (
            <div className="space-y-3 rounded-xl border border-white/10 bg-white/[0.02] p-3" data-testid="team-setup">
              <div className="space-y-1.5"><Label>{t("auth.companyName")}</Label><Input value={f.company_name} onChange={set("company_name")} data-testid="register-company" required /></div>
              <div className="flex items-center gap-2 rounded-lg bg-white/5 p-0.5 text-xs">
                {["month", "year"].map((iv) => <button type="button" key={iv} onClick={() => setInterval(iv)} data-testid={`interval-${iv}`} className={`flex-1 rounded-md py-1.5 ${interval === iv ? "bg-[#D6A653] font-semibold text-[#050607]" : "text-white/55"}`}>{iv === "month" ? t("auth.monthly") : t("auth.annual")}</button>)}
              </div>
              <div className="flex items-center justify-between">
                <Label>{t("auth.seats")}</Label>
                <div className="flex items-center gap-2">
                  <button type="button" onClick={() => setSeats((s) => Math.max(minSeats, s - 1))} data-testid="seats-dec" className="rounded-md border border-white/15 p-1 text-white/70 disabled:opacity-40" disabled={seats <= minSeats}><Minus className="h-3.5 w-3.5" /></button>
                  <span className="w-8 text-center text-sm font-medium text-white" data-testid="seats-count">{seats}</span>
                  <button type="button" onClick={() => setSeats((s) => s + 1)} data-testid="seats-inc" className="rounded-md border border-white/15 p-1 text-white/70"><Plus className="h-3.5 w-3.5" /></button>
                </div>
              </div>
              <p className="text-[11px] text-white/45" data-testid="seats-min-note">{t("auth.minSeats", { n: minSeats })}</p>
              <div className="flex items-center justify-between border-t border-white/8 pt-2 text-sm">
                <span className="text-white/60">{seats} × {sym}{seatPrice}/{interval === "year" ? t("auth.yr") : t("auth.mo")}</span>
                <span className="font-semibold text-white" data-testid="team-total">{sym}{total.toFixed(2)}/{interval === "year" ? t("auth.yr") : t("auth.mo")}</span>
              </div>
              <p className="text-[11px] text-[#D6A653]" data-testid="team-trial-note">{t("auth.teamTrialNote", { days: trialDays })}</p>
            </div>
          ) : (
            <div className="space-y-1.5"><Label>{t("auth.workspaceOptional")}</Label><Input value={f.workspace_name} onChange={set("workspace_name")} data-testid="register-workspace" /></div>
          )}

          {refCode ? (
            <div className="rounded-xl border border-[#D6A653]/30 bg-[#D6A653]/[0.07] px-3 py-2 text-xs text-[#D6A653]" data-testid="register-referral-banner">
              {refInfo?.pct ? t("auth.referralBannerPct", { code: refCode, pct: refInfo.pct }) : t("auth.referralBanner")}
            </div>
          ) : null}
          {error ? <p className="text-sm text-red-400" data-testid="register-error">{error}</p> : null}
          <Button type="submit" className="w-full rounded-full bg-[#D6A653] font-medium text-[#050607] transition-all hover:bg-[#E8B764] hover:shadow-[0_0_18px_rgba(214,166,83,0.35)] active:scale-[0.98]" disabled={loading} data-testid="register-submit">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : acct === "team" ? t("auth.startTeamTrial", { days: trialDays }) : t("auth.startTrial", { days: trialDays })}
          </Button>
        </form>
        <p className="mt-5 text-sm text-white/50">{t("auth.haveAccount")} <Link to="/login" className="text-[#D6A653] hover:underline">{t("auth.signInLink")}</Link></p>
      </div>
    </div>
  );
}
