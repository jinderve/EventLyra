export type SetupDraft = {
  sessionId: string;
  sourceLang: string;
  targetLang: string;
  audioMode: "file" | "mic" | null;
  fileName: string | null;
};

const KEY = "eventlyra.setup.v1";

export const defaultDraft = (): SetupDraft => ({
  sessionId: "1",
  sourceLang: "auto",
  targetLang: "es",
  audioMode: null,
  fileName: null,
});

export function loadDraft(): SetupDraft {
  try {
    const raw = sessionStorage.getItem(KEY);
    if (!raw) return defaultDraft();
    return { ...defaultDraft(), ...JSON.parse(raw) };
  } catch {
    return defaultDraft();
  }
}

export function saveDraft(next: Partial<SetupDraft>) {
  const merged = { ...loadDraft(), ...next };
  sessionStorage.setItem(KEY, JSON.stringify(merged));
  return merged;
}
