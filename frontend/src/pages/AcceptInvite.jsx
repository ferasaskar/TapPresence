import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Loader2, Users, ShieldCheck } from "lucide-react";
import { toast } from "sonner";

export default function AcceptInvite() {
  const { token } = useParams();
  const navigate = useNavigate();
  const { applyExternalSession } = useAuth();
  const [info, setInfo] = useState(null);
  const [err, setErr] = useState("");
  const [form, setForm] = useState({ name: "", password: "" });
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get(`/invites/${token}`)
      .then((r) => { setInfo(r.data); setForm((f) => ({ ...f, name: r.data.name || "" })); })
      .catch((e) => setErr(e?.response?.data?.detail || "This invitation is no longer valid."));
  }, [token]);

  const accept = async () => {
    if (!form.password || form.password.length < 8) { toast.error("Password must be at least 8 characters"); return; }
    setBusy(true);
    try {
      const { data } = await api.post(`/invites/${token}/accept`, { password: form.password, name: form.name });
      await applyExternalSession(data.token, data.refresh_token);
      toast.success("Welcome to the team!");
      navigate("/dashboard");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Could not accept the invitation");
    } finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen bg-[#050607] text-white flex items-center justify-center px-4" data-testid="accept-invite-page">
      <div className="w-full max-w-md rounded-2xl border border-white/10 bg-[#0d0f13] p-8">
        <div className="mb-6 flex items-center gap-2">
          <span className="text-xl font-bold">Tap<span className="text-[#D6A653]">Presence</span></span>
        </div>
        {err ? (
          <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-6 text-center text-sm text-amber-200" data-testid="invite-error">{err}</div>
        ) : !info ? (
          <div className="flex justify-center py-10"><Loader2 className="h-6 w-6 animate-spin text-[#D6A653]" /></div>
        ) : info.expired ? (
          <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-6 text-center text-sm text-amber-200" data-testid="invite-expired">
            This invitation has expired. Please ask your team admin to re-invite you.
          </div>
        ) : (
          <>
            <div className="mb-5 flex items-center gap-3 rounded-lg border border-white/10 bg-white/[0.03] px-4 py-3">
              <Users className="h-5 w-5 text-[#D6A653]" />
              <div className="text-sm">
                <p className="text-white/90">You're invited to <b>{info.workspace_name}</b></p>
                <p className="text-white/45">{info.email} · {info.role}</p>
              </div>
            </div>
            <label className="mb-1 block text-[11px] uppercase tracking-wider text-white/40">Your name</label>
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="invite-name"
              className="mb-4 w-full rounded-lg border border-white/12 bg-white/[0.03] px-3 py-2.5 text-sm text-white" placeholder="Your name" />
            <label className="mb-1 block text-[11px] uppercase tracking-wider text-white/40">Create a password</label>
            <input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} data-testid="invite-password"
              className="mb-5 w-full rounded-lg border border-white/12 bg-white/[0.03] px-3 py-2.5 text-sm text-white" placeholder="At least 8 characters" />
            <button onClick={accept} disabled={busy} data-testid="invite-accept-btn"
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#D6A653] px-4 py-3 text-sm font-semibold text-[#050607] hover:bg-[#E8B764] disabled:opacity-50">
              {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <><ShieldCheck className="h-4 w-4" /> Accept & join team</>}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
