// Email-safe signature HTML builder — table layout + inline styles + absolute URLs.
const ACCENT_HEX = { gold: "#D6A653", platinum: "#C0C0C8", blue: "#5B8DEF", emerald: "#34D399", bronze: "#B08D57", rose: "#E9A6B3" };

export const accentHex = (a) => ACCENT_HEX[a] || ACCENT_HEX.gold;

const esc = (s = "") => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

// opts: { photo, qr, title, company, phone, email, link, template, accent }
// urls: { profile, qr, photo }
export const buildSignatureHtml = (card, opts, urls) => {
  const id = card?.identity || {};
  const accent = accentHex(opts.accent || card?.accent);
  const name = esc(id.fullName || "");
  const title = esc(id.jobTitle || "");
  const company = esc(id.company || "");
  const phone = esc(id.phone || "");
  const email = esc(id.email || "");
  const font = "font-family:Arial,Helvetica,sans-serif;";
  const gray = "#5b5b5b";

  const photoImg = opts.photo && urls.photo
    ? `<img src="${esc(urls.photo)}" width="72" height="72" alt="${name}" style="border-radius:50%;display:block;object-fit:cover;border:2px solid ${accent};" />`
    : "";
  const qrImg = opts.qr
    ? `<img src="${esc(urls.qr)}" width="72" height="72" alt="QR" style="display:block;border:1px solid #e5e5e5;border-radius:8px;" />`
    : "";

  const lines = [];
  lines.push(`<div style="${font}font-size:16px;font-weight:bold;color:#1a1a1a;line-height:1.2;">${name}</div>`);
  if (opts.title && title) lines.push(`<div style="${font}font-size:13px;color:${gray};margin-top:2px;">${title}</div>`);
  if (opts.company && company) lines.push(`<div style="${font}font-size:13px;color:${accent};font-weight:bold;margin-top:2px;">${company}</div>`);
  const contact = [];
  if (opts.phone && phone) contact.push(`<a href="tel:${phone}" style="color:${gray};text-decoration:none;">${phone}</a>`);
  if (opts.email && email) contact.push(`<a href="mailto:${email}" style="color:${gray};text-decoration:none;">${email}</a>`);
  if (contact.length) lines.push(`<div style="${font}font-size:12px;color:${gray};margin-top:6px;">${contact.join(' &nbsp;•&nbsp; ')}</div>`);
  if (opts.link) lines.push(`<div style="margin-top:8px;"><a href="${esc(urls.profile)}" style="${font}font-size:12px;font-weight:bold;color:#fff;background:${accent};padding:6px 12px;border-radius:6px;text-decoration:none;display:inline-block;">View my card</a></div>`);

  const info = lines.join("");

  if (opts.template === "compact") {
    return `<table cellpadding="0" cellspacing="0" style="${font}"><tr>${photoImg ? `<td style="padding-right:12px;vertical-align:top;">${photoImg}</td>` : ""}<td style="vertical-align:top;">${info}</td></tr></table>`;
  }
  if (opts.template === "modern") {
    return `<table cellpadding="0" cellspacing="0" style="${font}border-left:3px solid ${accent};padding-left:14px;"><tr><td style="vertical-align:top;">${info}</td>${qrImg ? `<td style="padding-left:16px;vertical-align:top;">${qrImg}</td>` : ""}</tr></table>`;
  }
  // classic (default) — photo | info | qr
  return `<table cellpadding="0" cellspacing="0" style="${font}"><tr>${photoImg ? `<td style="padding-right:14px;vertical-align:top;border-right:1px solid #ececec;">${photoImg}</td>` : ""}<td style="padding:0 14px;vertical-align:top;">${info}</td>${qrImg ? `<td style="padding-left:14px;vertical-align:top;border-left:1px solid #ececec;">${qrImg}</td>` : ""}</tr></table>`;
};
