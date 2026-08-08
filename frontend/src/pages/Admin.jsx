import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import CardEditor from "@/components/admin/CardEditor";
import LeadsDialog from "@/components/admin/LeadsDialog";
import AnalyticsDialog from "@/components/admin/AnalyticsDialog";
import { TEMPLATES } from "@/components/templates/TemplateRenderer";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Plus, Pencil, Trash2, ExternalLink, LogOut, Loader2, Inbox, BarChart3 } from "lucide-react";
import { toast } from "sonner";

export default function Admin() {
  const { user, logout } = useAuth();
  const [cards, setCards] = useState(null);
  const [editing, setEditing] = useState(null); // null | {} for new | card obj
  const [leadsOpen, setLeadsOpen] = useState(false);
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
      <div className="min-h-screen bg-white">
        <div className="mx-auto max-w-7xl px-6 py-8">
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
    <div className="min-h-screen bg-neutral-50">
      <header className="border-b border-neutral-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-neutral-400">ARIADNI ID</p>
            <h1 className="text-lg font-semibold text-neutral-900">Card manager</h1>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="outline" size="sm" onClick={() => setLeadsOpen(true)} data-testid="inbox-button" className="relative">
              <Inbox className="w-4 h-4 mr-1" /> Inbox
              {unread > 0 ? <span className="absolute -right-2 -top-2 flex h-5 min-w-[20px] items-center justify-center rounded-full bg-neutral-900 px-1 text-[10px] text-white" data-testid="inbox-unread">{unread}</span> : null}
            </Button>
            <span className="text-sm text-neutral-500">{user?.email}</span>
            <Button variant="ghost" size="sm" onClick={logout} data-testid="logout-button"><LogOut className="w-4 h-4" /></Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-8">
        <div className="mb-6 flex items-center justify-between">
          <h2 className="text-sm font-medium text-neutral-500">{cards ? `${cards.length} cards` : ""}</h2>
          <Button onClick={() => setEditing({})} data-testid="new-card-button"><Plus className="w-4 h-4 mr-1" /> New card</Button>
        </div>

        {cards === null ? (
          <div className="flex justify-center py-20"><Loader2 className="w-6 h-6 animate-spin text-neutral-400" /></div>
        ) : cards.length === 0 ? (
          <div className="rounded-lg border border-dashed border-neutral-300 py-20 text-center text-neutral-500">No cards yet. Create your first one.</div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {cards.map((c) => (
              <div key={c.id} className="rounded-lg border border-neutral-200 bg-white p-5" data-testid={`card-item-${c.slug}`}>
                <div className="mb-3 flex items-center justify-between">
                  <Badge variant={c.status === "published" ? "default" : "secondary"}>{c.status}</Badge>
                  <span className="text-[11px] uppercase tracking-wider text-neutral-400">{tplName(c.templateId)}</span>
                </div>
                <h3 className="text-lg font-semibold text-neutral-900">{c.identity?.fullName || c.slug}</h3>
                <p className="text-sm text-neutral-500">{c.identity?.jobTitle}</p>
                <p className="mt-1 text-xs text-neutral-400">/{c.slug}</p>
                <div className="mt-4 flex items-center gap-2">
                  <Button size="sm" variant="outline" onClick={() => setEditing(c)} data-testid={`edit-${c.slug}`}><Pencil className="w-3.5 h-3.5 mr-1" /> Edit</Button>
                  <Button size="sm" variant="ghost" onClick={() => setStatsCard(c)} data-testid={`stats-${c.slug}`}><BarChart3 className="w-3.5 h-3.5" /></Button>
                  <a href={`/${c.slug}`} target="_blank" rel="noreferrer"><Button size="sm" variant="ghost" data-testid={`view-${c.slug}`}><ExternalLink className="w-3.5 h-3.5" /></Button></a>
                  <Button size="sm" variant="ghost" className="text-red-500 ml-auto" onClick={() => remove(c)} data-testid={`delete-${c.slug}`}><Trash2 className="w-3.5 h-3.5" /></Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      <LeadsDialog open={leadsOpen} onOpenChange={setLeadsOpen} onCountChange={setUnread} />
      <AnalyticsDialog card={statsCard} open={!!statsCard} onOpenChange={(v) => !v && setStatsCard(null)} />
    </div>
  );
}
