import { useEffect, useRef } from "react";
import type { Cue } from "@/lib/api";
import { cn } from "@/lib/utils";

function formatClock(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds));
  const minutes = Math.floor(total / 60);
  const rest = total % 60;
  return `${minutes}:${rest.toString().padStart(2, "0")}`;
}

export function TranscriptPanel({
  cues,
  active,
}: {
  cues: Cue[];
  active: Cue | null;
}) {
  const activeRef = useRef<HTMLLIElement | null>(null);

  useEffect(() => {
    const node = activeRef.current;
    if (!node) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    node.scrollIntoView({ block: "nearest", behavior: reduce ? "auto" : "smooth" });
  }, [active?.generation, active?.index]);

  return (
    <aside className="flex max-h-[40vh] flex-col overflow-hidden rounded-box border border-line bg-[linear-gradient(180deg,#10151f,#0c1118)] lg:max-h-[68vh]">
      <header className="border-b border-line px-4 py-3">
        <p className="text-[11px] uppercase tracking-[0.14em] text-muted">Transcript</p>
        <p className="mt-1 text-sm text-ink">
          {cues.length ? `${cues.length} lines` : "No lines yet"}
        </p>
      </header>
      {cues.length === 0 ? (
        <p className="px-4 py-8 text-sm text-muted">Waiting for captions…</p>
      ) : (
        <ol className="min-h-0 flex-1 space-y-1 overflow-y-auto px-2 py-3">
          {cues.map((cue) => {
            const isActive =
              active != null &&
              active.generation === cue.generation &&
              active.index === cue.index;
            return (
              <li
                key={`${cue.generation}-${cue.index}`}
                ref={isActive ? activeRef : undefined}
                className={cn(
                  "border-l-2 px-3 py-2",
                  isActive ? "border-signal bg-white/[0.03]" : "border-transparent",
                )}
              >
                <p className="text-[11px] tabular-nums text-muted">{formatClock(cue.start)}</p>
                <p className="mt-1 text-sm leading-snug text-white">{cue.original}</p>
                <p className="mt-1 text-sm leading-snug text-signal">{cue.translation}</p>
              </li>
            );
          })}
        </ol>
      )}
    </aside>
  );
}
