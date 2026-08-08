import { Download } from "lucide-react";
import { vcardUrl } from "@/lib/api";
import { useProfile } from "@/context/ProfileContext";

export const SaveContactButton = ({ slug, className = "", iconClassName = "", label = "Save Contact", subLabel }) => {
  const { track } = useProfile();
  return (
    <a
      href={vcardUrl(slug)}
      onClick={() => track("tap", "save")}
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
};
