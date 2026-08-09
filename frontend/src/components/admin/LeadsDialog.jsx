import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
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
      <DialogContent className="aria-dark max-h-[85vh] max-w-2xl overflow-y-auto border-white/10 bg-[#0A0B0D] text-white" data-testid="leads-dialog">
        <DialogHeader><DialogTitle className="flex items-center gap-2 text-white"><Inbox className="h-5 w-5 text-[#D6A653]" /> Inquiry inbox</DialogTitle></DialogHeader>
        {leads === null ? (
          <div className="flex justify-center py-16"><Loader2 className="h-6 w-6 animate-spin text-[#D6A653]" /></div>
        ) : leads.length === 0 ? (
          <p className="py-16 text-center text-white/50">No inquiries yet.</p>
        ) : (
          <div className="space-y-3">
            {leads.map((l) => (
              <div key={l.id} className={`rounded-xl border p-4 ${l.read ? "border-white/10 bg-white/[0.02]" : "border-[#D6A653]/30 bg-[#D6A653]/[0.06]"}`} data-testid={`lead-${l.id}`}>
                <div className="flex items-start justify-between gap-3" onClick={() => markRead(l)}>
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium text-white">{l.name}</span>
                      {!l.read ? <span className="rounded-full bg-[#D6A653] px-2 py-0.5 text-[10px] font-semibold text-[#050607]">New</span> : null}
                      {l.status ? <span className="rounded-full bg-white/10 px-2 py-0.5 text-[10px] text-white/70">{l.status}</span> : null}
                      <span className="text-xs text-white/35">/{l.cardSlug}</span>
                    </div>
                    <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs text-white/50">
                      {l.email ? <span className="flex items-center gap-1"><Mail className="h-3 w-3" /> {l.email}</span> : null}
                      {l.phone ? <span className="flex items-center gap-1"><Phone className="h-3 w-3" /> {l.phone}</span> : null}
                    </div>
                    {l.message ? <p className="mt-2 text-sm text-white/75">{l.message}</p> : null}
                  </div>
                  <button onClick={(e) => { e.stopPropagation(); remove(l); }} className="text-red-400/80 hover:text-red-400" data-testid={`lead-delete-${l.id}`}><Trash2 className="h-4 w-4" /></button>
                </div>

                <div className="mt-3 flex items-center gap-2 border-t border-white/8 pt-3">
                  <Button size="sm" onClick={() => openDraft(l)} className="rounded-lg border border-white/15 bg-transparent text-white hover:bg-white/5" data-testid={`lead-ai-${l.id}`}>
                    <Sparkles className="mr-1 h-3.5 w-3.5 text-[#D6A653]" /> AI follow-up
                  </Button>
                </div>

                {draftFor === l.id && (
                  <div className="mt-3 rounded-lg border border-white/10 bg-white/[0.03] p-3" data-testid={`ai-panel-${l.id}`}>
                    <div className="grid grid-cols-3 gap-2">
                      <Select value={opts.channel} onValueChange={(v) => setOpts((o) => ({ ...o, channel: v }))}>
                        <SelectTrigger className="h-8 text-xs" data-testid="ai-channel"><SelectValue /></SelectTrigger>
                        <SelectContent className="aria-pop"><SelectItem value="email">Email</SelectItem><SelectItem value="whatsapp">WhatsApp</SelectItem><SelectItem value="sms">SMS</SelectItem></SelectContent>
                      </Select>
                      <Select value={opts.tone} onValueChange={(v) => setOpts((o) => ({ ...o, tone: v }))}>
                        <SelectTrigger className="h-8 text-xs" data-testid="ai-tone"><SelectValue /></SelectTrigger>
                        <SelectContent className="aria-pop"><SelectItem value="professional">Professional</SelectItem><SelectItem value="warm">Warm</SelectItem><SelectItem value="short">Short</SelectItem></SelectContent>
                      </Select>
                      <Select value={opts.language} onValueChange={(v) => setOpts((o) => ({ ...o, language: v }))}>
                        <SelectTrigger className="h-8 text-xs" data-testid="ai-language"><SelectValue /></SelectTrigger>
                        <SelectContent className="aria-pop"><SelectItem value="en">English</SelectItem><SelectItem value="ar">العربية</SelectItem><SelectItem value="es">Español</SelectItem></SelectContent>
                      </Select>
                    </div>
                    <Button size="sm" className="mt-2 w-full rounded-lg bg-[#D6A653] font-medium text-[#050607] hover:bg-[#E8B764]" onClick={() => generate(l)} disabled={gen} data-testid={`ai-generate-${l.id}`}>
                      {gen ? <Loader2 className="h-4 w-4 animate-spin" /> : "Generate draft"}
                    </Button>
                    {draft ? (
                      <div className="mt-2">
                        <Textarea value={draft} onChange={(e) => setDraft(e.target.value)} rows={5} dir={RTL.includes(opts.language) ? "rtl" : "ltr"} data-testid="ai-draft" />
                        <Button size="sm" className="mt-2 rounded-lg border border-white/15 bg-transparent text-white hover:bg-white/5" onClick={copy} data-testid="ai-copy"><Copy className="mr-1 h-3.5 w-3.5" /> Copy</Button>
                        <span className="ml-2 text-xs text-white/40">Review before sending — AI never sends automatically.</span>
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
