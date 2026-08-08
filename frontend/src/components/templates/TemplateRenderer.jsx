import { BeigeLuxuryExecutive } from "@/components/templates/BeigeLuxuryExecutive";
import { ExecutiveBlackGold } from "@/components/templates/ExecutiveBlackGold";
import { FutureProfessional } from "@/components/templates/FutureProfessional";

export const TEMPLATES = [
  { id: "beige-luxury", name: "Beige Luxury Executive" },
  { id: "executive-black-gold", name: "Executive Black Gold" },
  { id: "future-professional", name: "Future Professional" },
];

export const TemplateRenderer = ({ data }) => {
  if (!data) return null;
  switch (data.templateId) {
    case "executive-black-gold":
      return <ExecutiveBlackGold data={data} />;
    case "future-professional":
      return <FutureProfessional data={data} />;
    case "beige-luxury":
    default:
      return <BeigeLuxuryExecutive data={data} />;
  }
};
