export type Cue = {
  index: number;
  generation: number;
  start: number;
  end: number;
  original: string;
  translation: string;
  source_lang: string;
  target_lang: string;
  latency_ms: number | null;
  queue_wait_ms: number | null;
};

export type Talk = {
  id: string;
  title: string;
  room?: string | null;
  track?: string | null;
  language?: string | null;
  source_lang?: string;
  target_lang?: string;
  speakers?: string[];
  tags?: string[];
  description?: string | null;
  image_url?: string | null;
  youtube_url?: string | null;
  audio_kind?: string | null;
  published?: boolean;
  channel_id?: string | null;
  status?: string;
  live?: boolean;
};

export type Session = {
  id: string;
  title: string;
  room: string | null;
  agenda_lang: string | null;
  description?: string | null;
  tags?: string[];
  speakers?: string[];
  image_url?: string | null;
  youtube_url?: string | null;
  track?: string | null;
  talk_id?: string | null;
  published?: boolean;
  audio_kind?: string | null;
  watchers?: number;
  source_lang: string;
  target_lang: string;
  status: string;
  pending: number;
  error: string | null;
  detected_lang: string | null;
  generation: number;
  latency_ms: number | null;
  queue_wait_ms: number | null;
  last_cue_at: number | null;
  playback?: {
    kind: "video" | "audio" | "youtube" | "mic" | null;
    has_media: boolean;
    youtube_id: string | null;
    youtube_url: string | null;
    is_live?: boolean;
    stream_origin_at?: number | null;
    delay_sec?: number | null;
    chunk_seconds?: number | null;
    ready_until?: number | null;
  };
  cues: Cue[];
};

export type EventPayload = {
  id: string;
  title: string;
  location?: string | null;
  timezone?: string | null;
  attribution: string;
  sessions_per_gpu: number;
  tags?: string[];
  channels: Array<{
    id: string;
    title: string;
    room: string | null;
    language: string | null;
  }>;
  talks?: Talk[];
};

export type ProductionRow = {
  id: string;
  title?: string;
  room?: string | null;
  status: string;
  pending: number;
  error: string | null;
  cue_count: number;
  latency_ms: number | null;
  queue_wait_ms: number | null;
  queue: number;
  source_lang: string;
  target_lang: string;
  watchers?: number;
};

export type ProductionSnapshot = {
  models_loaded: boolean;
  sessions_per_gpu: number;
  asr_model?: string;
  translation_model?: string;
  translation_quantization?: string;
  queue_total?: number;
  last_error?: string | null;
  last_latency_ms?: number | null;
  last_queue_wait_ms?: number | null;
  sessions: ProductionRow[];
};

async function parse<T>(response: Promise<Response>): Promise<T> {
  const resolved = await response;
  if (!resolved.ok) {
    const detail = await resolved.text();
    throw new Error(detail || `HTTP ${resolved.status}`);
  }
  return resolved.json() as Promise<T>;
}

export function getEvent() {
  return parse<EventPayload>(fetch("/api/event"));
}

export function listTalks() {
  return parse<{ talks: Talk[]; sessions_per_gpu: number }>(fetch("/api/talks"));
}

export type TalkDraft = {
  title: string;
  room?: string;
  track?: string;
  description?: string;
  tags?: string;
  speakers?: string;
  image_url?: string;
  youtube_url?: string;
  source_lang?: string;
  target_lang?: string;
  audio_kind?: string;
  published?: boolean;
};

export function createTalk(body: TalkDraft) {
  return parse<{ talk: Talk; channel_id: string | null; talks: Talk[] }>(
    fetch("/api/talks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  );
}

export function updateTalk(id: string, body: Partial<TalkDraft>) {
  return parse<{ talk: Talk; talks: Talk[] }>(
    fetch(`/api/talks/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  );
}

export function listSessions() {
  return parse<{ sessions: Session[] }>(fetch("/api/sessions"));
}

export function getSession(id: string) {
  return parse<Session>(fetch(`/api/sessions/${id}`));
}

export function patchSession(
  id: string,
  body: {
    source_lang?: string;
    target_lang?: string;
    title?: string;
    room?: string;
  },
) {
  return parse<Session>(
    fetch(`/api/sessions/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  );
}

export function resetSession(id: string) {
  return parse<Session>(fetch(`/api/sessions/${id}/reset`, { method: "POST" }));
}

export function stopSession(id: string) {
  return parse<Session>(fetch(`/api/sessions/${id}/stop`, { method: "POST" }));
}

export function startSessionMic(id: string) {
  return parse<Session & { generation: number }>(
    fetch(`/api/sessions/${id}/mic`, { method: "POST" }),
  );
}

export function uploadSessionFile(id: string, file: File) {
  const data = new FormData();
  data.append("file", file);
  return parse<{ chunks: number; generation: number }>(
    fetch(`/api/sessions/${id}/file`, { method: "POST", body: data }),
  );
}

export function startSessionUrl(id: string, url: string) {
  return parse<{ mode: string; chunks: number; generation: number }>(
    fetch(`/api/sessions/${id}/url`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    }),
  );
}

export function uploadPcm(
  id: string,
  pcm: ArrayBuffer,
  sampleRate: number,
  start: number,
) {
  return parse<{ chunks: number; generation: number }>(
    fetch(`/api/sessions/${id}/pcm?sample_rate=${sampleRate}&start=${start}`, {
      method: "POST",
      headers: { "Content-Type": "application/octet-stream" },
      body: pcm,
    }),
  );
}

export function getProduction() {
  return parse<ProductionSnapshot>(fetch("/api/production"));
}

export function exportSessionHref(id: string, fmt: "srt" | "vtt" | "txt") {
  return `/api/sessions/${id}/export?fmt=${fmt}`;
}

export function getHealth() {
  return parse<{
    models_loaded: boolean;
    message: string | null;
    sessions_per_gpu: number;
    asr_model: string;
    translation_model: string;
    chunk_seconds: number;
  }>(fetch("/api/health"));
}
