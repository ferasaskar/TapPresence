import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Bell, Inbox, CalendarClock, Users, CheckCheck, Loader2 } from "lucide-react";
import { useLocale } from "@/i18n/useLocale";

const TYPE_META = {
  new_lead: { tkey: "notifications.newLead", icon: Inbox, go: "/leads" },
  meeting_booked: { tkey: "notifications.meeting", icon: CalendarClock, go: "/meetings" },
  team_invite: { tkey: "notifications.team", icon: Users, go: "/settings" },
};

const relTime = (iso) => {
  const d = new Date(iso), s = Math.floor((Date.now() - d.getTime()) / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  if (s < 604800) return `${Math.floor(s / 86400)}d ago`;
  return d.toLocaleDateString([], { month: "short", day: "numeric" });
};

export const NotificationBell = () => {
  const navigate = useNavigate();
  const { t } = useLocale();
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState([]);
  const [unread, setUnread] = useState(0);
  const [loading, setLoading] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    api.get("/notifications")
      .then(({ data }) => { setItems(data.items || []); setUnread(data.unread || 0); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); const t = setInterval(load, 60000); return () => clearInterval(t); }, [load]);
  useEffect(() => { if (open) load(); }, [open, load]);

  const markOne = async (n) => {
    if (!n.read) {
      setItems((prev) => prev.map((x) => (x.id === n.id ? { ...x, read: true } : x)));
      setUnread((u) => Math.max(0, u - 1));
      api.patch(`/notifications/${n.id}/read`).catch(() => {});
    }
    const meta = TYPE_META[n.type];
    if (meta?.go) { setOpen(false); navigate(meta.go); }
  };

  const markAll = async () => {
    setItems((prev) => prev.map((x) => ({ ...x, read: true })));
    setUnread(0);
    api.post("/notifications/read-all").catch(() => {});
  };

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="relative rounded-full border border-white/12 bg-white/5 p-2 text-white/70 transition-colors hover:text-white"
        title="Notifications"
        data-testid="nav-notifications"
      >
        <Bell className="h-4 w-4 text-[#D6A653]" />
        {unread > 0 && (
          <span
            className="absolute -right-1 -top-1 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-[#D6A653] px-1 text-[10px] font-bold text-[#050607]"
            data-testid="notif-unread-badge"
          >
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>

      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent side="right" className="aria-dark w-full border-white/10 bg-[#0A0B0D] p-0 text-white sm:max-w-md" data-testid="notification-center">
          <SheetHeader className="flex flex-row items-center justify-between border-b border-white/8 px-5 py-4">
            <SheetTitle className="flex items-center gap-2 text-white"><Bell className="h-4 w-4 text-[#D6A653]" /> {t("notifications.title")}</SheetTitle>
            {unread > 0 && (
              <button onClick={markAll} className="flex items-center gap-1.5 text-xs text-[#D6A653] hover:underline" data-testid="notif-mark-all">
                <CheckCheck className="h-3.5 w-3.5" /> {t("notifications.markAll")}
              </button>
            )}
          </SheetHeader>

          <div className="max-h-[calc(100vh-72px)] overflow-y-auto">
            {loading && items.length === 0 ? (
              <div className="flex justify-center py-20"><Loader2 className="h-5 w-5 animate-spin text-[#D6A653]" /></div>
            ) : items.length === 0 ? (
              <div className="flex flex-col items-center px-6 py-24 text-center" data-testid="notif-empty">
                <div className="mb-3 rounded-full border border-white/10 bg-white/[0.03] p-4"><Bell className="h-6 w-6 text-white/30" /></div>
                <p className="text-sm text-white/60">{t("notifications.empty")}</p>
                <p className="mt-1 text-xs text-white/35">{t("notifications.emptySub")}</p>
              </div>
            ) : (
              <ul className="divide-y divide-white/6">
                {items.map((n) => {
                  const meta = TYPE_META[n.type] || { icon: Bell };
                  const Icon = meta.icon;
                  const label = meta.tkey ? t(meta.tkey) : n.type;
                  return (
                    <li key={n.id}>
                      <button
                        onClick={() => markOne(n)}
                        data-testid={`notif-item-${n.id}`}
                        className={`flex w-full items-start gap-3 px-5 py-3.5 text-left transition-colors hover:bg-white/[0.03] ${n.read ? "" : "bg-[#D6A653]/[0.05]"}`}
                      >
                        <span className="mt-0.5 shrink-0 rounded-lg border border-white/10 bg-white/[0.03] p-1.5"><Icon className="h-4 w-4 text-[#D6A653]" /></span>
                        <span className="min-w-0 flex-1">
                          <span className="flex items-center gap-2">
                            <span className="text-[10px] uppercase tracking-wide text-white/40">{label}</span>
                            {!n.read && <span className="h-1.5 w-1.5 rounded-full bg-[#D6A653]" data-testid="notif-unread-dot" />}
                          </span>
                          <p className="mt-0.5 truncate text-sm text-white">{n.title}</p>
                          {n.body ? <p className="truncate text-xs text-white/45">{n.body}</p> : null}
                        </span>
                        <span className="shrink-0 text-[11px] text-white/35">{relTime(n.created_at)}</span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </SheetContent>
      </Sheet>
    </>
  );
};
