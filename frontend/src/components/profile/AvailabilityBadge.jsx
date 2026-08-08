export const AvailabilityBadge = ({ label, className = "", dotClassName = "" }) => {
  if (!label) return null;
  return (
    <span className={className} data-testid="availability-badge">
      <span className={dotClassName} />
      {label}
    </span>
  );
};
