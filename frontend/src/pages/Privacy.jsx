import { Link } from "react-router-dom";
import { ArrowLeft, CalendarClock } from "lucide-react";

const CONTACT = "privacy@tappresence.com";
const EFFECTIVE = "June 11, 2026";

const S = ({ h, children, testid }) => (
  <section className="mt-6" data-testid={testid}>
    {h ? <h2 className="text-lg font-medium text-white">{h}</h2> : null}
    <div className="mt-2 space-y-2 text-sm leading-relaxed text-white/65">{children}</div>
  </section>
);

export default function Privacy() {
  return (
    <div className="aria-dark relative min-h-screen overflow-hidden bg-[#0B0D12] text-white" style={{ fontFamily: "'Outfit', sans-serif" }} data-testid="privacy-page">
      <div className="grain-overlay" style={{ opacity: 0.05 }} />
      <div className="relative mx-auto max-w-2xl px-6 py-16">
        <Link to="/" className="inline-flex items-center gap-2 text-sm text-white/60 transition-colors hover:text-white" data-testid="privacy-back">
          <ArrowLeft className="h-4 w-4" /> Back to home
        </Link>

        <div className="mt-8 rounded-2xl border border-white/10 bg-white/[0.03] p-8">
          <div className="flex items-center gap-3">
            <img src="/tp-mark.png" alt="TapPresence" className="h-6 w-6 object-contain" />
            <span className="text-[15px] font-semibold tracking-tight">TapPresence</span>
          </div>
          <h1 className="mt-6 text-3xl font-medium tracking-tight text-white" data-testid="privacy-title">Privacy Policy</h1>
          <p className="mt-2 text-xs text-white/40">Effective: {EFFECTIVE}</p>

          <S>
            TapPresence ("TapPresence", "we", "us") respects your privacy. This Privacy Policy explains what
            information we collect, how we use it, how we handle information obtained through Google APIs, and the
            choices and rights you have. TapPresence is a digital business card and networking platform (digital
            cards, QR/NFC sharing, lead capture, meeting booking, analytics, email signatures, teams and referrals).
          </S>

          {/* Prominent Google section for OAuth verification */}
          <div className="mt-8 rounded-xl border border-[#D4AF37]/30 bg-[#D4AF37]/[0.06] p-5" data-testid="privacy-google-section">
            <div className="flex items-center gap-2">
              <CalendarClock className="h-4 w-4 text-[#D4AF37]" />
              <h2 className="text-lg font-medium text-white">Google Calendar & Google user data</h2>
            </div>
            <div className="mt-3 space-y-3 text-sm leading-relaxed text-white/70">
              <p>
                TapPresence offers an optional Google Calendar integration for its meeting-booking feature. If you
                choose to connect your Google account, we request the Google Calendar events scope
                (<span className="font-mono text-[13px] text-white/80">https://www.googleapis.com/auth/calendar.events</span>).
              </p>
              <p>We use this access <span className="text-white">only</span> to:</p>
              <ul className="ml-5 list-disc space-y-1">
                <li><span className="text-white">Create</span> a calendar event when a meeting is booked through TapPresence.</li>
                <li><span className="text-white">Update / reschedule</span> that event when a booked meeting is rescheduled.</li>
                <li><span className="text-white">Delete</span> that event when the corresponding meeting is cancelled or declined.</li>
              </ul>
              <p>
                TapPresence only creates and manages calendar events that originate from its own booking feature. We do
                not read, modify, or delete unrelated events in your calendar, and we do not use your calendar data for
                any purpose other than syncing the meetings you book through TapPresence.
              </p>
              <p>
                We store the minimum data required to keep this working: your Google account email, OAuth tokens
                (used only to call the Google Calendar API on your behalf), and the identifier of each event we create.
                You can disconnect the integration at any time from Settings → Integrations, which revokes our access
                and deletes the stored connection.
              </p>
              <p className="font-medium text-white">
                We do not sell your Google user data, and we do not use it for advertising.
              </p>
              <p className="text-white/60">
                TapPresence's use and transfer of information received from Google APIs to any other app will adhere to
                the <a href="https://developers.google.com/terms/api-services-user-data-policy" target="_blank" rel="noopener noreferrer" className="text-[#D4AF37] underline underline-offset-2">Google API Services User Data Policy</a>,
                including the Limited Use requirements.
              </p>
            </div>
          </div>

          <S h="Information we collect">
            Account data (name, email, password hash, locale/market); card content you create; leads/contacts you
            capture (name, email, phone, company, notes, event/campaign); meeting details; usage/analytics events
            (views, scans, taps, NFC taps); and device/log data needed for security. If you connect Google Calendar,
            we also process the Google data described in the section above.
          </S>
          <S h="How we use information">
            To provide and secure the service, operate your cards, leads, meetings and analytics, sync bookings to your
            Google Calendar (only if connected), process subscriptions, prevent abuse, provide support, and send
            service and account messages. We do not sell your personal data and we do not use it for advertising.
          </S>
          <S h="Legal bases">
            Performance of our contract with you, our legitimate interests in operating and securing the service, your
            consent (e.g., connecting Google Calendar, non-essential cookies/analytics), and compliance with legal
            obligations.
          </S>
          <S h="Sharing & service providers">
            We use service providers (hosting/database, payment processor, transactional email, and AI processing for
            the business-card scanner and follow-up drafts) that process data on our behalf under contract. We may
            disclose data where required by law. We never sell your data.
          </S>
          <S h="Data retention">
            We keep data while your account is active and as needed for legal or operational purposes. Google Calendar
            tokens and connection data are retained only while the integration is connected and are deleted when you
            disconnect. You can export or delete your data at any time from Settings.
          </S>
          <S h="Your choices & rights">
            Subject to your jurisdiction, you may access, correct, export, restrict, or delete your personal data, and
            object to certain processing. You can disconnect Google Calendar at any time, and withdraw consent for
            non-essential analytics from the Privacy Center. To exercise your rights, contact {CONTACT}.
          </S>
          <S h="Security">
            We use encryption in transit, hashed passwords, access controls, rate limiting and tenant isolation. OAuth
            tokens are stored server-side and never exposed to the browser. No system is perfectly secure; please
            report concerns to {CONTACT}.
          </S>
          <S h="Changes to this policy">
            We may update this policy; material changes will be notified in-app or by email. Continued use after
            changes constitutes acceptance.
          </S>
          <S h="Contact">
            Questions about this policy or your data: <a href={`mailto:${CONTACT}`} className="text-[#D4AF37] underline underline-offset-2">{CONTACT}</a>.
          </S>

          <div className="mt-10 flex flex-wrap gap-3 border-t border-white/8 pt-6 text-sm">
            <Link to="/legal/terms" className="text-white/55 hover:text-[#D4AF37]" data-testid="privacy-link-terms">Terms</Link>
            <Link to="/legal/cookies" className="text-white/55 hover:text-[#D4AF37]" data-testid="privacy-link-cookies">Cookies</Link>
            <Link to="/legal/data" className="text-white/55 hover:text-[#D4AF37]" data-testid="privacy-link-data">Data deletion</Link>
            <Link to="/privacy-center" className="text-white/55 hover:text-[#D4AF37]" data-testid="privacy-link-center">Privacy choices</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
