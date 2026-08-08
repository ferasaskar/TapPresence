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
      {label ? <p className="text-sm font-medium text-neutral-700">{label}</p> : null}
      <div className="flex items-center gap-3">
        {value ? (
          <div className="relative">
            <img src={resolveImg(value)} alt="" className="h-16 w-16 rounded object-cover border border-neutral-200" />
            <button
              type="button"
              onClick={() => onChange("")}
              className="absolute -right-2 -top-2 rounded-full bg-neutral-900 p-0.5 text-white"
              data-testid={`${testId}-clear`}
            >
              <X className="w-3 h-3" />
            </button>
          </div>
        ) : (
          <div className="flex h-16 w-16 items-center justify-center rounded border border-dashed border-neutral-300 text-neutral-400">
            <Upload className="w-4 h-4" />
          </div>
        )}
        <div className="flex-1 space-y-2">
          <input ref={inputRef} type="file" accept="image/*" className="hidden" onChange={handleFile} data-testid={`${testId}-file`} />
          <Button type="button" variant="outline" size="sm" onClick={() => inputRef.current?.click()} disabled={uploading} data-testid={`${testId}-button`}>
            {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Upload"}
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
