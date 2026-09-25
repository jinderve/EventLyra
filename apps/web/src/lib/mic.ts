import { startSessionMic, stopSession, uploadPcm } from "./api";

type MicHandle = {
  stop: () => void;
};

type CaptureAudioData = {
  numberOfFrames: number;
  sampleRate: number;
  copyTo: (destination: Float32Array, options: { planeIndex: number; format?: string }) => void;
  close: () => void;
};

type TrackProcessorCtor = new (init: { track: MediaStreamTrack }) => {
  readable: ReadableStream<CaptureAudioData>;
};

const SILENCE_RMS = 0.001;

function floatToInt16(samples: Float32Array) {
  const pcm = new Int16Array(samples.length);
  for (let index = 0; index < samples.length; index += 1) {
    const sample = Math.max(-1, Math.min(1, samples[index]));
    pcm[index] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
  }
  return pcm;
}

function rms(samples: Float32Array) {
  if (!samples.length) return 0;
  let sum = 0;
  for (let index = 0; index < samples.length; index += 1) {
    sum += samples[index] * samples[index];
  }
  return Math.sqrt(sum / samples.length);
}

function looksLikeRealMic(label: string) {
  return !/stereo mix|what u hear|loopback|cable output|virtual cable|vb-audio/i.test(label);
}

const micConstraints = {
  channelCount: 1,
  echoCancellation: false,
  noiseSuppression: false,
  autoGainControl: true,
} as const;

async function openMicrophone(): Promise<MediaStream> {
  const first = await navigator.mediaDevices.getUserMedia({ audio: { ...micConstraints } });
  try {
    const devices = await navigator.mediaDevices.enumerateDevices();
    const inputs = devices.filter((device) => device.kind === "audioinput");
    const currentId = first.getAudioTracks()[0]?.getSettings().deviceId;
    const current = inputs.find((device) => device.deviceId === currentId);
    if (!current || looksLikeRealMic(current.label)) return first;
    const preferred = inputs.find((device) => looksLikeRealMic(device.label));
    if (!preferred) return first;
    first.getTracks().forEach((track) => track.stop());
    return navigator.mediaDevices.getUserMedia({
      audio: { ...micConstraints, deviceId: { exact: preferred.deviceId } },
    });
  } catch {
    return first;
  }
}

function trackProcessorCtor(): TrackProcessorCtor | null {
  const ctor = (window as unknown as { MediaStreamTrackProcessor?: TrackProcessorCtor }).MediaStreamTrackProcessor;
  return ctor ?? null;
}

export async function startMicrophone(
  sessionId: string,
  chunkSeconds: number,
  onError: (message: string | null) => void,
): Promise<MicHandle> {
  await startSessionMic(sessionId);
  let stream: MediaStream;
  try {
    stream = await openMicrophone();
  } catch (error) {
    await stopSession(sessionId).catch(() => undefined);
    throw new Error(
      error instanceof Error && error.name === "NotAllowedError"
        ? "Microphone permission was denied."
        : "Could not open the microphone.",
    );
  }
  const liveTrack = stream.getAudioTracks()[0];
  if (!liveTrack || liveTrack.readyState !== "live") {
    stream.getTracks().forEach((track) => track.stop());
    await stopSession(sessionId).catch(() => undefined);
    throw new Error("The microphone is not live. Check the Windows input device.");
  }

  let parts: Float32Array[] = [];
  let total = 0;
  let offset = 0;
  let sampleRate = liveTrack.getSettings().sampleRate || 48000;
  let stopped = false;
  let silentChunks = 0;
  let context: AudioContext | null = null;
  let workletNode: AudioWorkletNode | null = null;
  let scriptNode: ScriptProcessorNode | null = null;
  let sourceNode: MediaStreamAudioSourceNode | null = null;
  let reader: ReadableStreamDefaultReader<CaptureAudioData> | null = null;

  function takeBuffer() {
    if (!total) return null;
    const merged = new Float32Array(total);
    let cursor = 0;
    for (const part of parts) {
      merged.set(part, cursor);
      cursor += part.length;
    }
    const start = offset;
    offset += merged.length / sampleRate;
    parts = [];
    total = 0;
    return { merged, start };
  }

  function send(merged: Float32Array, start: number) {
    const level = rms(merged);
    if (level < SILENCE_RMS) {
      silentChunks += 1;
      if (silentChunks === 2) {
        const label = liveTrack.label || "default input";
        onError(
          `The microphone "${label}" is open, but no voice is reaching EventLyra. Switch the Windows input device and speak closer.`,
        );
      }
    } else {
      silentChunks = 0;
      onError(null);
    }
    const pcm = floatToInt16(merged);
    const bytes = pcm.buffer.slice(pcm.byteOffset, pcm.byteOffset + pcm.byteLength);
    void uploadPcm(sessionId, bytes, sampleRate, start).catch((error: Error) => {
      onError(error.message);
    });
  }

  function ingest(channel: Float32Array, rate?: number) {
    if (stopped) return;
    if (rate && rate !== sampleRate && !total) sampleRate = rate;
    parts.push(new Float32Array(channel));
    total += channel.length;
    if (total >= sampleRate * chunkSeconds) {
      const taken = takeBuffer();
      if (taken && taken.merged.length > sampleRate * 0.3) {
        send(taken.merged, taken.start);
      }
    }
  }

  function stopGraph() {
    stopped = true;
    const leftover = takeBuffer();
    if (leftover && leftover.merged.length > sampleRate * 0.3) {
      send(leftover.merged, leftover.start);
    }
    void reader?.cancel().catch(() => undefined);
    scriptNode?.disconnect();
    workletNode?.disconnect();
    sourceNode?.disconnect();
    if (context) void context.close();
    stream.getTracks().forEach((track) => track.stop());
  }

  const Processor = trackProcessorCtor();
  if (Processor) {
    const processor = new Processor({ track: liveTrack });
    reader = processor.readable.getReader();
    void (async () => {
      try {
        while (!stopped) {
          const { value, done } = await reader.read();
          if (done || !value) break;
          const samples = new Float32Array(value.numberOfFrames);
          try {
            value.copyTo(samples, { planeIndex: 0, format: "f32" });
          } catch {
            value.copyTo(samples, { planeIndex: 0 });
          }
          const rate = value.sampleRate;
          value.close();
          ingest(samples, rate);
        }
      } catch {
        /* reader cancelled or track ended */
      }
    })();
    return { stop: stopGraph };
  }

  context = new AudioContext();
  if (context.state === "suspended") await context.resume();
  if (context.state !== "running") {
    stopGraph();
    await stopSession(sessionId).catch(() => undefined);
    throw new Error("The browser kept the microphone graph suspended. Click Start live again.");
  }
  sampleRate = context.sampleRate;
  sourceNode = context.createMediaStreamSource(stream);
  const keepAlive = context.createGain();
  keepAlive.gain.value = 0.0001;

  try {
    const workletSource = `class EventLyraCapture extends AudioWorkletProcessor {
  process(inputs) {
    const channel = inputs[0] && inputs[0][0];
    if (channel && channel.length) this.port.postMessage(channel.slice());
    return true;
  }
}
registerProcessor("eventlyra-capture", EventLyraCapture);`;
    const blob = new Blob([workletSource], { type: "application/javascript" });
    const url = URL.createObjectURL(blob);
    await context.audioWorklet.addModule(url);
    URL.revokeObjectURL(url);
    workletNode = new AudioWorkletNode(context, "eventlyra-capture");
    workletNode.port.onmessage = (event: MessageEvent<Float32Array>) => ingest(event.data);
    sourceNode.connect(workletNode);
    workletNode.connect(keepAlive);
    keepAlive.connect(context.destination);
  } catch {
    scriptNode = context.createScriptProcessor(4096, 1, 1);
    scriptNode.onaudioprocess = (event) => {
      ingest(event.inputBuffer.getChannelData(0));
    };
    sourceNode.connect(scriptNode);
    scriptNode.connect(keepAlive);
    keepAlive.connect(context.destination);
  }

  return { stop: stopGraph };
}
