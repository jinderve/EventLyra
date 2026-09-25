# EventLyra

Subtítulos para varias sesiones de una charla, en un solo proceso local. Cada sesión transcribe el audio original (español o inglés) y muestra la traducción encima del video o del audio. Las sesiones comparten una sola copia de los modelos en la GPU.

Este corte cubre archivo y micrófono. El código es MIT. Los pesos de Gemma no van en el repositorio y se rigen por su propia licencia.

## Qué usa este corte

| Pieza | Modelo | Cómo entra en 12 GB |
| --- | --- | --- |
| Transcripción | faster-whisper `turbo` (`mobiuslabsgmbh/faster-whisper-large-v3-turbo`) | `compute_type=int8_float16` (INT8 en GPU) |
| Traducción | `google/translategemma-4b-it` | 8-bit con bitsandbytes, una sola copia en la GPU 0 |

La traducción pasa por una interfaz reemplazable (`eventlyra/engine/translator.py`). El único proveedor implementado es `local`. No hay cliente de Vertex, Gemini ni GCP.

## PC donde corre el demo

- Windows
- NVIDIA RTX 4070 SUPER (12 GB) con el driver al día
- Python 3.11 o 3.12
- Espacio en `E:\` para el entorno virtual y para `HF_HOME`

El intérprete de Python puede vivir en el perfil del usuario. El venv y los pesos no: el script los deja en `E:\EventLyra\venv` y `E:\EventLyra\hf-home`.

## Credenciales

1. Creá una cuenta en [huggingface.co/join](https://huggingface.co/join).
2. Aceptá la licencia Gemma en [google/translategemma-4b-it](https://huggingface.co/google/translategemma-4b-it).
3. Creá un token de lectura en [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens).
4. `scripts/setup-windows.ps1` pide `huggingface-cli login`. El token lo guarda el CLI de Hugging Face, fuera del git. No lo copies a un `.env` versionado ni al repositorio.

Sin esa cuenta y sin la licencia aceptada, el 4B no se puede bajar y no hay subtítulos reales.

## Modelos que hay que bajar

Solo estos dos, y los baja el script de setup (no los subas al git):

- `google/translategemma-4b-it` (el 4B; no el 12B ni el 27B)
- `mobiuslabsgmbh/faster-whisper-large-v3-turbo` (el alias `turbo` de faster-whisper)

## Setup en Windows

En PowerShell, desde el repositorio:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup-windows.ps1
```

El script:

1. Rechaza poner el venv, `HF_HOME` o el directorio de trabajo en `C:\`.
2. Crea `E:\EventLyra\venv`, `E:\EventLyra\hf-home` y `E:\EventLyra\work`.
3. Instala las dependencias y después torch desde `https://download.pytorch.org/whl/cu128`, para que no quede la rueda de CPU.
4. Instala ffmpeg con winget si falta.
5. Pide el login de Hugging Face y baja solo el 4B y el turbo.
6. Corta si `torch.cuda.is_available()` es falso.

## Cómo correr

K es la cantidad de sesiones de **este** proceso. No tiene valor oculto: hay que pasarlo.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run-windows.ps1 -SessionsPerGpu 2
```

Abrí http://127.0.0.1:8000

Para ver las dos sesiones a la vez, abrí esa dirección en dos ventanas. En cada una elegí una sesión distinta, el idioma original (detectar, español o inglés) y la traducción (español o inglés). Cargá un video o un audio, o usá el micrófono. El original y la traducción se dibujan sobre el reproductor.

El camino de evaluación es la transcripción en español o inglés y la traducción de inglés a español. Español a inglés usa el mismo modelo.

El arranque con modelos carga los pesos una vez. El log lo dice, y `GET /api/health` muestra un solo `asr_id` y un solo `translator_id` para todas las sesiones. La GPU procesa los fragmentos en serie: las sesiones comparten pesos, no se duplican en VRAM.

Sin GPU se puede abrir la interfaz, pero no hay subtítulos:

```powershell
python -m eventlyra --sessions-per-gpu 2 --sin-modelos
```

Ese modo responde 503 cuando se le manda audio.

## De 2 sesiones a más

K es `-SessionsPerGpu` / `--sessions-per-gpu`.

- Misma GPU, mismo proceso: subí K. Las sesiones siguen usando la misma copia de faster-whisper y la misma copia de TranslateGemma. La cola de la GPU reparte el tiempo. Si la memoria se queda corta por las activaciones, bajá K.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run-windows.ps1 -SessionsPerGpu 4
```

- Más sesiones que las que esa GPU puede atender: levantá el mismo API en otra GPU o en otra máquina, cada una con su propio K. Una GPU atiende K sesiones.

## Audios de prueba

No hay audios grandes en el git. Para armar uno:

```powershell
python scripts\preparar-muestra.py D:\charla.mp4 --nombre sesion-1
```

Queda `samples/sesion-1.wav` (mono, 16 kHz), ignorado por git. Cargalo desde la interfaz. El detalle está en `samples/README.md`.

## Desarrollo

Las pruebas de este repositorio no cargan los modelos:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest
```

## Licencia

El código de este repositorio está bajo MIT. Ver `LICENSE`.

Los pesos de TranslateGemma se descargan aparte y quedan sujetos a la licencia de Gemma: https://ai.google.dev/gemma/terms y la página del modelo en Hugging Face. faster-whisper turbo deriva de Whisper (MIT) en formato CTranslate2.
