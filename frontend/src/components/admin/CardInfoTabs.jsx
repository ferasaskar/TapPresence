import { ImageUploadField } from "@/components/admin/ImageUploadField";
import IndustryCustomizer from "@/components/admin/IndustryCustomizer";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Plus, Trash2 } from "lucide-react";

// Shared blank card. New cards default to the premium dark base (hidden from
// customers); existing cards keep their own templateId when edited.
export const emptyCard = {
  slug: "", templateId: "executive-black-gold", accent: "gold", custom_accent_color: "", status: "draft",
  industry: "", background_style: "", background_opacity: 0.14, background_intensity: "medium", background_position: "center", custom_background: "",
  identity: { fullName: "", jobTitle: "", company: "", companyLogo: "", profilePhoto: "", bio: "", city: "", country: "", availabilityBadge: "" },
  contact: { phone: "", whatsapp: "", email: "", website: "", address: "", mapsUrl: "" },
  social: { linkedin: "", instagram: "", x: "", youtube: "", tiktok: "" },
  actions: [], services: [], projects: [], booking: { bookingUrl: "" },
};

export const mergeCard = (initial) => ({
  ...emptyCard, ...initial,
  identity: { ...emptyCard.identity, ...(initial?.identity) },
  contact: { ...emptyCard.contact, ...(initial?.contact) },
  social: { ...emptyCard.social, ...(initial?.social) },
  booking: { ...emptyCard.booking, ...(initial?.booking) },
  services: initial?.services || [], projects: initial?.projects || [],
});

const Field = ({ label, children }) => (
  <div className="space-y-1.5">
    <Label className="text-xs text-white/55">{label}</Label>
    {children}
  </div>
);

const panelCls = "rounded-xl border border-white/10 bg-white/[0.02] p-4";
const tabTrigger = "rounded-lg px-3.5 py-2 text-sm text-white/55 transition-all data-[state=active]:bg-[#D6A653] data-[state=active]:text-[#050607] data-[state=active]:font-medium hover:text-white";

export default function CardInfoTabs({ form, setForm, showIndustry = true }) {
  const set = (path, value) => {
    setForm((f) => {
      const next = { ...f };
      if (path.includes(".")) { const [g, k] = path.split("."); next[g] = { ...next[g], [k]: value }; }
      else next[path] = value;
      return next;
    });
  };
  const setService = (i, k, v) => setForm((f) => { const s = [...f.services]; s[i] = { ...s[i], [k]: v }; return { ...f, services: s }; });
  const addService = () => setForm((f) => ({ ...f, services: [...f.services, { icon: "Sparkles", title: "", description: "", ctaUrl: "", order: f.services.length, enabled: true }] }));
  const delService = (i) => setForm((f) => ({ ...f, services: f.services.filter((_, x) => x !== i) }));
  const setProject = (i, k, v) => setForm((f) => { const p = [...f.projects]; p[i] = { ...p[i], [k]: v }; return { ...f, projects: p }; });
  const addProject = () => setForm((f) => ({ ...f, projects: [...f.projects, { coverImage: "", name: "", category: "", description: "", url: "", order: f.projects.length }] }));
  const delProject = (i) => setForm((f) => ({ ...f, projects: f.projects.filter((_, x) => x !== i) }));

  return (
    <Tabs defaultValue="identity">
      <TabsList className="flex h-auto flex-wrap gap-1 rounded-xl border border-white/10 bg-white/[0.03] p-1.5">
        <TabsTrigger value="identity" className={tabTrigger}>Identity</TabsTrigger>
        {showIndustry && <TabsTrigger value="industry" className={tabTrigger} data-testid="tab-industry">Industry</TabsTrigger>}
        <TabsTrigger value="contact" className={tabTrigger}>Contact</TabsTrigger>
        <TabsTrigger value="social" className={tabTrigger}>Social</TabsTrigger>
        <TabsTrigger value="services" className={tabTrigger}>Services</TabsTrigger>
        <TabsTrigger value="projects" className={tabTrigger}>Projects</TabsTrigger>
        <TabsTrigger value="booking" className={tabTrigger}>Booking</TabsTrigger>
      </TabsList>

      <TabsContent value="identity" className="space-y-4 pt-5">
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

      {showIndustry && (
        <TabsContent value="industry" className="pt-5">
          <IndustryCustomizer form={form} set={set} />
        </TabsContent>
      )}

      <TabsContent value="contact" className="space-y-3 pt-5">
        {["phone", "whatsapp", "email", "website", "address", "mapsUrl"].map((k) => (
          <Field key={k} label={k}><Input value={form.contact[k]} onChange={(e) => set(`contact.${k}`, e.target.value)} data-testid={`editor-contact-${k}`} /></Field>
        ))}
      </TabsContent>

      <TabsContent value="social" className="space-y-3 pt-5">
        {["linkedin", "instagram", "x", "youtube", "tiktok"].map((k) => (
          <Field key={k} label={k}><Input value={form.social[k]} onChange={(e) => set(`social.${k}`, e.target.value)} placeholder="https://" /></Field>
        ))}
      </TabsContent>

      <TabsContent value="services" className="space-y-4 pt-5">
        {form.services.map((s, i) => (
          <div key={i} className={`${panelCls} space-y-3`} data-testid={`editor-service-${i}`}>
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-white/50">Service {i + 1}</span>
              <button onClick={() => delService(i)} className="text-red-400/80 hover:text-red-400" data-testid={`del-service-${i}`}><Trash2 className="h-4 w-4" /></button>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Icon (lucide name)"><Input value={s.icon} onChange={(e) => setService(i, "icon", e.target.value)} placeholder="Building2" /></Field>
              <Field label="Title"><Input value={s.title} onChange={(e) => setService(i, "title", e.target.value)} /></Field>
            </div>
            <Field label="Description"><Textarea value={s.description} onChange={(e) => setService(i, "description", e.target.value)} rows={2} /></Field>
          </div>
        ))}
        <Button onClick={addService} className="rounded-lg border border-white/15 bg-transparent text-white hover:bg-white/5" data-testid="add-service"><Plus className="mr-1 h-4 w-4" /> Add service</Button>
      </TabsContent>

      <TabsContent value="projects" className="space-y-4 pt-5">
        {form.projects.map((p, i) => (
          <div key={i} className={`${panelCls} space-y-3`} data-testid={`editor-project-${i}`}>
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-white/50">Project {i + 1}</span>
              <button onClick={() => delProject(i)} className="text-red-400/80 hover:text-red-400" data-testid={`del-project-${i}`}><Trash2 className="h-4 w-4" /></button>
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
        <Button onClick={addProject} className="rounded-lg border border-white/15 bg-transparent text-white hover:bg-white/5" data-testid="add-project"><Plus className="mr-1 h-4 w-4" /> Add project</Button>
      </TabsContent>

      <TabsContent value="booking" className="space-y-3 pt-5">
        <Field label="Booking URL (Calendly / Cal.com)"><Input value={form.booking.bookingUrl} onChange={(e) => set("booking.bookingUrl", e.target.value)} data-testid="editor-booking" /></Field>
      </TabsContent>
    </Tabs>
  );
}
