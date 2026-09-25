import { resetSession, uploadPcm } from "./api";

type MicHandle = {
  stop: () => void;
};

function floatToInt16(samples: Float32Array) {
  const pcm = new Int16Array(samples.length);
  for (let index = 0; index < samples.length; index += 1) {
    const sample = Math.max(-1, Math.min(1, samples[index]));
    pcm[index] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
  }
  return pcm;
}

export async function startMicrophone(
  sessionId: string,
  chunkSeconds: number,
  onError: (message: string) => void,
): Promise<MicHandle> {
  await resetSession(sessionId);
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const context = new AudioContext();
  const source = context.createMediaStreamSource(stream);
  const processor = context.createScriptProcessor(4096, 1, 1);
  const gain = context.createGain();
  gain.gain.value = 0;
  const sampleRate = context.sampleRate;
  let parts: Float32Array[] = [];
  let total = 0;
  let offset = 0;
  let stopped = false;

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
    const pcm = floatToInt16(merged);
    void uploadPcm(sessionId, pcm.buffer, sampleRate, start).catch((error: Error) => {
      onError(error.message);
    });
  }

  processor.onaudioprocess = (event) => {
    if (stopped) return;
    const channel = event.inputBuffer.getChannelData(0);
    parts.push(new Float32Array(channel));
    total += channel.length;
    if (total >= sampleRate * chunkSeconds) {
      const taken = takeBuffer();
      if (taken && taken.merged.length > sampleRate * 0.3) {
        send(taken.merged, taken.start);
      }
    }
  };

  source.connect(processor);
  processor.connect(gain);
  gain.connect(context.destination);

  return {
    stop() {
      stopped = true;
      const leftover = takeBuffer();
      if (leftover && leftover.merged.length > sampleRate * 0.3) {
        send(leftover.merged, leftover.start);
      }
      processor.disconnect();
      source.disconnect();
      void context.close();
      stream.getTracks().forEach((track) => track.stop());
    },
  };
}
