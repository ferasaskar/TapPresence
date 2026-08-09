import { Phone, Mail, MessageCircle, Download, Nfc, Building2, Cpu } from "lucide-react";

const IMG = "https://static.prod-images.emergentagent.com/jobs/b7cf9ea3-4027-4bce-9aa9-3953ffa20ee3/images/";

const AriadniMark = ({ className = "" }) => (
  <svg viewBox="0 0 24 24" className={className} fill="none" aria-hidden>
    <path d="M12 3 L21 20 L15.6 20 L12 12 L8.4 20 L3 20 Z" fill="currentColor" />
  </svg>
);
const MedicalCross = ({ className = "", style }) => (
  <svg viewBox="0 0 24 24" className={className} style={style} fill="currentColor" aria-hidden>
    <path d="M9 3h6v6h6v6h-6v6H9v-6H3V9h6z" />
  </svg>
);

const CARDS = [
  {
    id: "real_estate", label: "Real Estate", labelIcon: Building2,
    name: "Alex Morgan", role: "Real Estate Consultant", company: "Morgan Properties",
    portrait: "https://images.unsplash.com/photo-1764546899196-b53061b1b609?crop=entropy&cs=srgb&fm=jpg&q=85&w=600",
    image: IMG + "d2c82f9a132290384b7015b8d3f12f0c7f766a1213e5f91e4eb2794e8bb247f6.jpeg",
    accent: "#D6A653", base: "8,8,9",
  },
  {
    id: "technology", label: "Technology", labelIcon: Cpu,
    name: "Daniel Quinn", role: "AI Solutions Architect", company: "TechFlow AI",
    portrait: "https://images.unsplash.com/photo-1676989880574-6be39345d345?crop=entropy&cs=srgb&fm=jpg&q=85&w=600",
    image: IMG + "447272e027a2357ae68521e30e1f5e5501d30bcdf27ede9cc9cbc06be3f47d1e.jpeg",
    accent: "#5AA6FF", base: "6,17,34",
  },
  {
    id: "healthcare", label: "Healthcare", labelIcon: MedicalCross, health: true,
    name: "Dr. Sophia Bennett", role: "General Practitioner", company: "HealthCare Clinic",
    portrait: "https://images.unsplash.com/photo-1559839734-2b71ea197ec2?crop=entropy&cs=srgb&fm=jpg&q=85&w=600",
    image: IMG + "23ec91a2e4b04c3e104b208e8c055b98d69e973ed86fa385df65f283f480d466.jpeg",
    accent: "#45C08A", base: "6,22,15",
  },
];

const ACTIONS = [
  { icon: Phone, label: "Call" },
  { icon: Mail, label: "Email" },
  { icon: MessageCircle, label: "WhatsApp" },
  { icon: Download, label: "Save" },
];

function Card({ c }) {
  const ac = c.accent;
  return (
    <div className="flex flex-col items-center">
      <div className="relative w-full max-w-[360px] overflow-hidden rounded-[30px] border"
        style={{
          borderColor: `${ac}66`,
          boxShadow: `0 30px 70px rgba(0,0,0,0.55), inset 0 0 0 1px ${ac}1a`,
          backgroundColor: `rgb(${c.base})`,
          backgroundImage: `linear-gradient(180deg, rgba(${c.base},0.10) 0%, rgba(${c.base},0.42) 40%, rgba(${c.base},0.86) 72%, rgba(${c.base},0.96) 100%), url("${c.image}")`,
          backgroundSize: "cover, cover",
          backgroundPosition: "center top, center top",
          backgroundRepeat: "no-repeat, no-repeat",
        }}
        data-testid={`ref-card-${c.id}`}>

        {/* healthcare decorative cross + heartbeat */}
        {c.health && (
          <>
            <MedicalCross className="pointer-events-none absolute left-5 top-16 h-12 w-12" style={{ color: ac, opacity: 0.22 }} />
            <svg viewBox="0 0 200 40" className="pointer-events-none absolute right-3 top-24 h-8 w-40" fill="none" aria-hidden>
              <polyline points="0,20 40,20 55,6 70,34 85,20 130,20 145,10 160,30 200,20" stroke={ac} strokeWidth="1.5" opacity="0.5" />
            </svg>
          </>
        )}

        <div className="relative z-10 flex flex-col items-center px-6 pb-7 pt-7">
          {/* logo (brand gold) */}
          <div className="flex items-center gap-1.5">
            <AriadniMark className="h-5 w-5 text-[#D6A653]" />
            <span className="text-[15px] font-semibold tracking-wide text-white">ARIADNI <span className="text-[#D6A653]">ID</span></span>
          </div>

          {/* portrait */}
          <div className="mt-5 h-[128px] w-[128px] overflow-hidden rounded-full" style={{ boxShadow: `0 0 0 3px ${ac}, 0 0 26px ${ac}55` }}>
            <img src={c.portrait} alt={c.name} className="h-full w-full object-cover" loading="lazy" />
          </div>

          <h3 className="mt-4 text-[24px] font-semibold text-white">{c.name}</h3>
          <p className="mt-1 text-[14px]" style={{ color: ac }}>{c.role}</p>
          <p className="mt-0.5 text-[12px]" style={{ color: `${ac}cc` }}>{c.company}</p>

          {/* actions */}
          <div className="mt-6 grid w-full grid-cols-4 gap-3">
            {ACTIONS.map((a) => (
              <div key={a.label} className="flex flex-col items-center gap-1.5">
                <span className="flex h-11 w-11 items-center justify-center rounded-full border" style={{ borderColor: `${ac}80` }}>
                  <a.icon className="h-4 w-4" style={{ color: ac }} strokeWidth={1.75} />
                </span>
                <span className="text-[10px] text-neutral-400">{a.label}</span>
              </div>
            ))}
          </div>

          {/* exchange */}
          <button className="mt-6 w-full rounded-xl border py-3.5 text-[14px] font-medium text-white transition-colors"
            style={{ borderColor: `${ac}80`, backgroundColor: `${ac}0f` }}
            data-testid={`ref-exchange-${c.id}`}>
            Exchange Contact
          </button>

          {/* tap */}
          <div className="mt-4 flex items-center gap-2 text-[12px] text-neutral-400">
            <Nfc className="h-4 w-4" style={{ color: ac }} /> Tap your card
          </div>
        </div>
      </div>

      {/* industry label under card */}
      <div className="mt-4 flex items-center gap-2">
        <c.labelIcon className="h-5 w-5" style={{ color: ac }} strokeWidth={1.75} />
        <span className="text-[15px] text-neutral-200">{c.label}</span>
      </div>
    </div>
  );
}

export default function IndustryCards() {
  return (
    <div className="grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-3" data-testid="industry-cards">
      {CARDS.map((c) => <Card key={c.id} c={c} />)}
    </div>
  );
}
