import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import { Nfc, QrCode, Wallet, ScanLine, Users, Sparkles, ArrowRight, Repeat } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const Feature = ({ icon: Icon, title, desc }) => (
  <div className="rounded-xl border border-ivory-border bg-white p-6 transition-all duration-300 hover:-translate-y-1 hover:border-[color:#B89973]" data-testid={`feature-${title.toLowerCase().replace(/\s+/g,'-')}`}>
    <span className="mb-4 inline-flex h-11 w-11 items-center justify-center rounded-lg" style={{ background: "rgba(184,153,115,0.12)" }}>
      <Icon className="w-5 h-5 text-[#B89973]" strokeWidth={1.5} />
    </span>
    <h3 className="font-serif text-xl tracking-tight text-ink">{title}</h3>
    <p className="mt-1 text-sm text-ink-soft leading-relaxed">{desc}</p>
  </div>
);

const money = (c) => c == null ? "Custom" : c === 0 ? "$0" : `$${(c / 100).toFixed(c % 100 ? 2 : 0)}`;

export default function Landing() {
  const [plans, setPlans] = useState([]);
  useEffect(() => { api.get("/plans").then((r) => setPlans(r.data.filter((p) => p.public))).catch(() => {}); }, []);

  return (
    <div className="min-h-screen bg-ivory-bg text-ink font-sans">
      {/* NAV */}
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <span className="font-serif text-2xl tracking-tight" data-testid="brand">ARIADNI <span className="text-[#B89973]">ID</span></span>
        <nav className="flex items-center gap-3 text-sm">
          <Link to="/login" className="text-ink-soft hover:text-ink" data-testid="nav-login">Sign in</Link>
          <Link to="/register" className="rounded-md bg-ink px-4 py-2 text-ivory-bg transition-colors hover:bg-ink-soft" data-testid="nav-register">Create your ID</Link>
        </nav>
      </header>

      {/* HERO */}
      <section className="mx-auto grid max-w-6xl grid-cols-1 items-center gap-12 px-6 pt-10 pb-20 lg:grid-cols-2">
        <div>
          <p className="text-xs uppercase tracking-[0.35em] text-[#B89973]">Premium Digital Identity & Networking</p>
          <h1 className="mt-5 font-serif text-5xl leading-[1.05] tracking-tight sm:text-6xl">
            Meet. Connect.<br />Follow&nbsp;Up. <span className="text-[#B89973]">Convert.</span>
          </h1>
          <p className="mt-6 max-w-md text-base leading-relaxed text-ink-soft">
            The digital business card is only the entry point. ARIADNI ID turns every introduction into a captured lead, an AI follow-up, and a closed deal — with NFC, Wallet, QR, and a world-class profile.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/register" className="inline-flex items-center gap-2 rounded-md bg-ink px-6 py-3.5 text-sm tracking-wide text-ivory-bg transition-colors hover:bg-ink-soft" data-testid="cta-create">
              Create your ID <ArrowRight className="w-4 h-4" />
            </Link>
            <Link to="/register?intent=nfc" className="inline-flex items-center gap-2 rounded-md border border-ink/20 px-6 py-3.5 text-sm tracking-wide transition-colors hover:bg-ivory-hover" data-testid="cta-nfc">
              <Nfc className="w-4 h-4 text-[#B89973]" /> Get NFC Card
            </Link>
            <Link to="/register?intent=team" className="inline-flex items-center gap-2 rounded-md border border-ink/20 px-6 py-3.5 text-sm tracking-wide transition-colors hover:bg-ivory-hover" data-testid="cta-team">
              <Users className="w-4 h-4 text-[#B89973]" /> For Teams
            </Link>
          </div>
        </div>
        {/* Live phone mockup */}
        <div className="flex justify-center">
          <div className="relative rounded-[2.5rem] border-[10px] border-ink bg-ink p-0 shadow-2xl" style={{ width: 300, height: 620 }}>
            <div className="absolute left-1/2 top-3 z-10 h-5 w-28 -translate-x-1/2 rounded-full bg-ink" />
            <iframe
              title="Live ARIADNI profile"
              src={`${BACKEND_URL.replace('/api','')}/feras-askar`}
              className="h-full w-full rounded-[1.8rem] bg-white"
              data-testid="hero-live-profile"
            />
          </div>
        </div>
      </section>

      {/* VALUE PROPS */}
      <section className="border-t border-ivory-border bg-white/60 py-20">
        <div className="mx-auto max-w-6xl px-6">
          <h2 className="font-serif text-4xl tracking-tight">One tap. A full networking engine.</h2>
          <div className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <Feature icon={Sparkles} title="Premium Profiles" desc="Three hand-crafted luxury templates with gold, platinum & rose accents." />
            <Feature icon={Nfc} title="NFC & QR" desc="Tap a card or scan a code — no app needed for the person you meet." />
            <Feature icon={Wallet} title="Apple & Google Wallet" desc="Your identity, always one swipe away in the phone wallet." />
            <Feature icon={Repeat} title="Contact Exchange" desc="Capture their details and send yours back — mutually, instantly." />
            <Feature icon={ScanLine} title="Card & Badge Scanner" desc="Scan paper cards and event badges straight into your CRM." />
            <Feature icon={Sparkles} title="AI Follow-Up" desc="Draft the perfect follow-up in seconds. You review, you send." />
          </div>
        </div>
      </section>

      {/* VERTICALS */}
      <section className="py-20">
        <div className="mx-auto max-w-6xl px-6">
          <p className="text-xs uppercase tracking-[0.35em] text-[#B89973]">Built for how you sell</p>
          <h2 className="mt-4 font-serif text-4xl tracking-tight">Industry-smart identities</h2>
          <div className="mt-10 grid grid-cols-2 gap-4 md:grid-cols-4">
            {["Real Estate", "Sales", "Consultants", "Founders / Tech", "Automotive", "Healthcare", "Agencies", "Enterprise"].map((v) => (
              <div key={v} className="rounded-lg border border-ivory-border bg-white p-5 text-center" data-testid={`vertical-${v.toLowerCase().replace(/[^a-z]/g,'')}`}>
                <span className="font-serif text-lg tracking-tight">{v}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* PRICING */}
      <section className="border-t border-ivory-border bg-white/60 py-20" data-testid="pricing">
        <div className="mx-auto max-w-6xl px-6">
          <h2 className="font-serif text-4xl tracking-tight">Simple, premium pricing</h2>
          <div className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {plans.map((p) => (
              <div key={p.id} className="flex flex-col rounded-xl border border-ivory-border bg-white p-7" data-testid={`plan-${p.id}`}>
                <span className="text-xs uppercase tracking-widest text-[#B89973]">{p.name}</span>
                <div className="mt-3 font-serif text-4xl tracking-tight">
                  {money(p.price_month)}{p.price_month ? <span className="text-base text-ink-soft">/mo</span> : null}
                </div>
                {p.per_seat ? <span className="mt-1 text-xs text-ink-soft">per seat, billed annually</span> : null}
                <Link to="/register" className="mt-6 rounded-md bg-ink px-4 py-2.5 text-center text-sm text-ivory-bg transition-colors hover:bg-ink-soft" data-testid={`plan-cta-${p.id}`}>
                  {p.custom ? "Contact sales" : "Get started"}
                </Link>
              </div>
            ))}
          </div>
          <p className="mt-6 text-xs text-ink-soft">Prices are admin-configurable. NFC hardware is a separate one-time purchase.</p>
        </div>
      </section>

      <footer className="border-t border-ivory-border py-10 text-center text-sm text-ink-soft">
        <p className="font-serif text-xl text-ink">ARIADNI ID</p>
        <p className="mt-2">© {new Date().getFullYear()} ARIADNI ID · Premium Digital Identity & Networking Platform</p>
        <div className="mt-3 flex items-center justify-center gap-4 text-xs">
          <Link to="/legal/privacy" className="hover:text-ink" data-testid="footer-privacy">Privacy</Link>
          <Link to="/legal/terms" className="hover:text-ink" data-testid="footer-terms">Terms</Link>
          <Link to="/login" className="hover:text-ink">Sign in</Link>
        </div>
      </footer>
    </div>
  );
}
