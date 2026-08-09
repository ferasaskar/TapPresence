import { Phone, Mail, MessageCircle, Download, Nfc, ArrowLeftRight } from "lucide-react";
import { qrUrl } from "@/lib/api";
import { ASSETS } from "./data";

const AriadniMark = ({ className = "", style }) => (
  <svg viewBox="0 0 24 24" className={className} style={style} fill="none" aria-hidden>
    <path d="M12 3 L21 20 L15.6 20 L12 12 L8.4 20 L3 20 Z" fill="currentColor" />
  </svg>
);

const QuickAction = ({ icon: Icon, label }) => (
  <div className="flex flex-col items-center gap-1">
    <div className="flex h-9 w-9 items-center justify-center rounded-full border border-white/12 bg-white/[0.06]">
      <Icon className="h-3.5 w-3.5 text-[#E9C880]" strokeWidth={1.75} />
    </div>
    <span className="text-[8px] tracking-wide text-neutral-400">{label}</span>
  </div>
);

// The phone + physical NFC card resting on a glowing luxury pedestal.
export default function HeroVisual() {
  return (
    <div className="relative mx-auto h-[560px] w-full max-w-[620px] sm:h-[600px]" data-testid="hero-visual">
      {/* ambient particle background */}
      <img src={ASSETS.heroAmbient} alt="" aria-hidden
        className="pointer-events-none absolute inset-0 h-full w-full object-cover opacity-60 mix-blend-screen" />

      {/* pedestal */}
      <div className="absolute bottom-6 left-1/2 -translate-x-1/2">
        <div className="lp-pedestal-glow lp-breathe absolute -top-10 left-1/2 h-40 w-[440px] -translate-x-1/2 rounded-full" />
        <div className="relative flex items-center justify-center">
          <div className="absolute h-[70px] w-[460px] rounded-[50%] border border-[#D6A653]/25" />
          <div className="absolute h-[52px] w-[360px] rounded-[50%] border border-[#D6A653]/35"
            style={{ boxShadow: "0 0 40px rgba(214,166,83,0.35)" }} />
          <div className="absolute h-[34px] w-[250px] rounded-[50%] border border-[#F0CD84]/50" />
        </div>
      </div>

      {/* NFC card (behind, right) */}
      <div className="absolute right-0 top-[132px]" style={{ transform: "rotate(-12deg)" }}>
        <div className="lp-float-card lp-nfc-card relative flex h-[210px] w-[330px] flex-col rounded-[18px] p-5">
          <div className="flex items-start justify-end">
            <Nfc className="h-6 w-6 text-[#D6A653]/85" strokeWidth={1.75} />
          </div>
          <div className="flex flex-1 flex-col items-center justify-center pl-16">
            <AriadniMark className="h-14 w-14 text-[#D6A653]" style={{ filter: "drop-shadow(0 4px 14px rgba(214,166,83,0.35))" }} />
            <div className="mt-1 flex items-center gap-1.5">
              <span className="lp-gold-text text-xl font-semibold tracking-tight">ARIADNI</span>
              <span className="text-xl font-semibold tracking-tight text-neutral-200">ID</span>
            </div>
          </div>
          <div className="flex items-end justify-between">
            <span className="text-[9px] tracking-[0.25em] text-neutral-600">DIGITAL IDENTITY</span>
            <div className="rounded-md bg-white p-1">
              <img src={qrUrl("feras-askar")} alt="Scan ARIADNI profile" className="h-12 w-12" style={{ filter: "sepia(1) saturate(2.2) hue-rotate(2deg) brightness(0.82)" }} />
            </div>
          </div>
        </div>
      </div>

      {/* Phone (front, center-left) */}
      <div className="lp-float absolute left-1/2 top-3" style={{ transform: "translateX(-82%) rotate(3deg)" }}>
        <div className="lp-phone relative h-[500px] w-[248px] rounded-[42px] p-[9px]">
          <div className="absolute left-1/2 top-4 z-20 h-[22px] w-[86px] -translate-x-1/2 rounded-full bg-black" />
          <div className="relative h-full w-full overflow-hidden rounded-[34px] bg-gradient-to-b from-[#0b0c0e] to-[#141518]">
            {/* profile UI */}
            <div className="flex h-full flex-col items-center px-5 pt-10">
              <div className="flex items-center gap-1.5">
                <AriadniMark className="h-4 w-4 text-[#D6A653]" />
                <span className="text-[11px] font-semibold tracking-wide text-neutral-200">ARIADNI <span className="text-[#D6A653]">ID</span></span>
              </div>
              <div className="mt-6 h-[92px] w-[92px] overflow-hidden rounded-full ring-2 ring-[#D6A653]/40">
                <img src={ASSETS.heroPortrait} alt="Alex Morgan" className="h-full w-full object-cover" />
              </div>
              <h3 className="mt-3 text-[17px] font-semibold text-white">Alex Morgan</h3>
              <p className="text-[11px] text-neutral-400">CEO &amp; Founder</p>
              <p className="text-[10px] tracking-[0.2em] text-[#D6A653]">ARIADNI ID</p>

              <div className="mt-5 grid w-full grid-cols-4 gap-2">
                <QuickAction icon={Phone} label="Call" />
                <QuickAction icon={Mail} label="Email" />
                <QuickAction icon={MessageCircle} label="WhatsApp" />
                <QuickAction icon={Download} label="Save" />
              </div>

              <button className="lp-btn-gold mt-5 flex w-full items-center justify-center gap-1.5 rounded-xl py-2.5 text-[12px]">
                <ArrowLeftRight className="h-3.5 w-3.5" /> Exchange Contact
              </button>

              <div className="mt-auto mb-6 flex items-center gap-1.5 text-[10px] text-neutral-500">
                <Nfc className="h-3.5 w-3.5 text-[#D6A653]" /> Tap your card
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
