import { useParams, Link } from "react-router-dom";

const CONTENT = {
  privacy: { title: "Privacy Policy", body: "This is placeholder privacy policy content for ARIADNI ID. Final approved legal language will be inserted here before launch. We describe what data we collect (profile info, leads you receive, analytics events), how it is used, retention, and your rights to export or delete your data." },
  terms: { title: "Terms of Service", body: "This is placeholder terms of service content for ARIADNI ID. Final approved legal language will be inserted here before launch. It covers acceptable use, subscriptions and billing, NFC hardware, and account termination." },
};

export default function Legal() {
  const { doc } = useParams();
  const c = CONTENT[doc] || { title: "Not found", body: "" };
  return (
    <div className="aria-dark relative min-h-screen overflow-hidden bg-[#050607] text-white" style={{ fontFamily: "'Outfit', sans-serif" }}>
      <div className="grain-overlay" style={{ opacity: 0.05 }} />
      <div className="relative mx-auto max-w-2xl px-6 py-16">
        <Link to="/" className="text-lg font-semibold tracking-tight text-white">ARIADNI <span className="text-[#D6A653]">ID</span></Link>
        <div className="mt-8 rounded-2xl border border-white/10 bg-white/[0.03] p-8">
          <h1 className="text-3xl font-medium tracking-tight text-white" data-testid="legal-title">{c.title}</h1>
          <p className="mt-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#D6A653]">Placeholder — pending legal review</p>
          <p className="mt-6 leading-relaxed text-white/65">{c.body}</p>
        </div>
      </div>
    </div>
  );
}
