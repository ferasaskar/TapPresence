import { useLocale } from "@/i18n/useLocale";
import { PartyPopper, X } from "lucide-react";

const COLORS = ["#D4AF37", "#F2E0C9", "#FFFFFF", "#E8B764"];

// Lightweight, elegant reward celebration. Rendered only when a NEWLY earned reward is
// detected (caller controls mounting + once-only logic via localStorage). No external deps.
export function RewardCelebration({ months, perReward, onClose }) {
  const { t } = useLocale();
  const pieces = Array.from({ length: 36 });
  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/70 backdrop-blur-sm" data-testid="reward-celebration" role="dialog">
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        {pieces.map((_, i) => {
          const left = Math.random() * 100;
          const delay = Math.random() * 0.6;
          const dur = 2.4 + Math.random() * 1.6;
          const size = 6 + Math.random() * 8;
          const color = COLORS[i % COLORS.length];
          return (
            <span key={i} className="tp-confetti" style={{
              left: `${left}%`, width: size, height: size * 0.4, background: color,
              animationDelay: `${delay}s`, animationDuration: `${dur}s`,
              transform: `rotate(${Math.random() * 360}deg)`,
            }} />
          );
        })}
      </div>
      <div className="relative mx-4 max-w-sm rounded-3xl border border-[#D4AF37]/40 bg-[#11121A] p-8 text-center shadow-[0_0_60px_rgba(212,175,55,0.25)]">
        <button onClick={onClose} className="absolute right-4 top-4 text-white/40 hover:text-white" data-testid="reward-celebration-close" aria-label={t("referralProgram.celebrateClose")}><X className="h-5 w-5" /></button>
        <span className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-[#D4AF37]/15">
          <PartyPopper className="h-8 w-8 text-[#D4AF37]" />
        </span>
        <h2 className="text-2xl font-light tracking-tight text-white" data-testid="reward-celebration-title">
          {t("referralProgram.celebrateTitle", { count: months })}
        </h2>
        <p className="mt-2 text-sm text-white/60">{t("referralProgram.celebrateBody", { count: perReward })}</p>
        <button onClick={onClose} className="mt-6 w-full rounded-full bg-[#D4AF37] py-3 text-sm font-medium text-[#0B0D12] transition-all hover:brightness-110 active:scale-95" data-testid="reward-celebration-cta">
          {t("referralProgram.celebrateClose")}
        </button>
      </div>
    </div>
  );
}
