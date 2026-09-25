import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { CaptionStage } from "@/components/caption-stage";
import { SiteHeader } from "@/components/site-header";
import { TalkOverview } from "@/components/talk-overview";
import { TranscriptPanel } from "@/components/transcript-panel";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { getSession, type Cue, type Session } from "@/lib/api";
import { subscribeSession } from "@/lib/realtime";
import { cn } from "@/lib/utils";
import {
  loadWatchPrefs,
  saveWatchPrefs,
  type CaptionSize,
  type CaptionText,
  type WatchPrefs,
} from "@/lib/watch-prefs";

export function WatchPage() {
  const { sessionId = "1" } = useParams();
  const [session, setSession] = useState<Session | null>(null);
  const [cues, setCues] = useState<Cue[]>([]);
  const [status, setStatus] = useState("ready");
  const [error, setError] = useState<string | null>(null);
  const [captionsOn, setCaptionsOn] = useState(true);
  const [transcriptOn, setTranscriptOn] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [prefs, setPrefs] = useState<WatchPrefs>(() =>
    typeof window === "undefined"
      ? { text: "translation", size: "s", volume: 80 }
      : loadWatchPrefs(),
  );
  const [shown, setShown] = useState<Cue | null>(null);

  function updatePrefs(next: Partial<WatchPrefs>) {
    setPrefs((current) => {
      const merged = { ...current, ...next };
      saveWatchPrefs(merged);
      return merged;
    });
  }

  useEffect(() => {
    let active = true;
    getSession(sessionId)
      .then((data) => {
        if (!active) return;
        setSession(data);
        setCues(data.cues);
        setStatus(data.status);
      })
      .catch((err: Error) => setError(err.message));
    const stop = subscribeSession(
      sessionId,
      (cue) => {
        setCues((current) => {
          const next = current.filter(
            (item) => !(item.generation === cue.generation && item.index === cue.index),
          );
          next.push(cue);
          next.sort((a, b) => a.start - b.start);
          return next;
        });
      },
      (payload) => {
        setStatus(payload.status);
        if (payload.error) setError(payload.error);
        void getSession(sessionId).then((data) => {
          if (active) setSession(data);
        });
      },
    );
    return () => {
      active = false;
      stop();
    };
  }, [sessionId]);

  const latest = cues.at(-1);

  return (
    <div className="stage min-h-screen">
      <SiteHeader />
      <main
        className={cn(
          "mx-auto flex w-full flex-col px-6 py-8",
          transcriptOn ? "max-w-7xl" : "max-w-6xl",
        )}
      >
        <header className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <Link to="/events" className={buttonVariants({ variant: "outline", size: "sm" })}>
              ← Back to events
            </Link>
            <p className="mt-3 text-xs uppercase tracking-[0.16em] text-muted">
              Events · Audience
            </p>
            <h1 className="mt-2 text-xl font-semibold">
              {session?.title || `Session ${sessionId}`}
            </h1>
            <p className="text-sm text-muted">{session?.room || "Room unpublished"}</p>
          </div>
          <Badge tone={status === "processing" ? "live" : "muted"}>
            {status === "processing"
              ? session?.playback?.is_live
                ? "EN VIVO"
                : "PROCESSING"
              : status}
          </Badge>
        </header>
        <section className="mt-6">
          {error ? <p className="mb-4 text-live">{error}</p> : null}
          <div
            className={cn(
              "grid gap-4",
              transcriptOn
                ? "xl:grid-cols-[minmax(0,1fr)_20rem_18rem]"
                : "lg:grid-cols-[minmax(0,1fr)_18rem]",
            )}
          >
            <CaptionStage
              sessionId={sessionId}
              session={session}
              cues={cues}
              liveCue={latest ?? null}
              captionsOn={captionsOn}
              transcriptOn={transcriptOn}
              settingsOpen={settingsOpen}
              captionText={prefs.text}
              captionSize={prefs.size}
              volume={prefs.volume}
              onCaptions={() => setCaptionsOn((value) => !value)}
              onTranscript={() => setTranscriptOn((value) => !value)}
              onSettings={() => setSettingsOpen((value) => !value)}
              onCaptionText={(value: CaptionText) => updatePrefs({ text: value })}
              onCaptionSize={(value: CaptionSize) => updatePrefs({ size: value })}
              onCloseSettings={() => setSettingsOpen(false)}
              onVolume={(value) => updatePrefs({ volume: Math.max(0, Math.min(100, value)) })}
              onShownChange={setShown}
            />
            {transcriptOn ? <TranscriptPanel cues={cues} active={shown} /> : null}
            <TalkOverview session={session} />
          </div>
        </section>
      </main>
    </div>
  );
}
