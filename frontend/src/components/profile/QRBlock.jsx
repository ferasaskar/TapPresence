import { qrUrl } from "@/lib/api";
import { useLocale } from "@/i18n/useLocale";

export const QRBlock = ({ slug, className = "", imgClassName = "", label = "show" }) => {
  const { t } = useLocale();
  return (
    <div className={className} data-testid="qr-block">
      <img
        src={qrUrl(slug)}
        alt="QR code to this profile"
        className={imgClassName}
        data-testid="qr-image"
      />
      {label ? <span className="text-xs tracking-wide opacity-70">{t("qr.scanToView")}</span> : null}
    </div>
  );
};
