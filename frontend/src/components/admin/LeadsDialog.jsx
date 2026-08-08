import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Trash2, Mail, Phone, Loader2, Inbox, Sparkles, Copy } from "lucide-react";
import { toast } from "sonner";

const RTL = ["ar"];

export default function LeadsDialog({ open, onOpenChange, onCountChange }) {
  const [leads, setLeads] = useState(null);
  const [draftFor, setDraftFor] = useState(null);
  const [opts, setOpts] = useState({ tone: "professional", channel: "email", language: "en" });
  const [draft, setDraft] = useState("");
  const [gen, setGen] = useState(false);

  const load = () => {
    api.get("/admin/leads").then((res) => {
      setLeads(res.data);
      onCountChange?.(res.data.filter((l) => !l.read).length);
    });
  };
  useEffect(() => { if (open) load(); }, [open]);

  const markRead = async (l) => { if (l.read) return; await api.patch(`/admin/leads/${l.id}`); load(); };
  const remove = async (l) => { await api.delete(`/admin/leads/${l.id}`); load(); };

  const openDraft = (l) => { setDraftFor(l.id); setDraft(""); };
  const generate = async (l) => {
    setGen(true); setDraft("");
    try {
      const { data } = await api.post("/ai/followup", {
        lead_name: l.name, company: l.company || "", notes: l.interest || l.message || "",
        owner_name: "", tone: opts.tone, channel: opts.channel, language: opts.language,
      });
      setDraft(data.draft);
      toast.success(`Draft ready (${data.provider})`);
    } catch { toast.error("Could not generate draft"); }
    finally { setGen(false); }
  };
  const copy = async () => { await navigator.clipboard.writeText(draft); toast.success("Copied"); };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto" data-testid="leads-dialog">
        <DialogHeader><DialogTitle className="flex items-center gap-2"><Inbox className="w-5 h-5" /> Inquiry inbox</DialogTitle></DialogHeader>
        {leads === null ? (
          <div className="flex justify-center py-16"><Loader2 className="w-6 h-6 animate-spin text-neutral-400" /></div>
        ) : leads.length === 0 ? (
          <p className="py-16 text-center text-neutral-500">No inquiries yet.</p>
        ) : (
          <div className="space-y-3">
            {leads.map((l) => (
              <div key={l.id} className={`rounded-lg border p-4 ${l.read ? "border-neutral-200 bg-white" : "border-neutral-900/20 bg-amber-50"}`} data-testid={`lead-${l.id}`}>
                <div className="flex items-start justify-between gap-3" onClick={() => markRead(l)}>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-neutral-900">{l.name}</span>
                      {!l.read ? <Badge className="text-[10px]">New</Badge> : null}
                      {l.status ? <Badge variant="secondary" className="text-[10px]">{l.status}</Badge> : null}
                      <span className="text-xs text-neutral-400">/{l.cardSlug}</span>
                    </div>
                    <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs text-neutral-500">
                      {l.email ? <span className="flex items-center gap-1"><Mail className="w-3 h-3" /> {l.email}</span> : null}
                      {l.phone ? <span className="flex items-center gap-1"><Phone className="w-3 h-3" /> {l.phone}</span> : null}
                    </div>
                    {l.message ? <p className="mt-2 text-sm text-neutral-700">{l.message}</p> : null}
                  </div>
                  <button onClick={(e) => { e.stopPropagation(); remove(l); }} className="text-red-500" data-testid={`lead-delete-${l.id}`}><Trash2 className="w-4 h-4" /></button>
                </div>

                <div className="mt-3 flex items-center gap-2 border-t border-neutral-100 pt-3">
                  <Button size="sm" variant="outline" onClick={() => openDraft(l)} data-testid={`lead-ai-${l.id}`}>
                    <Sparkles className="w-3.5 h-3.5 mr-1 text-[#B89973]" /> AI follow-up
                  </Button>
                </div>

                {draftFor === l.id && (
                  <div className="mt-3 rounded-md border border-neutral-200 bg-neutral-50 p-3" data-testid={`ai-panel-${l.id}`}>
                    <div className="grid grid-cols-3 gap-2">
                      <Select value={opts.channel} onValueChange={(v) => setOpts((o) => ({ ...o, channel: v }))}>
                        <SelectTrigger className="h-8 text-xs" data-testid="ai-channel"><SelectValue /></SelectTrigger>
                        <SelectContent><SelectItem value="email">Email</SelectItem><SelectItem value="whatsapp">WhatsApp</SelectItem><SelectItem value="sms">SMS</SelectItem></SelectContent>
                      </Select>
                      <Select value={opts.tone} onValueChange={(v) => setOpts((o) => ({ ...o, tone: v }))}>
                        <SelectTrigger className="h-8 text-xs" data-testid="ai-tone"><SelectValue /></SelectTrigger>
                        <SelectContent><SelectItem value="professional">Professional</SelectItem><SelectItem value="warm">Warm</SelectItem><SelectItem value="short">Short</SelectItem></SelectContent>
                      </Select>
                      <Select value={opts.language} onValueChange={(v) => setOpts((o) => ({ ...o, language: v }))}>
                        <SelectTrigger className="h-8 text-xs" data-testid="ai-language"><SelectValue /></SelectTrigger>
                        <SelectContent><SelectItem value="en">English</SelectItem><SelectItem value="ar">العربية</SelectItem><SelectItem value="es">Español</SelectItem></SelectContent>
                      </Select>
                    </div>
                    <Button size="sm" className="mt-2 w-full" onClick={() => generate(l)} disabled={gen} data-testid={`ai-generate-${l.id}`}>
                      {gen ? <Loader2 className="w-4 h-4 animate-spin" /> : "Generate draft"}
                    </Button>
                    {draft ? (
                      <div className="mt-2">
                        <Textarea value={draft} onChange={(e) => setDraft(e.target.value)} rows={5} dir={RTL.includes(opts.language) ? "rtl" : "ltr"} data-testid="ai-draft" />
                        <Button size="sm" variant="outline" className="mt-2" onClick={copy} data-testid="ai-copy"><Copy className="w-3.5 h-3.5 mr-1" /> Copy</Button>
                        <span className="ml-2 text-xs text-neutral-400">Review before sending — AI never sends automatically.</span>
                      </div>
                    ) : null}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
