import { INDUSTRY_CARDS } from "@/lib/industryCards";
import { IndustryCard } from "./IndustryCard";

// Full unified showcase — every industry rendered in the same master card format.
export default function IndustryCards() {
  return (
    <div className="grid grid-cols-1 gap-x-6 gap-y-10 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4" data-testid="industry-cards">
      {INDUSTRY_CARDS.map((c) => (
        <IndustryCard key={c.id} c={c} />
      ))}
    </div>
  );
}
