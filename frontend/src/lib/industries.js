// ARIADNI ID — Industry personalization engine (data-driven, template-agnostic).
// One base template + industry skin + accent + layered background.

const IMG = "https://static.prod-images.emergentagent.com/jobs/b7cf9ea3-4027-4bce-9aa9-3953ffa20ee3/images/";

export const INDUSTRIES = [
  { id: "real_estate", name: "Real Estate", icon: "Building2", image: IMG + "d2c82f9a132290384b7015b8d3f12f0c7f766a1213e5f91e4eb2794e8bb247f6.jpeg", accent: "gold", defaultOpacity: 0.15,
    styles: [{ id: "skyline", label: "City Skyline", type: "image" }, { id: "blueprint", label: "Blueprint", type: "pattern", pattern: "grid" }, { id: "architecture", label: "Architecture", type: "pattern", pattern: "lines" }] },
  { id: "business", name: "Business & Consulting", icon: "Briefcase", image: IMG + "9b16db82a5b24fb91253e6046b321b26daa4bbab3090d35ee1a845babcf66635.jpeg", accent: "platinum", defaultOpacity: 0.14,
    styles: [{ id: "glass", label: "Glass Towers", type: "image" }, { id: "geometry", label: "Geometry", type: "pattern", pattern: "grid" }] },
  { id: "sales", name: "Sales & Marketing", icon: "TrendingUp", image: IMG + "782d7af414bb8a53251e87281bfe15d15ad0a94fcda7ed8c0491bd9be6c7a5db.jpeg", accent: "gold", defaultOpacity: 0.15,
    styles: [{ id: "growth", label: "Growth", type: "image" }, { id: "points", label: "Data Points", type: "pattern", pattern: "dots" }] },
  { id: "technology", name: "Technology & AI", icon: "Cpu", image: IMG + "447272e027a2357ae68521e30e1f5e5501d30bcdf27ede9cc9cbc06be3f47d1e.jpeg", accent: "blue", defaultOpacity: 0.16,
    styles: [{ id: "neural", label: "Neural Network", type: "image" }, { id: "grid", label: "Data Grid", type: "pattern", pattern: "grid" }, { id: "particles", label: "Particles", type: "pattern", pattern: "dots" }] },
  { id: "healthcare", name: "Healthcare", icon: "HeartPulse", image: IMG + "23ec91a2e4b04c3e104b208e8c055b98d69e973ed86fa385df65f283f480d466.jpeg", accent: "emerald", defaultOpacity: 0.12,
    styles: [{ id: "wave", label: "Medical Wave", type: "image" }, { id: "abstract", label: "Clean Abstract", type: "pattern", pattern: "glow" }] },
  { id: "legal", name: "Legal Services", icon: "Scale", image: IMG + "418c39c0a1ada4ee213ca20117211887c218ff11da800c485497e847481a4489.jpeg", accent: "bronze", defaultOpacity: 0.14,
    styles: [{ id: "columns", label: "Columns", type: "image" }, { id: "marble", label: "Marble Lines", type: "pattern", pattern: "lines" }] },
  { id: "education", name: "Education & Training", icon: "GraduationCap", image: IMG + "452ba54873e3fcbe3946fab9d9f17bd96505a3f60812683840ecad5806913147.jpeg", accent: "gold", defaultOpacity: 0.13,
    styles: [{ id: "academic", label: "Academic", type: "image" }, { id: "geometry", label: "Geometry", type: "pattern", pattern: "grid" }] },
  { id: "hospitality", name: "Hospitality", icon: "Hotel", image: IMG + "96c623ebb474f490a218d010805b8da0e5b3ff3a17743583f509367ef9e6df04.jpeg", accent: "gold", defaultOpacity: 0.15,
    styles: [{ id: "interior", label: "Luxury Interior", type: "image" }, { id: "warm", label: "Warm Light", type: "pattern", pattern: "glow" }] },
  { id: "automotive", name: "Automotive", icon: "Car", image: IMG + "bfa23a5b48b5e3109555190832019296ad5ef55be922dfa0abf083d40796c4bf.jpeg", accent: "platinum", defaultOpacity: 0.15,
    styles: [{ id: "luxury_car", label: "Luxury Car", type: "image" }, { id: "speed", label: "Speed Lines", type: "pattern", pattern: "lines" }] },
  { id: "beauty", name: "Beauty & Wellness", icon: "Flower2", image: IMG + "2ee971f749a68580d1b69c42348edcd63ffa4c8d40b64f45565920e79697a3bd.jpeg", accent: "rose", defaultOpacity: 0.13,
    styles: [{ id: "editorial", label: "Editorial", type: "image" }, { id: "soft", label: "Soft Light", type: "pattern", pattern: "glow" }] },
  { id: "finance", name: "Finance", icon: "LineChart", image: IMG + "782d7af414bb8a53251e87281bfe15d15ad0a94fcda7ed8c0491bd9be6c7a5db.jpeg", accent: "gold", defaultOpacity: 0.14,
    styles: [{ id: "market", label: "Market Data", type: "image" }, { id: "lines", label: "Financial Lines", type: "pattern", pattern: "lines" }] },
  { id: "custom", name: "Custom Industry", icon: "Plus", image: "", accent: "gold", defaultOpacity: 0.14,
    styles: [{ id: "custom", label: "Custom Image", type: "custom" }] },
];

export const industryById = (id) => INDUSTRIES.find((i) => i.id === id);

const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

// Returns { css, size, repeat } for a CSS pattern layer, tinted by accent hex.
export function patternLayer(pattern, ac) {
  switch (pattern) {
    case "dots":
      return { css: `radial-gradient(${ac}2e 1.3px, transparent 1.7px)`, size: "20px 20px", repeat: "repeat" };
    case "lines":
      return { css: `repeating-linear-gradient(125deg, ${ac}1c 0 1px, transparent 1px 20px)`, size: "auto", repeat: "repeat" };
    case "grid":
      return { css: `repeating-linear-gradient(45deg, ${ac}18 0 1px, transparent 1px 26px)`, size: "auto", repeat: "repeat" };
    case "glow":
    default:
      return { css: `radial-gradient(70% 60% at 50% 32%, ${ac}2b, transparent 72%)`, size: "cover", repeat: "no-repeat" };
  }
}

// Builds an inline style object merged onto a template root. {} when no industry set
// so existing cards render exactly as before.
export function industryRootStyle(card, baseRgb, acHex) {
  if (!card || !card.industry) return {};
  const ind = industryById(card.industry);
  if (!ind) return {};
  const styleId = card.background_style || ind.styles[0]?.id;
  const style = ind.styles.find((s) => s.id === styleId) || ind.styles[0];

  const opacity = clamp(card.background_opacity ?? ind.defaultOpacity, 0, 0.3);
  const mult = { soft: 0.8, medium: 1, rich: 1.25 }[card.background_intensity || "medium"] || 1;
  const rgbAvg = baseRgb.split(",").reduce((a, n) => a + Number(n), 0) / 3;
  const isLight = rgbAvg > 140;
  let vis = clamp(opacity * mult, 0, 0.4);
  if (isLight) vis *= 0.6; // keep light templates readable

  const posMap = { left: "left center", right: "right center", center: "center", full: "center" };
  const pos = posMap[card.background_position || "center"] || "center";

  let layer, size, rep;
  if (card.custom_background) {
    layer = `url("${card.custom_background}")`; size = "cover"; rep = "no-repeat";
  } else if (style?.type === "pattern") {
    const p = patternLayer(style.pattern, acHex || "#C9A24B"); layer = p.css; size = p.size; rep = p.repeat;
  } else if (ind.image) {
    layer = `url("${ind.image}")`; size = "cover"; rep = "no-repeat";
  } else {
    return {};
  }

  // Directional readability scrim: lighter at top (image clearly visible), denser
  // toward the content below so text stays readable while the picture still shows.
  const aTop = clamp((isLight ? 0.88 : 0.72) - vis * 2.2, isLight ? 0.5 : 0.08, 0.92);
  const aMid = clamp(aTop + 0.22, 0, 1);
  const aBot = clamp(aTop + 0.44, 0, 1);
  const overlay = `linear-gradient(180deg, rgba(${baseRgb},${aTop.toFixed(3)}) 0%, rgba(${baseRgb},${aMid.toFixed(3)}) 55%, rgba(${baseRgb},${aBot.toFixed(3)}) 100%)`;
  return {
    backgroundImage: `${overlay}, ${layer}`,
    backgroundSize: `cover, ${size}`,
    backgroundPosition: `center, ${pos}`,
    backgroundRepeat: `no-repeat, ${rep}`,
    backgroundAttachment: "scroll",
  };
}

export const BASE_RGB = {
  "beige-luxury": "244,239,230",
  "executive-black-gold": "11,11,12",
  "future-professional": "7,10,22",
};
