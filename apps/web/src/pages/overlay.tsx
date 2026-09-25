import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { CaptionOverlay } from "@/components/caption-overlay";
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
    <main className="flex min-h-screen items-end justify-center bg-transparent p-8">
      <CaptionOverlay
        original={cue.original}
        translation={cue.translation}
        text="both"
        size="l"
        background="black"
      />
    </main>
  );
}
