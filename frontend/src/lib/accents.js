const hexToRgba = (hex, a) => {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${a})`;
};

const SETS = {
  "beige-luxury": { gold: "#B89973", platinum: "#8C8F94", rose: "#BC8A82" },
  "executive-black-gold": { gold: "#C9A24B", platinum: "#C3C7CE", rose: "#D6A0A0" },
  "future-professional": {
    gold: { p: "#E7B24B", s: "#C98A2B" },
    platinum: { p: "#4AA8FF", s: "#7A5CFF" },
    rose: { p: "#FF7EC8", s: "#8A5CFF" },
  },
};

export const ACCENT_OPTIONS = [
  { id: "gold", label: "Gold" },
  { id: "platinum", label: "Platinum" },
  { id: "rose", label: "Rose" },
];

export const accentValue = (templateId, accent) => {
  const set = SETS[templateId] || SETS["beige-luxury"];
  return set[accent] || set.gold;
};

// Single-hex accent (beige / black-gold). Returns hex string.
export const accentHex = (templateId, accent) => {
  const v = accentValue(templateId, accent);
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

const GRADS = {
  "executive-black-gold": {
    gold: ["#E7C56B", "#C9A24B", "#8f7328"],
    platinum: ["#E6E8EC", "#C3C7CE", "#8b8f96"],
    rose: ["#EBC3C1", "#D6A0A0", "#9c6f6f"],
  },
};

export const accentGrad = (templateId, accent) =>
  GRADS[templateId]?.[accent] || GRADS[templateId]?.gold || ["#C9A24B", "#C9A24B", "#C9A24B"];
