import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useLocale } from "@/i18n/useLocale";
import { OwnerNav } from "@/components/admin/OwnerNav";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Plug, KeyRound, Webhook, Plus, Copy, Trash2, Send, Loader2, Check } from "lucide-react";
import { toast } from "sonner";

const EXTERNAL = [
  { g: "CRM", items: ["hubspot", "salesforce", "pipedrive"] },
  { g: "Automation", items: ["zapier", "make"] },
  { g: "Billing", items: ["stripe", "revenuecat"] },
];

export default function IntegrationHub() {
  const { t } = useLocale();
  const [wid, setWid] = useState(undefined);
  const [hub, setHub] = useState(null);
  const [status, setStatus] = useState(null);
  const [reveal, setReveal] = useState(null); // {type, value}
  const [whOpen, setWhOpen] = useState(false);
  const [wh, setWh] = useState({ url: "", events: [] });

  const load = (id) => api.get(`/workspaces/${id}/hub`).then(({ data }) => setHub(data)).catch(() => setHub({ available_events: [], api_keys: [], webhooks: [] }));
  useEffect(() => {
    api.get("/workspaces/me").then(({ data }) => {
      const w = (data || []).find((x) => x.owner_id) || data?.[0];
      if (!w) { setWid(null); return; }
      setWid(w.id); load(w.id);
    }).catch(() => setWid(null));
    api.get("/integrations/status").then(({ data }) => setStatus(data)).catch(() => {});
  }, []);

  const copy = (v) => { navigator.clipboard.writeText(v); toast.success("Copied"); };

  const newKey = async () => {
    const name = window.prompt("API key name", "My integration");
    if (!name) return;
    try { const { data } = await api.post(`/workspaces/${wid}/api-keys`, { name }); setReveal({ type: "API key", value: data.key }); load(wid); }
    catch { toast.error("Failed"); }
  };
  const revokeKey = async (id) => { await api.delete(`/workspaces/${wid}/api-keys/${id}`).catch(() => {}); load(wid); };

  const addWebhook = async () => {
    if (!wh.url.startsWith("http")) { toast.error("Enter a valid URL"); return; }
    try { const { data } = await api.post(`/workspaces/${wid}/webhooks`, { url: wh.url, events: wh.events }); setReveal({ type: "Signing secret", value: data.secret }); setWhOpen(false); setWh({ url: "", events: [] }); load(wid); }
    catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };
  const testWebhook = async (id) => { const { data } = await api.post(`/workspaces/${wid}/webhooks/${id}/test`); toast.success(`Sent · status ${data.last_status}`); load(wid); };
  const delWebhook = async (id) => { await api.delete(`/workspaces/${wid}/webhooks/${id}`).catch(() => {}); load(wid); };

  const toggleEvent = (e) => setWh((s) => ({ ...s, events: s.events.includes(e) ? s.events.filter((x) => x !== e) : [...s.events, e] }));

  return (
    <div className="aria-dark relative min-h-screen bg-[#050607] text-white" style={{ fontFamily: "'Outfit', sans-serif" }} data-testid="integrations-page">
      <div className="grain-overlay" style={{ opacity: 0.04 }} />
      <OwnerNav active="integrations" />
      <main className="relative mx-auto max-w-4xl px-4 py-8 sm:px-8">
        <h2 className="flex items-center gap-2 text-2xl font-light tracking-tight text-white"><Plug className="h-5 w-5 text-[#D6A653]" /> {t("nav.integrations")}</h2>
        <p className="mt-1 text-sm text-white/45">API keys, signed webhooks and event subscriptions for your workspace.</p>

        {wid === undefined || (wid && !hub) ? (
          <div className="flex justify-center py-24"><Loader2 className="h-6 w-6 animate-spin text-[#D6A653]" /></div>
        ) : wid === null ? (
          <div className="mt-8 rounded-2xl border border-dashed border-white/12 py-24 text-center text-white/55" data-testid="integrations-denied">Workspace admin access required.</div>
        ) : (
          <div className="mt-6 space-y-5">
            {/* API keys */}
            <section className="rounded-2xl border border-white/10 bg-[#0A0B0D] p-5" data-testid="api-keys-section">
              <div className="mb-3 flex items-center justify-between">
                <h3 className="flex items-center gap-2 text-sm font-medium text-white"><KeyRound className="h-4 w-4 text-[#D6A653]" /> API keys</h3>
                <button onClick={newKey} data-testid="new-api-key" className="inline-flex items-center gap-1 rounded-full bg-[#D6A653] px-3 py-1.5 text-xs font-medium text-[#050607] hover:bg-[#E8B764]"><Plus className="h-3.5 w-3.5" /> New key</button>
              </div>
              {hub.api_keys.length === 0 ? <p className="py-4 text-center text-xs text-white/40">No API keys yet.</p> : (
                <ul className="divide-y divide-white/6">
                  {hub.api_keys.map((k) => (
                    <li key={k.id} className="flex items-center justify-between py-2.5" data-testid={`api-key-${k.id}`}>
                      <div><p className="text-sm text-white">{k.name}</p><p className="font-mono text-xs text-white/40">{k.prefix}••••</p></div>
                      {k.revoked ? <span className="text-[11px] text-white/35">revoked</span> : <button onClick={() => revokeKey(k.id)} className="rounded-md border border-red-500/25 px-2 py-1 text-[11px] text-red-300/80 hover:bg-red-500/10">Revoke</button>}
                    </li>
                  ))}
                </ul>
              )}
            </section>

            {/* Webhooks */}
            <section className="rounded-2xl border border-white/10 bg-[#0A0B0D] p-5" data-testid="webhooks-section">
              <div className="mb-3 flex items-center justify-between">
                <h3 className="flex items-center gap-2 text-sm font-medium text-white"><Webhook className="h-4 w-4 text-[#D6A653]" /> Webhooks</h3>
                <button onClick={() => setWhOpen(true)} data-testid="new-webhook" className="inline-flex items-center gap-1 rounded-full bg-[#D6A653] px-3 py-1.5 text-xs font-medium text-[#050607] hover:bg-[#E8B764]"><Plus className="h-3.5 w-3.5" /> Add webhook</button>
              </div>
              {hub.webhooks.length === 0 ? <p className="py-4 text-center text-xs text-white/40">No webhooks yet. Subscribe to events like lead.created.</p> : (
                <ul className="space-y-2">
                  {hub.webhooks.map((h) => (
                    <li key={h.id} className="rounded-xl border border-white/8 bg-white/[0.02] p-3" data-testid={`webhook-${h.id}`}>
                      <div className="flex items-center justify-between gap-2">
                        <p className="truncate font-mono text-xs text-white/80">{h.url}</p>
                        <div className="flex shrink-0 gap-1.5">
                          <button onClick={() => testWebhook(h.id)} title="Send test" data-testid={`webhook-test-${h.id}`} className="rounded-md border border-white/12 p-1.5 text-white/70 hover:text-white"><Send className="h-3.5 w-3.5" /></button>
                          <button onClick={() => delWebhook(h.id)} data-testid={`webhook-del-${h.id}`} className="rounded-md border border-red-500/25 p-1.5 text-red-300/80 hover:bg-red-500/10"><Trash2 className="h-3.5 w-3.5" /></button>
                        </div>
                      </div>
                      <div className="mt-2 flex flex-wrap items-center gap-1.5">
                        {(h.events || []).map((e) => <span key={e} className="rounded-full border border-[#D6A653]/25 bg-[#D6A653]/[0.06] px-2 py-0.5 text-[10px] text-[#D6A653]">{e}</span>)}
                        {h.last_status != null && <span className="text-[10px] text-white/35">last: {String(h.last_status)}</span>}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            {/* External providers (deferred) */}
            <section className="rounded-2xl border border-white/10 bg-[#0A0B0D] p-5" data-testid="external-providers">
              <h3 className="mb-3 text-sm font-medium text-white">External providers</h3>
              <p className="mb-3 text-xs text-white/40">Provider-neutral foundation is ready. Connections are enabled in a later phase.</p>
              <div className="space-y-3">
                {EXTERNAL.map((grp) => (
                  <div key={grp.g}>
                    <p className="mb-1.5 text-[10px] uppercase tracking-wide text-white/35">{grp.g}</p>
                    <div className="flex flex-wrap gap-2">
                      {grp.items.map((p) => (
                        <span key={p} className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.02] px-2.5 py-1 text-xs capitalize text-white/55" data-testid={`provider-${p}`}>{p} <span className="text-[10px] text-white/30">· not connected</span></span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          </div>
        )}
      </main>

      {/* reveal-once secret */}
      <Dialog open={!!reveal} onOpenChange={() => setReveal(null)}>
        <DialogContent className="aria-dark border-white/10 bg-[#0A0B0D] text-white sm:max-w-md" data-testid="reveal-dialog">
          <DialogHeader><DialogTitle className="text-white">{reveal?.type} — shown once</DialogTitle></DialogHeader>
          <p className="text-xs text-white/50">Copy and store this now. You won't be able to see it again.</p>
          <div className="mt-2 flex items-center gap-2 rounded-lg border border-white/12 bg-black/40 p-3">
            <code className="flex-1 break-all text-xs text-[#D6A653]">{reveal?.value}</code>
            <button onClick={() => copy(reveal.value)} className="shrink-0 rounded-md bg-[#D6A653] p-1.5 text-[#050607]" data-testid="reveal-copy"><Copy className="h-3.5 w-3.5" /></button>
          </div>
        </DialogContent>
      </Dialog>

      {/* add webhook */}
      <Dialog open={whOpen} onOpenChange={setWhOpen}>
        <DialogContent className="aria-dark border-white/10 bg-[#0A0B0D] text-white sm:max-w-md" data-testid="webhook-dialog">
          <DialogHeader><DialogTitle className="flex items-center gap-2 text-white"><Webhook className="h-4 w-4 text-[#D6A653]" /> Add webhook</DialogTitle></DialogHeader>
          <label className="mb-1 block text-xs text-white/50">Endpoint URL</label>
          <input value={wh.url} onChange={(e) => setWh({ ...wh, url: e.target.value })} data-testid="webhook-url" placeholder="https://example.com/hooks/tappresence" className="w-full rounded-lg border border-white/12 bg-white/[0.03] px-3 py-2.5 text-sm text-white" />
          <label className="mb-1 mt-3 block text-xs text-white/50">Events (empty = all)</label>
          <div className="flex flex-wrap gap-2">
            {(hub?.available_events || []).map((e) => (
              <button key={e} onClick={() => toggleEvent(e)} data-testid={`event-${e}`} className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs ${wh.events.includes(e) ? "border-[#D6A653] bg-[#D6A653]/10 text-[#D6A653]" : "border-white/12 text-white/60"}`}>{wh.events.includes(e) && <Check className="h-3 w-3" />}{e}</button>
            ))}
          </div>
          <button onClick={addWebhook} data-testid="webhook-submit" className="mt-4 w-full rounded-lg bg-[#D6A653] py-2.5 text-sm font-medium text-[#050607] hover:bg-[#E8B764]">Create webhook</button>
        </DialogContent>
      </Dialog>
    </div>
  );
}
