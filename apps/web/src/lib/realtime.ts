import type { Cue } from "./api";

export function subscribeSession(
  sessionId: string,
  onCue: (cue: Cue) => void,
  onStatus: (status: {
    status: string;
    pending: number;
    error: string | null;
    generation: number;
    detected_lang: string | null;
    stream_origin_at?: number | null;
  }) => void,
) {
  const source = new EventSource(`/api/sessions/${sessionId}/stream`);
  const seen = new Set<string>();
  source.addEventListener("cue", (event) => {
    const cue = JSON.parse((event as MessageEvent).data) as Cue;
    const key = `${cue.generation}-${cue.index}-${cue.start}`;
    if (seen.has(key)) return;
    seen.add(key);
    onCue(cue);
  });
  source.addEventListener("status", (event) => {
    onStatus(JSON.parse((event as MessageEvent).data));
  });
  return () => source.close();
}
