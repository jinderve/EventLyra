import type { Session } from "@/lib/api";

export function TalkOverview({ session }: { session: Session | null }) {
  if (!session) {
    return (
      <aside className="surface p-5">
        <p className="text-xs uppercase tracking-[0.16em] text-muted">Talk</p>
        <p className="mt-3 text-sm text-muted">Loading talk details…</p>
      </aside>
    );
  }
  return (
    <aside className="surface overflow-hidden p-5">
      {session.image_url ? (
        <img
          src={session.image_url}
          alt=""
          className="mb-4 aspect-video w-full object-cover"
        />
      ) : null}
      <p className="text-xs uppercase tracking-[0.16em] text-muted">Talk</p>
      <h2 className="mt-2 text-lg font-semibold leading-tight">{session.title}</h2>
      <p className="mt-2 text-sm text-muted">
        {session.room || "Room unpublished"}
        {session.track ? ` · ${session.track}` : ""}
      </p>
      {session.speakers?.length ? (
        <p className="mt-2 text-sm">{session.speakers.join(", ")}</p>
      ) : null}
      {session.description ? (
        <p className="mt-4 text-sm leading-relaxed text-muted">{session.description}</p>
      ) : (
        <p className="mt-4 text-sm text-muted">No description yet.</p>
      )}
      {session.tags?.length ? (
        <div className="mt-4 flex flex-wrap gap-2">
          {session.tags.map((tag) => (
            <span
              key={tag}
              className="rounded-[7px] border border-[#25324b] bg-[#0f1622] px-2 py-1 text-[11px] uppercase tracking-[0.12em] text-[#9fb4d6]"
            >
              {tag}
            </span>
          ))}
        </div>
      ) : null}
    </aside>
  );
}
