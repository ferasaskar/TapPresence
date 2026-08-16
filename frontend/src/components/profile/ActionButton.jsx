import { getIcon } from "@/lib/cardHelpers";
import { useProfile } from "@/context/ProfileContext";

// Behaviour-only action button. Templates pass the visual className.
export const ActionButton = ({ action, className = "", iconClassName = "", showSub = false, testId }) => {
  const { track } = useProfile();
  if (!action) return null;
  const Icon = getIcon(action.icon);
  const external = action.href?.startsWith("http");
  // Native-booking actions pass an onClick (no href) so they can open the in-app dialog.
  if (action.onClick && !action.href) {
    return (
      <button
        type="button"
        onClick={() => { track("tap", action.key); action.onClick(); }}
        data-testid={testId || `action-${action.key}`}
        className={className}
      >
        <Icon className={iconClassName} strokeWidth={1.5} />
        {showSub ? (
          <span className="flex flex-col leading-tight text-left">
            <span className="font-medium">{action.label}</span>
            <span className="text-xs opacity-60">{action.sublabel}</span>
          </span>
        ) : (
          <span>{action.label}</span>
        )}
      </button>
    );
  }
  return (
    <a
      href={action.href}
      target={external ? "_blank" : undefined}
      rel={external ? "noopener noreferrer" : undefined}
      onClick={() => track("tap", action.key)}
      data-testid={testId || `action-${action.key}`}
      className={className}
    >
      <Icon className={iconClassName} strokeWidth={1.5} />
      {showSub ? (
        <span className="flex flex-col leading-tight text-left">
          <span className="font-medium">{action.label}</span>
          <span className="text-xs opacity-60">{action.sublabel}</span>
        </span>
      ) : (
        <span>{action.label}</span>
      )}
    </a>
  );
};
