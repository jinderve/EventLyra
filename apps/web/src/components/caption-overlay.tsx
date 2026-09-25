import { cn } from "@/lib/utils";
import {
  CAPTION_SIZE_CLASS,
  type CaptionBg,
  type CaptionSize,
  type CaptionText,
} from "@/lib/watch-prefs";

export function CaptionOverlay({
  original,
  translation,
  text,
  size,
  background,
  empty,
}: {
  original?: string;
  translation?: string;
  text: CaptionText;
  size: CaptionSize;
  background: CaptionBg;
  empty?: boolean;
}) {
  const boxed = background === "black";
  if (empty) {
    return (
      <p
        className={cn(
          "text-lg text-white/70",
          boxed && "rounded-md bg-black/80 px-3 py-2",
        )}
      >
        Waiting for captions…
      </p>
    );
  }
  return (
    <div
      className={cn(
        "inline-block max-w-full text-center",
        boxed && "rounded-md bg-black/80 px-3 py-2 sm:px-4 sm:py-2.5",
      )}
    >
      {text !== "translation" && original ? (
        <p
          className={cn(
            CAPTION_SIZE_CLASS[size].primary,
            "font-semibold leading-tight text-white",
            !boxed && "drop-shadow-[0_2px_8px_rgba(0,0,0,0.85)]",
          )}
        >
          {original}
        </p>
      ) : null}
      {text !== "original" && translation ? (
        <p
          className={cn(
            text === "both"
              ? `mt-2 ${CAPTION_SIZE_CLASS[size].secondary}`
              : CAPTION_SIZE_CLASS[size].primary,
            "leading-tight text-white",
            !boxed && "drop-shadow-[0_2px_8px_rgba(0,0,0,0.85)]",
          )}
        >
          {translation}
        </p>
      ) : null}
    </div>
  );
}
