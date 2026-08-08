import { Download } from "lucide-react";
import { vcardUrl } from "@/lib/api";

export const SaveContactButton = ({ slug, className = "", iconClassName = "", label = "Save Contact", subLabel }) => (
  <a
    href={vcardUrl(slug)}
    data-testid="save-contact-button"
    className={className}
  >
    <Download className={iconClassName} strokeWidth={1.5} />
    <span className="flex flex-col leading-tight">
      <span>{label}</span>
      {subLabel ? <span className="text-xs opacity-60">{subLabel}</span> : null}
    </span>
  </a>
);
