import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Loader2 } from "lucide-react";

// Landing target for the Google OAuth callback when it hands back a real session (existing/linked users).
export default function GoogleFinish() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { applyExternalSession } = useAuth();

  useEffect(() => {
    const err = params.get("google_error");
    const token = params.get("token");
    const refresh = params.get("refresh");
    (async () => {
      if (token) {
        const data = await applyExternalSession(token, refresh);
        const role = data?.user?.role;
        navigate(role === "SUPER_ADMIN" ? "/control" : "/dashboard", { replace: true });
        return;
      }
      navigate(`/login${err ? `?google_error=${encodeURIComponent(err)}` : ""}`, { replace: true });
    })();
    // eslint-disable-next-line
  }, []);

  return (
    <div className="aria-dark relative flex min-h-screen items-center justify-center bg-[#050607]" style={{ fontFamily: "'Outfit', sans-serif" }} data-testid="google-finish">
      <div className="flex flex-col items-center gap-3 text-white/70">
        <Loader2 className="h-8 w-8 animate-spin text-[#D6A653]" />
        <p className="text-sm">Signing you in…</p>
      </div>
    </div>
  );
}
