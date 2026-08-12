import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import AnalyticsDialog from "./AnalyticsDialog";
import ScanCardDialog from "./ScanCardDialog";
import { NotificationBell } from "./NotificationCenter";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { useLocale } from "@/i18n/useLocale";
import {
  Home, CreditCard, CalendarDays, BarChart3, Settings as SettingsIcon, ScanLine, LogOut,
  ShieldCheck, Users, Mail, Plug, Receipt, Gift, Inbox, Smartphone, Menu, X, Building2, User,
} from "lucide-react";

const TpMark = ({ className = "" }) => (
  <img src="/tp-mark.png" alt="TapPresence" className={`object-contain ${className}`} aria-hidden />
);

// Role-aware app shell: fixed left sidebar on desktop, slide-out drawer on mobile,
// plus a sticky top bar with the current account context, notifications and profile.
export const OwnerNav = ({ active }) => {
  const { user, logout, entitlements, workspace, memberships } = useAuth();
  const { t } = useLocale();
  const navigate = useNavigate();
  const isAdmin = user?.role === "SUPER_ADMIN";
  const [cards, setCards] = useState([]);
  const [scanOpen, setScanOpen] = useState(false);
  const [analyticsCard, setAnalyticsCard] = useState(null);
  const [drawer, setDrawer] = useState(false);
  const [resent, setResent] = useState(false);
  const canTeam = isAdmin || !!entitlements?.team;
  const showVerify = user && user.email_verified === false;
  const resend = async () => { try { await api.post("/auth/resend-verification"); setResent(true); } catch (_) {} };

  const refresh = () => { api.get("/admin/cards").then((r) => setCards(r.data)).catch(() => {}); };
  useEffect(() => { refresh(); }, [isAdmin, user]);
  useEffect(() => {
    document.body.classList.add("tp-shell");
    return () => document.body.classList.remove("tp-shell");
  }, []);
  const primary = cards[0];

  // ---- Account context (Personal / Team workspace / Admin Console) ----
  const wsRole = (memberships || []).find((m) => m.workspace_id === workspace?.id)?.role || user?.role;
  const isTeam = workspace?.type === "team";
  const contextLabel = isAdmin ? t("nav.adminConsole") : isTeam ? (workspace?.name || t("nav.team")) : t("nav.personalAccount");
  const roleBadge = isAdmin ? t("nav.superAdmin")
    : wsRole === "WORKSPACE_OWNER" ? t("nav.owner")
    : wsRole === "WORKSPACE_ADMIN" ? t("nav.admin")
    : wsRole === "MANAGER" ? t("nav.manager")
    : t("nav.member");

  const go = (fn) => () => { fn(); setDrawer(false); };
  const main = [
    { key: "home", label: t("nav.home"), icon: Home, onClick: () => navigate("/dashboard") },
    { key: "cards", label: t("nav.cards"), icon: CreditCard, onClick: () => navigate("/admin") },
    { key: "leads", label: t("nav.leads"), icon: Inbox, onClick: () => navigate("/leads") },
    { key: "scanner", label: t("nav.scanner"), icon: ScanLine, onClick: () => setScanOpen(true) },
    { key: "meetings", label: t("nav.meetings"), icon: CalendarDays, onClick: () => navigate("/meetings") },
    { key: "analytics", label: t("nav.analytics"), icon: BarChart3, onClick: () => (primary ? setAnalyticsCard(primary) : navigate("/dashboard")) },
    { key: "signatures", label: t("nav.signatures"), icon: Mail, onClick: () => navigate("/signatures") },
    { key: "nfc", label: t("nav.nfc"), icon: Smartphone, onClick: () => navigate("/nfc") },
  ];
  const account = [
    { key: "billing", label: t("nav.billing"), icon: Receipt, onClick: () => navigate("/billing") },
    { key: "referral", label: t("nav.referral"), icon: Gift, onClick: () => navigate("/referral") },
    ...(canTeam ? [{ key: "team", label: t("nav.team"), icon: Users, onClick: () => navigate("/team") }] : []),
    ...(canTeam ? [{ key: "integrations", label: t("nav.integrations"), icon: Plug, onClick: () => navigate("/integrations") }] : []),
    { key: "settings", label: t("nav.settings"), icon: SettingsIcon, onClick: () => navigate("/settings") },
  ];
  const adminItems = [
    { key: "command", label: t("nav.command"), icon: ShieldCheck, onClick: () => navigate("/control") },
  ];

  const Item = ({ it }) => {
    const on = active === it.key;
    return (
      <button
        onClick={go(it.onClick)}
        data-testid={`nav-${it.key}`}
        className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-all ${on ? "bg-[#D6A653]/12 text-white" : "text-white/55 hover:bg-white/5 hover:text-white"}`}
      >
        <it.icon className={`h-4 w-4 shrink-0 ${on ? "text-[#D6A653]" : ""}`} />
        <span className="truncate">{it.label}</span>
      </button>
    );
  };

  const ContextBlock = () => (
    <div className="rounded-xl border border-white/10 bg-white/[0.03] px-3 py-3" data-testid="account-context">
      <div className="flex items-center gap-2">
        <span className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-lg ${isAdmin ? "bg-[#D6A653]/15 text-[#D6A653]" : "bg-white/8 text-white/70"}`}>
          {isAdmin ? <ShieldCheck className="h-3.5 w-3.5" /> : isTeam ? <Building2 className="h-3.5 w-3.5" /> : <User className="h-3.5 w-3.5" />}
        </span>
        <div className="min-w-0">
          <p className="truncate text-[13px] font-medium leading-tight text-white" data-testid="context-label">{contextLabel}</p>
          <span className="text-[10px] uppercase tracking-wider text-[#D6A653]/80" data-testid="context-role">{roleBadge}</span>
        </div>
      </div>
    </div>
  );

  const NavBody = ({ inDrawer }) => (
    <>
      <button onClick={go(() => navigate("/dashboard"))} className="flex items-center gap-2.5 px-1" data-testid="nav-brand">
        <TpMark className="h-6 w-6" />
        <div className="text-left">
          <p className="text-[10px] uppercase tracking-[0.3em] text-white/40">TapPresence</p>
          <h1 className="text-[13px] font-medium leading-tight text-white">{t("nav.studio")}</h1>
        </div>
      </button>

      <div className="mt-4"><ContextBlock /></div>

      {showVerify ? (
        <div className="mt-3 flex flex-col gap-1.5 rounded-xl border border-[#D6A653]/30 bg-[#D6A653]/[0.07] px-3 py-2.5 text-xs" data-testid="verify-banner">
          <span className="flex items-center gap-2 text-[#F2E0C9]"><Mail className="h-3.5 w-3.5 text-[#D6A653]" /> {resent ? t("auth.verifyResent") : t("auth.verifyBanner")}</span>
          {!resent ? <button onClick={resend} className="self-start rounded-lg border border-[#D6A653]/40 px-2.5 py-1 text-[#D6A653] hover:bg-[#D6A653]/15" data-testid="verify-resend">{t("auth.verifyResend")}</button> : null}
        </div>
      ) : null}

      <nav className="mt-4 flex-1 space-y-0.5 overflow-y-auto" data-testid="nav-items">
        {main.map((it) => <Item key={it.key} it={it} />)}
        <div className="my-3 border-t border-white/8" />
        {account.map((it) => <Item key={it.key} it={it} />)}
        {isAdmin ? (
          <>
            <div className="mt-4 mb-1 flex items-center gap-2 px-3">
              <ShieldCheck className="h-3 w-3 text-[#D6A653]/70" />
              <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#D6A653]/70">{t("nav.adminTools")}</p>
            </div>
            {adminItems.map((it) => <Item key={it.key} it={it} />)}
          </>
        ) : null}
      </nav>

      <button onClick={go(logout)} className="mt-3 flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-white/55 transition-colors hover:bg-white/5 hover:text-white" data-testid="nav-logout">
        <LogOut className="h-4 w-4" /> {t("nav.logout")}
      </button>
    </>
  );

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="tp-sidebar hidden flex-col border-white/8 bg-[#050607] px-4 py-5 lg:flex" style={{ borderInlineEndWidth: 1 }} data-testid="owner-sidebar">
        <NavBody />
      </aside>

      {/* Mobile drawer + overlay */}
      {drawer ? <div className="tp-drawer-overlay bg-black/60 backdrop-blur-sm lg:hidden" onClick={() => setDrawer(false)} data-testid="nav-drawer-overlay" /> : null}
      <aside className={`tp-drawer flex flex-col border-white/8 bg-[#050607] px-4 py-5 lg:hidden ${drawer ? "tp-open" : ""}`} style={{ borderInlineEndWidth: 1 }} data-testid="owner-drawer">
        <div className="mb-2 flex justify-end">
          <button onClick={() => setDrawer(false)} className="rounded-lg p-1.5 text-white/60 hover:bg-white/5 hover:text-white" data-testid="nav-drawer-close"><X className="h-5 w-5" /></button>
        </div>
        <NavBody inDrawer />
      </aside>

      {/* Top bar (sticky, sits in content flow → offset by sidebar on desktop) */}
      <header className="sticky top-0 z-30 border-b border-white/8 bg-[#050607]/85 backdrop-blur-xl" data-testid="owner-nav">
        <div className="flex items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <div className="flex items-center gap-2.5">
            <button onClick={() => setDrawer(true)} className="rounded-lg p-1.5 text-white/70 hover:bg-white/5 hover:text-white lg:hidden" data-testid="nav-hamburger" aria-label={t("nav.menu")}><Menu className="h-5 w-5" /></button>
            <button onClick={() => navigate("/dashboard")} className="flex items-center gap-2 lg:hidden" data-testid="nav-brand-mobile" aria-label="TapPresence">
              <TpMark className="h-6 w-6" />
              <span className="text-[15px] font-semibold leading-none tracking-tight text-white">Tap<span className="text-[#D6A653]">Presence</span></span>
            </button>
            <div className="hidden items-center gap-2 lg:flex" data-testid="topbar-context">
              {isAdmin ? <ShieldCheck className="h-4 w-4 text-[#D6A653]" /> : isTeam ? <Building2 className="h-4 w-4 text-white/50" /> : <User className="h-4 w-4 text-white/50" />}
              <span className="text-sm font-medium text-white">{contextLabel}</span>
              <span className="rounded-full border border-white/12 bg-white/5 px-2 py-0.5 text-[10px] uppercase tracking-wider text-[#D6A653]/80">{roleBadge}</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <LanguageSwitcher />
            <NotificationBell />
            <button onClick={() => setScanOpen(true)} className="rounded-full border border-white/12 bg-white/5 p-2 text-white/70 transition-colors hover:text-white" title={t("nav.scanCard")} data-testid="nav-scan"><ScanLine className="h-4 w-4 text-[#D6A653]" /></button>
            <button onClick={() => navigate("/settings")} className="flex h-8 w-8 items-center justify-center rounded-full border border-white/12 bg-white/5 text-xs font-medium text-white/80 transition-colors hover:text-white" title={user?.name || t("nav.settings")} data-testid="nav-profile">
              {(user?.name || "?").trim().charAt(0).toUpperCase()}
            </button>
          </div>
        </div>
      </header>

      <ScanCardDialog open={scanOpen} onOpenChange={setScanOpen} cards={cards} onSaved={refresh} />
      <AnalyticsDialog card={analyticsCard} open={!!analyticsCard} onOpenChange={(v) => !v && setAnalyticsCard(null)} />
    </>
  );
};
