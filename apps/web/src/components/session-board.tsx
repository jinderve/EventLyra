import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { AddTalkForm } from "@/components/add-talk-form";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  exportSessionHref,
  getHealth,
  getProduction,
  listSessions,
  listTalks,
  patchSession,
  resetSession,
  startSessionUrl,
  uploadSessionFile,
  type ProductionRow,
  type Session,
  type Talk,
} from "@/lib/api";
import { startMicrophone } from "@/lib/mic";
import { cn } from "@/lib/utils";

const SOURCES = [
  { id: "auto", label: "Detect" },
  { id: "es", label: "Spanish" },
  { id: "en", label: "English" },
  { id: "pt", label: "Portuguese" },
];
const TARGETS = SOURCES.filter((item) => item.id !== "auto");

type AudioChoice = "file" | "mic" | "url";

function defaultDraft(session: Session) {
  const url = session.youtube_url || session.playback?.youtube_url || "";
  return { url, mode: (url ? "url" : "file") as AudioChoice };
}

export function SessionBoard({ variant }: { variant: "setup" | "live" }) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [talks, setTalks] = useState<Talk[]>([]);
  const [rows, setRows] = useState<ProductionRow[]>([]);
  const [models, setModels] = useState<string | null>(null);
  const [chunkSeconds, setChunkSeconds] = useState(8);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<
    Record<string, { file?: File; url: string; mode: AudioChoice }>
  >({});
  const mics = useRef<Record<string, { stop: () => void }>>({});

  async function refresh() {
    const [listed, production, health, catalog] = await Promise.all([
      listSessions(),
      getProduction(),
      getHealth(),
      listTalks(),
    ]);
    setSessions(listed.sessions);
    setRows(production.sessions);
    setTalks(catalog.talks);
    setChunkSeconds(health.chunk_seconds || 8);
    setModels(
      health.models_loaded
        ? `${health.asr_model} + ${health.translation_model}`
        : health.message,
    );
    setDrafts((current) => {
      const next = { ...current };
      for (const session of listed.sessions) {
        next[session.id] ??= defaultDraft(session);
      }
      return next;
    });
  }

  useEffect(() => {
    void refresh().catch((err: Error) => setError(err.message));
    const timer = window.setInterval(() => {
      void refresh().catch(() => undefined);
    }, 2000);
    return () => {
      window.clearInterval(timer);
      Object.values(mics.current).forEach((handle) => handle.stop());
    };
  }, []);

  function draft(id: string) {
    return drafts[id] ?? { url: "", mode: "url" as AudioChoice };
  }

  async function saveLanguages(session: Session, source: string, target: string) {
    await patchSession(session.id, { source_lang: source, target_lang: target });
    await refresh();
  }

  async function start(session: Session) {
    setBusy(session.id);
    setError(null);
    try {
      await patchSession(session.id, {
        source_lang: session.source_lang,
        target_lang: session.target_lang,
      });
      const choice = draft(session.id);
      if (choice.mode === "file") {
        if (!choice.file) throw new Error("Choose a file before Start live.");
        await uploadSessionFile(session.id, choice.file);
      } else if (choice.mode === "url") {
        if (!choice.url.trim()) throw new Error("Paste a YouTube URL before Start live.");
        await startSessionUrl(session.id, choice.url.trim());
      } else {
        mics.current[session.id]?.stop();
        mics.current[session.id] = await startMicrophone(
          session.id,
          chunkSeconds,
          (message) => setError(message),
        );
      }
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start the session.");
    } finally {
      setBusy(null);
    }
  }

  async function stop(session: Session) {
    setBusy(session.id);
    setError(null);
    try {
      mics.current[session.id]?.stop();
      delete mics.current[session.id];
      await resetSession(session.id);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not stop the session.");
    } finally {
      setBusy(null);
    }
  }

  const extras = talks.filter((talk) => !talk.channel_id);

  return (
    <section className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs tracking-[0.2em] text-muted">
            {variant === "live" ? "LIVE DESK" : "CHANNELS"}
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">
            {variant === "live" ? "Operate the live rooms" : "Configure the rooms"}
          </h1>
        </div>
        <Badge tone={models?.includes("+") ? "online" : "muted"}>
          {models?.includes("+") ? "Models loaded" : "No models"}
        </Badge>
      </header>
      <p className="max-w-2xl text-sm text-muted">
        {variant === "live"
          ? "Measured infer latency, real audience count from open caption streams, then stop and export. Confidence is not measured in this engine."
          : "This process owns channels 1..K. Default talks already have image, description, tags, and a YouTube URL. Extra talks stay in Events until a GPU channel is free."}
      </p>
      {variant === "setup" ? <AddTalkForm onCreated={() => void refresh()} /> : null}
      {error ? <p className="text-live">{error}</p> : null}
      {!sessions.length ? <p className="text-muted">Loading channels…</p> : null}
      <ul className="grid gap-5">
        {sessions.map((session) => {
          const row = rows.find((item) => item.id === session.id);
          const live = session.status === "processing";
          const choice = draft(session.id);
          const cueCount = row?.cue_count ?? session.cues.length;
          const watchers = row?.watchers ?? session.watchers ?? 0;
          return (
            <li key={session.id} className="surface p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="flex min-w-0 flex-1 gap-4">
                  {session.image_url ? (
                    <img
                      src={session.image_url}
                      alt=""
                      className="hidden h-20 w-32 shrink-0 object-cover sm:block"
                    />
                  ) : null}
                  <div className="min-w-0">
                    <p className="text-xs text-muted">
                      Channel {session.id}
                      {session.track ? ` · ${session.track}` : ""}
                    </p>
                    <h2 className="mt-1 text-xl">{session.title}</h2>
                    <p className="text-sm text-muted">
                      {session.room || "Room unpublished"}
                      {session.speakers?.length ? ` · ${session.speakers.join(", ")}` : ""}
                    </p>
                  </div>
                </div>
                <Badge tone={live ? "live" : session.status === "error" ? "live" : "muted"}>
                  {live ? "EN VIVO" : session.status}
                </Badge>
              </div>
              {session.description ? (
                <p className="mt-4 text-sm text-muted">{session.description}</p>
              ) : null}
              {session.tags?.length ? (
                <div className="mt-3 flex flex-wrap gap-2">
                  {session.tags.map((tag) => (
                    <span
                      key={tag}
                      className="border border-line px-2 py-1 text-[11px] uppercase tracking-[0.12em] text-muted"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              ) : null}
              <div className="mt-5 grid gap-4 md:grid-cols-2">
                <label className="space-y-2 text-sm">
                  Source
                  <select
                    className="h-11 w-full rounded-control border border-line bg-[#0e131c] px-3"
                    value={session.source_lang}
                    onChange={(event) =>
                      void saveLanguages(session, event.target.value, session.target_lang)
                    }
                  >
                    {SOURCES.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="space-y-2 text-sm">
                  Target
                  <select
                    className="h-11 w-full rounded-control border border-line bg-[#0e131c] px-3"
                    value={session.target_lang}
                    onChange={(event) =>
                      void saveLanguages(session, session.source_lang, event.target.value)
                    }
                  >
                    {TARGETS.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <fieldset className="mt-5 space-y-3">
                <legend className="text-xs uppercase tracking-[0.16em] text-muted">
                  Audio
                </legend>
                <div className="flex flex-wrap gap-2">
                  {(["file", "mic", "url"] as AudioChoice[]).map((mode) => (
                    <button
                      key={mode}
                      type="button"
                      className={cn(
                        "h-9 rounded-control border px-3 text-sm",
                        choice.mode === mode
                          ? "border-primary text-ink"
                          : "border-line text-muted",
                      )}
                      onClick={() =>
                        setDrafts((current) => ({
                          ...current,
                          [session.id]: { ...choice, mode },
                        }))
                      }
                    >
                      {mode === "file" ? "File" : mode === "mic" ? "Microphone" : "YouTube URL"}
                    </button>
                  ))}
                </div>
                {choice.mode === "file" ? (
                  <input
                    type="file"
                    accept="audio/*,video/*"
                    className="block w-full text-sm"
                    onChange={(event) => {
                      const file = event.target.files?.[0];
                      setDrafts((current) => ({
                        ...current,
                        [session.id]: { ...choice, file, mode: "file" },
                      }));
                    }}
                  />
                ) : null}
                {choice.mode === "url" ? (
                  <div className="space-y-2">
                    <input
                      type="url"
                      placeholder="https://www.youtube.com/watch?v=…"
                      className="h-11 w-full rounded-control border border-line bg-[#0e131c] px-3 text-sm"
                      value={choice.url}
                      onChange={(event) =>
                        setDrafts((current) => ({
                          ...current,
                          [session.id]: { ...choice, url: event.target.value, mode: "url" },
                        }))
                      }
                    />
                    <p className="text-xs text-muted">
                      Public YouTube live or uploaded talk. EventLyra pulls the audio. Not RTMP.
                    </p>
                  </div>
                ) : null}
                {choice.mode === "mic" ? (
                  <p className="text-sm text-muted">
                    Start live opens this tab’s microphone. Another tab should take another channel.
                  </p>
                ) : null}
              </fieldset>
              <dl
                className={cn(
                  "mt-5 grid gap-3 text-sm",
                  variant === "live" ? "grid-cols-2 sm:grid-cols-5" : "grid-cols-2 sm:grid-cols-4",
                )}
              >
                <div>
                  <dt className="text-xs text-muted">Infer</dt>
                  <dd>{row?.latency_ms != null ? `${row.latency_ms} ms` : "—"}</dd>
                </div>
                <div>
                  <dt className="text-xs text-muted">Audience</dt>
                  <dd>{watchers}</dd>
                </div>
                {variant === "live" ? (
                  <div>
                    <dt className="text-xs text-muted">Confidence</dt>
                    <dd>—</dd>
                    <p className="text-[11px] text-muted">Not measured</p>
                  </div>
                ) : null}
                <div>
                  <dt className="text-xs text-muted">Queue wait</dt>
                  <dd>{row?.queue_wait_ms != null ? `${row.queue_wait_ms} ms` : "—"}</dd>
                </div>
                <div>
                  <dt className="text-xs text-muted">Cues</dt>
                  <dd>{cueCount}</dd>
                </div>
              </dl>
              {session.error ? <p className="mt-3 text-sm text-live">{session.error}</p> : null}
              <div className="mt-5 flex flex-wrap gap-3">
                <Button
                  variant="live"
                  disabled={busy === session.id}
                  onClick={() => void start(session)}
                >
                  Start live
                </Button>
                <Button
                  variant="outline"
                  disabled={busy === session.id}
                  onClick={() => void stop(session)}
                >
                  Stop live
                </Button>
                <Link
                  to={`/watch/${session.id}`}
                  className={buttonVariants({ variant: "ghost" })}
                >
                  Audience
                </Link>
                <Link
                  to={`/overlay/${session.id}`}
                  className={buttonVariants({ variant: "ghost" })}
                >
                  Overlay
                </Link>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                <span className="self-center text-xs uppercase tracking-[0.16em] text-muted">
                  Export
                </span>
                {(["srt", "vtt", "txt"] as const).map((fmt) => (
                  <a
                    key={fmt}
                    href={exportSessionHref(session.id, fmt)}
                    className={cn(
                      buttonVariants({ variant: "outline" }),
                      cueCount === 0 && "pointer-events-none opacity-40",
                    )}
                    aria-disabled={cueCount === 0}
                  >
                    {fmt.toUpperCase()}
                  </a>
                ))}
              </div>
            </li>
          );
        })}
      </ul>
      {variant === "setup" && extras.length ? (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold">Catalog only</h2>
          <p className="text-sm text-muted">
            These talks are saved and visible in Events. They do not have a GPU
            channel on this process.
          </p>
          <ul className="grid gap-3">
            {extras.map((talk) => (
              <li key={talk.id} className="surface p-4">
                <p className="font-medium">{talk.title}</p>
                <p className="text-sm text-muted">
                  {talk.room || "Room unpublished"}
                  {talk.speakers?.length ? ` · ${talk.speakers.join(", ")}` : ""}
                </p>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      <p className="text-xs text-muted">{models}</p>
    </section>
  );
}
