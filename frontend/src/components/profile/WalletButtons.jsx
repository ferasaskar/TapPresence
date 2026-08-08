import { useState } from "react";
import { Wallet, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { useProfile } from "@/context/ProfileContext";
import { toast } from "sonner";

const V = {
  beige: { btn: "flex items-center justify-center gap-2 rounded-md border border-ivory-border bg-ivory-surface px-4 py-3.5 text-sm tracking-wide text-ink transition-colors duration-300 hover:border-[color:var(--ac,#B89973)]", style: undefined },
  black: { btn: "flex items-center justify-center gap-2 rounded-xl border px-4 py-3.5 text-sm tracking-wide text-neutral-200 transition-colors duration-300", style: { borderColor: "rgba(255,255,255,0.12)", backgroundColor: "#111112" } },
  future: { btn: "flex items-center justify-center gap-2 rounded-2xl border border-white/10 bg-white/[0.04] backdrop-blur-xl px-4 py-3.5 text-sm tracking-wide text-slate-200 transition-colors duration-300 hover:border-sky-400/50", style: undefined },
};

export const WalletButtons = ({ slug, variant = "beige", iconColor = "#B89973" }) => {
  const v = V[variant] || V.beige;
  const { track } = useProfile();
  const [busy, setBusy] = useState("");

  const add = async (platform) => {
    setBusy(platform);
    track?.("tap", `wallet_${platform}`);
    try {
      const { data } = await api.get(`/cards/${slug}/wallet/${platform}`);
      if (data.configured && data.pass_url) {
        window.open(data.pass_url, "_blank", "noopener");
      } else {
        toast(`${platform === "apple" ? "Apple" : "Google"} Wallet coming soon`, {
          description: "Wallet passes activate once the provider is connected.",
        });
      }
    } catch {
      toast.error("Could not open wallet pass");
    } finally {
      setBusy("");
    }
  };

  return (
    <div className="mt-4 grid grid-cols-2 gap-4" data-testid="wallet-buttons">
      <button onClick={() => add("apple")} disabled={busy === "apple"} className={v.btn} style={v.style} data-testid="wallet-apple">
        {busy === "apple" ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wallet className="w-4 h-4" style={{ color: iconColor }} strokeWidth={1.75} />}
        Apple Wallet
      </button>
      <button onClick={() => add("google")} disabled={busy === "google"} className={v.btn} style={v.style} data-testid="wallet-google">
        {busy === "google" ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wallet className="w-4 h-4" style={{ color: iconColor }} strokeWidth={1.75} />}
        Google Wallet
      </button>
    </div>
  );
};
