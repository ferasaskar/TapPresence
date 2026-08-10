import jsQR from "jsqr";

// Decode a QR code from a data-URL image entirely in the browser (offline, no upload, no LLM cost).
// Returns the raw QR text, or null when no QR is found.
export function decodeQrFromDataUrl(dataUrl) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      try {
        // Downscale very large images for faster/more reliable decoding.
        const max = 1000;
        const scale = Math.min(1, max / Math.max(img.width, img.height));
        const w = Math.max(1, Math.round(img.width * scale));
        const h = Math.max(1, Math.round(img.height * scale));
        const c = document.createElement("canvas");
        c.width = w; c.height = h;
        const ctx = c.getContext("2d");
        ctx.drawImage(img, 0, 0, w, h);
        const { data } = ctx.getImageData(0, 0, w, h);
        const res = jsQR(data, w, h, { inversionAttempts: "attemptBoth" });
        resolve(res?.data || null);
      } catch {
        resolve(null);
      }
    };
    img.onerror = () => resolve(null);
    img.src = dataUrl;
  });
}

const EMPTY = { name: "", title: "", company: "", email: "", phone: "", website: "", address: "", notes: "" };

function unescapeVcard(v) {
  return (v || "").replace(/\\n/gi, " ").replace(/\\,/g, ",").replace(/\\;/g, ";").replace(/\\\\/g, "\\").trim();
}

// Parse common contact-QR payloads into scanner draft fields.
// Supports: vCard (2.1/3.0/4.0), MECARD, mailto:, tel:, and plain URLs.
// Returns a partial draft object, or null if the QR is not contact-like (so the caller can fall back to OCR).
export function parseContact(text) {
  if (!text) return null;
  const raw = text.trim();
  const upper = raw.toUpperCase();

  if (upper.startsWith("BEGIN:VCARD")) return parseVcard(raw);
  if (upper.startsWith("MECARD:")) return parseMecard(raw);
  if (upper.startsWith("MAILTO:")) return { ...EMPTY, email: raw.slice(7).split("?")[0].trim() };
  if (upper.startsWith("TEL:")) return { ...EMPTY, phone: raw.slice(4).trim() };
  if (/^https?:\/\//i.test(raw)) return { ...EMPTY, website: raw, notes: raw };
  return null;
}

function parseVcard(raw) {
  const out = { ...EMPTY };
  const lines = raw.replace(/\r\n/g, "\n").split("\n");
  for (const line of lines) {
    const idx = line.indexOf(":");
    if (idx < 0) continue;
    const rawKey = line.slice(0, idx);
    const key = rawKey.split(";")[0].toUpperCase();
    const val = unescapeVcard(line.slice(idx + 1));
    if (!val) continue;
    if (key === "FN" && !out.name) out.name = val;
    else if (key === "N" && !out.name) out.name = val.split(";").filter(Boolean).reverse().join(" ").trim();
    else if (key === "TITLE") out.title = val;
    else if (key === "ORG") out.company = val.split(";")[0].trim();
    else if (key === "EMAIL" && !out.email) out.email = val;
    else if (key === "TEL" && !out.phone) out.phone = val;
    else if (key === "URL" && !out.website) out.website = val;
    else if (key === "ADR" && !out.address) out.address = val.split(";").filter(Boolean).join(", ");
    else if (key === "NOTE") out.notes = out.notes ? `${out.notes} ${val}` : val;
  }
  return out.name || out.email || out.phone ? out : { ...EMPTY, notes: raw };
}

function parseMecard(raw) {
  const out = { ...EMPTY };
  const body = raw.replace(/^MECARD:/i, "");
  body.split(";").forEach((part) => {
    const i = part.indexOf(":");
    if (i < 0) return;
    const k = part.slice(0, i).toUpperCase();
    const v = part.slice(i + 1).trim();
    if (!v) return;
    if (k === "N") out.name = v.split(",").reverse().join(" ").trim();
    else if (k === "TEL") out.phone = v;
    else if (k === "EMAIL") out.email = v;
    else if (k === "ORG") out.company = v;
    else if (k === "URL") out.website = v;
    else if (k === "ADR") out.address = v;
    else if (k === "NOTE") out.notes = v;
  });
  return out.name || out.email || out.phone ? out : { ...EMPTY, notes: raw };
}
