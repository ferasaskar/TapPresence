import { useParams, Link } from "react-router-dom";

const CONTENT = {
  privacy: { title: "Privacy Policy", body: "This is placeholder privacy policy content for ARIADNI ID. Final approved legal language will be inserted here before launch. We describe what data we collect (profile info, leads you receive, analytics events), how it is used, retention, and your rights to export or delete your data." },
  terms: { title: "Terms of Service", body: "This is placeholder terms of service content for ARIADNI ID. Final approved legal language will be inserted here before launch. It covers acceptable use, subscriptions and billing, NFC hardware, and account termination." },
};

export default function Legal() {
  const { doc } = useParams();
  const c = CONTENT[doc] || { title: "Not found", body: "" };
  return (
    <div className="min-h-screen bg-ivory-bg font-sans text-ink">
      <div className="mx-auto max-w-2xl px-6 py-16">
        <Link to="/" className="font-serif text-2xl tracking-tight">ARIADNI <span className="text-[#B89973]">ID</span></Link>
        <h1 className="mt-8 font-serif text-4xl tracking-tight" data-testid="legal-title">{c.title}</h1>
        <p className="mt-2 text-xs uppercase tracking-widest text-[#B89973]">Placeholder — pending legal review</p>
        <p className="mt-6 leading-relaxed text-ink-soft">{c.body}</p>
      </div>
    </div>
  );
}
