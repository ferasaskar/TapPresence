import { useState } from "react";
import { api } from "@/lib/api";
import { TEMPLATES, TemplateRenderer } from "@/components/templates/TemplateRenderer";
import { ImageUploadField } from "@/components/admin/ImageUploadField";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { ACCENT_OPTIONS } from "@/lib/accents";
import { Plus, Trash2, Loader2, ArrowLeft, ExternalLink } from "lucide-react";
import { toast } from "sonner";

const empty = {
  slug: "", templateId: "beige-luxury", accent: "gold", status: "draft",
  identity: { fullName: "", jobTitle: "", company: "", companyLogo: "", profilePhoto: "", bio: "", city: "", country: "", availabilityBadge: "" },
  contact: { phone: "", whatsapp: "", email: "", website: "", address: "", mapsUrl: "" },
  social: { linkedin: "", instagram: "", x: "", youtube: "", tiktok: "" },
  actions: [], services: [], projects: [], booking: { bookingUrl: "" },
};

const Field = ({ label, children }) => (
  <div className="space-y-1.5">
    <Label className="text-xs text-neutral-600">{label}</Label>
    {children}
  </div>
);

export default function CardEditor({ initial, onBack, onSaved }) {
  const [form, setForm] = useState(() => ({ ...empty, ...initial, identity: { ...empty.identity, ...(initial?.identity) }, contact: { ...empty.contact, ...(initial?.contact) }, social: { ...empty.social, ...(initial?.social) }, booking: { ...empty.booking, ...(initial?.booking) }, services: initial?.services || [], projects: initial?.projects || [] }));
  const [saving, setSaving] = useState(false);
  const isNew = !initial?.id;

  const set = (path, value) => {
    setForm((f) => {
      const next = { ...f };
      if (path.includes(".")) {
        const [g, k] = path.split(".");
        next[g] = { ...next[g], [k]: value };
      } else {
        next[path] = value;
      }
      return next;
    });
  };

  const setService = (i, k, v) => setForm((f) => { const s = [...f.services]; s[i] = { ...s[i], [k]: v }; return { ...f, services: s }; });
  const addService = () => setForm((f) => ({ ...f, services: [...f.services, { icon: "Sparkles", title: "", description: "", ctaUrl: "", order: f.services.length, enabled: true }] }));
  const delService = (i) => setForm((f) => ({ ...f, services: f.services.filter((_, x) => x !== i) }));

  const setProject = (i, k, v) => setForm((f) => { const p = [...f.projects]; p[i] = { ...p[i], [k]: v }; return { ...f, projects: p }; });
  const addProject = () => setForm((f) => ({ ...f, projects: [...f.projects, { coverImage: "", name: "", category: "", description: "", url: "", order: f.projects.length }] }));
  const delProject = (i) => setForm((f) => ({ ...f, projects: f.projects.filter((_, x) => x !== i) }));

  const save = async () => {
    if (!form.slug.trim()) { toast.error("Slug is required"); return; }
    setSaving(true);
    try {
      const payload = { ...form, slug: form.slug.trim().toLowerCase().replace(/\s+/g, "-") };
      if (isNew) await api.post("/admin/cards", payload);
      else await api.put(`/admin/cards/${initial.id}`, payload);
      toast.success("Card saved");
      onSaved();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
      {/* FORM */}
      <div>
        <div className="mb-6 flex items-center justify-between">
          <button onClick={onBack} className="flex items-center gap-2 text-sm text-neutral-500 hover:text-neutral-900" data-testid="editor-back">
            <ArrowLeft className="w-4 h-4" /> Back
          </button>
          <div className="flex items-center gap-3">
            {form.status === "published" && form.slug ? (
              <a href={`/${form.slug}`} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-sm text-neutral-500 hover:text-neutral-900" data-testid="editor-view-live">
                View live <ExternalLink className="w-3.5 h-3.5" />
              </a>
            ) : null}
            <Button onClick={save} disabled={saving} data-testid="admin-save-button">
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : "Save card"}
            </Button>
          </div>
        </div>

        <div className="mb-6 grid grid-cols-2 lg:grid-cols-4 gap-4 rounded-lg border border-neutral-200 p-4">
          <Field label="Slug (URL)">
            <Input value={form.slug} onChange={(e) => set("slug", e.target.value)} placeholder="feras-askar" data-testid="editor-slug" />
          </Field>
          <Field label="Template">
            <Select value={form.templateId} onValueChange={(v) => set("templateId", v)}>
              <SelectTrigger data-testid="editor-template"><SelectValue /></SelectTrigger>
              <SelectContent>
                {TEMPLATES.map((t) => <SelectItem key={t.id} value={t.id}>{t.name}</SelectItem>)}
              </SelectContent>
            </Select>
          </Field>
          <Field label="Accent">
            <Select value={form.accent} onValueChange={(v) => set("accent", v)}>
              <SelectTrigger data-testid="editor-accent"><SelectValue /></SelectTrigger>
              <SelectContent>
                {ACCENT_OPTIONS.map((a) => <SelectItem key={a.id} value={a.id}>{a.label}</SelectItem>)}
              </SelectContent>
            </Select>
          </Field>
          <div className="flex items-center gap-3 pt-6">
            <Switch checked={form.status === "published"} onCheckedChange={(v) => set("status", v ? "published" : "draft")} data-testid="editor-published" />
            <span className="text-sm text-neutral-700">{form.status === "published" ? "Published" : "Draft"}</span>
          </div>
        </div>

        <Tabs defaultValue="identity">
          <TabsList className="flex flex-wrap h-auto">
            <TabsTrigger value="identity">Identity</TabsTrigger>
            <TabsTrigger value="contact">Contact</TabsTrigger>
            <TabsTrigger value="social">Social</TabsTrigger>
            <TabsTrigger value="services">Services</TabsTrigger>
            <TabsTrigger value="projects">Projects</TabsTrigger>
            <TabsTrigger value="booking">Booking</TabsTrigger>
          </TabsList>

          <TabsContent value="identity" className="space-y-4 pt-4">
            <ImageUploadField label="Profile photo" value={form.identity.profilePhoto} onChange={(v) => set("identity.profilePhoto", v)} testId="upload-photo" />
            <div className="grid grid-cols-2 gap-3">
              <Field label="Full name"><Input value={form.identity.fullName} onChange={(e) => set("identity.fullName", e.target.value)} data-testid="editor-fullname" /></Field>
              <Field label="Job title"><Input value={form.identity.jobTitle} onChange={(e) => set("identity.jobTitle", e.target.value)} /></Field>
              <Field label="Company"><Input value={form.identity.company} onChange={(e) => set("identity.company", e.target.value)} /></Field>
              <Field label="Availability badge"><Input value={form.identity.availabilityBadge} onChange={(e) => set("identity.availabilityBadge", e.target.value)} placeholder="Available for Work" /></Field>
              <Field label="City"><Input value={form.identity.city} onChange={(e) => set("identity.city", e.target.value)} /></Field>
              <Field label="Country"><Input value={form.identity.country} onChange={(e) => set("identity.country", e.target.value)} /></Field>
            </div>
            <Field label="Bio"><Textarea value={form.identity.bio} onChange={(e) => set("identity.bio", e.target.value)} rows={3} /></Field>
          </TabsContent>

          <TabsContent value="contact" className="space-y-3 pt-4">
            {["phone", "whatsapp", "email", "website", "address", "mapsUrl"].map((k) => (
              <Field key={k} label={k}><Input value={form.contact[k]} onChange={(e) => set(`contact.${k}`, e.target.value)} data-testid={`editor-contact-${k}`} /></Field>
            ))}
          </TabsContent>

          <TabsContent value="social" className="space-y-3 pt-4">
            {["linkedin", "instagram", "x", "youtube", "tiktok"].map((k) => (
              <Field key={k} label={k}><Input value={form.social[k]} onChange={(e) => set(`social.${k}`, e.target.value)} placeholder="https://" /></Field>
            ))}
          </TabsContent>

          <TabsContent value="services" className="space-y-4 pt-4">
            {form.services.map((s, i) => (
              <div key={i} className="rounded-lg border border-neutral-200 p-4 space-y-3" data-testid={`editor-service-${i}`}>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-neutral-500">Service {i + 1}</span>
                  <button onClick={() => delService(i)} className="text-red-500" data-testid={`del-service-${i}`}><Trash2 className="w-4 h-4" /></button>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="Icon (lucide name)"><Input value={s.icon} onChange={(e) => setService(i, "icon", e.target.value)} placeholder="Building2" /></Field>
                  <Field label="Title"><Input value={s.title} onChange={(e) => setService(i, "title", e.target.value)} /></Field>
                </div>
                <Field label="Description"><Textarea value={s.description} onChange={(e) => setService(i, "description", e.target.value)} rows={2} /></Field>
              </div>
            ))}
            <Button variant="outline" onClick={addService} data-testid="add-service"><Plus className="w-4 h-4 mr-1" /> Add service</Button>
          </TabsContent>

          <TabsContent value="projects" className="space-y-4 pt-4">
            {form.projects.map((p, i) => (
              <div key={i} className="rounded-lg border border-neutral-200 p-4 space-y-3" data-testid={`editor-project-${i}`}>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-neutral-500">Project {i + 1}</span>
                  <button onClick={() => delProject(i)} className="text-red-500" data-testid={`del-project-${i}`}><Trash2 className="w-4 h-4" /></button>
                </div>
                <ImageUploadField label="Cover image" value={p.coverImage} onChange={(v) => setProject(i, "coverImage", v)} testId={`upload-project-${i}`} />
                <div className="grid grid-cols-2 gap-3">
                  <Field label="Name"><Input value={p.name} onChange={(e) => setProject(i, "name", e.target.value)} /></Field>
                  <Field label="Category"><Input value={p.category} onChange={(e) => setProject(i, "category", e.target.value)} /></Field>
                </div>
                <Field label="Description"><Input value={p.description} onChange={(e) => setProject(i, "description", e.target.value)} /></Field>
                <Field label="Link URL"><Input value={p.url} onChange={(e) => setProject(i, "url", e.target.value)} /></Field>
              </div>
            ))}
            <Button variant="outline" onClick={addProject} data-testid="add-project"><Plus className="w-4 h-4 mr-1" /> Add project</Button>
          </TabsContent>

          <TabsContent value="booking" className="space-y-3 pt-4">
            <Field label="Booking URL (Calendly / Cal.com)"><Input value={form.booking.bookingUrl} onChange={(e) => set("booking.bookingUrl", e.target.value)} data-testid="editor-booking" /></Field>
          </TabsContent>
        </Tabs>
      </div>

      {/* LIVE PREVIEW */}
      <div className="lg:sticky lg:top-6 h-fit">
        <p className="mb-3 text-xs uppercase tracking-widest text-neutral-400">Live preview</p>
        <div className="overflow-hidden rounded-xl border border-neutral-200 shadow-sm" style={{ height: "78vh" }}>
          <div className="h-full overflow-y-auto" data-testid="editor-preview">
            <TemplateRenderer data={form} />
          </div>
        </div>
      </div>
    </div>
  );
}
