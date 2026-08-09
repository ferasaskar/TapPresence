// ARIADNI ID — ONE master industry-card system.
// Every industry renders in the SAME card structure (frame, logo, portrait,
// text hierarchy, 4 circular actions, Exchange Contact, "Tap your card", label).
// Only the background mood, accent color, industry icon and content change.
import { Building2, Briefcase, TrendingUp, Cpu, HeartPulse, Scale, GraduationCap, Hotel, Car, Flower2, LineChart, Plus } from "lucide-react";
import { ACCENT_OPTIONS } from "@/lib/accents";

const IMG = "https://static.prod-images.emergentagent.com/jobs/b7cf9ea3-4027-4bce-9aa9-3953ffa20ee3/images/";
const U = (id) => `https://images.unsplash.com/photo-${id}?crop=entropy&cs=srgb&fm=jpg&q=85&w=600`;

export const INDUSTRY_CARDS = [
  { id: "real_estate", label: "Real Estate", icon: Building2, accentId: "gold", accent: "#D6A653", base: "10,9,8",
    name: "Alex Morgan", role: "Real Estate Consultant", company: "Morgan Properties",
    portrait: U("1764546899196-b53061b1b609"),
    image: IMG + "d2c82f9a132290384b7015b8d3f12f0c7f766a1213e5f91e4eb2794e8bb247f6.jpeg" },

  { id: "business", label: "Business & Consulting", icon: Briefcase, accentId: "gold", accent: "#D8AE5E", base: "12,10,7",
    name: "Michael Anderson", role: "Business Consultant", company: "Anderson Consulting",
    portrait: U("1519085360753-af0119f7cbe7"),
    image: IMG + "9b16db82a5b24fb91253e6046b321b26daa4bbab3090d35ee1a845babcf66635.jpeg" },

  { id: "sales", label: "Sales & Marketing", icon: TrendingUp, accentId: "purple", accent: "#A879FF", base: "20,11,30",
    name: "Jessica Taylor", role: "Marketing Strategist", company: "GrowthLab Marketing",
    portrait: U("1494790108377-be9c29b29330"),
    image: IMG + "782d7af414bb8a53251e87281bfe15d15ad0a94fcda7ed8c0491bd9be6c7a5db.jpeg" },

  { id: "technology", label: "Technology & AI", icon: Cpu, accentId: "blue", accent: "#5AA6FF", base: "6,15,32",
    name: "Daniel Quinn", role: "AI Solutions Architect", company: "TechFlow AI",
    portrait: U("1560250097-0b93528c311a"),
    image: IMG + "447272e027a2357ae68521e30e1f5e5501d30bcdf27ede9cc9cbc06be3f47d1e.jpeg" },

  { id: "healthcare", label: "Healthcare", icon: HeartPulse, accentId: "emerald", accent: "#45C08A", base: "6,20,14", decoration: "medical",
    name: "Dr. Sophia Bennett", role: "General Practitioner", company: "HealthCare Clinic",
    portrait: U("1559839734-2b71ea197ec2"),
    image: IMG + "23ec91a2e4b04c3e104b208e8c055b98d69e973ed86fa385df65f283f480d466.jpeg" },

  { id: "legal", label: "Legal Services", icon: Scale, accentId: "blue", accent: "#7BA0DE", base: "10,14,24",
    name: "James Wilson", role: "Senior Attorney", company: "Wilson & Partners Law",
    portrait: U("1584940120505-117038d90b05"),
    image: IMG + "418c39c0a1ada4ee213ca20117211887c218ff11da800c485497e847481a4489.jpeg" },

  { id: "education", label: "Education & Training", icon: GraduationCap, accentId: "emerald", accent: "#3FB891", base: "7,19,16",
    name: "Emily Roberts", role: "Learning & Development Lead", company: "EduRise Academy",
    portrait: U("1573497019940-1c28c88b4f3e"),
    image: IMG + "452ba54873e3fcbe3946fab9d9f17bd96505a3f60812683840ecad5806913147.jpeg" },

  { id: "hospitality", label: "Hospitality", icon: Hotel, accentId: "gold", accent: "#E0B15C", base: "16,10,6",
    name: "David Martinez", role: "Hotel Manager", company: "Luxury Stays Group",
    portrait: U("1770452603217-89b4f03e8271"),
    image: IMG + "96c623ebb474f490a218d010805b8da0e5b3ff3a17743583f509367ef9e6df04.jpeg" },

  { id: "automotive", label: "Automotive", icon: Car, accentId: "red", accent: "#E5544B", base: "16,7,7",
    name: "Ryan Cooper", role: "Automotive Specialist", company: "Drive Performance",
    portrait: U("1652471943570-f3590a4e52ed"),
    image: IMG + "bfa23a5b48b5e3109555190832019296ad5ef55be922dfa0abf083d40796c4bf.jpeg" },

  { id: "beauty", label: "Beauty & Wellness", icon: Flower2, accentId: "rose", accent: "#E29BB4", base: "24,13,20",
    name: "Olivia Grace", role: "Wellness Coach", company: "Purely You Wellness",
    portrait: U("1573496359142-b8d87734a5a2"),
    image: IMG + "2ee971f749a68580d1b69c42348edcd63ffa4c8d40b64f45565920e79697a3bd.jpeg" },

  { id: "finance", label: "Finance", icon: LineChart, accentId: "emerald", accent: "#46B98A", base: "8,17,15",
    name: "Ethan Walker", role: "Financial Advisor", company: "Summit Financial Group",
    portrait: U("1767175620484-1ed37931a0d1"),
    image: IMG + "782d7af414bb8a53251e87281bfe15d15ad0a94fcda7ed8c0491bd9be6c7a5db.jpeg" },

  { id: "custom", label: "Custom Industry", icon: Plus, accentId: "platinum", accent: "#B9BEC7", base: "13,13,15",
    name: "Your Name", role: "Your Title", company: "Your Company",
    portrait: U("1614786269829-d24616faf56d"),
    image: "" },
];

export const industryCardById = (id) => INDUSTRY_CARDS.find((c) => c.id === id);

// Build a card config from live editor state so the preview stays in the same family.
export function previewCardConfig(form) {
  const preset = industryCardById(form.industry) || INDUSTRY_CARDS[0];
  let accent = preset.accent;
  if (form.accent === "custom" && form.custom_accent_color) {
    accent = form.custom_accent_color;
  } else {
    const opt = ACCENT_OPTIONS.find((a) => a.id === form.accent);
    if (opt) accent = opt.hex;
  }
  const id = form.identity || {};
  return {
    ...preset,
    accent,
    name: id.fullName || preset.name,
    role: id.jobTitle || preset.role,
    company: id.company || preset.company,
    portrait: id.profilePhoto || preset.portrait,
    image: form.custom_background || preset.image,
    opacity: form.background_opacity,
  };
}
