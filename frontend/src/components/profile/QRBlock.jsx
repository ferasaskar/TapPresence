import { qrUrl } from "@/lib/api";

export const QRBlock = ({ slug, className = "", imgClassName = "", label = "Scan to view" }) => (
  <div className={className} data-testid="qr-block">
    <img
      src={qrUrl(slug)}
      alt="QR code to this profile"
      className={imgClassName}
      data-testid="qr-image"
    />
    {label ? <span className="text-xs tracking-wide opacity-70">{label}</span> : null}
  </div>
);
