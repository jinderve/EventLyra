import { Captions, ScrollText, Settings, Volume2, VolumeX } from "lucide-react";
import type { ReactNode } from "react";
import { CaptionSettings } from "@/components/caption-settings";
import { cn } from "@/lib/utils";
import type { CaptionSize, CaptionText } from "@/lib/watch-prefs";

function Toggle({
  pressed,
  label,
  onClick,
  children,
}: {
  pressed: boolean;
  label: string;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      aria-pressed={pressed}
      aria-label={label}
      onClick={onClick}
      className={cn(
        "inline-flex h-11 min-w-11 items-center justify-center gap-2 rounded-control border px-3 text-[11px] font-medium uppercase tracking-[0.14em] transition-colors focus-visible:outline-none focus-visible:shadow-focus",
        pressed
          ? "border-signal/50 bg-canvas text-signal"
          : "border-line bg-canvas/90 text-muted hover:text-ink",
      )}
    >
      {children}
    </button>
  );
}

export function WatchControls({
  captionsOn,
  transcriptOn,
  settingsOpen,
  text,
  size,
  sourceLang,
  targetLang,
  volume,
  showVolume = false,
  onCaptions,
  onTranscript,
  onSettings,
  onText,
  onSize,
  onCloseSettings,
  onVolume,
}: {
  captionsOn: boolean;
  transcriptOn: boolean;
  settingsOpen: boolean;
  text: CaptionText;
  size: CaptionSize;
  sourceLang: string;
  targetLang: string;
  volume: number;
  showVolume?: boolean;
  onCaptions: () => void;
  onTranscript: () => void;
  onSettings: () => void;
  onText: (value: CaptionText) => void;
  onSize: (value: CaptionSize) => void;
  onCloseSettings: () => void;
  onVolume: (value: number) => void;
}) {
  const muted = volume === 0;
  return (
    <div
      data-watch-chrome
      className="pointer-events-auto relative flex items-center gap-2"
    >
      {showVolume ? (
        <div className="flex h-11 items-center gap-2 rounded-control border border-line bg-canvas/90 px-3">
          <button
            type="button"
            aria-label={muted ? "Unmute" : "Mute"}
            onClick={() => onVolume(muted ? 80 : 0)}
            className="text-ink hover:text-signal"
          >
            {muted ? (
              <VolumeX className="size-4" aria-hidden />
            ) : (
              <Volume2 className="size-4" aria-hidden />
            )}
          </button>
          <input
            type="range"
            min={0}
            max={100}
            step={1}
            value={volume}
            aria-label="YouTube volume"
            onChange={(event) => onVolume(Number(event.target.value))}
            className="h-1 w-20 cursor-pointer accent-primary sm:w-28"
          />
        </div>
      ) : null}
      <CaptionSettings
        open={settingsOpen}
        text={text}
        size={size}
        sourceLang={sourceLang}
        targetLang={targetLang}
        onText={onText}
        onSize={onSize}
        onClose={onCloseSettings}
      />
      <Toggle pressed={captionsOn} label="Toggle captions" onClick={onCaptions}>
        <Captions className="size-4" aria-hidden />
        CC
      </Toggle>
      <Toggle
        pressed={transcriptOn}
        label="Toggle transcript"
        onClick={onTranscript}
      >
        <ScrollText className="size-4" aria-hidden />
        Transcript
      </Toggle>
      <Toggle
        pressed={settingsOpen}
        label="Caption settings"
        onClick={onSettings}
      >
        <Settings className="size-4" aria-hidden />
      </Toggle>
    </div>
  );
}
