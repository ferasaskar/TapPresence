import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useLocale } from "@/i18n/useLocale";
import { OwnerNav } from "@/components/admin/OwnerNav";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Loader2, Users, UserPlus, ShieldCheck, CreditCard, Trash2, Mail } from "lucide-react";
import { toast } from "sonner";

const ROLES = ["WORKSPACE_ADMIN", "MANAGER", "MEMBER"];
const ADMIN_ROLES = ["WORKSPACE_OWNER", "WORKSPACE_ADMIN", "MANAGER"];

export default function Team() {
  const { user } = useAuth();
  const { t } = useLocale();
  const [ws, setWs] = useState(undefined); // undefined=loading, null=none
  const [members, setMembers] = useState([]);
  const [cards, setCards] = useState([]);
  const [denied, setDenied] = useState(false);
  const [inviteOpen, setInviteOpen] = useState(false);
  const [form, setForm] = useState({ email: "", name: "", role: "MEMBER" });

  const loadMembers = useCallback((wid) => {
    api.get(`/workspaces/${wid}/members`)
      .then(({ data }) => setMembers(data))
      .catch((e) => { if (e?.response?.status === 403) setDenied(true); });
  }, []);

  useEffect(() => {
    api.get("/workspaces/me").then(({ data }) => {
      if (!data || data.length === 0) { setWs(null); return; }
      const owned = data.find((w) => w.owner_id === user?.id);
      const primary = owned || data[0];
      setWs(primary);
      loadMembers(primary.id);
    }).catch(() => setWs(null));
    api.get("/admin/cards").then(({ data }) => setCards(data)).catch(() => {});
  }, [user, loadMembers]);

  const cardCount = (uid) => cards.filter((c) => c.owner_user_id === uid).length;

  const invite = async () => {
    if (!form.email.trim()) return;
    try {
      await api.post(`/workspaces/${ws.id}/members`, form);
      toast.success(t("team.inviteSent"));
      setInviteOpen(false); setForm({ email: "", name: "", role: "MEMBER" });
      loadMembers(ws.id);
    } catch { toast.error("Could not invite"); }
  };

  const changeRole = async (uid, role) => {
    try { await api.patch(`/workspaces/${ws.id}/members/${uid}`, { role }); toast.success(t("team.memberUpdated")); loadMembers(ws.id); }
    catch { toast.error("Update failed"); }
  };
  const toggleStatus = async (m) => {
    const status = m.status === "deactivated" ? "active" : "deactivated";
    try { await api.patch(`/workspaces/${ws.id}/members/${m.user_id}`, { status }); toast.success(t("team.memberUpdated")); loadMembers(ws.id); }
    catch { toast.error("Update failed"); }
  };
  const remove = async (uid) => {
    if (!window.confirm(t("team.confirmRemove"))) return;
    try { await api.delete(`/workspaces/${ws.id}/members/${uid}`); toast.success(t("team.memberRemoved")); loadMembers(ws.id); }
    catch (e) { toast.error(e?.response?.data?.detail || "Remove failed"); }
  };

  const isOwner = (uid) => ws?.owner_id === uid;

  return (
    <div className="aria-dark relative min-h-screen bg-[#050607] text-white" style={{ fontFamily: "'Outfit', sans-serif" }} data-testid="team-page">
      <div className="grain-overlay" style={{ opacity: 0.04 }} />
      <OwnerNav active="team" />
      <main className="relative mx-auto max-w-5xl px-4 py-8 sm:px-8">
        <div className="mb-6 flex items-end justify-between gap-3">
          <div>
            <h2 className="flex items-center gap-2 text-2xl font-light tracking-tight text-white"><Users className="h-5 w-5 text-[#D6A653]" /> {t("team.title")}</h2>
            <p className="mt-1 text-sm text-white/45">{t("team.subtitle")}</p>
          </div>
          {ws && !denied && (
            <button onClick={() => setInviteOpen(true)} data-testid="team-invite-open" className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-[#D6A653] px-4 py-2 text-sm font-medium text-[#050607] hover:bg-[#E8B764]">
              <UserPlus className="h-4 w-4" /> {t("team.invite")}
            </button>
          )}
        </div>

        {ws === undefined ? (
          <div className="flex justify-center py-24"><Loader2 className="h-6 w-6 animate-spin text-[#D6A653]" /></div>
        ) : ws === null ? (
          <div className="rounded-2xl border border-dashed border-white/12 py-24 text-center text-white/55" data-testid="team-no-workspace">{t("team.noWorkspace")}</div>
        ) : denied ? (
          <div className="flex flex-col items-center rounded-2xl border border-dashed border-white/12 py-24 text-center" data-testid="team-denied">
            <ShieldCheck className="mb-3 h-8 w-8 text-white/25" />
            <p className="text-white/60">{t("team.adminOnly")}</p>
          </div>
        ) : (
          <>
            <div className="mb-5 flex flex-wrap items-center gap-3 rounded-2xl border border-white/10 bg-[#0A0B0D] p-4" data-testid="team-workspace">
              <span className="text-base font-medium text-white">{ws.name}</span>
              <span className="rounded-full border border-[#D6A653]/30 bg-[#D6A653]/10 px-2.5 py-0.5 text-[11px] uppercase tracking-wide text-[#D6A653]">{t("team.plan")}: {ws.plan || "trial"}</span>
              <span className="text-xs text-white/45">{t("team.seats", { count: members.length })}</span>
            </div>

            <div className="overflow-hidden rounded-2xl border border-white/10 bg-[#0A0B0D]">
              <div className="hidden grid-cols-12 gap-2 border-b border-white/8 px-5 py-3 text-[11px] uppercase tracking-wide text-white/40 sm:grid">
                <div className="col-span-4">{t("team.members")}</div>
                <div className="col-span-3">{t("team.role")}</div>
                <div className="col-span-2">{t("team.assignedCards")}</div>
                <div className="col-span-3 text-right">{t("team.status")}</div>
              </div>
              <ul className="divide-y divide-white/6">
                {members.map((m) => {
                  const u = m.user || {};
                  return (
                    <li key={m.user_id} className="grid grid-cols-1 gap-3 px-5 py-4 sm:grid-cols-12 sm:items-center" data-testid={`member-row-${m.user_id}`}>
                      <div className="min-w-0 sm:col-span-4">
                        <p className="truncate text-sm font-medium text-white">{u.name || u.email || "—"} {isOwner(m.user_id) && <span className="ml-1 text-[10px] uppercase tracking-wide text-[#D6A653]">· {t("team.owner")}</span>}</p>
                        <p className="flex items-center gap-1 truncate text-xs text-white/45"><Mail className="h-3 w-3" /> {u.email}</p>
                      </div>
                      <div className="sm:col-span-3">
                        {isOwner(m.user_id) ? (
                          <span className="text-xs text-white/55">{m.role}</span>
                        ) : (
                          <Select value={ROLES.includes(m.role) ? m.role : "MEMBER"} onValueChange={(v) => changeRole(m.user_id, v)}>
                            <SelectTrigger className="h-8 w-40 border-white/12 bg-white/[0.03] text-xs text-white" data-testid={`member-role-${m.user_id}`}><SelectValue /></SelectTrigger>
                            <SelectContent className="aria-pop border-white/10 bg-[#0A0B0D] text-white">
                              {ROLES.map((r) => <SelectItem key={r} value={r} className="text-xs">{r.replace("WORKSPACE_", "").replace("_", " ")}</SelectItem>)}
                            </SelectContent>
                          </Select>
                        )}
                      </div>
                      <div className="flex items-center gap-1.5 text-sm text-white/70 sm:col-span-2"><CreditCard className="h-3.5 w-3.5 text-[#D6A653]" /> {cardCount(m.user_id)}</div>
                      <div className="flex items-center justify-start gap-2 sm:col-span-3 sm:justify-end">
                        <span className={`rounded-full px-2.5 py-0.5 text-[11px] ${m.status === "deactivated" ? "border border-white/12 bg-white/5 text-white/45" : m.status === "invited" ? "border border-[#D6A653]/30 bg-[#D6A653]/10 text-[#D6A653]" : "border border-emerald-400/30 bg-emerald-400/10 text-emerald-300"}`}>
                          {t(`team.${m.status === "deactivated" ? "deactivated" : m.status === "invited" ? "invited" : "active"}`)}
                        </span>
                        {!isOwner(m.user_id) && (
                          <>
                            <button onClick={() => toggleStatus(m)} data-testid={`member-toggle-${m.user_id}`} className="rounded-md border border-white/12 px-2 py-1 text-[11px] text-white/70 hover:text-white">
                              {m.status === "deactivated" ? t("team.activate") : t("team.deactivate")}
                            </button>
                            <button onClick={() => remove(m.user_id)} data-testid={`member-remove-${m.user_id}`} className="rounded-md border border-red-500/25 p-1.5 text-red-300/80 hover:bg-red-500/10"><Trash2 className="h-3.5 w-3.5" /></button>
                          </>
                        )}
                      </div>
                    </li>
                  );
                })}
              </ul>
            </div>
          </>
        )}
      </main>

      <Dialog open={inviteOpen} onOpenChange={setInviteOpen}>
        <DialogContent className="aria-dark border-white/10 bg-[#0A0B0D] text-white sm:max-w-md" data-testid="invite-dialog">
          <DialogHeader><DialogTitle className="flex items-center gap-2 text-white"><UserPlus className="h-4 w-4 text-[#D6A653]" /> {t("team.inviteTitle")}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div>
              <label className="mb-1 block text-xs text-white/50">{t("team.email")}</label>
              <input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} data-testid="invite-email" className="w-full rounded-lg border border-white/12 bg-white/[0.03] px-3 py-2.5 text-sm text-white" placeholder="name@company.com" />
            </div>
            <div>
              <label className="mb-1 block text-xs text-white/50">{t("team.name")}</label>
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="invite-name" className="w-full rounded-lg border border-white/12 bg-white/[0.03] px-3 py-2.5 text-sm text-white" />
            </div>
            <div>
              <label className="mb-1 block text-xs text-white/50">{t("team.role")}</label>
              <Select value={form.role} onValueChange={(v) => setForm({ ...form, role: v })}>
                <SelectTrigger className="w-full border-white/12 bg-white/[0.03] text-sm text-white" data-testid="invite-role"><SelectValue /></SelectTrigger>
                <SelectContent className="aria-pop border-white/10 bg-[#0A0B0D] text-white">
                  {ROLES.map((r) => <SelectItem key={r} value={r}>{r.replace("WORKSPACE_", "").replace("_", " ")}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <button onClick={invite} data-testid="invite-submit" className="w-full rounded-lg bg-[#D6A653] py-2.5 text-sm font-medium text-[#050607] hover:bg-[#E8B764]">{t("team.sendInvite")}</button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
