import { useEffect, useRef, useState } from "react";
import { WatchControls } from "@/components/watch-controls";
import { YouTubeStage } from "@/components/youtube-stage";
import { cueAt, liveAlignedTime } from "@/lib/cues";
import type { Cue, Session } from "@/lib/api";
import { CAPTION_SIZE_CLASS, type CaptionSize, type CaptionText } from "@/lib/watch-prefs";

export function CaptionStage({
  sessionId,
  session,
  cues,
  liveCue,
  captionsOn,
  transcriptOn,
  onCaptions,
  onTranscript,
  settingsOpen,
  captionText,
  captionSize,
  onSettings,
  onCaptionText,
  onCaptionSize,
  onCloseSettings,
  onShownChange,
  volume,
  onVolume,
}: {
  sessionId: string;
  session: Session | null;
  cues: Cue[];
  liveCue: Cue | null;
  captionsOn: boolean;
  transcriptOn: boolean;
  settingsOpen: boolean;
  captionText: CaptionText;
  captionSize: CaptionSize;
  volume: number;
  onCaptions: () => void;
  onTranscript: () => void;
  onSettings: () => void;
  onCaptionText: (value: CaptionText) => void;
  onCaptionSize: (value: CaptionSize) => void;
  onCloseSettings: () => void;
  onVolume: (value: number) => void;
  onShownChange?: (cue: Cue | null) => void;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);
  const [clockCue, setClockCue] = useState<Cue | null>(null);
  const [seekableLive, setSeekableLive] = useState(false);
  const [holdingVod, setHoldingVod] = useState(false);
  const playback = session?.playback;
  const kind = playback?.kind ?? null;
  const isYouTubeLive = kind === "youtube" && Boolean(playback?.is_live);
  const delaySec = playback?.delay_sec ?? 0;
  const readyUntil = Math.max(
    playback?.ready_until ?? 0,
    ...cues.map((cue) => cue.end),
  );
  const originAt = playback?.stream_origin_at ?? null;
  const mediaUrl = `/api/sessions/${sessionId}/media`;
  const useClock =
    kind === "video" ||
    kind === "audio" ||
    (kind === "youtube" && !isYouTubeLive) ||
    (isYouTubeLive && seekableLive);
  const shown =
    isYouTubeLive && seekableLive ? clockCue : useClock ? clockCue || liveCue : liveCue;

  useEffect(() => {
    onShownChange?.(shown);
  }, [onShownChange, shown]);

  useEffect(() => {
    if (kind !== "video" && kind !== "audio") {
      return;
    }
    const element = kind === "video" ? videoRef.current : audioRef.current;
    if (!element) return;
    const sync = () => setClockCue(cueAt(cues, element.currentTime));
    element.addEventListener("timeupdate", sync);
    element.addEventListener("seeked", sync);
    sync();
    return () => {
      element.removeEventListener("timeupdate", sync);
      element.removeEventListener("seeked", sync);
    };
  }, [cues, kind, session?.generation]);

  useEffect(() => {
    if (!isYouTubeLive || !seekableLive || originAt == null) {
      if (isYouTubeLive && !seekableLive) {
        setClockCue(null);
      }
      return;
    }
    const tick = () => {
      setClockCue(cueAt(cues, liveAlignedTime(Date.now() / 1000, originAt, delaySec)));
    };
    tick();
    const timer = window.setInterval(tick, 250);
    return () => window.clearInterval(timer);
  }, [cues, delaySec, isYouTubeLive, originAt, seekableLive]);

  useEffect(() => {
    setSeekableLive(false);
    if (kind !== "youtube") setClockCue(null);
  }, [kind, session?.generation]);

  return (
    <div className="relative min-h-[320px] overflow-hidden rounded-box border border-line bg-[linear-gradient(180deg,#10151f,#0c1118)] sm:min-h-[420px]">
      {kind === "video" && playback?.has_media ? (
        <video
          key={`${sessionId}-${session?.generation}-video`}
          ref={videoRef}
          className="block max-h-[68vh] w-full bg-black"
          src={mediaUrl}
          controls
          playsInline
          autoPlay
        />
      ) : null}
      {kind === "audio" && playback?.has_media ? (
        <div className="flex min-h-[320px] flex-col justify-end bg-[#05060a] px-4 pb-24 pt-10 sm:min-h-[420px]">
          <audio
            key={`${sessionId}-${session?.generation}-audio`}
            ref={audioRef}
            className="w-full"
            src={mediaUrl}
            controls
            autoPlay
          />
        </div>
      ) : null}
      {kind === "youtube" && playback?.youtube_id ? (
        <>
          <YouTubeStage
            key={`${sessionId}-${session?.generation}-${playback.youtube_id}`}
            videoId={playback.youtube_id}
            isLive={Boolean(playback.is_live)}
            delaySec={delaySec}
            readyUntil={readyUntil}
            volume={volume}
            onTime={(time) => setClockCue(cueAt(cues, time))}
            onSeekableChange={setSeekableLive}
            onHoldChange={setHoldingVod}
          />
          <div className="absolute inset-0 z-[5]" aria-hidden />
        </>
      ) : null}
      {kind === "mic" || !kind ? (
        <div className="grid min-h-[320px] place-items-center px-8 text-center text-muted sm:min-h-[420px]">
          {kind === "mic"
            ? "Live microphone. Captions appear over this stage."
            : "Waiting for the organizer to start video, audio, or YouTube."}
        </div>
      ) : null}
      {isYouTubeLive && delaySec > 0 ? (
        <p className="absolute left-3 top-3 z-10 max-w-[90%] text-left text-[11px] uppercase tracking-[0.14em] text-muted">
          {seekableLive
            ? `Picture delayed ${Math.round(delaySec)}s so captions match`
            : `This live cannot seek back. Captions lag the picture by ~${Math.round(delaySec)}s`}
        </p>
      ) : null}
      {kind === "youtube" && !isYouTubeLive ? (
        <p className="absolute left-3 top-3 z-10 max-w-[90%] text-left text-[11px] uppercase tracking-[0.14em] text-muted">
          {holdingVod
            ? "Holding picture until captions catch up"
            : "Playback follows the caption timeline"}
        </p>
      ) : null}
      <div className="pointer-events-none absolute inset-x-[4%] bottom-20 z-10 text-center sm:bottom-24">
        {captionsOn && shown ? (
          <>
            {captionText !== "translation" ? (
              <p
                className={`${CAPTION_SIZE_CLASS[captionSize].primary} font-semibold leading-tight text-white drop-shadow-[0_2px_8px_rgba(0,0,0,0.85)]`}
              >
                {shown.original}
              </p>
            ) : null}
            {captionText !== "original" ? (
              <p
                className={`${captionText === "both" ? `mt-3 ${CAPTION_SIZE_CLASS[captionSize].secondary}` : CAPTION_SIZE_CLASS[captionSize].primary} leading-tight text-signal drop-shadow-[0_2px_8px_rgba(0,0,0,0.85)]`}
              >
                {shown.translation}
              </p>
            ) : null}
          </>
        ) : null}
        {captionsOn && !shown ? (
          <p className="text-lg text-muted">Waiting for captions…</p>
        ) : null}
      </div>
      <div className="absolute inset-x-3 bottom-3 z-20 flex justify-end">
        <WatchControls
          captionsOn={captionsOn}
          transcriptOn={transcriptOn}
          settingsOpen={settingsOpen}
          text={captionText}
          size={captionSize}
          sourceLang={session?.detected_lang || session?.source_lang || "auto"}
          targetLang={session?.target_lang || "es"}
          volume={volume}
          showVolume={kind === "youtube"}
          onCaptions={onCaptions}
          onTranscript={onTranscript}
          onSettings={onSettings}
          onText={onCaptionText}
          onSize={onCaptionSize}
          onCloseSettings={onCloseSettings}
          onVolume={onVolume}
        />
      </div>
    </div>
  );
}
