import { useEffect, useId, useRef } from "react";

type YouTubePlayer = {
  getCurrentTime: () => number;
  getDuration: () => number;
  seekTo: (seconds: number, allowSeekAhead: boolean) => void;
  playVideo: () => void;
  pauseVideo: () => void;
  setVolume?: (volume: number) => void;
  mute?: () => void;
  unMute?: () => void;
  destroy: () => void;
};

function applyVolume(player: YouTubePlayer, volume: number) {
  const next = Math.max(0, Math.min(100, Math.round(volume)));
  if (next === 0) {
    player.setVolume?.(0);
    player.mute?.();
    return;
  }
  player.unMute?.();
  player.setVolume?.(next);
}

type PlayerEvent = { target: YouTubePlayer; data?: number };

declare global {
  interface Window {
    YT?: {
      Player: new (element: string | HTMLElement, options: Record<string, unknown>) => YouTubePlayer;
    };
    onYouTubeIframeAPIReady?: () => void;
  }
}

let apiReady: Promise<void> | null = null;

function loadYouTubeApi(): Promise<void> {
  if (window.YT?.Player) return Promise.resolve();
  if (apiReady) return apiReady;
  apiReady = new Promise((resolve) => {
    const previous = window.onYouTubeIframeAPIReady;
    window.onYouTubeIframeAPIReady = () => {
      previous?.();
      resolve();
    };
    if (!document.getElementById("eventlyra-youtube-api")) {
      const script = document.createElement("script");
      script.id = "eventlyra-youtube-api";
      script.src = "https://www.youtube.com/iframe_api";
      document.body.appendChild(script);
    }
  });
  return apiReady;
}

function alignLivePlayer(player: YouTubePlayer, delaySec: number): boolean {
  const duration = player.getDuration();
  if (!Number.isFinite(duration) || duration < delaySec + 2) {
    return false;
  }
  const target = Math.max(0, duration - delaySec);
  if (Math.abs(player.getCurrentTime() - target) > 2) {
    player.seekTo(target, true);
  }
  return true;
}

function holdVodToCaptions(player: YouTubePlayer, readyUntil: number): boolean {
  const time = player.getCurrentTime();
  if (!Number.isFinite(readyUntil) || readyUntil <= 0.3) {
    player.pauseVideo();
    return true;
  }
  if (time > readyUntil - 0.35) {
    player.pauseVideo();
    return true;
  }
  player.playVideo();
  return false;
}

export function YouTubeStage({
  videoId,
  isLive,
  delaySec,
  readyUntil = 0,
  volume = 80,
  onTime,
  onSeekableChange,
  onHoldChange,
}: {
  videoId: string;
  isLive: boolean;
  delaySec: number;
  readyUntil?: number;
  volume?: number;
  onTime?: (time: number) => void;
  onSeekableChange?: (seekable: boolean) => void;
  onHoldChange?: (holding: boolean) => void;
}) {
  const reactId = useId().replace(/:/g, "");
  const hostId = `eventlyra-yt-${reactId}`;
  const playerRef = useRef<YouTubePlayer | null>(null);
  const delayRef = useRef(delaySec);
  const liveRef = useRef(isLive);
  const readyRef = useRef(readyUntil);
  const onTimeRef = useRef(onTime);
  const onSeekableRef = useRef(onSeekableChange);
  const onHoldRef = useRef(onHoldChange);
  const volumeRef = useRef(volume);
  delayRef.current = delaySec;
  liveRef.current = isLive;
  readyRef.current = readyUntil;
  onTimeRef.current = onTime;
  onSeekableRef.current = onSeekableChange;
  onHoldRef.current = onHoldChange;
  volumeRef.current = volume;

  useEffect(() => {
    let cancelled = false;
    let poll: number | undefined;
    void loadYouTubeApi().then(() => {
      if (cancelled || !window.YT?.Player) return;
      const host = document.getElementById(hostId);
      if (!host) return;
      const player = new window.YT.Player(host, {
        videoId,
        width: "100%",
        height: "100%",
        playerVars: {
          autoplay: 1,
          controls: 0,
          cc_load_policy: 0,
          disablekb: 1,
          fs: 0,
          iv_load_policy: 3,
          modestbranding: 1,
          playsinline: 1,
          rel: 0,
          origin: window.location.origin,
        },
        events: {
          onReady: (event: PlayerEvent) => {
            applyVolume(event.target, volumeRef.current);
            if (liveRef.current) {
              event.target.playVideo();
              onSeekableRef.current?.(alignLivePlayer(event.target, delayRef.current));
              return;
            }
            onHoldRef.current?.(holdVodToCaptions(event.target, readyRef.current));
          },
          onStateChange: (event: PlayerEvent) => {
            if (liveRef.current && event.data === 1) {
              onSeekableRef.current?.(alignLivePlayer(event.target, delayRef.current));
            }
          },
        },
      });
      playerRef.current = player;
      poll = window.setInterval(() => {
        const current = playerRef.current;
        if (!current) return;
        if (liveRef.current) {
          onSeekableRef.current?.(alignLivePlayer(current, delayRef.current));
          return;
        }
        const time = current.getCurrentTime();
        onTimeRef.current?.(time);
        onHoldRef.current?.(holdVodToCaptions(current, readyRef.current));
      }, 250);
    });
    return () => {
      cancelled = true;
      if (poll) window.clearInterval(poll);
      playerRef.current?.destroy();
      playerRef.current = null;
    };
  }, [hostId, videoId]);

  useEffect(() => {
    const player = playerRef.current;
    if (!player) return;
    applyVolume(player, volume);
  }, [volume]);

  return (
    <div className="pointer-events-none aspect-video w-full bg-black">
      <div id={hostId} className="h-full w-full" />
    </div>
  );
}
