import { useEffect, useRef, useState } from "react";
import { CaptionOverlay } from "@/components/caption-overlay";
import { WatchControls } from "@/components/watch-controls";
import { YouTubeStage } from "@/components/youtube-stage";
import { cueAt, liveAlignedTime } from "@/lib/cues";
import type { Cue, Session } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { CaptionBg, CaptionSize, CaptionText } from "@/lib/watch-prefs";

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
  captionBg,
  onSettings,
  onCaptionText,
  onCaptionSize,
  onCaptionBg,
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
  captionBg: CaptionBg;
  volume: number;
  onCaptions: () => void;
  onTranscript: () => void;
  onSettings: () => void;
  onCaptionText: (value: CaptionText) => void;
  onCaptionSize: (value: CaptionSize) => void;
  onCaptionBg: (value: CaptionBg) => void;
  onCloseSettings: () => void;
  onVolume: (value: number) => void;
  onShownChange?: (cue: Cue | null) => void;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  const [clockCue, setClockCue] = useState<Cue | null>(null);
  const [seekableLive, setSeekableLive] = useState(false);
  const [holdingVod, setHoldingVod] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const [bottomHover, setBottomHover] = useState(false);
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
  const shown = useClock ? clockCue : liveCue;
  const chromeOpen = settingsOpen || bottomHover;

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

  useEffect(() => {
    const onChange = () => {
      setFullscreen(document.fullscreenElement === stageRef.current);
    };
    document.addEventListener("fullscreenchange", onChange);
    return () => document.removeEventListener("fullscreenchange", onChange);
  }, []);

  async function toggleFullscreen() {
    const node = stageRef.current;
    if (!node) return;
    if (document.fullscreenElement === node) {
      await document.exitFullscreen();
      return;
    }
    await node.requestFullscreen();
  }

  return (
    <div
      ref={stageRef}
      className="overflow-hidden rounded-box border border-line bg-[#05060a]"
    >
      <div className="relative aspect-video w-full bg-black">
        {kind === "video" && playback?.has_media ? (
          <video
            key={`${sessionId}-${session?.generation}-video`}
            ref={videoRef}
            className="absolute inset-0 h-full w-full bg-black object-contain"
            src={mediaUrl}
            controls
            playsInline
            autoPlay
          />
        ) : null}
        {kind === "audio" && playback?.has_media ? (
          <div className="absolute inset-0 flex flex-col justify-end bg-[#05060a] px-4 pb-24 pt-10">
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
          <div className="absolute inset-0 grid place-items-center px-8 text-center text-muted">
            {kind === "mic"
              ? "Live microphone. Captions appear over this stage."
              : "Waiting for the organizer to start video, audio, or YouTube."}
          </div>
        ) : null}
        {isYouTubeLive && delaySec > 0 ? (
          <p className="absolute left-3 top-3 z-10 max-w-[90%] text-left text-[11px] uppercase tracking-[0.14em] text-white/70">
            {seekableLive
              ? `Picture delayed ${Math.round(delaySec)}s so captions match`
              : `This live cannot seek back. Captions lag the picture by ~${Math.round(delaySec)}s`}
          </p>
        ) : null}
        {kind === "youtube" && !isYouTubeLive ? (
          <p className="absolute left-3 top-3 z-10 max-w-[90%] text-left text-[11px] uppercase tracking-[0.14em] text-white/70">
            {holdingVod
              ? "Holding picture until captions catch up"
              : "Playback follows the caption timeline"}
          </p>
        ) : null}
        <div
          className={cn(
            "pointer-events-none absolute inset-x-[5%] z-10 flex justify-center transition-[bottom] duration-200 motion-reduce:transition-none",
            chromeOpen ? "bottom-20 sm:bottom-24" : "bottom-6",
          )}
        >
          {captionsOn && shown ? (
            <CaptionOverlay
              original={shown.original}
              translation={shown.translation}
              text={captionText}
              size={captionSize}
              background={captionBg}
            />
          ) : null}
          {captionsOn && !shown ? (
            <CaptionOverlay
              text={captionText}
              size={captionSize}
              background={captionBg}
              empty
            />
          ) : null}
        </div>
        <div
          className="absolute inset-x-0 bottom-0 z-20 h-[22%] min-h-28"
          onMouseEnter={() => setBottomHover(true)}
          onMouseLeave={() => setBottomHover(false)}
          onFocusCapture={() => setBottomHover(true)}
          onBlurCapture={(event) => {
            if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
              setBottomHover(false);
            }
          }}
        >
          <div
            className={cn(
              "absolute inset-x-3 bottom-3 flex justify-end transition-opacity duration-200 motion-reduce:transition-none",
              chromeOpen
                ? "opacity-100"
                : "pointer-events-none opacity-0 [@media(hover:none)]:pointer-events-auto [@media(hover:none)]:opacity-100",
            )}
          >
          <WatchControls
            captionsOn={captionsOn}
            transcriptOn={transcriptOn}
            settingsOpen={settingsOpen}
            text={captionText}
            size={captionSize}
            captionBg={captionBg}
            sourceLang={session?.detected_lang || session?.source_lang || "auto"}
            targetLang={session?.target_lang || "es"}
            volume={volume}
            showVolume={kind === "youtube"}
            fullscreen={fullscreen}
            onCaptions={onCaptions}
            onTranscript={onTranscript}
            onSettings={onSettings}
            onText={onCaptionText}
            onSize={onCaptionSize}
            onCaptionBg={onCaptionBg}
            onCloseSettings={onCloseSettings}
            onVolume={onVolume}
            onFullscreen={() => void toggleFullscreen()}
          />
          </div>
        </div>
      </div>
    </div>
  );
}
