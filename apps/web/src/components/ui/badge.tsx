import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function Badge({
  className,
  tone = "muted",
  children,
}: {
  className?: string;
  tone?: "muted" | "live" | "online" | "signal";
  children: ReactNode;
}) {
  const tones = {
    muted: "border-line text-muted",
    live: "border-live/40 text-live",
    online: "border-online/40 text-online",
    signal: "border-signal/40 text-signal",
  };
  return (
    <span
      className={cn(
        "inline-flex w-fit items-center self-start rounded-full border px-2 py-0.5 text-[11px] font-medium uppercase tracking-[0.14em]",
        tones[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}
