import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { AddTalkForm, TalkForm } from "@/components/add-talk-form";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { TalkTags } from "@/components/talk-tags";
import {
  exportSessionHref,
  getHealth,
  getProduction,
  listSessions,
  listTalks,
  patchSession,
  startSessionUrl,
  stopSession,
  updateTalk,
  uploadSessionFile,
  type ProductionRow,
  type Session,
  type Talk,
} from "@/lib/api";
import { startMicrophone } from "@/lib/mic";
import { cn } from "@/lib/utils";
import { languageLabel } from "@/lib/watch-prefs";

type AudioChoice = "file" | "mic" | "url";

function defaultDraft(session: Session, talk?: Talk) {
  const url = talk?.youtube_url || session.youtube_url || session.playback?.youtube_url || "";
  const kind = (talk?.audio_kind || session.audio_kind || (url ? "url" : "file")) as AudioChoice;
  return { url, mode: kind === "mic" || kind === "file" || kind === "url" ? kind : "url" };
}

function audioLabel(mode: AudioChoice, url: string) {
  if (mode === "mic") return "Microphone";
  if (mode === "file") return "File";
  return url ? "YouTube" : "No audio yet";
}

function canPublish(talk: Talk | undefined, session: Session | undefined, url: string, mode: AudioChoice) {
  const source = talk?.source_lang || session?.source_lang;
  const target = talk?.target_lang || session?.target_lang;
  const hasAudio = mode === "mic" || mode === "file" || Boolean(url || talk?.youtube_url);
  return Boolean(source && target && hasAudio);
}

export function SessionBoard({ variant }: { variant: "setup" | "live" }) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [talks, setTalks] = useState<Talk[]>([]);
  const [rows, setRows] = useState<ProductionRow[]>([]);
  const [models, setModels] = useState<string | null>(null);
  const [chunkSeconds, setChunkSeconds] = useState(8);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [editing, setEditing] = useState<string | null>(null);
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
        const talk = catalog.talks.find((item) => item.channel_id === session.id);
        next[session.id] ??= defaultDraft(session, talk);
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

  function talkFor(session: Session) {
    return talks.find((item) => item.channel_id === session.id || item.id === session.talk_id);
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
        const url = choice.url.trim() || session.youtube_url || "";
        if (!url) throw new Error("Paste a YouTube URL before Start live.");
        await startSessionUrl(session.id, url);
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
      await stopSession(session.id);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not stop the session.");
    } finally {
      setBusy(null);
    }
  }

  async function publish(talk: Talk, next: boolean) {
    setBusy(talk.id);
    setError(null);
    try {
      await updateTalk(talk.id, { published: next });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update publish state.");
    } finally {
      setBusy(null);
    }
  }

  const extras = talks.filter((talk) => !talk.channel_id);
  const liveSessions = sessions.filter((session) => {
    const talk = talkFor(session);
    return Boolean(talk?.published ?? session.published);
  });
  const visible = variant === "live" ? liveSessions : sessions;

  return (
    <section className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs tracking-[0.2em] text-muted">
            {variant === "live" ? "LIVE DESK" : "CHANNELS"}
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">
            {variant === "live" ? "Operate published rooms" : "Configure the rooms"}
          </h1>
        </div>
        <Badge tone={models?.includes("+") ? "online" : "muted"}>
          {models?.includes("+") ? "Models loaded" : "No models"}
        </Badge>
      </header>
      <p className="max-w-2xl text-sm text-muted">
        {variant === "live"
          ? "Only published sessions appear here. Start, stop, overlay, and export the transcript. Stop keeps the cues so SRT, VTT, and TXT still download. Confidence is not measured."
          : "Review source, target, and audio, then publish. Edit a room to change its setup. Live desk and Events only show published rooms."}
      </p>
      {variant === "setup" ? <AddTalkForm onCreated={() => void refresh()} /> : null}
      {error ? <p className="text-live">{error}</p> : null}
      {variant === "live" && !visible.length ? (
        <p className="text-muted">
          No published sessions yet. Configure a room in Sessions and press Publish.
        </p>
      ) : null}
      {!sessions.length ? <p className="text-muted">Loading channels…</p> : null}
      <ul className="grid gap-5">
        {visible.map((session) => {
          const talk = talkFor(session);
          const row = rows.find((item) => item.id === session.id);
          const live = session.status === "processing";
          const choice = draft(session.id);
          const cueCount = row?.cue_count ?? session.cues.length;
          const watchers = row?.watchers ?? session.watchers ?? 0;
          const published = Boolean(talk?.published ?? session.published);
          const ready = canPublish(talk, session, choice.url, choice.mode);
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
                <div className="flex flex-wrap gap-2">
                  <Badge tone={published ? "online" : "muted"}>
                    {published ? "Published" : "Draft"}
                  </Badge>
                  <Badge tone={live ? "live" : session.status === "error" ? "live" : "muted"}>
                    {live ? "EN VIVO" : session.status}
                  </Badge>
                </div>
              </div>
              <TalkTags tags={session.tags} className="mt-3" />

              {variant === "setup" ? (
                <>
                  <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-3">
                    <div>
                      <dt className="text-xs uppercase tracking-[0.14em] text-muted">Source</dt>
                      <dd className="mt-1">{languageLabel(session.source_lang)}</dd>
                    </div>
                    <div>
                      <dt className="text-xs uppercase tracking-[0.14em] text-muted">Target</dt>
                      <dd className="mt-1">{languageLabel(session.target_lang)}</dd>
                    </div>
                    <div className="min-w-0">
                      <dt className="text-xs uppercase tracking-[0.14em] text-muted">Audio</dt>
                      <dd className="mt-1">{audioLabel(choice.mode, choice.url)}</dd>
                      {choice.mode === "url" && choice.url ? (
                        <p className="mt-1 truncate text-xs text-muted" title={choice.url}>
                          {choice.url}
                        </p>
                      ) : null}
                    </div>
                  </dl>
                  {editing === session.id && talk ? (
                    <div className="mt-5">
                      <TalkForm
                        talk={talk}
                        onDone={() => {
                          setEditing(null);
                          void refresh();
                        }}
                        onCancel={() => setEditing(null)}
                      />
                    </div>
                  ) : (
                    <div className="mt-5 flex flex-wrap gap-3">
                      <Button variant="outline" onClick={() => setEditing(session.id)}>
                        Edit session
                      </Button>
                      <Button
                        disabled={busy === talk?.id || (!published && !ready)}
                        onClick={() => talk && void publish(talk, !published)}
                      >
                        {published ? "Unpublish" : "Publish"}
                      </Button>
                    </div>
                  )}
                  {!ready && !published ? (
                    <p className="mt-3 text-sm text-muted">
                      Publish needs a source, a target, and an audio source.
                    </p>
                  ) : null}
                </>
              ) : (
                <>
                  <p className="mt-4 text-sm text-ink">
                    {languageLabel(session.source_lang)} → {languageLabel(session.target_lang)}
                    <span className="text-muted"> · {audioLabel(choice.mode, choice.url)}</span>
                  </p>
                  {choice.mode === "file" ? (
                    <input
                      type="file"
                      accept="audio/*,video/*"
                      className="mt-4 block w-full text-sm"
                      onChange={(event) => {
                        const file = event.target.files?.[0];
                        setDrafts((current) => ({
                          ...current,
                          [session.id]: { ...choice, file, mode: "file" },
                        }));
                      }}
                    />
                  ) : null}
                  <dl className="mt-5 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
                    <div>
                      <dt className="text-xs text-muted">Infer</dt>
                      <dd>{row?.latency_ms != null ? `${row.latency_ms} ms` : "—"}</dd>
                    </div>
                    <div>
                      <dt className="text-xs text-muted">Audience</dt>
                      <dd>{watchers}</dd>
                    </div>
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
                </>
              )}
            </li>
          );
        })}
      </ul>
      {variant === "setup" && extras.length ? (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold">Catalog only</h2>
          <p className="text-sm text-muted">
            These talks are saved. They do not have a GPU channel, so they cannot
            go to Live desk.
          </p>
          <ul className="grid gap-3">
            {extras.map((talk) => (
              <li key={talk.id} className="surface p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-medium">{talk.title}</p>
                    <p className="text-sm text-muted">
                      {talk.room || "Room unpublished"}
                      {talk.speakers?.length ? ` · ${talk.speakers.join(", ")}` : ""}
                    </p>
                    <p className="mt-1 text-sm">
                      {languageLabel(talk.source_lang)} → {languageLabel(talk.target_lang)}
                    </p>
                    <TalkTags tags={talk.tags} className="mt-2" />
                  </div>
                  <Badge tone={talk.published ? "online" : "muted"}>
                    {talk.published ? "Published" : "Draft"}
                  </Badge>
                </div>
                {editing === talk.id ? (
                  <div className="mt-4">
                    <TalkForm
                      talk={talk}
                      onDone={() => {
                        setEditing(null);
                        void refresh();
                      }}
                      onCancel={() => setEditing(null)}
                    />
                  </div>
                ) : (
                  <div className="mt-4 flex flex-wrap gap-3">
                    <Button variant="outline" onClick={() => setEditing(talk.id)}>
                      Edit session
                    </Button>
                    <Button
                      variant="outline"
                      disabled
                      title="A GPU channel is required to publish to Live desk"
                    >
                      Publish
                    </Button>
                  </div>
                )}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      <p className="text-xs text-muted">{models}</p>
    </section>
  );
}
