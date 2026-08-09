import { useEffect, useState, useCallback } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { api } from "@/lib/api";
import { ProfileContext } from "@/context/ProfileContext";
import { TemplateRenderer } from "@/components/templates/TemplateRenderer";
import { Loader2, Globe } from "lucide-react";

const LANG_LABELS = { en: "EN", ar: "العربية", es: "ES", fr: "FR", de: "DE", pt: "PT" };
const RTL = ["ar"];

export default function PublicProfile() {
  const { slug } = useParams();
  const [searchParams] = useSearchParams();
  const [card, setCard] = useState(null);
  const [state, setState] = useState("loading");
  const [lang, setLang] = useState(searchParams.get("lang") || localStorage.getItem(`lang_${slug}`) || "");

  const track = useCallback(
    (type, key = "") => { api.post(`/cards/${slug}/track`, { type, key }).catch(() => {}); },
    [slug]
  );

  const load = useCallback((l, first) => {
    api.get(`/cards/${slug}${l ? `?lang=${l}` : ""}`)
      .then((res) => {
        setCard(res.data);
        setState("ready");
        const id = res.data.identity || {};
        document.title = `${id.fullName || slug} — ${id.jobTitle || "ARIADNI ID"}`;
        if (first) {
          track("view");
          if (searchParams.get("src") === "qr") track("scan");
        }
      })
      .catch(() => setState("notfound"));
  }, [slug]); // eslint-disable-line

  useEffect(() => { setState("loading"); load(lang, true); }, [slug]); // eslint-disable-line

  const changeLang = (l) => {
    setLang(l);
    localStorage.setItem(`lang_${slug}`, l);
    load(l, false);
  };

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

  const langs = card._availableLangs || ["en"];
  const active = card._activeLang || langs[0];
  const isRtl = RTL.includes(active);

  return (
    <ProfileContext.Provider value={{ track, publicView: true }}>
      <div data-testid="public-profile" dir={isRtl ? "rtl" : "ltr"}>
        {langs.length > 1 && (
          <div className="pointer-events-none fixed top-3 z-50 flex w-full justify-center" data-testid="lang-switcher">
            <div className="pointer-events-auto flex items-center gap-1 rounded-full border border-black/10 bg-white/70 px-2 py-1 text-xs shadow-sm backdrop-blur-md">
              <Globe className="mx-1 h-3.5 w-3.5 opacity-60" />
              {langs.map((l) => (
                <button
                  key={l}
                  onClick={() => changeLang(l)}
                  data-testid={`lang-${l}`}
                  className={`rounded-full px-2.5 py-1 transition-colors ${active === l ? "bg-ink text-white" : "text-ink-soft hover:text-ink"}`}
                >
                  {LANG_LABELS[l] || l.toUpperCase()}
                </button>
              ))}
            </div>
          </div>
        )}
        <TemplateRenderer data={card} />
      </div>
    </ProfileContext.Provider>
  );
}
