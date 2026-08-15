import { useParams, Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { useLocale } from "@/i18n/useLocale";
import { useSeo, breadcrumb } from "@/lib/seo";

// NOTE: Company-specific legal facts are marked with [[ ... ]] and MUST be supplied by TapPresence
// (legal entity name, address, jurisdiction, contact, DPO). Do not treat this as legal advice.
const COMPANY = "[[COMPANY LEGAL NAME]]";
const JURISDICTION = "[[GOVERNING LAW / JURISDICTION]]";
const CONTACT = "legal@tappresence.com";
const PRIVACY_CONTACT = "privacy@tappresence.com";
const EFFECTIVE = "[[EFFECTIVE DATE]]";

const S = ({ h, children }) => (
  <section className="mt-6">
    {h ? <h2 className="text-lg font-medium text-white">{h}</h2> : null}
    <div className="mt-2 space-y-2 text-sm leading-relaxed text-white/65">{children}</div>
  </section>
);

const DOCS = {
  terms: {
    title: "Terms of Service",
    render: () => (
      <>
        <p className="text-xs text-white/40">Effective: {EFFECTIVE}</p>
        <S>These Terms of Service ("Terms") govern your access to and use of TapPresence, operated by {COMPANY} ("TapPresence", "we", "us"). By creating an account or using the service you agree to these Terms.</S>
        <S h="1. The service">TapPresence provides digital business cards, sharing (QR/NFC/link), lead capture, a lightweight contact pipeline, a business-card/QR scanner, meeting booking, analytics, email signatures, teams and referrals, delivered as a web application.</S>
        <S h="2. Accounts & trial">New accounts include a 14-day free trial. After the trial you must subscribe to a paid plan to continue using premium features. You are responsible for your credentials and all activity under your account, and must provide accurate information.</S>
        <S h="3. Plans, billing & renewal">Paid plans are billed monthly or annually through our payment processor. Subscriptions renew automatically until cancelled. You may cancel at any time; access continues until the end of the current billing period. Prices may vary by region/currency. Taxes may apply. Fees are non-refundable except where required by law.</S>
        <S h="4. Acceptable use">You agree not to misuse the service, including unlawful, infringing, deceptive, or abusive activity, scraping, reverse engineering, sending spam, or capturing personal data without a lawful basis and appropriate notice/consent. You are responsible for the contacts and content you upload.</S>
        <S h="5. Your content">You retain ownership of the content you submit. You grant TapPresence a limited licence to host, process and display it solely to operate the service. You represent you have the rights and consents necessary for the data (including leads) you collect.</S>
        <S h="6. Teams">Workspace owners/admins control members, shared cards and locked branding. Removing a member does not delete data owned by other members of the workspace.</S>
        <S h="7. Suspension & termination">We may suspend or terminate accounts that violate these Terms or create risk to the service or others. You may delete your account at any time from Settings; deletion removes data you own and cannot be undone.</S>
        <S h="8. Disclaimers & liability">The service is provided "as is". To the maximum extent permitted by law, TapPresence disclaims implied warranties and is not liable for indirect or consequential damages. Nothing limits liability that cannot be limited by law.</S>
        <S h="9. Changes">We may update these Terms; material changes will be notified in-app or by email. Continued use after changes constitutes acceptance.</S>
        <S h="10. Governing law">These Terms are governed by the laws of {JURISDICTION}. Contact: {CONTACT}.</S>
      </>
    ),
  },
  privacy: {
    title: "Privacy Policy",
    render: () => (
      <>
        <p className="text-xs text-white/40">Effective: {EFFECTIVE}</p>
        <S>{COMPANY} ("TapPresence") respects your privacy. This policy explains what we collect, why, and your rights.</S>
        <S h="Data we collect">Account data (name, email, password hash, locale/market); card content you create; leads/contacts you capture (name, email, phone, company, notes, event/campaign); meeting details; usage/analytics events (views, scans, taps, NFC taps); and device/log data needed for security.</S>
        <S h="How we use it">To provide and secure the service, operate your cards/leads/meetings/analytics, process subscriptions, prevent abuse, provide support, and communicate service and account messages. We do not sell your personal data.</S>
        <S h="Legal bases">Performance of our contract with you, our legitimate interests in operating and securing the service, your consent (e.g., non-essential cookies/analytics), and compliance with legal obligations.</S>
        <S h="Sharing & processors">We use service providers (hosting/database, payment processor, transactional email, AI processing for scanner OCR and follow-up drafts) that process data on our behalf under contract. We may disclose data where required by law.</S>
        <S h="International transfers">Where data is processed in other countries, we rely on appropriate safeguards as required by applicable law.</S>
        <S h="Retention">We keep data while your account is active and as needed for legal/operational purposes. You can export or delete your data at any time from Settings.</S>
        <S h="Your rights">Subject to your jurisdiction, you may access, correct, export, restrict, or delete your personal data, and object to certain processing. Contact {PRIVACY_CONTACT}. Data controller: {COMPANY}, [[REGISTERED ADDRESS]]. [[DPO / EU-UK REPRESENTATIVE IF APPLICABLE]].</S>
        <S h="Security">We use encryption in transit, hashed passwords, access controls, rate limiting and tenant isolation. No system is perfectly secure; report concerns to {PRIVACY_CONTACT}.</S>
      </>
    ),
  },
  cookies: {
    title: "Cookie & Consent Notice",
    render: () => (
      <>
        <S>TapPresence uses a minimal set of storage and cookies. Essential storage (authentication tokens, language preference) is required for the service to function and cannot be disabled.</S>
        <S h="Analytics & consent">Public-card analytics are gated by your consent banner. Where required, non-essential analytics run only after you accept. You can withdraw consent from the Privacy Center at any time.</S>
        <S h="What we store">Essential: session/refresh tokens, language preference, consent choice. Analytics: aggregate card views, scans, taps and NFC events used to give owners performance insights. We do not use third-party advertising cookies.</S>
        <S h="Managing preferences">Adjust choices via the consent banner / Privacy Center, or clear site data in your browser. Questions: {PRIVACY_CONTACT}.</S>
      </>
    ),
  },
  data: {
    title: "Account & Data Deletion",
    render: () => (
      <>
        <S>You are in control of your data. You can export or permanently delete your account from Settings → Data & privacy.</S>
        <S h="Export">Download a machine-readable copy of your account, cards, leads and related data at any time.</S>
        <S h="Deletion">Deleting your account permanently removes the data you own (your cards, leads, analytics, meetings, notifications, referral records and API keys) and revokes your sessions. Data belonging to other members of a shared workspace is preserved. Deletion is irreversible.</S>
        <S h="How to request">Use Settings → Delete account, or email {PRIVACY_CONTACT} and we will action verified requests within the timeframe required by applicable law.</S>
      </>
    ),
  },
};

export default function Legal() {
  const { doc } = useParams();
  const { t } = useLocale();
  const c = DOCS[doc];
  useSeo({
    title: c ? `${c.title || doc} — TapPresence` : "Legal — TapPresence",
    description: c ? `TapPresence ${(c.title || doc)}. Read our legal terms, privacy and policies.` : "TapPresence legal documents — terms, privacy and policies.",
    path: doc ? `/legal/${doc}` : "/legal",
    noindex: !c,
    jsonLd: c ? [breadcrumb([{ name: "Home", path: "/" }, { name: "Legal", path: "/legal" }, { name: c.title || doc, path: `/legal/${doc}` }])] : undefined,
  });
  return (
    <div className="aria-dark relative min-h-screen overflow-hidden bg-[#0B0D12] text-white" style={{ fontFamily: "'Outfit', sans-serif" }}>
      <div className="grain-overlay" style={{ opacity: 0.05 }} />
      <div className="relative mx-auto max-w-2xl px-6 py-16">
        <Link to="/" className="inline-flex items-center gap-2 text-sm text-white/60 transition-colors hover:text-white" data-testid="legal-back">
          <ArrowLeft className="h-4 w-4" /> {t("legal.backHome")}
        </Link>
        <div className="mt-8 rounded-2xl border border-white/10 bg-white/[0.03] p-8">
          <div className="flex items-center gap-3">
            <img src="/tp-mark.png" alt="TapPresence" className="h-6 w-6 object-contain" />
            <span className="text-[15px] font-semibold tracking-tight">TapPresence</span>
          </div>
          <h1 className="mt-6 text-3xl font-medium tracking-tight text-white" data-testid="legal-title">{c ? c.title : t("legal.notFound")}</h1>
          {c ? c.render() : null}
          <div className="mt-10 flex flex-wrap gap-3 border-t border-white/8 pt-6 text-sm">
            <Link to="/legal/terms" className="text-white/55 hover:text-[#D4AF37]" data-testid="legal-link-terms">Terms</Link>
            <Link to="/legal/privacy" className="text-white/55 hover:text-[#D4AF37]" data-testid="legal-link-privacy">Privacy</Link>
            <Link to="/legal/cookies" className="text-white/55 hover:text-[#D4AF37]" data-testid="legal-link-cookies">Cookies</Link>
            <Link to="/legal/data" className="text-white/55 hover:text-[#D4AF37]" data-testid="legal-link-data">Data deletion</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
