import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "@/lib/api";
import { TemplateRenderer } from "@/components/templates/TemplateRenderer";
import { Loader2 } from "lucide-react";

export default function PublicProfile() {
  const { slug } = useParams();
  const [card, setCard] = useState(null);
  const [state, setState] = useState("loading");

  useEffect(() => {
    let alive = true;
    setState("loading");
    api
      .get(`/cards/${slug}`)
      .then((res) => {
        if (!alive) return;
        setCard(res.data);
        setState("ready");
        const id = res.data.identity || {};
        document.title = `${id.fullName || slug} — ${id.jobTitle || "ARIADNI ID"}`;
      })
      .catch(() => alive && setState("notfound"));
    return () => { alive = false; };
  }, [slug]);

  if (state === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-ivory-bg" data-testid="profile-loading">
        <Loader2 className="w-6 h-6 animate-spin text-gold" />
      </div>
    );
  }

  if (state === "notfound") {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-ivory-bg text-ink px-6 text-center" data-testid="profile-notfound">
        <h1 className="font-serif text-4xl">Profile not found</h1>
        <p className="text-ink-soft">This card doesn't exist or hasn't been published yet.</p>
      </div>
    );
  }

  return (
    <div data-testid="public-profile">
      <TemplateRenderer data={card} />
    </div>
  );
}
