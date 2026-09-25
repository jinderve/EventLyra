import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { TalkTags } from "@/components/talk-tags";
import { buttonVariants } from "@/components/ui/button";
import { getEvent, type EventPayload, type Talk } from "@/lib/api";
import { languageLabel } from "@/lib/watch-prefs";

function audioLabel(talk: Talk) {
  if (talk.audio_kind === "mic") return "Microphone";
  if (talk.audio_kind === "file") return "File";
  if (talk.youtube_url || talk.audio_kind === "url") return "YouTube";
  return "No audio yet";
}

export function SetupEventPage() {
  const [event, setEvent] = useState<EventPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getEvent()
      .then(setEvent)
      .catch((err: Error) => setError(err.message));
  }, []);

  const talks = event?.talks || [];

  return (
    <section className="space-y-6">
      <h1 className="text-3xl font-semibold tracking-tight">Confirm the event</h1>
      <p className="max-w-2xl text-muted">
        This is the edition summary. Sessions are configured and published in the
        next step — not from here.
      </p>
      {error ? (
        <p className="text-live">{error}</p>
      ) : !event ? (
        <p className="text-muted">Loading edition…</p>
      ) : (
        <dl className="surface grid gap-4 p-6 sm:grid-cols-2">
          <div>
            <dt className="text-xs uppercase tracking-[0.16em] text-muted">Event</dt>
            <dd className="mt-1 text-lg">{event.title}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-[0.16em] text-muted">K on this GPU</dt>
            <dd className="mt-1 text-lg">{event.sessions_per_gpu} channels</dd>
          </div>
          {event.tags?.length ? (
            <div className="sm:col-span-2">
              <dt className="text-xs uppercase tracking-[0.16em] text-muted">Tags</dt>
              <dd className="mt-2">
                <TalkTags tags={event.tags} />
              </dd>
            </div>
          ) : null}
          <div className="sm:col-span-2">
            <dt className="text-xs uppercase tracking-[0.16em] text-muted">Source</dt>
            <dd className="mt-1 text-sm text-muted">{event.attribution}</dd>
          </div>
        </dl>
      )}
      <div className="space-y-3">
        <h2 className="text-lg font-semibold">Configured sessions</h2>
        <p className="text-sm text-muted">
          Source, target, and audio as they stand now. Edit or publish them in
          Sessions.
        </p>
        {!talks.length ? (
          <p className="text-muted">No sessions yet.</p>
        ) : (
          <ul className="grid gap-3">
            {talks.map((talk) => (
              <li key={talk.id} className="surface flex gap-4 p-4">
                {talk.image_url ? (
                  <img
                    src={talk.image_url}
                    alt=""
                    className="hidden h-16 w-28 shrink-0 object-cover sm:block"
                  />
                ) : null}
                <div className="min-w-0 flex-1 space-y-2">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="text-xs text-muted">
                        {talk.channel_id ? `Channel ${talk.channel_id}` : "Catalog"}
                        {talk.track ? ` · ${talk.track}` : ""}
                      </p>
                      <h3 className="mt-1 text-base font-medium leading-tight">{talk.title}</h3>
                      <p className="text-sm text-muted">
                        {talk.room || "Room unpublished"}
                        {talk.speakers?.length ? ` · ${talk.speakers.join(", ")}` : ""}
                      </p>
                    </div>
                    <Badge tone={talk.published ? "online" : "muted"}>
                      {talk.published ? "Published" : "Draft"}
                    </Badge>
                  </div>
                  <p className="text-sm text-ink">
                    {languageLabel(talk.source_lang)} → {languageLabel(talk.target_lang)}
                    <span className="text-muted"> · {audioLabel(talk)}</span>
                  </p>
                  <TalkTags tags={talk.tags} />
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
      <Link to="/setup/sessions" className={buttonVariants()}>
        Continue to sessions
      </Link>
    </section>
  );
}
