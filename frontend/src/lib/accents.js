const hexToRgba = (hex, a) => {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${a})`;
};

const SETS = {
  "beige-luxury": { gold: "#B89973", platinum: "#8C8F94", rose: "#BC8A82", blue: "#5B84B1", emerald: "#4E8C74", purple: "#8A6FB0", bronze: "#A9743B", red: "#B5544B" },
  "executive-black-gold": { gold: "#C9A24B", platinum: "#C3C7CE", rose: "#D6A0A0", blue: "#5FA8E8", emerald: "#52B788", purple: "#A78BFA", bronze: "#C08A3E", red: "#E5544B" },
  "future-professional": {
    gold: { p: "#E7B24B", s: "#C98A2B" },
    platinum: { p: "#4AA8FF", s: "#7A5CFF" },
    rose: { p: "#FF7EC8", s: "#8A5CFF" },
    blue: { p: "#45A6FF", s: "#2E6FE0" },
    emerald: { p: "#34D399", s: "#0E9E6E" },
    purple: { p: "#A78BFA", s: "#7A5CFF" },
    bronze: { p: "#D8A24B", s: "#9F6F29" },
    red: { p: "#FF6A5C", s: "#C0392B" },
  },
};

export const ACCENT_OPTIONS = [
  { id: "gold", label: "Gold", hex: "#C9A24B" },
  { id: "platinum", label: "Platinum", hex: "#C3C7CE" },
  { id: "blue", label: "Blue", hex: "#45A6FF" },
  { id: "emerald", label: "Emerald", hex: "#34D399" },
  { id: "purple", label: "Purple", hex: "#A78BFA" },
  { id: "rose", label: "Rose", hex: "#D6A0A0" },
  { id: "bronze", label: "Bronze", hex: "#C08A3E" },
  { id: "red", label: "Red", hex: "#E5544B" },
];

export const accentValue = (templateId, accent, custom) => {
  const set = SETS[templateId] || SETS["beige-luxury"];
  if (accent === "custom" && custom) {
    return templateId === "future-professional" ? { p: custom, s: custom } : custom;
  }
  return set[accent] || set.gold;
};

// Single-hex accent (beige / black-gold). Returns hex string.
export const accentHex = (templateId, accent, custom) => {
  const v = accentValue(templateId, accent, custom);
  return typeof v === "string" ? v : v.p;
};

export const accentVars = (hex) => ({
  "--ac": hex,
  "--ac-60": hexToRgba(hex, 0.6),
  "--ac-40": hexToRgba(hex, 0.4),
  "--ac-35": hexToRgba(hex, 0.35),
  "--ac-12": hexToRgba(hex, 0.12),
});

export { hexToRgba };

const clampByte = (n) => Math.max(0, Math.min(255, Math.round(n)));
// amt > 0 lightens toward white, amt < 0 darkens toward black
export const shadeHex = (hex, amt) => {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16), g = parseInt(h.slice(2, 4), 16), b = parseInt(h.slice(4, 6), 16);
  const target = amt < 0 ? 0 : 255;
  const t = Math.abs(amt);
  const mix = (c) => clampByte(c + (target - c) * t);
  return `#${[mix(r), mix(g), mix(b)].map((x) => x.toString(16).padStart(2, "0")).join("")}`;
};

// Derive a light→base→dark gradient from the SELECTED accent (works for any
// accent, not just gold). Keeps buttons/CTAs faithful to the chosen colour.
export const accentGrad = (templateId, accent, custom) => {
  const hex = accentHex(templateId, accent, custom);
  return [shadeHex(hex, 0.32), hex, shadeHex(hex, -0.42)];
};
