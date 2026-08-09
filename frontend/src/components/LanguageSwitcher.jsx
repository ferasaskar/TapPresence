import { useState } from "react";
import { Globe, Check } from "lucide-react";
import { useLocale } from "@/i18n/useLocale";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";

export const LanguageSwitcher = () => {
  const { lng, langs, setLanguage, t } = useLocale();
  const [open, setOpen] = useState(false);
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          className="rounded-full border border-white/12 bg-white/5 p-2 text-white/70 transition-colors hover:text-white"
          title={t("nav.language")}
          data-testid="language-switcher"
        >
          <Globe className="h-4 w-4 text-[#D6A653]" />
        </button>
      </PopoverTrigger>
      <PopoverContent align="end" className="aria-pop w-44 border-white/10 bg-[#0A0B0D] p-1 text-white" data-testid="language-menu">
        {langs.map((l) => (
          <button
            key={l.code}
            onClick={() => { try { localStorage.setItem("tp_lang_manual", "1"); localStorage.setItem("tp_locale_toast_shown", "1"); } catch (e) {} setLanguage(l.code); setOpen(false); }}
            data-testid={`lang-option-${l.code}`}
            className={`flex w-full items-center justify-between rounded-md px-3 py-2 text-sm transition-colors hover:bg-white/[0.06] ${lng === l.code ? "text-[#D6A653]" : "text-white/80"}`}
            dir={l.dir}
          >
            {l.label}
            {lng === l.code && <Check className="h-4 w-4" />}
          </button>
        ))}
      </PopoverContent>
    </Popover>
  );
};
