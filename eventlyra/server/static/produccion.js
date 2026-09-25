const resumen = document.querySelector("#resumen");
const cuerpo = document.querySelector("#tabla tbody");

function celda(texto) {
  const td = document.createElement("td");
  td.textContent = texto == null || texto === "" ? "—" : String(texto);
  return td;
}

async function refrescar() {
  const response = await fetch("/api/produccion");
  const data = await response.json();
  const ids = data.modelos_cargados
    ? `asr ${data.asr_id} · traductor ${data.translator_id}`
    : "modelos no cargados";
  resumen.textContent = (
    `K=${data.sessions_per_gpu}. ${ids}. Cola total ${data.cola_total}. `
    + `Última latencia ${data.ultima_latencia_ms == null ? "—" : data.ultima_latencia_ms + " ms"}.`
  );
  cuerpo.replaceChildren();
  for (const sesion of data.sesiones) {
    const tr = document.createElement("tr");
    tr.append(
      celda(sesion.id),
      celda(sesion.titulo),
      celda(sesion.sala),
      celda(`${sesion.idioma_origen} → ${sesion.idioma_destino}`),
      celda(sesion.estado),
      celda(sesion.cola),
      celda(sesion.cues),
      celda(sesion.latencia_ms == null ? null : `${sesion.latencia_ms} ms`),
      celda(sesion.error),
    );
    cuerpo.append(tr);
  }
}

refrescar().catch((error) => {
  resumen.textContent = error.message;
});
setInterval(() => {
  refrescar().catch(() => {});
}, 1000);
