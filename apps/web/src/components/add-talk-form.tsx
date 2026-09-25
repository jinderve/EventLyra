import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { createTalk } from "@/lib/api";

const EMPTY = {
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
};

export function AddTalkForm({ onCreated }: { onCreated: () => void }) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState(EMPTY);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await createTalk(draft);
      setDraft(EMPTY);
      setOpen(false);
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save the talk.");
    } finally {
      setBusy(false);
    }
  }

  if (!open) {
    return (
      <Button variant="outline" onClick={() => setOpen(true)}>
        Add session
      </Button>
    );
  }

  return (
    <form onSubmit={(event) => void submit(event)} className="surface space-y-4 p-5">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">New session</h2>
        <button type="button" className="text-sm text-muted" onClick={() => setOpen(false)}>
          Cancel
        </button>
      </div>
      <p className="text-sm text-muted">
        Metadata is saved to the event catalog. Only the first K talks get a GPU
        channel and can go live on this process.
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
        YouTube URL
        <input
          className="h-11 w-full rounded-control border border-line bg-[#0e131c] px-3"
          value={draft.youtube_url}
          onChange={(event) => setDraft({ ...draft, youtube_url: event.target.value })}
        />
      </label>
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
        Save session
      </Button>
    </form>
  );
}
