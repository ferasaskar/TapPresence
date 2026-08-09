import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import CardEditor from "@/components/admin/CardEditor";
import LeadsDialog from "@/components/admin/LeadsDialog";
import AnalyticsDialog from "@/components/admin/AnalyticsDialog";
import ScanCardDialog from "@/components/admin/ScanCardDialog";
import { TEMPLATES } from "@/components/templates/TemplateRenderer";
import { motion } from "framer-motion";
import { Plus, Pencil, Trash2, ExternalLink, LogOut, Loader2, Inbox, ScanLine, BarChart3, LayoutGrid } from "lucide-react";
import { toast } from "sonner";

const AriadniMark = ({ className = "" }) => (
  <svg viewBox="0 0 24 24" className={className} fill="none" aria-hidden>
    <path d="M12 3 L21 20 L15.6 20 L12 12 L8.4 20 L3 20 Z" fill="currentColor" />
  </svg>
);

const HeaderBtn = ({ children, className = "", ...props }) => (
  <button className={`inline-flex items-center gap-1.5 rounded-full border border-white/12 bg-white/5 px-4 py-2 text-sm text-white/80 transition-all hover:border-white/25 hover:text-white active:scale-95 ${className}`} {...props}>
    {children}
  </button>
);

export default function Admin() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [cards, setCards] = useState(null);
  const [editing, setEditing] = useState(null);
  const [leadsOpen, setLeadsOpen] = useState(false);
  const [scanOpen, setScanOpen] = useState(false);
  const [unread, setUnread] = useState(0);
  const [statsCard, setStatsCard] = useState(null);

  const load = () => {
    setCards(null);
    api.get("/admin/cards").then((res) => setCards(res.data)).catch(() => setCards([]));
    api.get("/admin/leads").then((res) => setUnread(res.data.filter((l) => !l.read).length)).catch(() => {});
  };

  useEffect(() => { load(); }, []);

  const remove = async (card) => {
    if (!window.confirm(`Delete ${card.slug}?`)) return;
    try {
      await api.delete(`/admin/cards/${card.id}`);
      toast.success("Card deleted");
      load();
    } catch {
      toast.error("Delete failed");
    }
  };

  const tplName = (id) => TEMPLATES.find((t) => t.id === id)?.name || id;

  if (editing !== null) {
    return (
      <div className="aria-dark min-h-screen bg-[#050607]" style={{ fontFamily: "'Outfit', sans-serif" }}>
        <div className="mx-auto max-w-7xl px-4 py-8 sm:px-8">
          <CardEditor
            initial={editing}
            onBack={() => setEditing(null)}
            onSaved={() => { setEditing(null); load(); }}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="aria-dark relative min-h-screen bg-[#050607] text-white" style={{ fontFamily: "'Outfit', sans-serif" }}>
      <div className="grain-overlay" style={{ opacity: 0.04 }} />

      <header className="sticky top-0 z-40 border-b border-white/8 bg-[#050607]/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-4 sm:px-8">
          <div className="flex items-center gap-2.5">
            <AriadniMark className="h-5 w-5 text-[#D6A653]" />
            <div>
              <p className="text-[10px] uppercase tracking-[0.3em] text-white/40">ARIADNI ID</p>
              <h1 className="text-[15px] font-medium leading-tight text-white">Card Manager</h1>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <HeaderBtn onClick={() => setScanOpen(true)} data-testid="scan-button"><ScanLine className="h-4 w-4 text-[#D6A653]" /> Scan card</HeaderBtn>
            <div className="relative">
              <HeaderBtn onClick={() => setLeadsOpen(true)} data-testid="inbox-button"><Inbox className="h-4 w-4" /> Inbox</HeaderBtn>
              {unread > 0 ? <span className="absolute -right-1.5 -top-1.5 flex h-5 min-w-[20px] items-center justify-center rounded-full bg-[#D6A653] px-1 text-[10px] font-semibold text-[#050607]" data-testid="inbox-unread">{unread}</span> : null}
            </div>
            <span className="hidden text-sm text-white/40 sm:inline">{user?.email}</span>
            <button onClick={logout} className="rounded-full p-2 text-white/60 transition-colors hover:bg-white/5 hover:text-white" data-testid="logout-button"><LogOut className="h-4 w-4" /></button>
          </div>
        </div>
      </header>

      <main className="relative mx-auto max-w-7xl px-4 py-10 sm:px-8">
        <div className="mb-7 flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-light tracking-tight text-white">Your Cards</h2>
            <p className="mt-1 text-sm text-white/45">{cards ? `${cards.length} ${cards.length === 1 ? "profile" : "profiles"} in your studio` : "Loading…"}</p>
          </div>
          <button onClick={() => navigate("/templates")} className="inline-flex items-center gap-1.5 rounded-full bg-[#D6A653] px-5 py-2.5 text-sm font-medium text-[#050607] transition-all hover:bg-[#E8B764] hover:shadow-[0_0_18px_rgba(214,166,83,0.35)] active:scale-95" data-testid="new-card-button">
            <Plus className="h-4 w-4" /> Create Card
          </button>
        </div>

        {cards === null ? (
          <div className="flex justify-center py-24"><Loader2 className="h-6 w-6 animate-spin text-[#D6A653]" /></div>
        ) : cards.length === 0 ? (
          <div className="flex flex-col items-center rounded-2xl border border-dashed border-white/12 py-24 text-center">
            <LayoutGrid className="mb-4 h-10 w-10 text-[#D6A653]/40" strokeWidth={1.25} />
            <p className="text-white/60">No cards yet.</p>
            <button onClick={() => navigate("/templates")} className="mt-4 rounded-full border border-[#D6A653]/40 px-5 py-2 text-sm text-[#D6A653] transition-colors hover:bg-[#D6A653]/10" data-testid="empty-new-card">Create your first card</button>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {cards.map((c, i) => (
              <motion.div
                key={c.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: i * 0.05 }}
                className="group rounded-2xl border border-white/10 bg-[#0A0B0D] p-6 transition-all hover:border-white/20 hover:shadow-[0_0_30px_rgba(214,166,83,0.08)]"
                data-testid={`card-item-${c.slug}`}
              >
                <div className="mb-4 flex items-center justify-between">
                  <span className={c.status === "published"
                    ? "rounded-full border border-[#D6A653]/30 bg-[#D6A653]/15 px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-wider text-[#D6A653]"
                    : "rounded-full border border-white/10 bg-white/10 px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-wider text-white/60"}>
                    {c.status}
                  </span>
                  <span className="text-[10px] uppercase tracking-wider text-white/35">{tplName(c.templateId)}</span>
                </div>
                <h3 className="text-lg font-medium text-white">{c.identity?.fullName || c.slug}</h3>
                <p className="text-sm text-white/55">{c.identity?.jobTitle}</p>
                <p className="mt-1 text-xs text-[#D6A653]/80">/{c.slug}</p>
                <div className="mt-5 flex items-center gap-1.5 border-t border-white/8 pt-4">
                  <button onClick={() => setEditing(c)} className="inline-flex items-center gap-1.5 rounded-lg border border-white/12 px-3 py-1.5 text-xs text-white/80 transition-colors hover:border-[#D6A653]/50 hover:text-white" data-testid={`edit-${c.slug}`}><Pencil className="h-3.5 w-3.5" /> Edit</button>
                  <button onClick={() => setStatsCard(c)} className="rounded-lg p-2 text-white/55 transition-colors hover:bg-white/5 hover:text-white" data-testid={`stats-${c.slug}`}><BarChart3 className="h-3.5 w-3.5" /></button>
                  <a href={`/${c.slug}`} target="_blank" rel="noreferrer" className="rounded-lg p-2 text-white/55 transition-colors hover:bg-white/5 hover:text-white" data-testid={`view-${c.slug}`}><ExternalLink className="h-3.5 w-3.5" /></a>
                  <button onClick={() => remove(c)} className="ml-auto rounded-lg p-2 text-red-400/70 transition-colors hover:bg-red-500/10 hover:text-red-400" data-testid={`delete-${c.slug}`}><Trash2 className="h-3.5 w-3.5" /></button>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </main>

      <LeadsDialog open={leadsOpen} onOpenChange={setLeadsOpen} onCountChange={setUnread} />
      <ScanCardDialog open={scanOpen} onOpenChange={setScanOpen} cards={cards || []} onSaved={load} />
      <AnalyticsDialog card={statsCard} open={!!statsCard} onOpenChange={(v) => !v && setStatsCard(null)} />
    </div>
  );
}
