import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { createTalk, updateTalk, type Talk, type TalkDraft } from "@/lib/api";

const EMPTY: TalkDraft = {
  title: "",
  room: "",
  track: "",
  description: "",
  tags: "",
  speakers: "",
  image_url: "",
  youtube_url: "",
  source_lang: "auto",
  target_lang: "es",
  audio_kind: "url",
};

function fromTalk(talk: Talk): TalkDraft {
  return {
    title: talk.title,
    room: talk.room || "",
    track: talk.track || "",
    description: talk.description || "",
    tags: (talk.tags || []).join(", "),
    speakers: (talk.speakers || []).join(", "),
    image_url: talk.image_url || "",
    youtube_url: talk.youtube_url || "",
    source_lang: talk.source_lang || "auto",
    target_lang: talk.target_lang || "es",
    audio_kind: talk.audio_kind || (talk.youtube_url ? "url" : "file"),
  };
}

export function TalkForm({
  talk,
  onDone,
  onCancel,
}: {
  talk?: Talk;
  onDone: () => void;
  onCancel: () => void;
}) {
  const [draft, setDraft] = useState<TalkDraft>(talk ? fromTalk(talk) : EMPTY);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (talk) {
        await updateTalk(talk.id, draft);
      } else {
        await createTalk(draft);
      }
      onDone();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save the talk.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={(event) => void submit(event)} className="surface space-y-4 p-5">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">{talk ? "Edit session" : "New session"}</h2>
        <button type="button" className="text-sm text-muted" onClick={onCancel}>
          Cancel
        </button>
      </div>
      <p className="text-sm text-muted">
        {talk
          ? "Changes apply to this event catalog card. Publish from the summary when the room is ready."
          : "Metadata is saved to the event catalog. Only the first K talks get a GPU channel."}
      </p>
      <label className="block space-y-1 text-sm">
        Title
        <input
          required
          className="h-11 w-full rounded-control border border-line bg-[#0e131c] px-3"
          value={draft.title}
          onChange={(event) => setDraft({ ...draft, title: event.target.value })}
        />
      </label>
      <div className="grid gap-3 md:grid-cols-2">
        <label className="space-y-1 text-sm">
          Room
          <input
            className="h-11 w-full rounded-control border border-line bg-[#0e131c] px-3"
            value={draft.room}
            onChange={(event) => setDraft({ ...draft, room: event.target.value })}
          />
        </label>
        <label className="space-y-1 text-sm">
          Track
          <input
            className="h-11 w-full rounded-control border border-line bg-[#0e131c] px-3"
            value={draft.track}
            onChange={(event) => setDraft({ ...draft, track: event.target.value })}
          />
        </label>
      </div>
      <label className="block space-y-1 text-sm">
        Description
        <textarea
          className="min-h-24 w-full rounded-control border border-line bg-[#0e131c] px-3 py-2"
          value={draft.description}
          onChange={(event) => setDraft({ ...draft, description: event.target.value })}
        />
      </label>
      <label className="block space-y-1 text-sm">
        Tags
        <input
          className="h-11 w-full rounded-control border border-line bg-[#0e131c] px-3"
          placeholder="softskills, liderazgo"
          value={draft.tags}
          onChange={(event) => setDraft({ ...draft, tags: event.target.value })}
        />
      </label>
      <label className="block space-y-1 text-sm">
        Speakers
        <input
          className="h-11 w-full rounded-control border border-line bg-[#0e131c] px-3"
          placeholder="Name, Name"
          value={draft.speakers}
          onChange={(event) => setDraft({ ...draft, speakers: event.target.value })}
        />
      </label>
      <label className="block space-y-1 text-sm">
        Image URL
        <input
          className="h-11 w-full rounded-control border border-line bg-[#0e131c] px-3"
          value={draft.image_url}
          onChange={(event) => setDraft({ ...draft, image_url: event.target.value })}
        />
      </label>
      <label className="block space-y-1 text-sm">
        Audio
        <select
          className="h-11 w-full rounded-control border border-line bg-[#0e131c] px-3"
          value={draft.audio_kind || "url"}
          onChange={(event) => setDraft({ ...draft, audio_kind: event.target.value })}
        >
          <option value="url">YouTube URL</option>
          <option value="file">File</option>
          <option value="mic">Microphone</option>
        </select>
      </label>
      {draft.audio_kind !== "file" && draft.audio_kind !== "mic" ? (
        <label className="block space-y-1 text-sm">
          YouTube URL
          <input
            className="h-11 w-full rounded-control border border-line bg-[#0e131c] px-3"
            value={draft.youtube_url}
            onChange={(event) =>
              setDraft({ ...draft, youtube_url: event.target.value, audio_kind: "url" })
            }
          />
        </label>
      ) : (
        <p className="text-sm text-muted">
          {draft.audio_kind === "file"
            ? "The operator chooses the file on Live desk when starting the room."
            : "Live desk opens this tab’s microphone. Another tab should take another channel."}
        </p>
      )}
      <div className="grid gap-3 md:grid-cols-2">
        <label className="space-y-1 text-sm">
          Source
          <select
            className="h-11 w-full rounded-control border border-line bg-[#0e131c] px-3"
            value={draft.source_lang}
            onChange={(event) => setDraft({ ...draft, source_lang: event.target.value })}
          >
            <option value="auto">Detect</option>
            <option value="es">Spanish</option>
            <option value="en">English</option>
            <option value="pt">Portuguese</option>
          </select>
        </label>
        <label className="space-y-1 text-sm">
          Target
          <select
            className="h-11 w-full rounded-control border border-line bg-[#0e131c] px-3"
            value={draft.target_lang}
            onChange={(event) => setDraft({ ...draft, target_lang: event.target.value })}
          >
            <option value="es">Spanish</option>
            <option value="en">English</option>
            <option value="pt">Portuguese</option>
          </select>
        </label>
      </div>
      {error ? <p className="text-sm text-live">{error}</p> : null}
      <Button type="submit" disabled={busy}>
        {talk ? "Save changes" : "Save session"}
      </Button>
    </form>
  );
}

export function AddTalkForm({ onCreated }: { onCreated: () => void }) {
  const [open, setOpen] = useState(false);

  if (!open) {
    return (
      <Button variant="outline" onClick={() => setOpen(true)}>
        Add session
      </Button>
    );
  }

  return (
    <TalkForm
      onDone={() => {
        setOpen(false);
        onCreated();
      }}
      onCancel={() => setOpen(false)}
    />
  );
}
