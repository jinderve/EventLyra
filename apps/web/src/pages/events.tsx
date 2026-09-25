import { useEffect, useState } from "react";
import { SiteHeader } from "@/components/site-header";
import { TalkCard } from "@/components/talk-card";
import { getEvent, type EventPayload, type Talk } from "@/lib/api";

type Filter = "all" | "live" | "upcoming";

export function EventsPage() {
  const [event, setEvent] = useState<EventPayload | null>(null);
  const [filter, setFilter] = useState<Filter>("all");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function refresh() {
      try {
        const data = await getEvent();
        if (!cancelled) {
          setEvent(data);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Could not load events.");
      }
    }
    void refresh();
    const timer = window.setInterval(() => void refresh(), 4000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  const talks = (event?.talks || []).filter((talk: Talk) => {
    if (!talk.published) return false;
    if (filter === "live") return Boolean(talk.live);
    if (filter === "upcoming") return !talk.live;
    return true;
  });

  return (
    <div className="stage min-h-screen">
      <SiteHeader />
      <main className="mx-auto max-w-6xl px-6 py-10">
        <p className="text-xs uppercase tracking-[0.16em] text-muted">Events</p>
        <div className="mt-3 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-4xl font-semibold tracking-tight">
              {event?.title || "Live events"}
            </h1>
            <p className="mt-2 max-w-xl text-muted">
              Join a room with real-time captions. The audience view keeps the
              talk overview and captions — no latency or confidence meters.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {(["all", "live", "upcoming"] as Filter[]).map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => setFilter(item)}
                className={
                  filter === item
                    ? "h-10 rounded-control border border-[#8251ff] bg-[linear-gradient(90deg,#7647ff,#9462ff)] px-3 text-sm text-white"
                    : "h-10 rounded-control border border-line bg-[#0e131c] px-3 text-sm text-muted"
                }
              >
                {item === "all" ? "All" : item === "live" ? "Live" : "Upcoming"}
              </button>
            ))}
          </div>
        </div>
        {error ? <p className="mt-6 text-live">{error}</p> : null}
        {!talks.length && !error ? (
          <p className="mt-10 text-muted">
            {event?.talks?.some((talk) => !talk.published)
              ? "No published talks yet. An organizer publishes a configured session from Sessions."
              : "No talks in this filter."}
          </p>
        ) : (
          <ul className="mt-10 grid auto-rows-fr items-stretch gap-5 md:grid-cols-2">
            {talks.map((talk) => (
              <li key={talk.id} className="h-full min-h-[28rem]">
                <TalkCard talk={talk} />
              </li>
            ))}
          </ul>
        )}
      </main>
    </div>
  );
}
