import { useState } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2 } from "lucide-react";

const fmtErr = (d) => typeof d === "string" ? d : Array.isArray(d) ? d.map((e) => e?.msg || "").join(" ") : "Something went wrong.";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const intent = params.get("intent");
  const [f, setF] = useState({ name: "", email: "", password: "", workspace_name: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const set = (k) => (e) => setF((s) => ({ ...s, [k]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      await register(f);
      navigate("/admin");
    } catch (err) {
      setError(fmtErr(err.response?.data?.detail) || err.message);
    } finally { setLoading(false); }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-ivory-bg px-6 font-sans">
      <div className="w-full max-w-sm">
        <Link to="/" className="font-serif text-2xl tracking-tight text-ink">ARIADNI <span className="text-[#B89973]">ID</span></Link>
        <h1 className="mt-6 font-serif text-3xl tracking-tight text-ink">Create your ID</h1>
        <p className="mt-1 text-sm text-ink-soft">
          {intent === "nfc" ? "Set up your account, then order & activate your NFC card." : intent === "team" ? "Start your workspace and invite your team." : "Publish a premium profile in minutes."}
        </p>
        <form onSubmit={submit} className="mt-6 space-y-4">
          <div className="space-y-2"><Label>Full name</Label><Input value={f.name} onChange={set("name")} data-testid="register-name" required /></div>
          <div className="space-y-2"><Label>Work email</Label><Input type="email" value={f.email} onChange={set("email")} data-testid="register-email" required /></div>
          <div className="space-y-2"><Label>Password</Label><Input type="password" value={f.password} onChange={set("password")} data-testid="register-password" required minLength={6} /></div>
          <div className="space-y-2"><Label>Workspace / company (optional)</Label><Input value={f.workspace_name} onChange={set("workspace_name")} data-testid="register-workspace" /></div>
          {error ? <p className="text-sm text-red-600" data-testid="register-error">{error}</p> : null}
          <Button type="submit" className="w-full" disabled={loading} data-testid="register-submit">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Create account"}
          </Button>
        </form>
        <p className="mt-4 text-sm text-ink-soft">Already have an account? <Link to="/login" className="text-ink underline">Sign in</Link></p>
      </div>
    </div>
  );
}
