import { Share2, Printer } from "lucide-react";
import { posterUrl } from "@/lib/api";
import { toast } from "sonner";

const V = {
  beige: { btn: "flex items-center justify-center gap-2 rounded-md border border-ivory-border bg-ivory-surface px-4 py-3.5 text-sm tracking-wide text-ink transition-colors duration-300 hover:border-[color:var(--ac,#B89973)]", icon: "" },
  black: { btn: "flex items-center justify-center gap-2 rounded-xl border px-4 py-3.5 text-sm tracking-wide text-neutral-200 transition-colors duration-300", style: { borderColor: "rgba(255,255,255,0.12)", backgroundColor: "#111112" } },
  future: { btn: "flex items-center justify-center gap-2 rounded-2xl border border-white/10 bg-white/[0.04] backdrop-blur-xl px-4 py-3.5 text-sm tracking-wide text-slate-200 transition-colors duration-300 hover:border-sky-400/50" },
};

export const ShareBar = ({ slug, name, variant = "beige", iconColor = "#B89973" }) => {
  const v = V[variant] || V.beige;
  const shareUrl = `${window.location.origin}/${slug}`;

  const doShare = async () => {
    if (navigator.share) {
      try { await navigator.share({ title: name, text: `${name} — digital card`, url: shareUrl }); } catch (_) {}
    } else {
      try { await navigator.clipboard.writeText(shareUrl); toast.success("Profile link copied"); }
      catch { toast.error("Could not copy link"); }
    }
  };

  return (
    <div className="mt-6 grid grid-cols-2 gap-4" data-testid="share-bar">
      <button onClick={doShare} className={v.btn} style={v.style} data-testid="share-button">
        <Share2 className="w-4 h-4" style={{ color: iconColor }} strokeWidth={1.75} /> Share
      </button>
      <a href={posterUrl(slug)} className={v.btn} style={v.style} data-testid="download-poster" download>
        <Printer className="w-4 h-4" style={{ color: iconColor }} strokeWidth={1.75} /> QR Poster
      </a>
    </div>
  );
};
