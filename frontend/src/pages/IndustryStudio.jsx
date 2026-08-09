import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { OwnerNav } from "@/components/admin/OwnerNav";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Loader2, Palette, RotateCcw, Save, EyeOff, Eye } from "lucide-react";
import { toast } from "sonner";

const ACCENTS = ["gold", "platinum", "blue", "emerald", "bronze", "rose"];

export default function IndustryStudio() {
  const { user } = useAuth();
  const isSuper = user?.role === "SUPER_ADMIN";
  const [list, setList] = useState(undefined);
  const [edits, setEdits] = useState({});

  const load = () => api.get("/admin/industries").then(({ data }) => setList(data.industries)).catch(() => setList(null));
  useEffect(() => { if (!isSuper) { setList(null); return; } load(); }, [isSuper]);

  const setField = (id, k, v) => setEdits((e) => ({ ...e, [id]: { ...e[id], [k]: v } }));
  const eff = (row) => ({ ...row.effective, ...(edits[row.id] || {}) });

  const save = async (row) => {
    const e = eff(row);
    const payload = { name: e.name, recommended_accent: e.recommended_accent, default_opacity: Number(e.default_opacity), image: e.image, status: e.status || "active" };
    try { await api.put(`/admin/industries/${row.id}`, payload); toast.success("Saved"); setEdits((x) => { const n = { ...x }; delete n[row.id]; return n; }); load(); }
    catch { toast.error("Save failed"); }
  };
  const reset = async (row) => {
    try { await api.delete(`/admin/industries/${row.id}`); toast.success("Reset to default"); setEdits((x) => { const n = { ...x }; delete n[row.id]; return n; }); load(); }
    catch { toast.error("Reset failed"); }
  };

  return (
    <div className="aria-dark relative min-h-screen bg-[#050607] text-white" style={{ fontFamily: "'Outfit', sans-serif" }} data-testid="industry-studio-page">
      <div className="grain-overlay" style={{ opacity: 0.04 }} />
      <OwnerNav active="industries" />
      <main className="relative mx-auto max-w-5xl px-4 py-8 sm:px-8">
        <h2 className="flex items-center gap-2 text-2xl font-light tracking-tight text-white"><Palette className="h-5 w-5 text-[#D6A653]" /> Industry Studio</h2>
        <p className="mt-1 text-sm text-white/45">Customize industry visual presets. Changes apply to every new card's industry catalog.</p>

        {!isSuper ? (
          <div className="mt-8 rounded-2xl border border-dashed border-white/12 py-24 text-center text-white/55" data-testid="studio-denied">Super admin only.</div>
        ) : list === undefined ? (
          <div className="flex justify-center py-24"><Loader2 className="h-6 w-6 animate-spin text-[#D6A653]" /></div>
        ) : !list ? (
          <div className="mt-8 rounded-2xl border border-dashed border-white/12 py-24 text-center text-white/55">Could not load industries.</div>
        ) : (
          <div className="mt-6 space-y-3">
            {list.map((row) => {
              const e = eff(row);
              const overridden = Object.keys(row.override || {}).length > 0;
              const dirty = !!edits[row.id];
              const disabled = e.status === "disabled";
              return (
                <div key={row.id} className={`rounded-2xl border bg-[#0A0B0D] p-4 ${disabled ? "border-white/8 opacity-70" : "border-white/10"}`} data-testid={`industry-row-${row.id}`}>
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                    <div className="flex items-center gap-3 sm:w-52 sm:shrink-0">
                      <span className="h-9 w-9 shrink-0 rounded-lg border border-white/10" style={{ backgroundImage: e.image ? `url(${e.image})` : "none", backgroundColor: "#15161a", backgroundSize: "cover", backgroundPosition: "center" }} />
                      <div className="min-w-0">
                        <input value={e.name || ""} onChange={(ev) => setField(row.id, "name", ev.target.value)} data-testid={`industry-name-${row.id}`} className="w-full bg-transparent text-sm font-medium text-white outline-none" />
                        <p className="text-[10px] uppercase tracking-wide text-white/35">{row.id}{overridden ? " · overridden" : ""}</p>
                      </div>
                    </div>

                    <div className="grid flex-1 grid-cols-2 gap-2 sm:grid-cols-3">
                      <div>
                        <label className="mb-1 block text-[10px] uppercase tracking-wide text-white/40">Accent</label>
                        <Select value={ACCENTS.includes(e.recommended_accent) ? e.recommended_accent : "gold"} onValueChange={(v) => setField(row.id, "recommended_accent", v)}>
                          <SelectTrigger className="h-8 border-white/12 bg-white/[0.03] text-xs text-white" data-testid={`industry-accent-${row.id}`}><SelectValue /></SelectTrigger>
                          <SelectContent className="aria-pop border-white/10 bg-[#0A0B0D] text-white">{ACCENTS.map((a) => <SelectItem key={a} value={a} className="text-xs capitalize">{a}</SelectItem>)}</SelectContent>
                        </Select>
                      </div>
                      <div>
                        <label className="mb-1 block text-[10px] uppercase tracking-wide text-white/40">Opacity {Number(e.default_opacity).toFixed(2)}</label>
                        <input type="range" min="0.05" max="0.35" step="0.01" value={e.default_opacity ?? 0.15} onChange={(ev) => setField(row.id, "default_opacity", ev.target.value)} data-testid={`industry-opacity-${row.id}`} className="w-full accent-[#D6A653]" />
                      </div>
                      <div className="col-span-2 sm:col-span-1">
                        <label className="mb-1 block text-[10px] uppercase tracking-wide text-white/40">Image URL</label>
                        <input value={e.image || ""} onChange={(ev) => setField(row.id, "image", ev.target.value)} data-testid={`industry-image-${row.id}`} className="w-full rounded-md border border-white/12 bg-white/[0.03] px-2 py-1 text-xs text-white outline-none" placeholder="https://…" />
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5 sm:shrink-0">
                      <button onClick={() => setField(row.id, "status", disabled ? "active" : "disabled")} title={disabled ? "Enable" : "Disable"} data-testid={`industry-toggle-${row.id}`} className="rounded-md border border-white/12 p-1.5 text-white/60 hover:text-white">{disabled ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}</button>
                      <button onClick={() => save(row)} disabled={!dirty} data-testid={`industry-save-${row.id}`} className={`inline-flex items-center gap-1 rounded-md px-2.5 py-1.5 text-xs ${dirty ? "bg-[#D6A653] text-[#050607] hover:bg-[#E8B764]" : "border border-white/10 text-white/30"}`}><Save className="h-3.5 w-3.5" /> Save</button>
                      {overridden && <button onClick={() => reset(row)} title="Reset" data-testid={`industry-reset-${row.id}`} className="rounded-md border border-white/12 p-1.5 text-white/60 hover:text-white"><RotateCcw className="h-3.5 w-3.5" /></button>}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}
