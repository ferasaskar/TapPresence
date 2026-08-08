import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Trash2, Mail, Phone, Loader2, Inbox } from "lucide-react";

export default function LeadsDialog({ open, onOpenChange, onCountChange }) {
  const [leads, setLeads] = useState(null);

  const load = () => {
    api.get("/admin/leads").then((res) => {
      setLeads(res.data);
      onCountChange?.(res.data.filter((l) => !l.read).length);
    });
  };

  useEffect(() => { if (open) load(); }, [open]);

  const markRead = async (l) => {
    if (l.read) return;
    await api.patch(`/admin/leads/${l.id}`);
    load();
  };
  const remove = async (l) => {
    await api.delete(`/admin/leads/${l.id}`);
    load();
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto" data-testid="leads-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><Inbox className="w-5 h-5" /> Inquiry inbox</DialogTitle>
        </DialogHeader>
        {leads === null ? (
          <div className="flex justify-center py-16"><Loader2 className="w-6 h-6 animate-spin text-neutral-400" /></div>
        ) : leads.length === 0 ? (
          <p className="py-16 text-center text-neutral-500">No inquiries yet.</p>
        ) : (
          <div className="space-y-3">
            {leads.map((l) => (
              <div key={l.id} onClick={() => markRead(l)} className={`rounded-lg border p-4 cursor-pointer ${l.read ? "border-neutral-200 bg-white" : "border-neutral-900/20 bg-amber-50"}`} data-testid={`lead-${l.id}`}>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-neutral-900">{l.name}</span>
                      {!l.read ? <Badge className="text-[10px]">New</Badge> : null}
                      <span className="text-xs text-neutral-400">/{l.cardSlug}</span>
                    </div>
                    <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs text-neutral-500">
                      {l.email ? <span className="flex items-center gap-1"><Mail className="w-3 h-3" /> {l.email}</span> : null}
                      {l.phone ? <span className="flex items-center gap-1"><Phone className="w-3 h-3" /> {l.phone}</span> : null}
                    </div>
                    {l.message ? <p className="mt-2 text-sm text-neutral-700">{l.message}</p> : null}
                    <p className="mt-2 text-[11px] text-neutral-400">{new Date(l.created_at).toLocaleString()}</p>
                  </div>
                  <button onClick={(e) => { e.stopPropagation(); remove(l); }} className="text-red-500" data-testid={`lead-delete-${l.id}`}><Trash2 className="w-4 h-4" /></button>
                </div>
              </div>
            ))}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
