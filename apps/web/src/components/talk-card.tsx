import { Link } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import type { Talk } from "@/lib/api";
import { cn } from "@/lib/utils";

export function TalkCard({
  talk,
  href,
  footer,
}: {
  talk: Talk;
  href?: string;
  footer?: string;
}) {
  const to = href ?? (talk.channel_id ? `/watch/${talk.channel_id}` : undefined);
  const label =
    footer ??
    (to ? "Enter room →" : "Waiting for a GPU channel (K is full)");
  const body = (
    <>
      {talk.image_url ? (
        <img
          src={talk.image_url}
          alt=""
          className="aspect-video w-full shrink-0 object-cover"
        />
      ) : (
        <div className="aspect-video w-full shrink-0 bg-[#090d14]" />
      )}
      <div className="flex min-h-0 flex-1 flex-col gap-3 p-5">
        <Badge tone={talk.live ? "live" : "muted"}>
          {talk.live ? "EN VIVO" : talk.channel_id ? "Ready" : "Catalog"}
        </Badge>
        <h2 className="line-clamp-2 min-h-[3.25rem] text-xl font-semibold leading-tight">
          {talk.title}
        </h2>
        <p className="line-clamp-1 text-sm text-muted">
          {talk.room || "Room unpublished"}
          {talk.speakers?.length ? ` · ${talk.speakers.join(", ")}` : ""}
        </p>
        <p className="line-clamp-3 min-h-[3.75rem] text-sm text-muted">
          {talk.description || "No description yet."}
        </p>
        <div className="flex min-h-[2rem] flex-wrap content-start gap-2">
          {(talk.tags || []).map((tag) => (
            <span
              key={tag}
              className="rounded-[7px] border border-[#25324b] bg-[#0f1622] px-2 py-1 text-[11px] uppercase tracking-[0.12em] text-[#9fb4d6]"
            >
              {tag}
            </span>
          ))}
        </div>
        <p className="mt-auto text-sm text-ink">{label}</p>
      </div>
    </>
  );
  const frame = cn(
    "flex h-full flex-col overflow-hidden border border-line bg-[linear-gradient(180deg,#10151f,#0c1118)]",
    "rounded-box",
    talk.live && "border-[#344363] bg-[linear-gradient(135deg,rgba(51,29,105,0.38),rgba(12,17,24,0.96))]",
  );
  if (!to) {
    return <article className={frame}>{body}</article>;
  }
  return (
    <Link to={to} className={cn(frame, "hover:border-[#394865]")}>
      {body}
    </Link>
  );
}
