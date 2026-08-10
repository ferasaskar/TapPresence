import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, resolveImg } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { OwnerNav } from "@/components/admin/OwnerNav";
import { AnalyticsOverview } from "@/components/admin/AnalyticsOverview";
import { OnboardingChecklist } from "@/components/admin/OnboardingChecklist";
import { ReferralNudge } from "@/components/admin/ReferralNudge";
import { useLocale } from "@/i18n/useLocale";
import { Loader2, Eye, QrCode, MousePointerClick, Inbox, Pencil, ExternalLink, Share2, CalendarDays, Plus, Clock, User, CheckCircle2, CircleDot } from "lucide-react";
import { toast } from "sonner";

const Stat = ({ icon: Icon, label, value, testId }) => (
  <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4" data-testid={testId}>
    <Icon className="mb-2 h-4 w-4 text-[#D6A653]" />
    <p className="text-2xl font-semibold text-white">{value ?? "—"}</p>
    <p className="text-[11px] uppercase tracking-wide text-white/45">{label}</p>
  </div>
);

const Quick = ({ icon: Icon, label, onClick, testId }) => (
  <button onClick={onClick} data-testid={testId} className="flex items-center gap-2 rounded-xl border border-white/12 bg-white/[0.02] px-4 py-3 text-sm text-white/80 transition-all hover:border-[#D6A653]/50 hover:text-white">
    <Icon className="h-4 w-4 text-[#D6A653]" /> {label}
  </button>
);

export default function Home() {
  const { user } = useAuth();
  const { t, formatDateTime } = useLocale();
  const navigate = useNavigate();
  const [cards, setCards] = useState(null);
  const [stats, setStats] = useState(null);
  const [newLeads, setNewLeads] = useState(0);
  const [meetings, setMeetings] = useState([]);
  const [overview, setOverview] = useState(null);

  useEffect(() => {
    api.get("/admin/cards").then(({ data }) => {
      setCards(data);
      if (data[0]) api.get(`/admin/cards/${data[0].id}/analytics`).then((r) => setStats(r.data)).catch(() => setStats({}));
      else setStats({});
    }).catch(() => { setCards([]); setStats({}); });
    api.get("/admin/leads").then(({ data }) => setNewLeads(data.filter((l) => !l.read).length)).catch(() => {});
    api.get("/admin/meetings", { params: { filter: "upcoming" } }).then(({ data }) => setMeetings(data)).catch(() => {});
    api.get("/admin/analytics/overview", { params: { days: 30 } }).then(({ data }) => setOverview(data)).catch(() => {});
  }, []);

  const primary = cards?.[0];
  const share = async () => {
    const url = `${window.location.origin}/${primary.slug}`;
    if (navigator.share) { try { await navigator.share({ title: primary.identity?.fullName, url }); } catch (_) {} }
    else { try { await navigator.clipboard.writeText(url); toast.success(t("home.linkCopied")); } catch { toast.error("Could not copy"); } }
  };

  return (
    <div className="aria-dark relative min-h-screen bg-[#050607] text-white" style={{ fontFamily: "'Outfit', sans-serif" }} data-testid="home-page">
      <div className="grain-overlay" style={{ opacity: 0.04 }} />
      <OwnerNav active="home" />

      <main className="relative mx-auto max-w-7xl px-4 py-8 sm:px-8">
        <div className="mb-6">
          <h2 className="text-2xl font-light tracking-tight text-white">{user?.name ? t("home.welcome", { name: user.name.split(" ")[0] }) : t("home.welcomeNoName")}</h2>
          <p className="mt-1 text-sm text-white/45">{t("home.subtitle")}</p>
        </div>

        {cards !== null ? <div className="mb-6"><ReferralNudge /></div> : null}

        {cards === null ? (
          <div className="flex justify-center py-24"><Loader2 className="h-6 w-6 animate-spin text-[#D6A653]" /></div>
        ) : cards.length === 0 ? (
          <div className="flex flex-col items-center rounded-2xl border border-dashed border-white/12 py-24 text-center" data-testid="home-empty">
            <p className="text-white/60">{t("home.noCard")}</p>
            <button onClick={() => navigate("/templates")} className="mt-4 inline-flex items-center gap-1.5 rounded-full bg-[#D6A653] px-5 py-2.5 text-sm font-medium text-[#050607] hover:bg-[#E8B764]" data-testid="home-create-card"><Plus className="h-4 w-4" /> {t("home.createFirst")}</button>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            {/* Left: card + quick actions */}
            <div className="lg:col-span-1">
              <div className="rounded-2xl border border-white/10 bg-[#0A0B0D] p-5" data-testid="home-card">
                <div className="flex items-center gap-3">
                  <div className="h-14 w-14 overflow-hidden rounded-full border border-white/10 bg-white/5">
                    {primary.identity?.profilePhoto ? <img src={resolveImg(primary.identity.profilePhoto)} alt="" className="h-full w-full object-cover" /> : null}
                  </div>
                  <div className="min-w-0">
                    <h3 className="truncate text-lg font-medium text-white">{primary.identity?.fullName || primary.slug}</h3>
                    <p className="truncate text-sm text-white/55">{primary.identity?.jobTitle}</p>
                  </div>
                </div>
                <div className="mt-3 flex items-center gap-2">
                  <span className={primary.status === "published"
                    ? "inline-flex items-center gap-1 rounded-full border border-emerald-400/30 bg-emerald-400/10 px-2.5 py-0.5 text-[11px] font-medium text-emerald-300"
                    : "inline-flex items-center gap-1 rounded-full border border-white/12 bg-white/5 px-2.5 py-0.5 text-[11px] text-white/60"} data-testid="home-status">
                    {primary.status === "published" ? <CheckCircle2 className="h-3 w-3" /> : <CircleDot className="h-3 w-3" />} {primary.status === "published" ? t("home.published") : t("home.draft")}
                  </span>
                  <span className="text-xs text-[#D6A653]/80">/{primary.slug}</span>
                </div>

                <div className="mt-5 grid grid-cols-2 gap-2">
                  <Quick icon={Pencil} label={t("home.editCard")} onClick={() => navigate("/admin")} testId="quick-edit" />
                  <Quick icon={ExternalLink} label={t("home.viewPublic")} onClick={() => window.open(`/${primary.slug}`, "_blank")} testId="quick-view" />
                  <Quick icon={Share2} label={t("home.shareCard")} onClick={share} testId="quick-share" />
                  <Quick icon={Inbox} label={t("home.viewLeads")} onClick={() => navigate("/leads")} testId="quick-leads" />
                  <Quick icon={CalendarDays} label={t("home.meetings")} onClick={() => navigate("/meetings")} testId="quick-meetings" />
                  {cards.length > 1 ? <Quick icon={Plus} label={t("home.cardsCount", { count: cards.length })} onClick={() => navigate("/admin")} testId="quick-allcards" /> : <Quick icon={Plus} label={t("home.newCard")} onClick={() => navigate("/templates")} testId="quick-newcard" />}
                </div>
              </div>
            </div>

            {/* Right: stats + upcoming */}
            <div className="space-y-6 lg:col-span-2">
              <OnboardingChecklist primary={primary} overview={overview} newLeads={newLeads} onNavigate={navigate} />
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4" data-testid="home-stats">
                <Stat icon={Eye} label={t("home.views")} value={stats?.views} testId="home-views" />
                <Stat icon={MousePointerClick} label={t("home.taps")} value={stats?.taps} testId="home-taps" />
                <Stat icon={QrCode} label={t("home.scans")} value={stats?.scans} testId="home-scans" />
                <Stat icon={Inbox} label={t("home.newLeads")} value={newLeads} testId="home-newleads" />
              </div>

              <AnalyticsOverview data={overview} />

              <div className="rounded-2xl border border-white/10 bg-[#0A0B0D] p-5" data-testid="home-upcoming">
                <div className="mb-3 flex items-center justify-between">
                  <h3 className="flex items-center gap-2 text-sm font-medium text-white"><CalendarDays className="h-4 w-4 text-[#D6A653]" /> {t("home.upcoming")}</h3>
                  <button onClick={() => navigate("/meetings")} className="text-xs text-[#D6A653] hover:underline" data-testid="home-view-meetings">{t("home.viewAll")}</button>
                </div>
                {meetings.length === 0 ? (
                  <p className="py-6 text-center text-sm text-white/45">{t("home.noMeetings")}</p>
                ) : (
                  <div className="space-y-2">
                    {meetings.slice(0, 5).map((m) => (
                      <div key={m.id} className="flex items-center justify-between rounded-xl border border-white/8 bg-white/[0.02] px-4 py-3" data-testid={`home-meeting-${m.id}`}>
                        <div className="min-w-0">
                          <p className="truncate text-sm text-white">{m.meeting_type_title} <span className="text-white/40">· {m.visitor_name}</span></p>
                          <p className="mt-0.5 flex items-center gap-1 text-xs text-white/50"><Clock className="h-3 w-3 text-[#D6A653]" /> {formatDateTime(m.start_utc, m.owner_timezone)}</p>
                        </div>
                        {m.status === "requested" ? <span className="shrink-0 rounded-full border border-[#D6A653]/40 bg-[#D6A653]/10 px-2 py-0.5 text-[10px] uppercase tracking-wider text-[#D6A653]">{t("home.pending")}</span> : <span className="shrink-0 rounded-full border border-emerald-400/30 bg-emerald-400/10 px-2 py-0.5 text-[10px] uppercase tracking-wider text-emerald-300">{t("home.confirmed")}</span>}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
