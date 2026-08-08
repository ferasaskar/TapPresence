import { useState } from "react";
import { Loader2, Check } from "lucide-react";
import { api } from "@/lib/api";
import { toast } from "sonner";

const V = {
  beige: {
    card: "rounded-lg border border-ivory-border bg-ivory-surface p-7",
    heading: "font-serif text-3xl tracking-tight text-ink",
    sub: "text-ink-soft",
    input: "w-full rounded-md border border-ivory-border bg-white px-4 py-3 text-sm text-ink placeholder:text-ink-soft/50 outline-none transition-colors focus:border-[color:var(--ac,#B89973)]",
    btn: "w-full rounded-md bg-ink px-4 py-3.5 text-sm tracking-wide text-ivory-bg transition-colors duration-300 hover:bg-ink-soft disabled:opacity-60",
    ok: "text-ink",
  },
  black: {
    card: "rounded-xl border p-7",
    cardStyle: { borderColor: "rgba(255,255,255,0.12)", backgroundColor: "#111112" },
    heading: "font-serif text-3xl tracking-tight text-neutral-100",
    sub: "text-neutral-400",
    input: "w-full rounded-md border px-4 py-3 text-sm text-neutral-100 placeholder:text-neutral-600 outline-none transition-colors",
    inputStyle: { borderColor: "rgba(255,255,255,0.12)", backgroundColor: "#0B0B0C" },
    btn: "w-full rounded-full px-4 py-3.5 text-sm font-medium uppercase tracking-widest text-black transition-transform duration-300 hover:scale-[1.01] disabled:opacity-60",
    btnStyle: { background: "linear-gradient(90deg,#E7C56B,#C9A24B,#8f7328)" },
    ok: "text-neutral-100",
  },
  future: {
    card: "rounded-2xl border border-white/10 bg-white/[0.04] backdrop-blur-xl p-7",
    heading: "text-3xl font-semibold tracking-tight text-white",
    sub: "text-slate-400",
    input: "w-full rounded-xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-white placeholder:text-slate-500 outline-none transition-colors focus:border-sky-400/60",
    btn: "w-full rounded-full px-4 py-3.5 text-sm font-semibold uppercase tracking-widest text-white transition-transform duration-300 hover:scale-[1.01] disabled:opacity-60",
    btnStyle: { background: "linear-gradient(90deg,#6d5cff,#2b8cff)" },
    ok: "text-white",
  },
};

export const InquiryForm = ({ slug, variant = "beige", accentColor = "#B89973" }) => {
  const v = V[variant] || V.beige;
  const [form, setForm] = useState({ name: "", email: "", phone: "", message: "" });
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    if (!form.name.trim() || (!form.email.trim() && !form.phone.trim())) {
      toast.error("Please add your name and an email or phone");
      return;
    }
    setLoading(true);
    try {
      await api.post(`/cards/${slug}/leads`, form);
      setSent(true);
      toast.success("Message sent — thank you");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not send your message");
    } finally {
      setLoading(false);
    }
  };

  if (sent) {
    return (
      <section className={`mt-6 ${v.card} text-center`} style={v.cardStyle} data-testid="inquiry-success">
        <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full" style={{ background: accentColor }}>
          <Check className="w-6 h-6 text-white" />
        </div>
        <h2 className={`${v.heading} mb-1`}>Message sent</h2>
        <p className={`text-sm ${v.sub}`}>Thank you — I'll be in touch shortly.</p>
      </section>
    );
  }

  return (
    <section className={`mt-6 ${v.card}`} style={v.cardStyle} data-testid="inquiry-form">
      <p className="text-[11px] uppercase tracking-[0.35em] mb-2" style={{ color: accentColor }}>Get in touch</p>
      <h2 className={`${v.heading} mb-5`}>Send a message</h2>
      <form onSubmit={submit} className="space-y-3">
        <input className={v.input} style={v.inputStyle} placeholder="Your name" value={form.name} onChange={set("name")} data-testid="inquiry-name" />
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <input className={v.input} style={v.inputStyle} type="email" placeholder="Email" value={form.email} onChange={set("email")} data-testid="inquiry-email" />
          <input className={v.input} style={v.inputStyle} placeholder="Phone" value={form.phone} onChange={set("phone")} data-testid="inquiry-phone" />
        </div>
        <textarea className={v.input} style={v.inputStyle} rows={3} placeholder="How can I help?" value={form.message} onChange={set("message")} data-testid="inquiry-message" />
        <button type="submit" className={v.btn} style={v.btnStyle} disabled={loading} data-testid="inquiry-submit">
          {loading ? <Loader2 className="mx-auto w-4 h-4 animate-spin" /> : "Send message"}
        </button>
      </form>
    </section>
  );
};
