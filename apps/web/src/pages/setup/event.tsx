import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AddTalkForm } from "@/components/add-talk-form";
import { TalkCard } from "@/components/talk-card";
import { buttonVariants } from "@/components/ui/button";
import { getEvent, type EventPayload } from "@/lib/api";

export function SetupEventPage() {
  const [event, setEvent] = useState<EventPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  function refresh() {
    getEvent()
      .then(setEvent)
      .catch((err: Error) => setError(err.message));
  }

  useEffect(() => {
    refresh();
  }, []);

  const talks = event?.talks || [];

  return (
    <section className="space-y-6">
      <h1 className="text-3xl font-semibold tracking-tight">Confirm the event</h1>
      <p className="max-w-2xl text-muted">
        The two Nerdearla default talks are already configured: image,
        description, tags, speakers, and YouTube URL. Add another session when
        you need a new card in Sessions and Events.
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
              <dd className="mt-2 flex flex-wrap gap-2">
                {event.tags.map((tag) => (
                  <span
                    key={tag}
                    className="rounded-[7px] border border-[#25324b] bg-[#0f1622] px-2 py-1 text-[11px] uppercase tracking-[0.12em] text-[#9fb4d6]"
                  >
                    {tag}
                  </span>
                ))}
              </dd>
            </div>
          ) : null}
          <div className="sm:col-span-2">
            <dt className="text-xs uppercase tracking-[0.16em] text-muted">Source</dt>
            <dd className="mt-1 text-sm text-muted">{event.attribution}</dd>
          </div>
        </dl>
      )}
      <AddTalkForm onCreated={refresh} />
      {talks.length ? (
        <ul className="grid auto-rows-fr items-stretch gap-5 md:grid-cols-2">
          {talks.map((talk) => (
            <li key={talk.id} className="h-full min-h-[28rem]">
              <TalkCard
                talk={talk}
                href="/setup/sessions"
                footer={
                  talk.channel_id
                    ? `Channel ${talk.channel_id} · continue to sessions →`
                    : "Saved in catalog · no GPU channel yet"
                }
              />
            </li>
          ))}
        </ul>
      ) : null}
      <Link to="/setup/sessions" className={buttonVariants()}>
        Continue to sessions
      </Link>
    </section>
  );
}
