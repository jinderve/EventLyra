import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";
import {
  CAPTION_SIZES,
  languageLabel,
  type CaptionSize,
  type CaptionText,
} from "@/lib/watch-prefs";

const PREVIEW_SIZE: Record<CaptionSize, { primary: string; secondary: string }> = {
  s: { primary: "text-sm", secondary: "text-xs" },
  m: { primary: "text-base", secondary: "text-sm" },
  l: { primary: "text-xl", secondary: "text-base" },
  xl: { primary: "text-2xl", secondary: "text-xl" },
};

function Segment<T extends string>({
  value,
  options,
  onChange,
  labelFor,
}: {
  value: T;
  options: Array<{ id: T; label: string }>;
  onChange: (value: T) => void;
  labelFor: (id: T) => string;
}) {
  return (
    <div className="flex flex-wrap gap-1" role="group">
      {options.map((option) => {
        const selected = option.id === value;
        return (
          <button
            key={option.id}
            type="button"
            aria-pressed={selected}
            aria-label={labelFor(option.id)}
            onClick={() => onChange(option.id)}
            className={cn(
              "h-9 min-w-9 rounded-control border px-2.5 text-[11px] font-medium uppercase tracking-[0.12em] transition-colors focus-visible:outline-none focus-visible:shadow-focus",
              selected
                ? "border-signal/50 bg-canvas text-signal"
                : "border-line text-muted hover:text-ink",
            )}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}

export function CaptionSettings({
  open,
  text,
  size,
  sourceLang,
  targetLang,
  onText,
  onSize,
  onClose,
}: {
  open: boolean;
  text: CaptionText;
  size: CaptionSize;
  sourceLang: string;
  targetLang: string;
  onText: (value: CaptionText) => void;
  onSize: (value: CaptionSize) => void;
  onClose: () => void;
}) {
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    const onPointer = (event: MouseEvent) => {
      const target = event.target as HTMLElement | null;
      if (panelRef.current?.contains(target)) return;
      if (target?.closest("[data-watch-chrome]")) return;
      onClose();
    };
    document.addEventListener("keydown", onKey);
    const timer = window.setTimeout(() => {
      document.addEventListener("mousedown", onPointer);
    }, 0);
    return () => {
      window.clearTimeout(timer);
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onPointer);
    };
  }, [open, onClose]);

  if (!open) return null;

  const preview = PREVIEW_SIZE[size];
  const sample =
    text === "original"
      ? "Original caption"
      : text === "translation"
        ? "Translated caption"
        : null;

  return (
    <div
      ref={panelRef}
      role="dialog"
      aria-label="Caption settings"
      className="absolute bottom-14 right-0 z-30 w-[min(18.5rem,calc(100vw-2rem))] rounded-box border border-line bg-[linear-gradient(180deg,#10151f,#0c1118)] p-3 text-left shadow-[0_12px_40px_rgba(0,0,0,0.45)]"
    >
      <p className="text-[11px] uppercase tracking-[0.14em] text-muted">Preview</p>
      <div className="mt-2 min-h-14 border border-line bg-[#05060a] px-3 py-3 text-center">
        {sample ? (
          <p
            className={cn(
              "font-semibold leading-tight",
              preview.primary,
              text === "translation" ? "text-signal" : "text-white",
            )}
          >
            {sample}
          </p>
        ) : (
          <>
            <p className={cn("font-semibold leading-tight text-white", preview.primary)}>
              Original caption
            </p>
            <p className={cn("mt-1 leading-tight text-signal", preview.secondary)}>
              Translated caption
            </p>
          </>
        )}
      </div>

      <p className="mt-4 text-[11px] uppercase tracking-[0.14em] text-muted">Text</p>
      <div className="mt-2">
        <Segment
          value={text}
          onChange={onText}
          labelFor={(id) =>
            id === "original"
              ? `Original ${languageLabel(sourceLang)}`
              : id === "translation"
                ? `Translation ${languageLabel(targetLang)}`
                : "Original and translation"
          }
          options={[
            { id: "original", label: `Orig ${languageLabel(sourceLang)}` },
            { id: "translation", label: languageLabel(targetLang) },
            { id: "both", label: "Both" },
          ]}
        />
      </div>

      <p className="mt-4 text-[11px] uppercase tracking-[0.14em] text-muted">Size</p>
      <div className="mt-2">
        <Segment
          value={size}
          onChange={onSize}
          labelFor={(id) => `Caption size ${id.toUpperCase()}`}
          options={CAPTION_SIZES.map((id) => ({ id, label: id.toUpperCase() }))}
        />
      </div>
    </div>
  );
}
