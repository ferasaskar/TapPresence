import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { OwnerNav } from "@/components/admin/OwnerNav";
import { User, Mail, ShieldCheck, Globe, Clock, CreditCard, LogOut, Building2 } from "lucide-react";

const Row = ({ icon: Icon, label, value, testId }) => (
  <div className="flex items-center justify-between border-b border-white/8 py-3.5 last:border-0" data-testid={testId}>
    <span className="flex items-center gap-2.5 text-sm text-white/55"><Icon className="h-4 w-4 text-[#D6A653]" /> {label}</span>
    <span className="text-sm text-white">{value || "—"}</span>
  </div>
);

export default function Settings() {
  const { user, workspace, logout } = useAuth();
  const navigate = useNavigate();
  const [cardCount, setCardCount] = useState(null);
  const isAdmin = user?.role === "SUPER_ADMIN";

  useEffect(() => { api.get("/admin/cards").then(({ data }) => setCardCount(data.length)).catch(() => setCardCount(0)); }, []);

  return (
    <div className="aria-dark relative min-h-screen bg-[#050607] text-white" style={{ fontFamily: "'Outfit', sans-serif" }} data-testid="settings-page">
      <div className="grain-overlay" style={{ opacity: 0.04 }} />
      <OwnerNav active="settings" />

      <main className="relative mx-auto max-w-2xl px-4 py-8 sm:px-8">
        <h2 className="mb-1 text-2xl font-light tracking-tight text-white">Settings</h2>
        <p className="mb-6 text-sm text-white/45">Your account and workspace.</p>

        <div className="rounded-2xl border border-white/10 bg-[#0A0B0D] p-6" data-testid="settings-account">
          <p className="mb-2 text-xs uppercase tracking-wider text-[#D6A653]">Account</p>
          <Row icon={User} label="Name" value={user?.name} testId="settings-name" />
          <Row icon={Mail} label="Email" value={user?.email} testId="settings-email" />
          <Row icon={ShieldCheck} label="Role" value={isAdmin ? "Super Admin" : "Member"} testId="settings-role" />
          <Row icon={Building2} label="Workspace" value={workspace?.name} testId="settings-workspace" />
          <Row icon={Clock} label="Timezone" value={user?.timezone} testId="settings-timezone" />
          <Row icon={Globe} label="Language" value={user?.language?.toUpperCase()} testId="settings-language" />
          <Row icon={CreditCard} label="Your cards" value={cardCount === null ? "…" : String(cardCount)} testId="settings-cardcount" />
        </div>

        <div className="mt-5 flex flex-wrap gap-3">
          <button onClick={() => navigate("/admin")} className="inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/5 px-5 py-2.5 text-sm text-white/80 hover:text-white" data-testid="settings-manage-card"><CreditCard className="h-4 w-4 text-[#D6A653]" /> Manage my card</button>
          <button onClick={logout} className="inline-flex items-center gap-2 rounded-full border border-red-400/30 bg-red-500/10 px-5 py-2.5 text-sm text-red-300 hover:bg-red-500/20" data-testid="settings-logout"><LogOut className="h-4 w-4" /> Log out</button>
        </div>

        <p className="mt-6 text-xs text-white/35">Profile editing, password change and notification preferences are coming in a later phase.</p>
      </main>
    </div>
  );
}
