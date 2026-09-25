export type CaptionText = "original" | "translation" | "both";
export type CaptionSize = "s" | "m" | "l" | "xl";
export type CaptionBg = "none" | "black";

export type WatchPrefs = {
  text: CaptionText;
  size: CaptionSize;
  volume: number;
  captionBg: CaptionBg;
};

const STORAGE_KEY = "eventlyra.watch.captions.v3";
const LEGACY_KEY = "eventlyra.watch.captions.v2";

export const DEFAULT_WATCH_PREFS: WatchPrefs = {
  text: "translation",
  size: "s",
  volume: 80,
  captionBg: "black",
};

export function clampVolume(value: number): number {
  if (!Number.isFinite(value)) return DEFAULT_WATCH_PREFS.volume;
  return Math.max(0, Math.min(100, Math.round(value)));
}

export const CAPTION_SIZES: CaptionSize[] = ["s", "m", "l", "xl"];

export const CAPTION_SIZE_CLASS: Record<
  CaptionSize,
  { primary: string; secondary: string }
> = {
  s: { primary: "text-lg sm:text-xl", secondary: "text-base sm:text-lg" },
  m: { primary: "text-2xl sm:text-4xl", secondary: "text-xl sm:text-3xl" },
  l: { primary: "text-3xl sm:text-5xl", secondary: "text-2xl sm:text-4xl" },
  xl: { primary: "text-4xl sm:text-6xl", secondary: "text-3xl sm:text-5xl" },
};

export function languageLabel(code: string | null | undefined): string {
  const key = (code || "").toLowerCase();
  if (key === "es") return "ES";
  if (key === "en") return "EN";
  if (key === "pt") return "PT";
  if (key === "auto") return "Auto";
  return code ? code.toUpperCase() : "—";
}

function parsePrefs(raw: string): WatchPrefs {
  const parsed = JSON.parse(raw) as Partial<WatchPrefs>;
  const text =
    parsed.text === "original" || parsed.text === "translation" || parsed.text === "both"
      ? parsed.text
      : DEFAULT_WATCH_PREFS.text;
  const size = CAPTION_SIZES.includes(parsed.size as CaptionSize)
    ? (parsed.size as CaptionSize)
    : DEFAULT_WATCH_PREFS.size;
  const volume = clampVolume(
    typeof parsed.volume === "number" ? parsed.volume : DEFAULT_WATCH_PREFS.volume,
  );
  const captionBg = parsed.captionBg === "none" || parsed.captionBg === "black"
    ? parsed.captionBg
    : DEFAULT_WATCH_PREFS.captionBg;
  return { text, size, volume, captionBg };
}

export function loadWatchPrefs(): WatchPrefs {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY) || window.localStorage.getItem(LEGACY_KEY);
    if (!raw) return DEFAULT_WATCH_PREFS;
    return parsePrefs(raw);
  } catch {
    return DEFAULT_WATCH_PREFS;
  }
}

export function saveWatchPrefs(prefs: WatchPrefs): void {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
}
