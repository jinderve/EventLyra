const params = new URLSearchParams(window.location.search);
const sesion = params.get("sesion") || "1";
const lineaOriginal = document.querySelector("#linea-original");
const lineaTraduccion = document.querySelector("#linea-traduccion");

let cues = [];
let generacion = 0;

function cueVivo() {
  if (!cues.length) {
    return null;
  }
  return cues[cues.length - 1];
}

function pintar(cue) {
  lineaOriginal.textContent = cue ? cue.original : "";
  lineaTraduccion.textContent = cue ? cue.traduccion : "";
}

const fuente = new EventSource(`/api/sessions/${sesion}/eventos`);
fuente.addEventListener("cue", (event) => {
  const cue = JSON.parse(event.data);
  if (cue.generacion !== generacion) {
    generacion = cue.generacion;
    cues = [];
  }
  if (!cues.some((item) => item.indice === cue.indice && item.generacion === cue.generacion)) {
    cues.push(cue);
    pintar(cueVivo());
  }
});
fuente.addEventListener("estado", (event) => {
  const data = JSON.parse(event.data);
  if (data.generacion !== generacion) {
    generacion = data.generacion;
    cues = [];
    pintar(null);
  }
});
