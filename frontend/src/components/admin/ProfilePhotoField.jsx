import { useRef, useState } from "react";
import { api, resolveImg } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Upload, Loader2, RotateCcw, ZoomIn } from "lucide-react";

// Profile photo with live circular crop: upload / paste URL, drag to reposition,
// zoom slider, reset. Framing saved as imageScale / imageOffsetX / imageOffsetY
// and applied identically in the live preview and the published card.
export function ProfilePhotoField({ id, set }) {
  const url = id.profilePhoto || "";
  const scale = id.imageScale || 1;
  const ox = id.imageOffsetX || 0;
  const oy = id.imageOffsetY || 0;
  const inputRef = useRef(null);
  const boxRef = useRef(null);
  const drag = useRef(null);
  const [uploading, setUploading] = useState(false);

  const upload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const f = new FormData();
      f.append("file", file);
      const { data } = await api.post("/upload", f, { headers: { "Content-Type": "multipart/form-data" } });
      set("identity.profilePhoto", data.url);
      set("identity.imageScale", 1); set("identity.imageOffsetX", 0); set("identity.imageOffsetY", 0);
    } catch (err) { console.error("upload failed", err); }
    finally { setUploading(false); }
  };

  const clamp = (v) => Math.max(-60, Math.min(60, v));
  const onDown = (e) => { if (!url) return; const p = e.touches ? e.touches[0] : e; drag.current = { x: p.clientX, y: p.clientY, ox, oy }; };
  const onMove = (e) => {
    if (!drag.current) return;
    const p = e.touches ? e.touches[0] : e;
    const box = boxRef.current?.offsetWidth || 160;
    const dx = ((p.clientX - drag.current.x) / box) * 100;
    const dy = ((p.clientY - drag.current.y) / box) * 100;
    set("identity.imageOffsetX", Math.round(clamp(drag.current.ox + dx)));
    set("identity.imageOffsetY", Math.round(clamp(drag.current.oy + dy)));
  };
  const onUp = () => { drag.current = null; };
  const reset = () => { set("identity.imageScale", 1); set("identity.imageOffsetX", 0); set("identity.imageOffsetY", 0); };

  return (
    <div className="space-y-3">
      <p className="text-sm font-medium text-white/70">Profile photo</p>
      <div className="flex flex-wrap items-start gap-5">
        <div>
          <div
            ref={boxRef}
            onMouseDown={onDown} onMouseMove={onMove} onMouseUp={onUp} onMouseLeave={onUp}
            onTouchStart={onDown} onTouchMove={onMove} onTouchEnd={onUp}
            className="relative h-40 w-40 overflow-hidden rounded-full border-2 border-[#D6A653]/50 bg-[#0A0B0D]"
            style={{ touchAction: "none", cursor: url ? "move" : "default" }}
            data-testid="photo-crop-box"
          >
            {url ? (
              <img src={resolveImg(url)} alt="" draggable={false} className="h-full w-full select-none object-cover" style={{ transform: `translate(${ox}%, ${oy}%) scale(${scale})`, transformOrigin: "center" }} />
            ) : (
              <div className="flex h-full w-full items-center justify-center text-xs text-white/30">No photo</div>
            )}
            <div className="pointer-events-none absolute inset-0 rounded-full ring-1 ring-inset ring-white/10" />
          </div>
          {url ? <p className="mt-2 text-center text-[10px] text-white/40">Drag to reposition</p> : null}
        </div>

        <div className="min-w-[200px] flex-1 space-y-3">
          <input ref={inputRef} type="file" accept="image/*" className="hidden" onChange={upload} data-testid="photo-file" />
          <div className="flex gap-2">
            <Button type="button" size="sm" onClick={() => inputRef.current?.click()} disabled={uploading} className="rounded-lg border border-white/15 bg-transparent text-white hover:bg-white/5" data-testid="photo-upload-btn">
              {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <><Upload className="mr-1 h-4 w-4" /> Upload</>}
            </Button>
            {url ? (
              <Button type="button" size="sm" onClick={reset} className="rounded-lg border border-white/15 bg-transparent text-white hover:bg-white/5" data-testid="photo-reset">
                <RotateCcw className="mr-1 h-4 w-4" /> Reset
              </Button>
            ) : null}
          </div>
          <Input value={url} onChange={(e) => set("identity.profilePhoto", e.target.value)} placeholder="or paste image URL" className="text-xs" data-testid="upload-photo-url" />
          {url ? (
            <div>
              <div className="mb-1 flex items-center justify-between text-xs text-white/55">
                <span className="flex items-center gap-1"><ZoomIn className="h-3.5 w-3.5" /> Zoom</span>
                <span>{scale.toFixed(2)}x</span>
              </div>
              <input type="range" min="1" max="3" step="0.01" value={scale} onChange={(e) => set("identity.imageScale", parseFloat(e.target.value))} className="w-full accent-[#D6A653]" data-testid="photo-zoom" />
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
