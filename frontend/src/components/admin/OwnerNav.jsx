import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import AnalyticsDialog from "./AnalyticsDialog";
import ScanCardDialog from "./ScanCardDialog";
import { NotificationBell } from "./NotificationCenter";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { useLocale } from "@/i18n/useLocale";
import { Home, CreditCard, CalendarDays, BarChart3, Settings as SettingsIcon, ScanLine, LogOut, ShieldCheck, Users, Mail, Plug, Receipt, Gift } from "lucide-react";

const AriadniMark = ({ className = "" }) => (
  <img src="/tp-mark.png" alt="TapPresence" className={`object-contain ${className}`} aria-hidden />
);

// Shared, role-aware owner navigation. Reused across Home / My Card / Meetings / Settings.
export const OwnerNav = ({ active }) => {
  const { user, logout, entitlements } = useAuth();
  const { t } = useLocale();
  const navigate = useNavigate();
  const isAdmin = user?.role === "SUPER_ADMIN";
  const [cards, setCards] = useState([]);
  const [scanOpen, setScanOpen] = useState(false);
  const [analyticsCard, setAnalyticsCard] = useState(null);
  const canTeam = isAdmin || !!entitlements?.team;
  const [resent, setResent] = useState(false);
  const showVerify = user && user.email_verified === false;
  const resend = async () => { try { await api.post("/auth/resend-verification"); setResent(true); } catch (_) {} };

  const refresh = () => {
    api.get("/admin/cards").then((r) => setCards(r.data)).catch(() => {});
  };
  useEffect(() => { refresh(); }, [isAdmin, user]);
  const primary = cards[0];

  const items = [
    { key: "home", label: t("nav.home"), icon: Home, onClick: () => navigate("/dashboard") },
    { key: "cards", label: cards.length > 1 ? t("nav.myCards") : t("nav.myCard"), icon: CreditCard, onClick: () => navigate("/admin") },
    { key: "meetings", label: t("nav.meetings"), icon: CalendarDays, onClick: () => navigate("/meetings") },
    { key: "analytics", label: t("nav.analytics"), icon: BarChart3, onClick: () => (primary ? setAnalyticsCard(primary) : navigate("/dashboard")) },
    { key: "signatures", label: t("nav.signatures"), icon: Mail, onClick: () => navigate("/signatures") },
    { key: "billing", label: t("nav.billing"), icon: Receipt, onClick: () => navigate("/billing") },
    { key: "referral", label: t("nav.referral"), icon: Gift, onClick: () => navigate("/referral") },
    ...(canTeam ? [{ key: "team", label: t("nav.team"), icon: Users, onClick: () => navigate("/team") }] : []),
    ...(canTeam ? [{ key: "integrations", label: t("nav.integrations"), icon: Plug, onClick: () => navigate("/integrations") }] : []),
    ...(isAdmin ? [{ key: "command", label: t("nav.command"), icon: ShieldCheck, onClick: () => navigate("/admin/platform") }] : []),
    { key: "settings", label: t("nav.settings"), icon: SettingsIcon, onClick: () => navigate("/settings") },
  ];

  return (
    <header className="sticky top-0 z-40 border-b border-white/8 bg-[#050607]/85 backdrop-blur-xl" data-testid="owner-nav">
      <div className="mx-auto max-w-7xl px-4 py-3 sm:px-8">
        <div className="flex items-center justify-between gap-3">
          <button onClick={() => navigate("/dashboard")} className="flex items-center gap-2.5" data-testid="nav-brand">
            <AriadniMark className="h-5 w-5 text-[#D6A653]" />
            <div className="text-left">
              <p className="text-[10px] uppercase tracking-[0.3em] text-white/40">TapPresence</p>
              <h1 className="text-[14px] font-medium leading-tight text-white">{t("nav.studio")}</h1>
            </div>
          </button>
          <div className="flex items-center gap-2">
            {isAdmin ? (
              <span className="hidden items-center gap-1.5 rounded-full border border-[#D6A653]/40 bg-[#D6A653]/10 px-3 py-1 text-[11px] font-medium text-[#D6A653] sm:inline-flex" data-testid="nav-role-badge"><ShieldCheck className="h-3.5 w-3.5" /> {t("nav.superAdmin")}</span>
            ) : (
              <span className="hidden rounded-full border border-white/12 bg-white/5 px-3 py-1 text-[11px] text-white/55 sm:inline" data-testid="nav-role-badge">{user?.name || t("nav.member")}</span>
            )}
            <LanguageSwitcher />
            <NotificationBell />
            {isAdmin ? (
              <button onClick={() => setScanOpen(true)} className="rounded-full border border-white/12 bg-white/5 p-2 text-white/70 transition-colors hover:text-white" title={t("nav.scanCard")} data-testid="nav-scan"><ScanLine className="h-4 w-4 text-[#D6A653]" /></button>
            ) : null}
            <button onClick={logout} className="rounded-full p-2 text-white/60 transition-colors hover:bg-white/5 hover:text-white" data-testid="nav-logout"><LogOut className="h-4 w-4" /></button>
          </div>
        </div>

        {showVerify ? (
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-[#D6A653]/30 bg-[#D6A653]/[0.07] px-4 py-2.5 text-xs" data-testid="verify-banner">
            <span className="flex items-center gap-2 text-[#F2E0C9]"><Mail className="h-3.5 w-3.5 text-[#D6A653]" /> {resent ? t("auth.verifyResent") : t("auth.verifyBanner")}</span>
            {!resent ? <button onClick={resend} className="rounded-lg border border-[#D6A653]/40 px-2.5 py-1 text-[#D6A653] hover:bg-[#D6A653]/15" data-testid="verify-resend">{t("auth.verifyResend")}</button> : null}
          </div>
        ) : null}

        {/* nav pills — horizontally scrollable on mobile */}
        <nav className="mt-3 flex gap-1.5 overflow-x-auto pb-0.5" data-testid="nav-items">
          {items.map((it) => {
            const on = active === it.key;
            return (
              <button
                key={it.key}
                onClick={it.onClick}
                data-testid={`nav-${it.key}`}
                className={`relative flex shrink-0 items-center gap-1.5 rounded-full border px-3.5 py-1.5 text-sm transition-all ${on ? "border-[#D6A653] bg-[#D6A653]/12 text-white" : "border-white/10 text-white/55 hover:border-white/25 hover:text-white"}`}
              >
                <it.icon className={`h-4 w-4 ${on ? "text-[#D6A653]" : ""}`} />
                {it.label}
              </button>
            );
          })}
        </nav>
      </div>

      <ScanCardDialog open={scanOpen} onOpenChange={setScanOpen} cards={cards} onSaved={refresh} />
      <AnalyticsDialog card={analyticsCard} open={!!analyticsCard} onOpenChange={(v) => !v && setAnalyticsCard(null)} />
    </header>
  );
};
