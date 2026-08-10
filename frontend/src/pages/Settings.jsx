import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useLocale } from "@/i18n/useLocale";
import { OwnerNav } from "@/components/admin/OwnerNav";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { User, Mail, ShieldCheck, Globe, Clock, CreditCard, LogOut, Building2, Download, Trash2, Shield, Loader2 } from "lucide-react";

const Row = ({ icon: Icon, label, value, testId }) => (
  <div className="flex items-center justify-between border-b border-white/8 py-3.5 last:border-0" data-testid={testId}>
    <span className="flex items-center gap-2.5 text-sm text-white/55"><Icon className="h-4 w-4 text-[#D4AF37]" /> {label}</span>
    <span className="text-sm text-white">{value || "—"}</span>
  </div>
);

export default function Settings() {
  const { user, workspace, logout } = useAuth();
  const { t } = useLocale();
  const navigate = useNavigate();
  const [cardCount, setCardCount] = useState(null);
  const [exporting, setExporting] = useState(false);
  const [delOpen, setDelOpen] = useState(false);
  const [confirmText, setConfirmText] = useState("");
  const [deleting, setDeleting] = useState(false);
  const isAdmin = user?.role === "SUPER_ADMIN";

  useEffect(() => { api.get("/admin/cards").then(({ data }) => setCardCount(data.length)).catch(() => setCardCount(0)); }, []);

  const exportData = async () => {
    setExporting(true);
    try {
      const { data } = await api.get("/account/export");
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `tappresence-data-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success(t("dataRights.exported"));
    } catch (e) {
      toast.error(e.response?.data?.detail || "Export failed");
    } finally { setExporting(false); }
  };

  const deleteAccount = async () => {
    setDeleting(true);
    try {
      await api.delete("/account");
      toast.success(t("dataRights.deleted"));
      logout();
    } catch (e) {
      toast.error(e.response?.data?.detail || t("dataRights.deleteFailed"));
      setDeleting(false);
    }
  };

  return (
    <div className="aria-dark relative min-h-screen bg-[#0B0D12] text-white" style={{ fontFamily: "'Outfit', sans-serif" }} data-testid="settings-page">
      <div className="grain-overlay" style={{ opacity: 0.04 }} />
      <OwnerNav active="settings" />

      <main className="relative mx-auto max-w-2xl px-4 py-8 sm:px-8">
        <h2 className="mb-1 text-2xl font-light tracking-tight text-white">{t("settings.title")}</h2>
        <p className="mb-6 text-sm text-white/45">{t("settings.subtitle")}</p>

        <div className="rounded-2xl border border-white/10 bg-[#11121A] p-6" data-testid="settings-account">
          <p className="mb-2 text-xs uppercase tracking-wider text-[#D4AF37]">{t("settings.account")}</p>
          <Row icon={User} label={t("settings.name")} value={user?.name} testId="settings-name" />
          <Row icon={Mail} label={t("settings.email")} value={user?.email} testId="settings-email" />
          <Row icon={ShieldCheck} label={t("settings.role")} value={isAdmin ? t("nav.superAdmin") : t("nav.member")} testId="settings-role" />
          <Row icon={Building2} label={t("settings.workspace")} value={workspace?.name} testId="settings-workspace" />
          <Row icon={Clock} label={t("settings.timezone")} value={user?.timezone} testId="settings-timezone" />
          <Row icon={Globe} label={t("settings.language")} value={user?.language?.toUpperCase()} testId="settings-language" />
          <Row icon={CreditCard} label={t("settings.cards")} value={cardCount === null ? "…" : String(cardCount)} testId="settings-cardcount" />
        </div>

        {/* Data & privacy */}
        <div className="mt-5 rounded-2xl border border-white/10 bg-[#11121A] p-6" data-testid="settings-data-privacy">
          <p className="mb-4 flex items-center gap-2 text-xs uppercase tracking-wider text-[#D4AF37]"><Shield className="h-3.5 w-3.5" /> {t("dataRights.section")}</p>

          <div className="flex flex-col gap-3 border-b border-white/8 pb-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-medium text-white">{t("dataRights.exportTitle")}</p>
              <p className="mt-0.5 text-sm text-white/50">{t("dataRights.exportDesc")}</p>
            </div>
            <button onClick={exportData} disabled={exporting} className="inline-flex shrink-0 items-center justify-center gap-2 rounded-full border border-white/15 bg-white/5 px-5 py-2.5 text-sm text-white/85 transition-colors hover:bg-white/10 disabled:opacity-60" data-testid="settings-export-btn">
              {exporting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4 text-[#D4AF37]" />} {exporting ? t("dataRights.exporting") : t("dataRights.exportBtn")}
            </button>
          </div>

          <div className="flex flex-col gap-3 pt-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-medium text-white">{t("dataRights.deleteTitle")}</p>
              <p className="mt-0.5 text-sm text-white/50">{t("dataRights.deleteDesc")}</p>
            </div>
            <button onClick={() => { setConfirmText(""); setDelOpen(true); }} className="inline-flex shrink-0 items-center justify-center gap-2 rounded-full border border-red-400/30 bg-red-500/10 px-5 py-2.5 text-sm text-red-300 transition-colors hover:bg-red-500/20" data-testid="settings-delete-btn">
              <Trash2 className="h-4 w-4" /> {t("dataRights.deleteBtn")}
            </button>
          </div>

          <Link to="/privacy-center" className="mt-4 inline-block text-sm text-[#D4AF37] hover:underline" data-testid="settings-privacy-center">{t("landing.footer.privacyChoices")}</Link>
        </div>

        <div className="mt-5 flex flex-wrap gap-3">
          <button onClick={() => navigate("/admin")} className="inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/5 px-5 py-2.5 text-sm text-white/80 hover:text-white" data-testid="settings-manage-card"><CreditCard className="h-4 w-4 text-[#D4AF37]" /> {t("settings.manageCard")}</button>
          <button onClick={logout} className="inline-flex items-center gap-2 rounded-full border border-red-400/30 bg-red-500/10 px-5 py-2.5 text-sm text-red-300 hover:bg-red-500/20" data-testid="settings-logout"><LogOut className="h-4 w-4" /> {t("settings.logout")}</button>
        </div>
      </main>

      <Dialog open={delOpen} onOpenChange={setDelOpen}>
        <DialogContent className="aria-dark max-w-md border-white/10 bg-[#11121A] text-white" data-testid="delete-account-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-300"><Trash2 className="h-5 w-5" /> {t("dataRights.confirmTitle")}</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-white/60">{t("dataRights.confirmBody")}</p>
          <div className="mt-2">
            <label className="text-xs text-white/50">{t("dataRights.confirmPrompt")}</label>
            <Input value={confirmText} onChange={(e) => setConfirmText(e.target.value)} className="mt-1" data-testid="delete-confirm-input" />
          </div>
          <DialogFooter className="gap-2 sm:gap-2">
            <button onClick={() => setDelOpen(false)} className="rounded-full border border-white/15 px-5 py-2.5 text-sm text-white/80 hover:bg-white/5" data-testid="delete-cancel">{t("dataRights.cancel")}</button>
            <button onClick={deleteAccount} disabled={confirmText !== t("dataRights.confirmWord") || deleting} className="inline-flex items-center gap-2 rounded-full bg-red-500 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-red-600 disabled:cursor-not-allowed disabled:opacity-40" data-testid="delete-confirm-btn">
              {deleting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />} {deleting ? t("dataRights.deleting") : t("dataRights.confirmBtn")}
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
