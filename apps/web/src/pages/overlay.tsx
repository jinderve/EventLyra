import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getSession, type Cue } from "@/lib/api";
import { subscribeSession } from "@/lib/realtime";

export function OverlayPage() {
  const { sessionId = "1" } = useParams();
  const [cue, setCue] = useState<Cue | null>(null);

  useEffect(() => {
    document.documentElement.style.background = "transparent";
    document.body.style.background = "transparent";
    getSession(sessionId)
      .then((data) => setCue(data.cues.at(-1) ?? null))
      .catch(() => undefined);
    return subscribeSession(sessionId, setCue, () => undefined);
  }, [sessionId]);

  if (!cue) {
    return <main className="min-h-screen bg-transparent" />;
  }

  return (
    <main className="flex min-h-screen items-end bg-transparent p-8">
      <div className="max-w-5xl">
        <p className="text-3xl font-semibold text-white drop-shadow-[0_2px_8px_rgba(0,0,0,0.85)]">
          {cue.original}
        </p>
        <p className="mt-3 text-2xl text-signal drop-shadow-[0_2px_8px_rgba(0,0,0,0.85)]">
          {cue.translation}
        </p>
      </div>
    </main>
  );
}
