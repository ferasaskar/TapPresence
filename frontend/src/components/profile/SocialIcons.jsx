import { socialList, getIcon } from "@/lib/cardHelpers";

export const SocialIcons = ({ social, className = "", itemClassName = "" }) => {
  const items = socialList(social);
  if (!items.length) return null;
  return (
    <div className={className} data-testid="social-icons">
      {items.map((s) => {
        const Icon = getIcon(s.icon);
        return (
          <a
            key={s.key}
            href={s.url}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={s.label}
            data-testid={`social-${s.key}`}
            className={itemClassName}
          >
            <Icon className="w-[18px] h-[18px]" strokeWidth={1.5} />
          </a>
        );
      })}
    </div>
  );
};
