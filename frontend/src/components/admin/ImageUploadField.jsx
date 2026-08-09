import { useRef, useState } from "react";
import { api, resolveImg } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Upload, Loader2, X } from "lucide-react";

export function ImageUploadField({ value, onChange, label, testId }) {
  const inputRef = useRef(null);
  const [uploading, setUploading] = useState(false);

  const handleFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const { data } = await api.post("/upload", form, { headers: { "Content-Type": "multipart/form-data" } });
      onChange(data.url);
    } catch (err) {
      console.error("upload failed", err);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-2">
      {label ? <p className="text-sm font-medium text-white/70">{label}</p> : null}
      <div className="flex items-center gap-3">
        {value ? (
          <div className="relative">
            <img src={resolveImg(value)} alt="" className="h-16 w-16 rounded-lg border border-white/10 object-cover" />
            <button
              type="button"
              onClick={() => onChange("")}
              className="absolute -right-2 -top-2 rounded-full bg-[#D6A653] p-0.5 text-[#050607]"
              data-testid={`${testId}-clear`}
            >
              <X className="h-3 w-3" />
            </button>
          </div>
        ) : (
          <div className="flex h-16 w-16 items-center justify-center rounded-lg border border-dashed border-white/20 text-white/40 transition-colors hover:border-[#D6A653]/60 hover:text-[#D6A653]">
            <Upload className="h-4 w-4" />
          </div>
        )}
        <div className="flex-1 space-y-2">
          <input ref={inputRef} type="file" accept="image/*" className="hidden" onChange={handleFile} data-testid={`${testId}-file`} />
          <Button type="button" size="sm" onClick={() => inputRef.current?.click()} disabled={uploading} className="rounded-lg border border-white/15 bg-transparent text-white hover:bg-white/5" data-testid={`${testId}-button`}>
            {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Upload"}
          </Button>
          <Input
            value={value || ""}
            onChange={(e) => onChange(e.target.value)}
            placeholder="or paste image URL"
            className="text-xs"
            data-testid={`${testId}-url`}
          />
        </div>
      </div>
    </div>
  );
}
