import type { Cue } from "./api";

export function cueAt(cues: Cue[], time: number): Cue | null {
  if (!Number.isFinite(time) || time < 0) return null;
  const active = cues.find((cue) => time >= cue.start && time < cue.end);
  if (active) return active;
  const started = cues.filter((cue) => cue.start <= time);
  return started.at(-1) ?? null;
}

export function liveAlignedTime(
  nowSec: number,
  originAt: number,
  delaySec: number,
): number {
  return nowSec - originAt - delaySec;
}
