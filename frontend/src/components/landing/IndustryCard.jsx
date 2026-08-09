import { Phone, Mail, MessageCircle, Download, Nfc } from "lucide-react";

const AriadniMark = ({ className = "" }) => (
  <svg viewBox="0 0 24 24" className={className} fill="none" aria-hidden>
    <path d="M12 3 L21 20 L15.6 20 L12 12 L8.4 20 L3 20 Z" fill="currentColor" />
  </svg>
);

const MedicalDecoration = ({ ac }) => (
  <>
    <svg viewBox="0 0 24 24" className="pointer-events-none absolute left-5 top-14 h-10 w-10" style={{ color: ac, opacity: 0.22 }} fill="currentColor" aria-hidden>
      <path d="M9 3h6v6h6v6h-6v6H9v-6H3V9h6z" />
    </svg>
    <svg viewBox="0 0 200 40" className="pointer-events-none absolute right-3 top-20 h-8 w-36" fill="none" aria-hidden>
      <polyline points="0,20 40,20 55,6 70,34 85,20 130,20 145,10 160,30 200,20" stroke={ac} strokeWidth="1.5" opacity="0.5" />
    </svg>
  </>
);

const ACTIONS = [
  { icon: Phone, label: "Call" },
  { icon: Mail, label: "Email" },
  { icon: MessageCircle, label: "WhatsApp" },
  { icon: Download, label: "Save" },
];

// The ONE master industry card. Same structure for every industry — the
// background mood, accent, icon and content are the only things that change.
export function IndustryCard({ c, className = "" }) {
  const ac = c.accent;
  const base = c.base || "10,10,12";
  const mult = { soft: 1.3, medium: 1, rich: 0.68 }[c.intensity] || 1;
  const a0raw = c.opacity != null ? 0.30 - c.opacity : 0.08;
  const a0 = Math.min(0.5, Math.max(0.02, a0raw * mult));
  const posX = { left: "left", right: "right", center: "center", full: "center" }[c.position] || "center";
  const bg = c.image
    ? `linear-gradient(180deg, rgba(${base},${a0}) 0%, rgba(${base},0.46) 42%, rgba(${base},0.88) 72%, rgba(${base},0.97) 100%), url("${c.image}")`
    : `radial-gradient(120% 85% at 50% 0%, rgba(${base},0.72), rgba(${base},0.98))`;
  const LabelIcon = c.icon;

  return (
    <div className={`flex flex-col items-center ${className}`}>
      <div
        className="relative w-full max-w-[360px] overflow-hidden rounded-[28px] border"
        style={{
          borderColor: `${ac}59`,
          boxShadow: `0 30px 70px rgba(0,0,0,0.55), inset 0 0 0 1px ${ac}1f`,
          backgroundColor: `rgb(${base})`,
          backgroundImage: bg,
          backgroundSize: "cover, cover",
          backgroundPosition: `center top, ${posX} top`,
          backgroundRepeat: "no-repeat, no-repeat",
        }}
        data-testid={`ind-card-${c.id}`}
      >
        {c.decoration === "medical" && <MedicalDecoration ac={ac} />}

        <div className="relative z-10 flex flex-col items-center px-6 pb-7 pt-6">
          {/* brand header */}
          <div className="flex items-center gap-1.5">
            <AriadniMark className="h-5 w-5 text-[#D6A653]" />
            <span className="text-[14px] font-semibold tracking-wide text-white">ARIADNI <span className="text-[#D6A653]">ID</span></span>
          </div>

          {/* portrait */}
          <div className="mt-5 h-[120px] w-[120px] overflow-hidden rounded-full" style={{ boxShadow: `0 0 0 3px ${ac}, 0 0 24px ${ac}55` }}>
            <img src={c.portrait} alt={c.name} className="h-full w-full object-cover" loading="lazy" />
          </div>

          {/* text hierarchy */}
          <h3 className="mt-4 text-center text-[22px] font-semibold leading-tight text-white">{c.name}</h3>
          <p className="mt-1 text-center text-[13px]" style={{ color: ac }}>{c.role}</p>
          <p className="mt-0.5 text-center text-[11px]" style={{ color: `${ac}cc` }}>{c.company}</p>

          {/* action icons */}
          <div className="mt-5 grid w-full grid-cols-4 gap-2">
            {ACTIONS.map((a) => (
              <div key={a.label} className="flex flex-col items-center gap-1.5" data-testid={`ind-action-${c.id}-${a.label.toLowerCase()}`}>
                <span className="flex h-11 w-11 items-center justify-center rounded-full border" style={{ borderColor: `${ac}80` }}>
                  <a.icon className="h-4 w-4" style={{ color: ac }} strokeWidth={1.75} />
                </span>
                <span className="text-[10px] text-neutral-400">{a.label}</span>
              </div>
            ))}
          </div>

          {/* main CTA */}
          <div className="mt-5 w-full rounded-xl border py-3 text-center text-[13px] font-medium text-white" style={{ borderColor: `${ac}80`, backgroundColor: `${ac}12` }} data-testid={`ind-exchange-${c.id}`}>
            Exchange Contact
          </div>

          {/* tap micro-copy */}
          <div className="mt-3.5 flex items-center gap-2 text-[11px] text-neutral-400">
            <Nfc className="h-3.5 w-3.5" style={{ color: ac }} /> Tap your card
          </div>
        </div>
      </div>

      {/* industry label */}
      <div className="mt-4 flex items-center gap-2" data-testid={`ind-label-${c.id}`}>
        <LabelIcon className="h-5 w-5" style={{ color: ac }} strokeWidth={1.75} />
        <span className="text-[14px] text-neutral-200">{c.label}</span>
      </div>
    </div>
  );
}
