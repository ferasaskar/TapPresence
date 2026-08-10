import { useEffect, useState, useCallback } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { api } from "@/lib/api";
import { ProfileContext } from "@/context/ProfileContext";
import { getConsent } from "@/components/ConsentBanner";
import { TemplateRenderer } from "@/components/templates/TemplateRenderer";
import { useLocale } from "@/i18n/useLocale";
import { toast } from "sonner";
import { Loader2, Globe, Share2 } from "lucide-react";

const LANG_LABELS = { en: "EN", ar: "العربية", es: "ES", fr: "FR", de: "DE", pt: "PT" };
const RTL = ["ar"];

export default function PublicProfile() {
  const { slug } = useParams();
  const [searchParams] = useSearchParams();
  const { t } = useLocale();
  const [card, setCard] = useState(null);
  const [state, setState] = useState("loading");
  const [lang, setLang] = useState(searchParams.get("lang") || localStorage.getItem(`lang_${slug}`) || "");

  const track = useCallback(
    (type, key = "") => {
      // Respect the visitor's analytics consent: skip only when explicitly rejected.
      if (getConsent()?.analytics === false) return;
      api.post(`/cards/${slug}/track`, { type, key }).catch(() => {});
    },
    [slug]
  );

  const load = useCallback((l, first) => {
    api.get(`/cards/${slug}${l ? `?lang=${l}` : ""}`)
      .then((res) => {
        setCard(res.data);
        setState("ready");
        const id = res.data.identity || {};
        document.title = `${id.fullName || slug} — ${id.jobTitle || "TapPresence"}`;
        if (first) {
          track("view");
          if (searchParams.get("src") === "qr") track("scan");
        }
      })
      .catch(() => setState("notfound"));
  }, [slug]); // eslint-disable-line

  useEffect(() => { setState("loading"); load(lang, true); }, [slug]); // eslint-disable-line

  // Public-card visitors: mirror the displayed card language onto the document dir
  useEffect(() => {
    if (!card) return;
    const a = card._activeLang || (card._availableLangs || ["en"])[0];
    document.documentElement.dir = RTL.includes(a) ? "rtl" : "ltr";
  }, [card]);

  const changeLang = (l) => {
    setLang(l);
    localStorage.setItem(`lang_${slug}`, l);
    load(l, false);
  };

  const shareCard = async () => {
    const url = window.location.href.split("?")[0];
    const name = card?.identity?.fullName || slug;
    track("tap", "card_shared");
    if (navigator.share) {
      try { await navigator.share({ title: name, text: t("share.cardShareText"), url }); } catch {}
    } else {
      navigator.clipboard.writeText(url);
      toast.success(t("share.copied"));
    }
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
        <h1 className="font-serif text-4xl">{t("profileNotFound.title")}</h1>
        <p className="text-ink-soft">{t("profileNotFound.body")}</p>
      </div>
    );
  }

  const langs = card._availableLangs || ["en"];
  const active = card._activeLang || langs[0];
  const isRtl = RTL.includes(active);

  return (
    <ProfileContext.Provider value={{ track, publicView: true }}>
      <div data-testid="public-profile" dir={isRtl ? "rtl" : "ltr"}>
        <button onClick={shareCard} aria-label={t("share.native")} data-testid="public-share-btn"
          className="pointer-events-auto fixed right-3 top-3 z-50 flex h-9 w-9 items-center justify-center rounded-full border border-black/10 bg-white/70 text-ink shadow-sm backdrop-blur-md transition-transform hover:scale-105 active:scale-95">
          <Share2 className="h-4 w-4" />
        </button>
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
