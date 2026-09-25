export type LanguageCode = "es" | "en" | "pt" | "auto";

export type CueMessage = {
  index: number;
  generation: number;
  start: number;
  end: number;
  original: string;
  translation: string;
  source_lang: string;
  target_lang: string;
  latency_ms: number | null;
};

export type SessionStatus = {
  status: "ready" | "preparing" | "processing" | "error";
  pending: number;
  error: string | null;
  generation: number;
  detected_lang: string | null;
};
