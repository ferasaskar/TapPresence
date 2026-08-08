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
    <div className="flex min-h-screen items-center justify-center bg-ivory-bg px-6 font-sans">
      <div className="w-full max-w-md rounded-xl border border-ivory-border bg-white p-8 text-center">
        <span className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full" style={{ background: "rgba(184,153,115,0.12)" }}>
          <Nfc className="w-7 h-7 text-[#B89973]" />
        </span>
        {done ? (
          <>
            <CheckCircle2 className="mx-auto mb-2 w-10 h-10 text-green-600" />
            <h1 className="font-serif text-3xl tracking-tight text-ink">Card activated</h1>
            <p className="mt-2 text-sm text-ink-soft">Every tap now opens your selected profile.</p>
          </>
        ) : (
          <>
            <h1 className="font-serif text-3xl tracking-tight text-ink">Activate your NFC card</h1>
            <p className="mt-2 text-sm text-ink-soft" data-testid="activate-token">Token: {token || "missing"}</p>
            {lookup?.assigned ? <p className="mt-2 text-xs text-amber-600">This card is already linked — activating will relink it.</p> : null}
            <div className="mt-6 text-left">
              <Select value={selected} onValueChange={setSelected}>
                <SelectTrigger data-testid="activate-card-select"><SelectValue placeholder="Choose a card to link" /></SelectTrigger>
                <SelectContent>
                  {cards.map((c) => <SelectItem key={c.id} value={c.id}>{c.identity?.fullName || c.slug} · /{c.slug}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <Button onClick={activate} className="mt-5 w-full" disabled={loading || !token} data-testid="activate-submit">
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Activate card"}
            </Button>
          </>
        )}
      </div>
    </div>
  );
}
