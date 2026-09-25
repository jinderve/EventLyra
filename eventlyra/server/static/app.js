const sesionSelect = document.querySelector("#sesion");
const origenSelect = document.querySelector("#origen");
const destinoSelect = document.querySelector("#destino");
const archivoInput = document.querySelector("#archivo");
const microfonoButton = document.querySelector("#microfono");
const aviso = document.querySelector("#aviso");
const estado = document.querySelector("#estado");
const capacidad = document.querySelector("#capacidad");
const video = document.querySelector("#video");
const audio = document.querySelector("#audio");
const lienzo = document.querySelector("#lienzo");
const lineaOriginal = document.querySelector("#linea-original");
const lineaTraduccion = document.querySelector("#linea-traduccion");
const historial = document.querySelector("#historial");

const state = {
  chunkSeconds: 8,
  modelosCargados: false,
  cues: [],
  generacion: 0,
  eventos: null,
  media: null,
  mic: null,
};

function sesionActual() {
  return sesionSelect.value;
}

function mostrarAviso(texto) {
  if (!texto) {
    aviso.hidden = true;
    aviso.textContent = "";
    return;
  }
  aviso.hidden = false;
  aviso.textContent = texto;
}

function formatoTiempo(segundos) {
  const total = Math.max(0, Math.floor(segundos));
  const minutos = String(Math.floor(total / 60)).padStart(2, "0");
  const resto = String(total % 60).padStart(2, "0");
  return `${minutos}:${resto}`;
}

function pintarEstado(texto) {
  estado.textContent = texto;
}

function cueEn(tiempo) {
  let elegido = null;
  for (const cue of state.cues) {
    if (tiempo + 0.05 >= cue.inicio && tiempo <= cue.fin + 0.35) {
      if (!elegido || cue.inicio >= elegido.inicio) {
        elegido = cue;
      }
    }
  }
  return elegido;
}

function pintarSubtitulo(cue) {
  lineaOriginal.textContent = cue ? cue.original : "";
  lineaTraduccion.textContent = cue ? cue.traduccion : "";
}

function pintarHistorial() {
  historial.replaceChildren();
  const ordenados = [...state.cues].sort((a, b) => a.inicio - b.inicio || a.indice - b.indice);
  for (const cue of ordenados) {
    const item = document.createElement("li");
    const tiempo = document.createElement("span");
    tiempo.textContent = `${formatoTiempo(cue.inicio)} · ${cue.idioma_origen} → ${cue.idioma_destino}`;
    item.append(tiempo, document.createTextNode(cue.original));
    const traduccion = document.createElement("div");
    traduccion.textContent = cue.traduccion;
    item.append(traduccion);
    historial.append(item);
  }
}

function pintarDesdeReloj() {
  if (state.mic) {
    pintarSubtitulo(state.cues[state.cues.length - 1] || null);
    return;
  }
  if (state.media && state.media.src) {
    pintarSubtitulo(cueEn(state.media.currentTime));
    return;
  }
  pintarSubtitulo(null);
}

function reemplazarMedio(elemento, file) {
  if (state.media && state.media.src) {
    URL.revokeObjectURL(state.media.src);
  }
  video.hidden = true;
  audio.hidden = true;
  video.removeAttribute("src");
  audio.removeAttribute("src");
  const url = URL.createObjectURL(file);
  elemento.hidden = false;
  elemento.src = url;
  state.media = elemento;
  lienzo.hidden = true;
  elemento.load();
}

async function leerJson(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data.detail || "La solicitud no se completó.";
    throw new Error(typeof detail === "string" ? detail : "La solicitud no se completó.");
  }
  return data;
}

async function sincronizarIdioma() {
  await leerJson(await fetch(`/api/sessions/${sesionActual()}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      idioma_origen: origenSelect.value,
      idioma_destino: destinoSelect.value,
    }),
  }));
}

function cerrarEventos() {
  if (state.eventos) {
    state.eventos.close();
    state.eventos = null;
  }
}

function abrirEventos() {
  cerrarEventos();
  state.cues = [];
  pintarHistorial();
  pintarDesdeReloj();
  const fuente = new EventSource(`/api/sessions/${sesionActual()}/eventos`);
  state.eventos = fuente;
  fuente.addEventListener("cue", (event) => {
    const cue = JSON.parse(event.data);
    if (cue.generacion !== state.generacion) {
      state.generacion = cue.generacion;
      state.cues = [];
    }
    if (!state.cues.some((item) => item.indice === cue.indice && item.generacion === cue.generacion)) {
      state.cues.push(cue);
      pintarHistorial();
      pintarDesdeReloj();
    }
  });
  fuente.addEventListener("estado", (event) => {
    const data = JSON.parse(event.data);
    if (data.generacion !== state.generacion) {
      state.generacion = data.generacion;
      state.cues = [];
      pintarHistorial();
      pintarDesdeReloj();
    }
    const detalle = data.error ? ` ${data.error}` : "";
    pintarEstado(`Sesión ${sesionActual()}: ${data.estado}.${detalle}`);
    if (data.estado === "error" && data.error) {
      mostrarAviso(data.error);
    }
  });
}

async function cargarSesion() {
  const data = await leerJson(await fetch(`/api/sessions/${sesionActual()}`));
  origenSelect.value = data.idioma_origen;
  destinoSelect.value = data.idioma_destino;
  state.generacion = data.generacion;
  state.cues = data.cues;
  pintarHistorial();
  pintarDesdeReloj();
  pintarEstado(`Sesión ${data.id}: ${data.estado}.`);
  abrirEventos();
}

function detenerMicrofono() {
  if (!state.mic) {
    return;
  }
  const { context, processor, source, stream, gain, flush } = state.mic;
  flush();
  processor.onaudioprocess = null;
  source.disconnect();
  processor.disconnect();
  gain.disconnect();
  stream.getTracks().forEach((track) => track.stop());
  context.close();
  state.mic = null;
  microfonoButton.textContent = "Usar micrófono";
  microfonoButton.setAttribute("aria-pressed", "false");
}

function unirCanales(partes, total) {
  const merged = new Float32Array(total);
  let offset = 0;
  for (const parte of partes) {
    merged.set(parte, offset);
    offset += parte.length;
  }
  return merged;
}

function floatAInt16(muestras) {
  const pcm = new Int16Array(muestras.length);
  for (let i = 0; i < muestras.length; i += 1) {
    const sample = Math.max(-1, Math.min(1, muestras[i]));
    pcm[i] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
  }
  return pcm;
}

async function enviarPcm(muestras, sampleRate, inicio) {
  const pcm = floatAInt16(muestras);
  const params = new URLSearchParams({
    sample_rate: String(sampleRate),
    inicio: String(inicio),
  });
  const response = await fetch(`/api/sessions/${sesionActual()}/pcm?${params}`, {
    method: "POST",
    headers: { "Content-Type": "application/octet-stream" },
    body: pcm.buffer,
  });
  await leerJson(response);
}

async function iniciarMicrofono() {
  detenerMicrofono();
  await sincronizarIdioma();
  await leerJson(await fetch(`/api/sessions/${sesionActual()}/reiniciar`, { method: "POST" }));
  state.cues = [];
  pintarHistorial();
  pintarDesdeReloj();
  state.media = null;
  video.hidden = true;
  audio.hidden = true;
  lienzo.hidden = false;
  lienzo.firstElementChild.textContent = "Micrófono en vivo. La traducción aparece abajo.";
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const context = new AudioContext();
  const source = context.createMediaStreamSource(stream);
  const processor = context.createScriptProcessor(4096, 1, 1);
  const gain = context.createGain();
  gain.gain.value = 0;
  const sampleRate = context.sampleRate;
  let partes = [];
  let total = 0;
  let offset = 0;

  function tomarBuffer() {
    if (!total) {
      return null;
    }
    const merged = unirCanales(partes, total);
    const inicio = offset;
    offset += merged.length / sampleRate;
    partes = [];
    total = 0;
    return { merged, inicio };
  }

  function flush() {
    const tomado = tomarBuffer();
    if (tomado && tomado.merged.length > sampleRate * 0.3) {
      enviarPcm(tomado.merged, sampleRate, tomado.inicio).catch((error) => {
        mostrarAviso(error.message);
      });
    }
  }

  processor.onaudioprocess = (event) => {
    const canal = event.inputBuffer.getChannelData(0);
    partes.push(new Float32Array(canal));
    total += canal.length;
    if (total >= sampleRate * state.chunkSeconds) {
      const tomado = tomarBuffer();
      if (tomado) {
        enviarPcm(tomado.merged, sampleRate, tomado.inicio).catch((error) => {
          mostrarAviso(error.message);
        });
      }
    }
  };

  source.connect(processor);
  processor.connect(gain);
  gain.connect(context.destination);
  state.mic = { context, processor, source, stream, gain, flush };
  microfonoButton.textContent = "Detener micrófono";
  microfonoButton.setAttribute("aria-pressed", "true");
  pintarEstado(`Sesión ${sesionActual()}: escuchando el micrófono.`);
}

archivoInput.addEventListener("change", async () => {
  const file = archivoInput.files && archivoInput.files[0];
  if (!file) {
    return;
  }
  detenerMicrofono();
  mostrarAviso("");
  try {
    await sincronizarIdioma();
    state.cues = [];
    pintarHistorial();
    pintarDesdeReloj();
    const esVideo = (file.type || "").startsWith("video/") || /\.(mp4|mkv|webm|mov)$/i.test(file.name);
    reemplazarMedio(esVideo ? video : audio, file);
    if (!esVideo) {
      lienzo.hidden = false;
      lienzo.firstElementChild.textContent = file.name;
    }
    pintarEstado(`Sesión ${sesionActual()}: se está enviando el archivo.`);
    const form = new FormData();
    form.append("archivo", file, file.name);
    const response = await fetch(`/api/sessions/${sesionActual()}/archivo`, {
      method: "POST",
      body: form,
    });
    const data = await leerJson(response);
    pintarEstado(`Sesión ${sesionActual()}: ${data.fragmentos} fragmentos en la cola compartida.`);
  } catch (error) {
    mostrarAviso(error.message);
    pintarEstado("No se pudo procesar el archivo.");
  }
});

microfonoButton.addEventListener("click", async () => {
  mostrarAviso("");
  try {
    if (state.mic) {
      detenerMicrofono();
      pintarEstado(`Sesión ${sesionActual()}: micrófono detenido.`);
      return;
    }
    await iniciarMicrofono();
  } catch (error) {
    detenerMicrofono();
    mostrarAviso(error.message || "No se pudo usar el micrófono.");
  }
});

sesionSelect.addEventListener("change", () => {
  detenerMicrofono();
  cargarSesion().catch((error) => mostrarAviso(error.message));
});

for (const select of [origenSelect, destinoSelect]) {
  select.addEventListener("change", () => {
    sincronizarIdioma().catch((error) => mostrarAviso(error.message));
  });
}

for (const medio of [video, audio]) {
  medio.addEventListener("timeupdate", pintarDesdeReloj);
  medio.addEventListener("seeked", pintarDesdeReloj);
}

async function iniciar() {
  const salud = await leerJson(await fetch("/api/health"));
  state.chunkSeconds = salud.chunk_seconds;
  state.modelosCargados = salud.modelos_cargados;
  capacidad.textContent = salud.modelos_cargados
    ? `Este proceso atiende ${salud.sessions_per_gpu} sesiones (K) con una sola copia de los modelos.`
    : `K = ${salud.sessions_per_gpu}. ${salud.mensaje}`;
  if (!salud.modelos_cargados) {
    mostrarAviso(salud.mensaje);
  }
  const listado = await leerJson(await fetch("/api/sessions"));
  sesionSelect.replaceChildren();
  for (const sesion of listado.sesiones) {
    const option = document.createElement("option");
    option.value = sesion.id;
    option.textContent = `Sesión ${sesion.id}`;
    sesionSelect.append(option);
  }
  await cargarSesion();
}

iniciar().catch((error) => mostrarAviso(error.message));
