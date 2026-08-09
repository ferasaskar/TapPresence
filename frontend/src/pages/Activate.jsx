import { useEffect, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Nfc, Loader2, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";

export default function Activate() {
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const { user, ready } = useAuth();
  const navigate = useNavigate();
  const [cards, setCards] = useState([]);
  const [selected, setSelected] = useState("");
  const [lookup, setLookup] = useState(null);
  const [done, setDone] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (token) api.get(`/nfc/lookup/${token}`).then((r) => setLookup(r.data)).catch(() => setLookup({ error: true }));
  }, [token]);

  useEffect(() => {
    if (ready && !user) { navigate(`/login?next=/activate?token=${token}`); return; }
    if (user) api.get("/admin/cards").then((r) => setCards(r.data)).catch(() => {});
  }, [ready, user]); // eslint-disable-line

  const activate = async () => {
    if (!selected) { toast.error("Choose a card to link"); return; }
    setLoading(true);
    try {
      await api.post("/nfc/activate", { token, card_id: selected });
      setDone(true);
      toast.success("NFC card activated");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Activation failed");
    } finally { setLoading(false); }
  };

  return (
    <div className="aria-dark relative flex min-h-screen items-center justify-center overflow-hidden bg-[#050607] px-6" style={{ fontFamily: "'Outfit', sans-serif" }}>
      <div className="grain-overlay" style={{ opacity: 0.05 }} />
      <div className="aria-gold-radial pointer-events-none absolute inset-0" />
      <div className="relative w-full max-w-md rounded-2xl border border-white/10 bg-white/[0.04] p-8 text-center backdrop-blur-xl shadow-[0_30px_80px_rgba(0,0,0,0.6)]">
        <span className="relative mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-full" style={{ background: "rgba(214,166,83,0.12)", boxShadow: "0 0 32px rgba(214,166,83,0.3)" }}>
          <span className="absolute inset-0 animate-ping rounded-full" style={{ background: "rgba(214,166,83,0.15)" }} />
          <Nfc className="relative h-8 w-8 text-[#D6A653]" />
        </span>
        {done ? (
          <>
            <CheckCircle2 className="mx-auto mb-2 h-10 w-10 text-emerald-400" />
            <h1 className="text-2xl font-medium tracking-tight text-white">Card activated</h1>
            <p className="mt-2 text-sm text-white/50">Every tap now opens your selected profile.</p>
          </>
        ) : (
          <>
            <h1 className="text-2xl font-medium tracking-tight text-white">Activate your NFC card</h1>
            <p className="mt-2 text-xs text-white/40" data-testid="activate-token">Token: {token || "missing"}</p>
            {lookup?.assigned ? <p className="mt-2 text-xs text-[#D6A653]">This card is already linked — activating will relink it.</p> : null}
            <div className="mt-6 text-left">
              <Select value={selected} onValueChange={setSelected}>
                <SelectTrigger data-testid="activate-card-select"><SelectValue placeholder="Choose a card to link" /></SelectTrigger>
                <SelectContent className="aria-pop">
                  {cards.map((c) => <SelectItem key={c.id} value={c.id}>{c.identity?.fullName || c.slug} · /{c.slug}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <Button onClick={activate} className="mt-5 w-full rounded-full bg-[#D6A653] font-medium text-[#050607] transition-all hover:bg-[#E8B764] hover:shadow-[0_0_18px_rgba(214,166,83,0.35)] active:scale-[0.98]" disabled={loading || !token} data-testid="activate-submit">
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Activate card"}
            </Button>
          </>
        )}
      </div>
    </div>
  );
}
